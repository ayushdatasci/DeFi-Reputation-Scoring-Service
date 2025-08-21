# AI Engineer Challenge: DeFi Reputation Scoring Server

## Overview
You are tasked with building a production-ready AI server that processes DeFi transaction data and calculates wallet reputation scores. This challenge tests your ability to integrate AI models, handle real-time data streams, and build scalable microservices.

## Problem Statement
Build a Kafka-based microservice that:
1. Consumes wallet transaction messages from a Kafka topic
2. Processes the data using provided AI scoring logic
3. Calculates reputation scores for wallets
4. Publishes results to output Kafka topics

## Architecture Requirements

### Input: Kafka Message Format
Your server will receive messages from the `wallet-transactions` topic with this structure:

```json
{
  "wallet_address": "0x742d35Cc6634C0532925a3b8D4C9db96590e4265",
  "data": [
    {
      "protocolType": "dexes",
      "transactions": [
        {
          "document_id": "507f1f77bcf86cd799439011",
          "action": "swap",
          "timestamp": 1703980800,
          "caller": "0x742d35Cc6634C0532925a3b8D4C9db96590e4265",
          "protocol": "uniswap_v3",
          "poolId": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
          "poolName": "Uniswap V3 USDC/WETH 0.05%",
          "tokenIn": {
            "amount": 1000000000,
            "amountUSD": 1000.0,
            "address": "0xa0b86a33e6c3d4c3e6c3d4c3e6c3d4c3e6c3d4c3",
            "symbol": "USDC"
          },
          "tokenOut": {
            "amount": 500000000000000000,
            "amountUSD": 1000.0,
            "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
            "symbol": "WETH"
          }
        },
        {
          "document_id": "507f1f77bcf86cd799439012",
          "action": "deposit",
          "timestamp": 1703980900,
          "caller": "0x742d35Cc6634C0532925a3b8D4C9db96590e4265",
          "protocol": "uniswap_v3",
          "poolId": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
          "poolName": "Uniswap V3 USDC/WETH 0.05%",
          "token0": {
            "amount": 500000000,
            "amountUSD": 500.0,
            "address": "0xa0b86a33e6c3d4c3e6c3d4c3e6c3d4c3e6c3d4c3",
            "symbol": "USDC"
          },
          "token1": {
            "amount": 250000000000000000,
            "amountUSD": 500.0,
            "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
            "symbol": "WETH"
          }
        }
      ]
    }
  ]
}
```

### Output: Success Message Format
Publish successful results to `wallet-scores-success` topic:

```json
{
  "wallet_address": "0x742d35Cc6634C0532925a3b8D4C9db96590e4265",
  "zscore": "750.123456789012345678",
  "timestamp": 1703980800,
  "processing_time_ms": 1250,
  "categories": [
    {
      "category": "dexes",
      "score": 750.12,
      "transaction_count": 2,
      "features": {
        "total_deposit_usd": 500.0,
        "total_swap_volume": 1000.0,
        "num_deposits": 1,
        "num_swaps": 1,
        "avg_hold_time_days": 15.5,
        "unique_pools": 1
      }
    }
  ]
}
```

### Output: Failure Message Format
Publish failures to `wallet-scores-failure` topic:

```json
{
  "wallet_address": "0x742d35Cc6634C0532925a3b8D4C9db96590e4265",
  "error": "Failed to process DEX transactions: Invalid token data",
  "timestamp": 1703980800,
  "processing_time_ms": 500,
  "categories": [
    {
      "category": "dexes",
      "error": "Invalid token data",
      "transaction_count": 2
    }
  ]
}
```

## Technical Requirements

### 1. Environment Setup
- Python 3.11+
- FastAPI for health endpoints
- Kafka for message processing
- MongoDB for configuration data
- Docker for containerization

### 2. Core Components Required
- **Kafka Consumer/Producer**: Handle message streaming
- **AI Model Integration**: Process transaction data using provided logic
- **Score Calculation**: Implement reputation scoring algorithms
- **Error Handling**: Robust error handling with proper logging
- **Health Monitoring**: Health check endpoints

### 3. Configuration Management
Load these from environment variables:
```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_INPUT_TOPIC=wallet-transactions
KAFKA_SUCCESS_TOPIC=wallet-scores-success
KAFKA_FAILURE_TOPIC=wallet-scores-failure
KAFKA_CONSUMER_GROUP=ai-scoring-service

# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=ai_scoring
MONGODB_TOKENS_COLLECTION=tokens
MONGODB_THRESHOLDS_COLLECTION=protocol-thresholds-percentiles

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=production
```

## AI Model Integration Challenge

### Provided Assets
You will receive a Jupyter notebook (`dex_scoring_model.ipynb`) containing:
- Data preprocessing functions
- Feature engineering logic
- Scoring algorithms for DEX transactions
- Sample data and expected outputs

### Your Task
1. **Extract the AI Logic**: Convert notebook functions into production code
2. **Handle Data Conversion**: Transform JSON input to pandas DataFrame format
3. **Implement Scoring**: Calculate both LP (Liquidity Provider) and Swap scores
4. **Feature Engineering**: Extract meaningful features from transaction data
5. **Score Aggregation**: Combine multiple scores into final reputation score

### Key Challenges
- **Data Preprocessing**: Handle missing/invalid transaction data gracefully
- **Feature Extraction**: Calculate metrics like holding time, volume patterns, frequency
- **Score Normalization**: Ensure scores are in consistent 0-1000 range
- **Performance**: Process wallets efficiently with proper async handling
- **Error Recovery**: Handle edge cases and malformed data

