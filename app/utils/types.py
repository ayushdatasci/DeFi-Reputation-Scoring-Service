"""Pydantic models for data validation in the AI scoring service."""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime


class TokenData(BaseModel):
    """Token data for swap transactions."""
    amount: int
    amountUSD: float
    address: str
    symbol: str


class SwapTransaction(BaseModel):
    """Swap transaction model."""
    document_id: str
    action: str = Field(..., pattern="^swap$")
    timestamp: int
    caller: str
    protocol: str
    poolId: str
    poolName: str
    tokenIn: TokenData
    tokenOut: TokenData


class LPTransaction(BaseModel):
    """LP (deposit/withdraw) transaction model."""
    document_id: str
    action: str = Field(..., pattern="^(deposit|withdraw)$")
    timestamp: int
    caller: str
    protocol: str
    poolId: str
    poolName: str
    token0: TokenData
    token1: TokenData


class Transaction(BaseModel):
    """Generic transaction model that can handle both swap and LP transactions."""
    document_id: str
    action: str = Field(..., pattern="^(swap|deposit|withdraw)$")
    timestamp: int
    caller: str
    protocol: str
    poolId: str
    poolName: str
    
    # Optional fields for different transaction types
    tokenIn: Optional[TokenData] = None
    tokenOut: Optional[TokenData] = None
    token0: Optional[TokenData] = None
    token1: Optional[TokenData] = None
    
    @validator('tokenIn', 'tokenOut', pre=True, always=True)
    def validate_swap_tokens(cls, v, values):
        """Validate that swap transactions have tokenIn and tokenOut."""
        if values.get('action') == 'swap' and v is None:
            raise ValueError('Swap transactions must have tokenIn and tokenOut')
        return v
    
    @validator('token0', 'token1', pre=True, always=True)
    def validate_lp_tokens(cls, v, values):
        """Validate that LP transactions have token0 and token1."""
        if values.get('action') in ['deposit', 'withdraw'] and v is None:
            raise ValueError('LP transactions must have token0 and token1')
        return v


class ProtocolData(BaseModel):
    """Protocol data containing transactions."""
    protocolType: str = Field(..., pattern="^dexes$")
    transactions: List[Transaction]


class WalletTransactionMessage(BaseModel):
    """Input message from Kafka wallet-transactions topic."""
    wallet_address: str
    data: List[ProtocolData]


class ScoreFeatures(BaseModel):
    """Features calculated for scoring."""
    total_deposit_usd: float = 0.0
    total_swap_volume: float = 0.0
    num_deposits: int = 0
    num_swaps: int = 0
    avg_hold_time_days: float = 0.0
    unique_pools: int = 0
    total_withdraw_usd: Optional[float] = 0.0
    num_withdraws: Optional[int] = 0
    withdraw_ratio: Optional[float] = 0.0
    account_age_days: Optional[float] = 0.0
    unique_pools_swapped: Optional[int] = 0
    avg_swap_size: Optional[float] = 0.0
    token_diversity_score: Optional[int] = 0
    swap_frequency_score: Optional[float] = 0.0


class CategoryResult(BaseModel):
    """Result for a specific category (e.g., dexes)."""
    category: str
    score: float
    transaction_count: int
    features: ScoreFeatures


class CategoryError(BaseModel):
    """Error result for a specific category."""
    category: str
    error: str
    transaction_count: int


class WalletScoreSuccessMessage(BaseModel):
    """Success message for wallet-scores-success topic."""
    wallet_address: str
    zscore: str = Field(..., description="Score as string with 18 decimal places")
    timestamp: int
    processing_time_ms: int
    categories: List[CategoryResult]
    
    @validator('zscore')
    def validate_zscore_format(cls, v):
        """Validate zscore is a valid number string."""
        try:
            float(v)
        except ValueError:
            raise ValueError('zscore must be a valid number string')
        return v


class WalletScoreFailureMessage(BaseModel):
    """Failure message for wallet-scores-failure topic."""
    wallet_address: str
    error: str
    timestamp: int
    processing_time_ms: int
    categories: List[CategoryError]


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = "healthy"
    timestamp: datetime
    version: str = "1.0.0"
    uptime_seconds: float


class StatsResponse(BaseModel):
    """Statistics response model."""
    total_processed: int = 0
    successful_processed: int = 0
    failed_processed: int = 0
    average_processing_time_ms: float = 0.0
    uptime_seconds: float = 0.0
    last_processed_timestamp: Optional[int] = None


class ServiceInfo(BaseModel):
    """Service information model."""
    service: str = "AI DeFi Reputation Scoring Server"
    version: str = "1.0.0"
    description: str = "Kafka-based microservice for calculating DeFi wallet reputation scores"
    endpoints: List[str] = [
        "/",
        "/api/v1/health",
        "/api/v1/stats"
    ]


class AppConfig(BaseModel):
    """Application configuration model."""
    # Service Configuration
    service_name: str = "DeFi Reputation Scoring Server"
    service_version: str = "1.0.0"
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_input_topic: str = "wallet-transactions"
    kafka_success_topic: str = "wallet-scores-success"
    kafka_failure_topic: str = "wallet-scores-failure"
    kafka_consumer_group: str = "ai-scoring-service"
    
    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "ai_scoring"
    mongodb_tokens_collection: str = "tokens"
    mongodb_thresholds_collection: str = "protocol-thresholds-percentiles"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    environment: str = "production"
    
    class Config:
        env_prefix = ""
        case_sensitive = False