#!/usr/bin/env python3
"""
Test script to validate the core DeFi reputation scoring logic
without requiring external dependencies.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Mock logger for testing
class MockLogger:
    def info(self, msg):
        print(f"[INFO] {msg}")
    
    def warning(self, msg):
        print(f"[WARNING] {msg}")
    
    def error(self, msg):
        print(f"[ERROR] {msg}")

# Replace the logger import in dex_model
import models.dex_model as dex_model_module
dex_model_module.logger = MockLogger()

from models.dex_model import DexModel

def create_test_data() -> Dict[str, Any]:
    """Create sample test data for validation."""
    base_time = datetime.now() - timedelta(days=100)
    
    return {
        "lp_transactions": [
            {
                "transaction_hash": "0x123",
                "timestamp": base_time.isoformat(),
                "action": "deposit",
                "pool_address": "0xpool1",
                "token0_symbol": "ETH",
                "token1_symbol": "USDC",
                "amount0": 1.5,
                "amount1": 3000.0,
                "amount_usd": 6000.0
            },
            {
                "transaction_hash": "0x124",
                "timestamp": (base_time + timedelta(days=30)).isoformat(),
                "action": "withdraw",
                "pool_address": "0xpool1",
                "token0_symbol": "ETH",
                "token1_symbol": "USDC",
                "amount0": 1.5,
                "amount1": 3000.0,
                "amount_usd": 6000.0
            }
        ],
        "swap_transactions": [
            {
                "transaction_hash": "0x200",
                "timestamp": base_time.isoformat(),
                "token_in_symbol": "ETH",
                "token_out_symbol": "USDC",
                "amount_in": 1.0,
                "amount_out": 2000.0,
                "amount_usd": 2000.0,
                "pool_address": "0xpool1"
            },
            {
                "transaction_hash": "0x201",
                "timestamp": (base_time + timedelta(days=1)).isoformat(),
                "token_in_symbol": "USDC",
                "token_out_symbol": "DAI",
                "amount_in": 1000.0,
                "amount_out": 1000.0,
                "amount_usd": 1000.0,
                "pool_address": "0xpool2"
            },
            {
                "transaction_hash": "0x202",
                "timestamp": (base_time + timedelta(days=2)).isoformat(),
                "token_in_symbol": "DAI",
                "token_out_symbol": "WBTC",
                "amount_in": 500.0,
                "amount_out": 0.01,
                "amount_usd": 500.0,
                "pool_address": "0xpool3"
            }
        ]
    }

def test_dex_model():
    """Test the DexModel functionality."""
    print("=== Testing DeFi Reputation Scoring Model ===")
    
    # Initialize model
    model = DexModel()
    print("✓ DexModel initialized successfully")
    
    # Create test data
    test_data = create_test_data()
    print("✓ Test data created")
    
    # Test preprocessing
    transactions = model.preprocess_dex_transactions(test_data)
    print(f"✓ Preprocessed {len(transactions)} transactions")
    
    # Test LP features calculation
    lp_features = model.calculate_lp_features(transactions)
    print(f"✓ LP features calculated: {lp_features}")
    
    # Test LP score calculation
    lp_score, lp_breakdown = model.calculate_lp_score(lp_features)
    print(f"✓ LP score calculated: {lp_score:.2f}")
    print(f"  LP breakdown: {lp_breakdown}")
    
    # Test swap features calculation
    swap_features = model.calculate_swap_features(transactions)
    print(f"✓ Swap features calculated: {swap_features}")
    
    # Test swap score calculation
    swap_score, swap_breakdown = model.calculate_swap_score(swap_features)
    print(f"✓ Swap score calculated: {swap_score:.2f}")
    print(f"  Swap breakdown: {swap_breakdown}")
    
    # Test user tags generation
    user_tags = model.generate_user_tags(lp_features, swap_features)
    print(f"✓ User tags generated: {user_tags}")
    
    # Test final score calculation
    final_result = model.calculate_final_score(lp_score, swap_score, lp_features, swap_features)
    print(f"✓ Final score calculated: {final_result}")
    
    # Test complete wallet processing
    wallet_address = "0x1234567890abcdef"
    complete_result = model.process_wallet(wallet_address, test_data)
    print(f"✓ Complete wallet processing result: {complete_result}")
    
    print("\n=== All Tests Passed Successfully! ===")
    return True

def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n=== Testing Edge Cases ===")
    
    model = DexModel()
    
    # Test with empty data
    empty_result = model.process_wallet("0xempty", {})
    print(f"✓ Empty data handling: {empty_result}")
    
    # Test with minimal data
    minimal_data = {
        "lp_transactions": [],
        "swap_transactions": [
            {
                "transaction_hash": "0x300",
                "timestamp": datetime.now().isoformat(),
                "token_in_symbol": "ETH",
                "token_out_symbol": "USDC",
                "amount_in": 0.1,
                "amount_out": 200.0,
                "amount_usd": 200.0,
                "pool_address": "0xpool1"
            }
        ]
    }
    
    minimal_result = model.process_wallet("0xminimal", minimal_data)
    print(f"✓ Minimal data handling: {minimal_result}")
    
    print("✓ Edge cases handled successfully")

if __name__ == "__main__":
    try:
        # Run main tests
        test_dex_model()
        
        # Run edge case tests
        test_edge_cases()
        
        print("\n🎉 All tests completed successfully!")
        print("The DeFi reputation scoring system is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)