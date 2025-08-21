import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.utils.types import (
    HealthResponse,
    StatsResponse,
    ServiceInfo,
    AppConfig
)
from app.services.kafka_service import KafkaService, KafkaServiceManager
from app.models.dex_model import DexModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service manager
kafka_manager: KafkaServiceManager = None
service_start_time: datetime = None

# Application configuration
config = AppConfig(
    service_name=os.getenv("SERVICE_NAME", "DeFi Reputation Scoring Server"),
    service_version=os.getenv("SERVICE_VERSION", "1.0.0"),
    kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    kafka_input_topic=os.getenv("KAFKA_INPUT_TOPIC", "wallet-transactions"),
    kafka_success_topic=os.getenv("KAFKA_SUCCESS_TOPIC", "wallet-scores-success"),
    kafka_failure_topic=os.getenv("KAFKA_FAILURE_TOPIC", "wallet-scores-failure"),
    kafka_consumer_group=os.getenv("KAFKA_CONSUMER_GROUP", "ai-scoring-service"),
    mongodb_url=os.getenv("MONGODB_URL", "mongodb://localhost:27017"),
    mongodb_database=os.getenv("MONGODB_DATABASE", "ai_scoring"),
    log_level=os.getenv("LOG_LEVEL", "INFO")
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global kafka_manager
    
    # Startup
    global service_start_time
    service_start_time = datetime.utcnow()
    logger.info(f"Starting {config.service_name} v{config.service_version}")
    
    try:
        # Initialize Kafka service
        kafka_service = KafkaService(
            bootstrap_servers=config.kafka_bootstrap_servers,
            input_topic=config.kafka_input_topic,
            success_topic=config.kafka_success_topic,
            failure_topic=config.kafka_failure_topic,
            consumer_group=config.kafka_consumer_group
        )
        
        kafka_manager = KafkaServiceManager(kafka_service)
        
        # Start Kafka service in background
        await kafka_manager.start_background()
        logger.info("Kafka service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start services: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down services...")
        if kafka_manager:
            await kafka_manager.stop_background()
        logger.info("Services shut down successfully")

# Create FastAPI application
app = FastAPI(
    title=config.service_name,
    description="AI-powered DeFi reputation scoring server that processes wallet transaction data and generates reputation scores using machine learning models.",
    version=config.service_version,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=ServiceInfo)
async def root():
    """Root endpoint providing service information."""
    return ServiceInfo(
        service_name=config.service_name,
        version=config.service_version,
        description="AI-powered DeFi reputation scoring server",
        status="running",
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/health", response_model=HealthResponse)
@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check Kafka service health
        kafka_health = {"status": "unknown", "details": {}}
        
        if kafka_manager:
            health_data = await kafka_manager.health_check()
            kafka_health = {
                "status": "healthy" if health_data.get("service_running") else "unhealthy",
                "details": health_data
            }
        
        # Check DexModel health (basic instantiation test)
        model_health = {"status": "unknown"}
        try:
            dex_model = DexModel()
            model_health = {"status": "healthy"}
        except Exception as e:
            model_health = {"status": "unhealthy", "error": str(e)}
        
        # Determine overall health
        overall_status = "healthy"
        if kafka_health["status"] != "healthy" or model_health["status"] != "healthy":
            overall_status = "unhealthy"
        
        # Calculate uptime
        uptime_seconds = 0.0
        if service_start_time:
            uptime_seconds = (datetime.utcnow() - service_start_time).total_seconds()
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version=config.service_version,
            uptime_seconds=uptime_seconds
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        # Calculate uptime even on error
        uptime_seconds = 0.0
        if service_start_time:
            uptime_seconds = (datetime.utcnow() - service_start_time).total_seconds()
        
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            version=config.service_version,
            uptime_seconds=uptime_seconds
        )

@app.get("/stats", response_model=StatsResponse)
@app.get("/api/v1/stats", response_model=StatsResponse)
async def get_stats():
    """Get service statistics."""
    try:
        # Calculate uptime
        uptime_seconds = 0.0
        if service_start_time:
            uptime_seconds = (datetime.utcnow() - service_start_time).total_seconds()
        
        # Get Kafka stats if available
        total_processed = 0
        successful_processed = 0
        failed_processed = 0
        average_processing_time_ms = 0.0
        last_processed_timestamp = None
        
        if kafka_manager:
            kafka_stats = kafka_manager.kafka_service.get_stats()
            total_processed = kafka_stats.get("total_processed", 0)
            successful_processed = kafka_stats.get("successful_processed", 0)
            failed_processed = kafka_stats.get("failed_processed", 0)
            average_processing_time_ms = kafka_stats.get("average_processing_time_ms", 0.0)
            last_processed_timestamp = kafka_stats.get("last_processed_timestamp")
        
        return StatsResponse(
            total_processed=total_processed,
            successful_processed=successful_processed,
            failed_processed=failed_processed,
            average_processing_time_ms=average_processing_time_ms,
            uptime_seconds=uptime_seconds,
            last_processed_timestamp=last_processed_timestamp
        )
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e}")

@app.post("/admin/restart-kafka")
async def restart_kafka_service(background_tasks: BackgroundTasks):
    """Admin endpoint to restart Kafka service."""
    try:
        if not kafka_manager:
            raise HTTPException(status_code=500, detail="Kafka manager not initialized")
        
        # Stop current service
        await kafka_manager.stop_background()
        
        # Start new service
        await kafka_manager.start_background()
        
        return {"message": "Kafka service restarted successfully", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error(f"Failed to restart Kafka service: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to restart Kafka service: {e}")

@app.get("/admin/config")
async def get_config():
    """Admin endpoint to get current configuration (sensitive data masked)."""
    safe_config = {
        "service_name": config.service_name,
        "service_version": config.service_version,
        "kafka_input_topic": config.kafka_input_topic,
        "kafka_success_topic": config.kafka_success_topic,
        "kafka_failure_topic": config.kafka_failure_topic,
        "kafka_consumer_group": config.kafka_consumer_group,
        "log_level": config.log_level,
        "kafka_bootstrap_servers": "***masked***",
        "mongodb_url": "***masked***"
    }
    
    return {
        "config": safe_config,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    
    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, config.log_level.upper()))
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENVIRONMENT", "production") == "development",
        log_level=config.log_level.lower()
    )