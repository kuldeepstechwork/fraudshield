"""Load test script for FraudShield detector endpoint.

Sends mixed payment payloads to /api/v1/payments/ to exercise fraud rules and stress Kafka.

Usage:
    python src/services/producer_cli/load_test.py --concurrency 50 --total 1000 --rate 200

This uses httpx and asyncio to send requests concurrently. It produces a mix of scenarios:
- normal
- high value
- very high value
- high risk country
- country mismatch
- rapid transactions (bursts)
- ip velocity (multiple requests from same IP)
- card reuse across many users

The script reports successes/failures and basic latency stats.
"""

import asyncio
import random
import uuid
import argparse
import time
import statistics

import httpx

BASE_URL = "http://localhost:8000/api/v1/payments/"

# Reuse some IDs from your data or generate new ones
DEFAULT_MERCHANT = "3e8f4099-4c8d-4bf0-b392-c85de5fac85b"
KNOWN_USER = "cba83bd5-ba0b-4a15-ba04-4efdc87431d2"

# Mix of IPs to emulate traffic
IP_POOL = [
    "192.168.2.2",
    "203.0.113.10",
    "203.0.113.11",
    "198.51.100.5",
    "203.0.113.45",
    "192.0.2.50",
    "198.51.100.10",
]

CARD_LAST4_POOL = ["1111","2222","3333","4444","5555","6666","7777","8888","9999"]

SCENARIOS = [
    "normal",
    "high_value",
    "very_high_value",
    "high_risk_country",
    "country_mismatch",
    "rapid_user",
    "ip_velocity",
    "card_reuse",
]


def build_payload(scenario: str, user_id: str = None, card_last_four: str = None, ip: str = None):
    uid = user_id or str(uuid.uuid4())
    payload = {
        "transaction_id": str(uuid.uuid4()),
        "idempotency_key": str(uuid.uuid4()),
        "user_id": uid,
        "merchant_id": DEFAULT_MERCHANT,
        "amount": 10,
        "currency": "USD",
        "payment_method": "credit_card",
        "card_type": "standard",
        "card_last_four": card_last_four or random.choice(CARD_LAST4_POOL),
        "transaction_type": "sale",
        "ip_address": ip or random.choice(IP_POOL),
        "device_fingerprint": "test-device-fingerprint",
        "country": "US",
    }

    if scenario == "normal":
        payload["amount"] = round(random.uniform(1, 50), 2)
    elif scenario == "high_value":
        payload["amount"] = round(random.uniform(1000, 2000), 2)
    elif scenario == "very_high_value":
        payload["amount"] = round(random.uniform(5000, 15000), 2)
    elif scenario == "high_risk_country":
        payload["amount"] = round(random.uniform(1, 200), 2)
        payload["country"] = "NG"
        payload["ip_address"] = ip or "198.51.100.5"
    elif scenario == "country_mismatch":
        payload["amount"] = round(random.uniform(1, 200), 2)
        payload["country"] = "US" if random.random() < 0.5 else "GB"
        # choose a user likely to have different country (use KNOWN_USER to test mismatch)
        payload["user_id"] = KNOWN_USER
    elif scenario == "rapid_user":
        payload["amount"] = round(random.uniform(1, 10), 2)
        payload["user_id"] = KNOWN_USER
    elif scenario == "ip_velocity":
        payload["amount"] = round(random.uniform(1, 20), 2)
        payload["ip_address"] = "203.0.113.45"
    elif scenario == "card_reuse":
        payload["amount"] = round(random.uniform(1, 30), 2)
        # allow caller to pass card_last_four, else pick a common one
        payload["card_last_four"] = card_last_four or "9999"
    return payload


async def worker(job_q: asyncio.Queue, results: list, client: httpx.AsyncClient):
    while True:
        job = await job_q.get()
        if job is None:
            job_q.task_done()
            break
        scenario, user_id, card_last_four, ip = job
        payload = build_payload(scenario, user_id=user_id, card_last_four=card_last_four, ip=ip)
        start = time.monotonic()
        try:
            headers = {"X-API-Key": "dev-secret-key"}
            r = await client.post(BASE_URL, json=payload, headers=headers, timeout=10)
            latency = time.monotonic() - start
            results.append((r.status_code, latency, scenario, payload))
        except Exception as e:
            latency = time.monotonic() - start
            results.append((None, latency, scenario, str(e)))
        job_q.task_done()


async def run_load_test(total: int, concurrency: int, rate: int):
    job_q = asyncio.Queue()
    results = []
    client = httpx.AsyncClient()

    # Prepare jobs: random mix of scenarios, but ensure we include bursts for rapid_user and ip_velocity
    for i in range(total):
        scenario = random.choices(SCENARIOS, weights=[40,10,5,5,5,10,10,15])[0]
        # for card reuse, choose a shared last4 occasionally
        card_last_four = None
        user_id = None
        ip = None
        if scenario == "card_reuse":
            card_last_four = "9999"
            user_id = str(uuid.uuid4())
        elif scenario == "rapid_user":
            user_id = KNOWN_USER
        elif scenario == "ip_velocity":
            ip = "203.0.113.45"
            user_id = str(uuid.uuid4())
        job_q.put_nowait((scenario, user_id, card_last_four, ip))

    # Add stop signals
    for _ in range(concurrency):
        job_q.put_nowait(None)

    workers = [asyncio.create_task(worker(job_q, results, client)) for _ in range(concurrency)]

    # Rate limiting: dispatch at approximately `rate` requests/sec by sleeping between batches
    # But here we already enqueued jobs; if you want precise pacing implement a producer that enqueues.

    start_time = time.monotonic()
    await job_q.join()
    elapsed = time.monotonic() - start_time

    # Cancel workers
    for w in workers:
        w.cancel()
    await client.aclose()

    # Summarize results
    statuses = [r[0] for r in results]
    latencies = [r[1] for r in results if r[1] is not None]
    ok = sum(1 for s in statuses if s and 200 <= s < 300)
    errs = len(results) - ok
    print(f"Total requests: {len(results)}, OK: {ok}, Errors: {errs}")
    if latencies:
        print(f"Latency ms p50/ p90/ p99: {statistics.median(latencies)*1000:.1f} / {statistics.quantiles(latencies, n=10)[8]*1000:.1f} / {max(latencies)*1000:.1f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--total", type=int, default=200, help="Total number of requests")
    parser.add_argument("--concurrency", type=int, default=20, help="Number of concurrent workers")
    parser.add_argument("--rate", type=int, default=0, help="Target requests per second (0=unlimited)")
    args = parser.parse_args()

    asyncio.run(run_load_test(args.total, args.concurrency, args.rate))


if __name__ == "__main__":
    main()