## Scoring Algorithm Hints
The DEX model should calculate:
- **LP Scores**: Based on deposit/withdraw patterns, holding times, liquidity retention
- **Swap Scores**: Based on trading volume, frequency, token diversity
- **Combined Score**: Weighted average of LP and Swap scores
- **User Tags**: Categorize users (e.g., "Whale LP", "Active Trader", "HODLer")

## Deliverables

### 1. Core Application
- `app/main.py` - FastAPI application entry point
- `app/services/kafka_service.py` - Kafka consumer/producer
- `app/models/dex_model.py` - AI scoring model implementation
- `app/utils/types.py` - Pydantic models for data validation

### 2. Configuration
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration
- `.env.example` - Environment variables template

### 3. API Endpoints
- `GET /` - Service info
- `GET /api/v1/health` - Health check
- `GET /api/v1/stats` - Processing statistics

### 4. Documentation
- `README.md` - Setup and deployment instructions
- Code comments explaining AI model integration

## Evaluation Criteria

### Technical Excellence (40%)
- Clean, maintainable code architecture
- Proper error handling and logging
- Efficient async/await usage
- Robust data validation

### AI Integration (30%)
- Correct implementation of scoring algorithms
- Proper data preprocessing and feature engineering
- Handling of edge cases and invalid data
- Performance optimization

### Production Readiness (20%)
- Docker containerization
- Environment configuration
- Health monitoring
- Scalability considerations

### Problem Solving (10%)
- Creative solutions to complex challenges
- Code organization and modularity
- Testing approach
- Documentation quality

## Success Metrics
- Successfully processes 1000+ wallets/minute
- <2 second average processing time per wallet
- >99% uptime with proper error handling
- Accurate score calculation matching expected outputs
- Clean logs with proper structured logging

## Bonus Points
- Unit tests for critical components
- Monitoring/metrics integration
- Graceful shutdown handling
- Memory and CPU optimization
- Advanced error recovery strategies

## Time Expectation
This challenge should take 6-8 hours for an experienced AI engineer. Focus on core functionality first, then optimize and add advanced features.

Good luck! This challenge will test your ability to build production-ready AI services that can handle real-world DeFi data at scale.

## Quick Start Guide

### 1. Setup Development Environment
```bash
# Clone or create your project directory
mkdir ai-scoring-server && cd ai-scoring-server

# Copy challenge files
cp AI_ENGINEER_CHALLENGE.md README.md
cp .env.challenge .env
cp dex_scoring_model.ipynb .
cp test_challenge.py .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (create requirements.txt based on challenge needs)
pip install fastapi uvicorn pydantic kafka-python confluent-kafka pymongo pandas numpy structlog python-dotenv httpx
```

### 2. Start External Services
```bash
# Start Kafka (using Docker)
docker run -d --name kafka-test -p 9092:9092 \
  -e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  confluentinc/cp-kafka:latest

# Start MongoDB (using Docker)
docker run -d --name mongo-test -p 27017:27017 mongo:latest

# Create Kafka topics
kafka-topics --create --topic wallet-transactions --bootstrap-server localhost:9092
kafka-topics --create --topic wallet-scores-success --bootstrap-server localhost:9092
kafka-topics --create --topic wallet-scores-failure --bootstrap-server localhost:9092
```

### 3. Implement Your Solution
Study the `dex_scoring_model.ipynb` notebook and implement:
- `app/main.py` - FastAPI application
- `app/services/kafka_service.py` - Kafka consumer/producer
- `app/models/dex_model.py` - AI scoring model
- `app/utils/types.py` - Pydantic models

### 4. Test Your Implementation
```bash
# Start your server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# In another terminal, run tests
python test_challenge.py

# Send test message to Kafka
kafka-console-producer --topic wallet-transactions --bootstrap-server localhost:9092
# Paste the sample JSON from the challenge
```

### 5. Validate Output
Check that your server produces messages in the correct format on the success/failure topics:

```bash
# Monitor success topic
kafka-console-consumer --topic wallet-scores-success --bootstrap-server localhost:9092 --from-beginning

# Monitor failure topic
kafka-console-consumer --topic wallet-scores-failure --bootstrap-server localhost:9092 --from-beginning
```

## Submission Checklist

- [ ] Server starts without errors
- [ ] Health endpoints respond correctly
- [ ] Kafka consumer processes messages
- [ ] AI model calculates scores correctly
- [ ] Success messages have correct format
- [ ] Failure messages have correct format
- [ ] Docker container builds and runs
- [ ] Performance meets requirements (1000+ wallets/minute)
- [ ] Code is well-documented
- [ ] Error handling is robust

## Common Pitfalls to Avoid

1. **JSON Serialization**: Handle NumPy/Pandas types properly
2. **Async/Await**: Don't block the event loop with synchronous operations
3. **Error Handling**: Catch and handle all possible exceptions
4. **Memory Management**: Don't accumulate data in memory indefinitely
5. **Data Validation**: Validate all input data with Pydantic
6. **Logging**: Use structured logging for debugging
7. **Configuration**: Load all settings from environment variables

## Bonus Implementation Ideas

- Implement caching for frequently accessed data
- Add metrics and monitoring endpoints
- Implement graceful shutdown handling
- Add unit tests for critical functions
- Optimize DataFrame operations for performance
- Implement retry logic for failed operations
- Add configuration validation on startup

---

**Time Limit**: 6-8 hours
**Difficulty**: Senior Level
**Focus**: Production-ready AI microservice development
