# fraudshield/src/services/detector/api/health.py

from fastapi import APIRouter, status

router = APIRouter()

@router.get("", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint to verify the service is running.
    """
    return {"status": "ok", "message": "FraudShield Detector API is running!"}