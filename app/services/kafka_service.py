import asyncio
import json
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.utils.types import (
    WalletTransactionMessage,
    WalletScoreSuccessMessage,
    WalletScoreFailureMessage
)
from app.models.dex_model import DexModel

logger = logging.getLogger(__name__)

class KafkaService:
    """Kafka service for consuming wallet transaction messages and producing score results."""
    
    def __init__(
        self,
        bootstrap_servers: str,
        input_topic: str,
        success_topic: str,
        failure_topic: str,
        consumer_group: str = "ai-scoring-service",
        auto_offset_reset: str = "latest"
    ):
        self.bootstrap_servers = bootstrap_servers
        self.input_topic = input_topic
        self.success_topic = success_topic
        self.failure_topic = failure_topic
        self.consumer_group = consumer_group
        self.auto_offset_reset = auto_offset_reset
        
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.producer: Optional[AIOKafkaProducer] = None
        self.dex_model = DexModel()
        
        # Statistics tracking
        self.stats = {
            "messages_processed": 0,
            "messages_failed": 0,
            "last_processed_at": None,
            "service_started_at": None
        }
        
    async def start(self):
        """Start Kafka consumer and producer."""
        try:
            # Initialize consumer
            self.consumer = AIOKafkaConsumer(
                self.input_topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                auto_offset_reset=self.auto_offset_reset,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                enable_auto_commit=True,
                auto_commit_interval_ms=1000
            )
            
            # Initialize producer
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                compression_type="gzip"
            )
            
            # Start both services
            await self.consumer.start()
            await self.producer.start()
            
            self.stats["service_started_at"] = datetime.utcnow().isoformat()
            logger.info(f"Kafka service started. Consuming from {self.input_topic}, producing to {self.success_topic} and {self.failure_topic}")
            
        except Exception as e:
            logger.error(f"Failed to start Kafka service: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop Kafka consumer and producer."""
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")
            
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
    
    async def process_message(self, message_data: Dict[str, Any]) -> None:
        """Process a single wallet transaction message."""
        start_time = datetime.utcnow()
        
        try:
            # Validate input message
            wallet_message = WalletTransactionMessage(**message_data)
            
            logger.info(f"Processing wallet: {wallet_message.wallet_address}")
            
            # Convert data format for DexModel (expects dict, not list)
            protocol_data = {}
            for protocol in wallet_message.data:
                if protocol.protocolType == "dexes":
                    protocol_data = {
                        "protocolType": protocol.protocolType,
                        "transactions": [tx.dict() for tx in protocol.transactions]
                    }
                    break
            
            # Process wallet using DexModel
            result = self.dex_model.process_wallet(
                wallet_message.wallet_address,
                protocol_data
            )
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Convert result format to match our schema
            from ..utils.types import CategoryResult, ScoreFeatures
            
            categories = []
            
            # Add LP category
            if "lp_category" in result:
                lp_cat = result["lp_category"]
                lp_features = ScoreFeatures(**lp_cat.get("features", {}))
                categories.append(CategoryResult(
                    category="liquidity_provision",
                    score=lp_cat["score"],
                    transaction_count=len([tx for tx in protocol_data.get("transactions", []) if tx.get("action") in ["deposit", "withdraw"]]),
                    features=lp_features
                ))
            
            # Add Swap category
            if "swap_category" in result:
                swap_cat = result["swap_category"]
                swap_features = ScoreFeatures(**swap_cat.get("features", {}))
                categories.append(CategoryResult(
                    category="trading",
                    score=swap_cat["score"],
                    transaction_count=len([tx for tx in protocol_data.get("transactions", []) if tx.get("action") == "swap"]),
                    features=swap_features
                ))
            
            # Create success message
            success_message = WalletScoreSuccessMessage(
                wallet_address=wallet_message.wallet_address,
                zscore=str(result["zscore"]),
                timestamp=int(datetime.utcnow().timestamp()),
                processing_time_ms=int(processing_time),
                categories=categories
            )
            
            # Send to success topic
            await self.send_success_result(success_message.dict())
            
            # Update stats
            self.stats["messages_processed"] += 1
            self.stats["last_processed_at"] = datetime.utcnow().isoformat()
            
            logger.info(f"Successfully processed wallet {wallet_message.wallet_address} with zscore {result['zscore']}")
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            
            # Try to extract wallet address for error message
            wallet_address = "unknown"
            try:
                wallet_address = message_data.get("wallet_address", "unknown")
            except:
                pass
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Create failure message
            failure_message = WalletScoreFailureMessage(
                wallet_address=wallet_address,
                error=str(e),
                timestamp=int(datetime.utcnow().timestamp()),
                processing_time_ms=int(processing_time),
                categories=[]
            )
            
            # Send error to failure topic
            await self.send_failure_result(failure_message.dict())
            
            # Update stats
            self.stats["messages_failed"] += 1
    
    async def send_success_result(self, result_data: Dict[str, Any]) -> None:
        """Send success result message to success topic."""
        try:
            await self.producer.send_and_wait(
                self.success_topic,
                value=result_data
            )
            logger.debug(f"Sent success result to {self.success_topic}")
            
        except KafkaError as e:
            logger.error(f"Failed to send success result to Kafka: {e}")
            raise
    
    async def send_failure_result(self, result_data: Dict[str, Any]) -> None:
        """Send failure result message to failure topic."""
        try:
            await self.producer.send_and_wait(
                self.failure_topic,
                value=result_data
            )
            logger.debug(f"Sent failure result to {self.failure_topic}")
            
        except KafkaError as e:
            logger.error(f"Failed to send failure result to Kafka: {e}")
            raise
    
    async def consume_messages(self) -> None:
        """Main consumer loop."""
        if not self.consumer:
            raise RuntimeError("Consumer not initialized. Call start() first.")
        
        logger.info("Starting message consumption loop")
        
        try:
            async for message in self.consumer:
                try:
                    await self.process_message(message.value)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Continue processing other messages
                    continue
                    
        except Exception as e:
            logger.error(f"Consumer loop error: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of Kafka connections."""
        health_status = {
            "kafka_consumer": "unknown",
            "kafka_producer": "unknown",
            "last_error": None
        }
        
        try:
            # Check consumer
            if self.consumer and not self.consumer._closed:
                health_status["kafka_consumer"] = "healthy"
            else:
                health_status["kafka_consumer"] = "disconnected"
            
            # Check producer
            if self.producer and not self.producer._closed:
                health_status["kafka_producer"] = "healthy"
            else:
                health_status["kafka_producer"] = "disconnected"
                
        except Exception as e:
            health_status["last_error"] = str(e)
            logger.error(f"Health check error: {e}")
        
        return health_status
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return self.stats.copy()
    
    async def run(self) -> None:
        """Run the Kafka service (start and consume messages)."""
        await self.start()
        try:
            await self.consume_messages()
        finally:
            await self.stop()


class KafkaServiceManager:
    """Manager for Kafka service lifecycle."""
    
    def __init__(self, kafka_service: KafkaService):
        self.kafka_service = kafka_service
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start_background(self) -> None:
        """Start Kafka service in background task."""
        if self._running:
            logger.warning("Kafka service is already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_with_retry())
        logger.info("Kafka service started in background")
    
    async def stop_background(self) -> None:
        """Stop background Kafka service."""
        if not self._running:
            return
        
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        await self.kafka_service.stop()
        logger.info("Kafka service stopped")
    
    async def _run_with_retry(self) -> None:
        """Run Kafka service with automatic retry on failures."""
        retry_count = 0
        max_retries = 5
        base_delay = 5  # seconds
        
        while self._running:
            try:
                await self.kafka_service.run()
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    logger.error(f"Max retries ({max_retries}) exceeded. Stopping service.")
                    break
                
                delay = base_delay * (2 ** (retry_count - 1))  # Exponential backoff
                logger.error(f"Kafka service error (attempt {retry_count}/{max_retries}): {e}")
                logger.info(f"Retrying in {delay} seconds...")
                
                await asyncio.sleep(delay)
            else:
                # Reset retry count on successful run
                retry_count = 0
    
    @property
    def is_running(self) -> bool:
        """Check if the service is running."""
        return self._running and self._task and not self._task.done()
    
    async def health_check(self) -> Dict[str, Any]:
        """Get health status of the service."""
        kafka_health = await self.kafka_service.health_check()
        
        return {
            "service_running": self.is_running,
            "kafka_health": kafka_health,
            "stats": self.kafka_service.get_stats()
        }