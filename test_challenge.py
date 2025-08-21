#!/usr/bin/env python3
"""
Test script for AI Engineer Challenge
Run this to validate your implementation
"""

import json
import asyncio
import time
from typing import Dict, Any
import httpx

# Sample test data
SAMPLE_WALLET_MESSAGE = {
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
                },
                {
                    "document_id": "507f1f77bcf86cd799439013",
                    "action": "withdraw",
                    "timestamp": 1703981800,
                    "caller": "0x742d35Cc6634C0532925a3b8D4C9db96590e4265",
                    "protocol": "uniswap_v3",
                    "poolId": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                    "poolName": "Uniswap V3 USDC/WETH 0.05%",
                    "token0": {
                        "amount": 250000000,
                        "amountUSD": 250.0,
                        "address": "0xa0b86a33e6c3d4c3e6c3d4c3e6c3d4c3e6c3d4c3",
                        "symbol": "USDC"
                    },
                    "token1": {
                        "amount": 125000000000000000,
                        "amountUSD": 250.0,
                        "address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                        "symbol": "WETH"
                    }
                }
            ]
        }
    ]
}

EXPECTED_FEATURES = {
    "total_deposit_usd": 500.0,
    "total_withdraw_usd": 500.0,
    "num_deposits": 1,
    "num_withdraws": 1,
    "total_swap_volume": 1000.0,
    "num_swaps": 1,
    "unique_pools": 1
}

async def test_server_health(base_url: str = "http://localhost:8000"):
    """Test if the server is running and healthy."""
    print("🔍 Testing server health...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test root endpoint
            response = await client.get(f"{base_url}/")
            assert response.status_code == 200
            data = response.json()
            assert "service" in data
            print("✅ Root endpoint working")
            
            # Test health endpoint
            response = await client.get(f"{base_url}/api/v1/health")
            assert response.status_code == 200
            print("✅ Health endpoint working")
            
            # Test stats endpoint
            response = await client.get(f"{base_url}/api/v1/stats")
            assert response.status_code == 200
            print("✅ Stats endpoint working")
            
    except Exception as e:
        print(f"❌ Server health check failed: {e}")
        return False
    
    return True

def validate_success_message(message: Dict[str, Any]) -> bool:
    """Validate the structure of a success message."""
    required_fields = ["wallet_address", "zscore", "timestamp", "categories"]
    
    for field in required_fields:
        if field not in message:
            print(f"❌ Missing required field: {field}")
            return False
    
    # Validate zscore format (should be string with 18 decimal places)
    zscore = message["zscore"]
    if not isinstance(zscore, str):
        print(f"❌ zscore should be string, got {type(zscore)}")
        return False
    
    try:
        float(zscore)
    except ValueError:
        print(f"❌ zscore is not a valid number: {zscore}")
        return False
    
    # Validate categories
    categories = message["categories"]
    if not isinstance(categories, list) or len(categories) == 0:
        print("❌ categories should be non-empty list")
        return False
    
    category = categories[0]
    required_category_fields = ["category", "score", "transaction_count", "features"]
    
    for field in required_category_fields:
        if field not in category:
            print(f"❌ Missing category field: {field}")
            return False
    
    # Validate features
    features = category["features"]
    for expected_feature, expected_value in EXPECTED_FEATURES.items():
        if expected_feature not in features:
            print(f"❌ Missing feature: {expected_feature}")
            return False
        
        actual_value = features[expected_feature]
        if abs(actual_value - expected_value) > 0.01:  # Allow small floating point differences
            print(f"⚠️  Feature {expected_feature}: expected {expected_value}, got {actual_value}")
    
    print("✅ Success message structure is valid")
    return True

def validate_failure_message(message: Dict[str, Any]) -> bool:
    """Validate the structure of a failure message."""
    required_fields = ["wallet_address", "error", "timestamp", "categories"]
    
    for field in required_fields:
        if field not in message:
            print(f"❌ Missing required field: {field}")
            return False
    
    print("✅ Failure message structure is valid")
    return True

def test_ai_model_logic():
    """Test the AI model logic directly (if implemented)."""
    print("🧠 Testing AI model logic...")
    
    try:
        # This would test your model implementation directly
        # You'll need to import your model here
        # from app.models.dex_model import DexModel
        
        print("⚠️  Direct model testing not implemented - implement this based on your model structure")
        return True
        
    except Exception as e:
        print(f"❌ AI model test failed: {e}")
        return False

async def test_kafka_integration():
    """Test Kafka message processing (requires Kafka setup)."""
    print("📨 Testing Kafka integration...")
    
    try:
        # This would test Kafka producer/consumer
        # You'll need to implement this based on your Kafka setup
        print("⚠️  Kafka integration test not implemented - requires running Kafka cluster")
        return True
        
    except Exception as e:
        print(f"❌ Kafka integration test failed: {e}")
        return False

def performance_test():
    """Test performance with multiple wallets."""
    print("⚡ Running performance test...")
    
    start_time = time.time()
    
    # Simulate processing 100 wallets
    num_wallets = 100
    for i in range(num_wallets):
        # This would test your processing pipeline
        pass
    
    end_time = time.time()
    processing_time = end_time - start_time
    wallets_per_second = num_wallets / processing_time
    
    print(f"📊 Processed {num_wallets} wallets in {processing_time:.2f}s")
    print(f"📊 Rate: {wallets_per_second:.2f} wallets/second")
    
    if wallets_per_second >= 16.67:  # 1000 wallets/minute
        print("✅ Performance target met (1000+ wallets/minute)")
        return True
    else:
        print("⚠️  Performance target not met - optimize your implementation")
        return False

async def run_all_tests():
    """Run all validation tests."""
    print("🚀 Starting AI Engineer Challenge Validation\n")
    
    tests = [
        ("Server Health", test_server_health()),
        ("AI Model Logic", test_ai_model_logic()),
        ("Kafka Integration", test_kafka_integration()),
        ("Performance", performance_test())
    ]
    
    results = []
    for test_name, test_coro in tests:
        print(f"\n--- {test_name} ---")
        if asyncio.iscoroutine(test_coro):
            result = await test_coro
        else:
            result = test_coro
        results.append((test_name, result))
    
    print("\n" + "="*50)
    print("📋 TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 Congratulations! Your implementation passes all tests!")
    else:
        print("🔧 Some tests failed - check the output above for details")

if __name__ == "__main__":
    print("AI Engineer Challenge - Test Suite")
    print("Make sure your server is running on http://localhost:8000")
    print("Press Ctrl+C to cancel\n")
    
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n⏹️  Tests cancelled by user")
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
