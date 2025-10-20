# fraudshield/src/services/detector/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.common.db import engine, Base
from src.common.config import settings

# Import API routers
from src.services.detector.api.endpoints_v1 import router as v1_router
from src.services.detector.api.health import router as health_router

# Import ALL ORM models to ensure SQLAlchemy knows about them for `Base.metadata.create_all`
# This is crucial if you intend to use `create_all` for development
import src.models.payment_models
import src.models.user_models
import src.models.fraud_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI application.
    """
    # --- Startup events ---
    print(f"[{datetime.utcnow().isoformat()}] Detector service starting...")
    
    # In a production environment, use Alembic for migrations.
    # For development/initial setup, you can uncomment this to create tables automatically.
    # Be careful with this in production as it won't handle schema changes gracefully.
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    # print(f"[{datetime.utcnow().isoformat()}] Database tables checked/created (if create_all was enabled).")

    yield # Application runs here

    # --- Shutdown events ---
    print(f"[{datetime.utcnow().isoformat()}] Detector service shutting down...")


# Initialize the FastAPI application
app = FastAPI(
    title="FraudShield Detector API",
    version="1.0.0",
    description="API for ingesting payments and querying fraud status in real-time.",
    lifespan=lifespan # Attach the lifespan context manager
)

# Include API routers
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(v1_router, prefix="/api/v1", tags=["API v1"])

# Main execution block for development
if __name__ == "__main__":
    import uvicorn
    # This assumes you are running from the project root: fraudshield-project
    # The app is located at src/services/detector/main.py
    uvicorn.run(
        "src.services.detector.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True  # For development, watches for code changes
    )