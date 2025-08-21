"""DeFi DEX Reputation Scoring Model.

This module contains the AI scoring logic for DEX (Decentralized Exchange) transactions.
Converted from Jupyter notebook for production use.
Optimized for Python 3.11+ with modern type hints and performance improvements.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, TypedDict, Union
import statistics
import math
from functools import lru_cache
from dataclasses import dataclass

# Type definitions for better type safety
class TransactionDict(TypedDict, total=False):
    """Type definition for transaction dictionary."""
    type: str
    action: str
    amount_usd: float
    timestamp: Union[str, float]
    token_in: str
    token_out: str
    pool: str

@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """Immutable score breakdown for better performance."""
    volume_score: float
    frequency_score: float
    retention_score: float
    holding_score: float
    diversity_score: float
    total_score: float

# from ..utils.types import WalletTransactionMessage, ScoreFeatures, CategoryResult
# Note: Imports commented out for standalone testing

# Simple logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DexModel:
    """DeFi DEX reputation scoring model optimized for Python 3.11+."""
    
    __slots__ = ('stable_tokens', '_cache_size')
    
    def __init__(self, cache_size: int = 128):
        """Initialize the DexModel with performance optimizations.
        
        Args:
            cache_size: Size of LRU cache for expensive calculations
        """
        self.stable_tokens: frozenset[str] = frozenset({
            'USDC', 'USDT', 'DAI', 'LUSD', 'USDP', 'TUSD', 'FRAX'
        })
        self._cache_size = cache_size
        logger.info("DexModel initialized with Python 3.11+ optimizations")
    
    @lru_cache(maxsize=128)
    def _parse_timestamp(self, timestamp: Union[str, float]) -> Optional[float]:
        """Parse timestamp with caching for performance.
        
        Args:
            timestamp: Timestamp as string or float
            
        Returns:
            Parsed timestamp as float or None if invalid
        """
        if isinstance(timestamp, (int, float)):
            return float(timestamp)
        
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.timestamp()
            except (ValueError, AttributeError):
                return None
        
        return None
    
    def preprocess_dex_transactions(self, protocol_data: Dict[str, Any]) -> list[TransactionDict]:
        """
        Convert raw protocol data to list of transaction dictionaries.
        
        Args:
            protocol_data: Protocol data with transactions
            
        Returns:
            List of processed transaction dictionaries
        """
        transactions: list[TransactionDict] = []
        
        # Process LP transactions with improved performance
        lp_transactions = protocol_data.get('lp_transactions', [])
        transactions.extend(
            {'type': 'lp', **tx} for tx in lp_transactions
        )
        
        # Process swap transactions with improved performance
        swap_transactions = protocol_data.get('swap_transactions', [])
        transactions.extend(
            {'type': 'swap', **tx} for tx in swap_transactions
        )
        
        return transactions
    
    def calculate_holding_time(self, deposits: list[Dict], withdraws: list[Dict]) -> float:
        """
        Calculate realistic holding time by matching deposits to withdraws.
        Uses cached timestamp parsing for better performance.
        """
        if not deposits:
            return 0.0
        
        holding_times: list[float] = []
        
        for deposit in deposits:
            deposit_timestamp = deposit.get('timestamp')
            if not deposit_timestamp:
                continue
            
            deposit_time = self._parse_timestamp(deposit_timestamp)
            if deposit_time is None:
                continue
            
            # Find next withdraw after this deposit using list comprehension
            future_withdraws = [
                parsed_time
                for w in withdraws
                if (parsed_time := self._parse_timestamp(w.get('timestamp'))) is not None
                and parsed_time > deposit_time
            ]
            
            if future_withdraws:
                # Use earliest withdraw
                withdraw_time = min(future_withdraws)
                holding_time = (withdraw_time - deposit_time) / 86400  # Convert to days
                holding_times.append(holding_time)
        
        return statistics.mean(holding_times) if holding_times else 0.0
    
    def calculate_lp_features(self, transactions: list[TransactionDict]) -> dict[str, float]:
        """
        Calculate LP-specific features from transaction data.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Dictionary with LP features
        """
        if not transactions:
            return {}
        
        # Filter LP transactions using more efficient filtering
        lp_transactions = [tx for tx in transactions if tx.get('type') == 'lp']
        deposits = [tx for tx in lp_transactions if tx.get('action') == 'deposit']
        withdraws = [tx for tx in lp_transactions if tx.get('action') == 'withdraw']
        
        # Basic metrics with improved performance
        total_deposit_usd = sum(tx.get('amount_usd', 0.0) for tx in deposits)
        total_withdraw_usd = sum(tx.get('amount_usd', 0.0) for tx in withdraws)
        num_deposits = len(deposits)
        num_withdraws = len(withdraws)
        
        # Calculate withdraw ratio
        withdraw_ratio = total_withdraw_usd / total_deposit_usd if total_deposit_usd > 0 else 0.0
        
        # Calculate account age using cached timestamp parsing
        if lp_transactions:
            timestamps = [
                parsed_time
                for tx in lp_transactions
                if (parsed_time := self._parse_timestamp(tx.get('timestamp'))) is not None
            ]
            
            if len(timestamps) >= 2:
                account_age_days = (max(timestamps) - min(timestamps)) / 86400
            else:
                account_age_days = 0.0
        else:
            account_age_days = 0.0
        
        # Calculate average holding time
        avg_hold_time_days = self.calculate_holding_time(deposits, withdraws)
        
        # Unique pools
        unique_pools = len(set(tx['pool_id'] for tx in lp_transactions if tx.get('pool_id')))
        
        return {
            'total_deposit_usd': total_deposit_usd,
            'total_withdraw_usd': total_withdraw_usd,
            'num_deposits': num_deposits,
            'num_withdraws': num_withdraws,
            'withdraw_ratio': withdraw_ratio,
            'avg_hold_time_days': avg_hold_time_days,
            'account_age_days': account_age_days,
            'unique_pools': unique_pools
        }
    
    def calculate_lp_score(self, features: dict[str, float]) -> tuple[float, ScoreBreakdown]:
        """
        Calculate LP reputation score based on features.
        
        Returns:
            Tuple of (score, score_breakdown)
        """
        if not features:
            empty_breakdown = ScoreBreakdown(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            return 0.0, empty_breakdown
        
        # Volume score (0-300 points) with improved calculation
        volume_score = min(features.get('total_deposit_usd', 0.0) / 10000 * 300, 300)
        
        # Frequency score (0-200 points)
        frequency_score = min(features.get('num_deposits', 0) * 20, 200)
        
        # Retention score (0-250 points) - higher is better for low withdraw ratio
        retention_score = max(0, (1 - features.get('withdraw_ratio', 0.0)) * 250)
        
        # Holding time score (0-150 points)
        holding_score = min(features.get('avg_hold_time_days', 0.0) / 30 * 150, 150)
        
        # Diversity score (0-100 points)
        diversity_score = min(features.get('unique_pools', 0) * 20, 100)
        
        total_score = volume_score + frequency_score + retention_score + holding_score + diversity_score
        
        breakdown = ScoreBreakdown(
            volume_score=volume_score,
            frequency_score=frequency_score,
            retention_score=retention_score,
            holding_score=holding_score,
            diversity_score=diversity_score,
            total_score=total_score
        )
        
        return total_score, breakdown
    
    @lru_cache(maxsize=64)
    def _is_stable_token(self, token: str) -> bool:
        """Check if token is a stablecoin with caching."""
        return token.upper() in self.stable_tokens
    
    def calculate_token_diversity(self, swaps: list[Dict]) -> int:
        """
        Calculate token diversity score based on variety of tokens traded.
        Uses modern Python features for better performance.
        """
        if not swaps:
            return 0
        
        # Get all unique tokens using set comprehensions
        tokens_in = {tx['token_in_symbol'] for tx in swaps if tx.get('token_in_symbol')}
        tokens_out = {tx['token_out_symbol'] for tx in swaps if tx.get('token_out_symbol')}
        all_tokens = tokens_in.union(tokens_out)
        
        # Count stable vs volatile tokens using cached method
        stable_count = sum(1 for token in all_tokens if self._is_stable_token(token))
        volatile_count = len(all_tokens) - stable_count
        
        # Weighted diversity score (volatile tokens worth more)
        diversity_score = stable_count * 10 + volatile_count * 15
        
        return min(diversity_score, 150)  # Cap at 150 points
    
    def calculate_swap_frequency(self, swaps: list[Dict]) -> float:
        """
        Calculate swap frequency score based on trading patterns.
        Uses cached timestamp parsing for better performance.
        """
        if not swaps or len(swaps) < 2:
            return 0.0
        
        # Parse timestamps using cached method
        parsed_swaps = [
            {**swap, 'parsed_timestamp': parsed_time}
            for swap in swaps
            if (parsed_time := self._parse_timestamp(swap.get('timestamp'))) is not None
        ]
        
        if len(parsed_swaps) < 2:
            return 0.0
        
        # Calculate time between swaps
        swaps_sorted = sorted(parsed_swaps, key=lambda x: x['parsed_timestamp'])
        time_diffs = []
        
        for i in range(1, len(swaps_sorted)):
            time_diff = swaps_sorted[i]['parsed_timestamp'] - swaps_sorted[i-1]['parsed_timestamp']
            time_diffs.append(time_diff)
        
        # Convert to hours
        time_diffs_hours = [diff / 3600 for diff in time_diffs]
        
        # Calculate average time between swaps
        avg_time_between_swaps = statistics.mean(time_diffs_hours)
        
        # Score based on frequency (lower time = higher score)
        if avg_time_between_swaps <= 1:  # Less than 1 hour
            return 100.0
        elif avg_time_between_swaps <= 24:  # Less than 1 day
            return 80.0
        elif avg_time_between_swaps <= 168:  # Less than 1 week
            return 60.0
        elif avg_time_between_swaps <= 720:  # Less than 1 month
            return 40.0
        else:
            return 20.0
    
    def calculate_swap_features(self, transactions: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate swap-specific features from transaction data.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Dictionary with swap features
        """
        if not transactions:
            return {}
        
        # Filter swap transactions
        swaps = [tx for tx in transactions if tx.get('type') == 'swap']
        
        if not swaps:
            return {
                'total_swap_volume': 0.0,
                'num_swaps': 0,
                'unique_tokens_swapped': 0,
                'unique_pools_swapped': 0,
                'avg_swap_size': 0.0,
                'token_diversity_score': 0,
                'swap_frequency_score': 0.0
            }
        
        # Basic swap metrics
        total_swap_volume = sum(tx.get('amount_usd', 0) for tx in swaps)
        num_swaps = len(swaps)
        avg_swap_size = total_swap_volume / num_swaps if num_swaps > 0 else 0
        
        # Token diversity
        unique_tokens = set()
        for tx in swaps:
            token_in = tx.get('token_in_symbol', '')
            token_out = tx.get('token_out_symbol', '')
            if token_in:
                unique_tokens.add(token_in)
            if token_out:
                unique_tokens.add(token_out)
        
        unique_tokens_swapped = len(unique_tokens)
        
        # Pool diversity
        unique_pools = set()
        for tx in swaps:
            pool_id = tx.get('pool_id', tx.get('pool_address', ''))
            if pool_id:
                unique_pools.add(pool_id)
        unique_pools_swapped = len(unique_pools)
        
        # Token diversity analysis
        token_diversity_score = self.calculate_token_diversity(swaps)
        
        # Swap frequency analysis
        swap_frequency_score = self.calculate_swap_frequency(swaps)
        
        return {
            'total_swap_volume': total_swap_volume,
            'num_swaps': num_swaps,
            'unique_tokens_swapped': unique_tokens_swapped,
            'unique_pools_swapped': unique_pools_swapped,
            'avg_swap_size': avg_swap_size,
            'token_diversity_score': token_diversity_score,
            'swap_frequency_score': swap_frequency_score
        }
    
    def calculate_swap_score(self, features: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
        """Calculate swap score based on features."""
        if not features:
            return 0.0, {}
        
        # Volume score (0-100 points)
        volume_score = min(features.get('total_swap_volume', 0) / 10000 * 100, 100)
        
        # Frequency score (0-100 points)
        frequency_score = min(features.get('num_swaps', 0) / 50 * 100, 100)
        
        # Token diversity score (0-100 points)
        diversity_score = min(features.get('token_diversity_score', 0) / 20 * 100, 100)
        
        # Activity score (0-100 points)
        activity_score = min(features.get('swap_frequency_score', 0) / 50 * 100, 100)
        
        # Pool diversity score (0-100 points)
        pool_diversity_score = min(features.get('unique_pools_swapped', 0) / 10 * 100, 100)
        
        # Calculate total score
        total_score = (
            volume_score * 0.3 +
            frequency_score * 0.2 +
            diversity_score * 0.2 +
            activity_score * 0.15 +
            pool_diversity_score * 0.15
        )
        
        breakdown = {
            'volume_score': volume_score,
            'frequency_score': frequency_score,
            'diversity_score': diversity_score,
            'activity_score': activity_score,
            'pool_diversity_score': pool_diversity_score
        }
        
        return total_score, breakdown
    
    def generate_user_tags(self, lp_features: Dict[str, float], swap_features: Dict[str, float]) -> List[str]:
        """Generate user tags based on LP and Swap behavior."""
        tags = []
        
        # LP Tags
        total_deposit = lp_features.get('total_deposit_usd', 0)
        if total_deposit >= 100000:
            tags.append('Whale LP')
        elif total_deposit >= 50000:
            tags.append('Large LP')
        elif total_deposit >= 10000:
            tags.append('Medium LP')
        elif total_deposit >= 1000:
            tags.append('Small LP')
        
        # Holding behavior tags
        avg_holding_time = lp_features.get('avg_hold_time_days', 0)
        if avg_holding_time >= 90:
            tags.append('Long-term Holder')
        elif avg_holding_time >= 30:
            tags.append('Medium-term Holder')
        
        # Swap Tags
        total_volume = swap_features.get('total_swap_volume', 0)
        if total_volume >= 500000:
            tags.append('Whale Trader')
        elif total_volume >= 100000:
            tags.append('Large Trader')
        
        # Trading frequency tags
        num_swaps = swap_features.get('num_swaps', 0)
        if num_swaps >= 100:
            tags.append('High Frequency Trader')
        elif num_swaps >= 50:
            tags.append('Active Trader')
        
        # Diversity tags
        token_diversity = swap_features.get('token_diversity_score', 0)
        if token_diversity >= 15:
            tags.append('Diversified Trader')
        
        return tags
    
    def calculate_final_score(self, lp_score: float, swap_score: float, lp_features: Dict, swap_features: Dict) -> Dict[str, Any]:
        """Calculate final combined score and generate user tags."""
        # Weighted combination (60% LP, 40% Swap)
        final_score = (lp_score * 0.6) + (swap_score * 0.4)
        
        # Normalize to z-score (simplified)
        zscore = (final_score - 50) / 25  # Assuming mean=50, std=25
        zscore = max(-3, min(3, zscore))  # Clamp between -3 and 3
        
        # Generate user tags
        user_tags = self.generate_user_tags(lp_features, swap_features)
        
        return {
            'zscore': round(zscore, 3),
            'lp_category': {
                'score': round(lp_score, 2),
                'features': lp_features,
                'tags': [tag for tag in user_tags if 'LP' in tag or 'Holder' in tag]
            },
            'swap_category': {
                'score': round(swap_score, 2),
                'features': swap_features,
                'tags': [tag for tag in user_tags if 'Trader' in tag]
            }
        }
    
    def process_wallet(self, wallet_address: str, protocol_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main pipeline function to process wallet and return complete scoring result."""
        try:
            logger.info(f"Processing wallet: {wallet_address}")
            
            # Step 1: Preprocess data
            transactions = self.preprocess_dex_transactions(protocol_data)
            
            if not transactions:
                logger.warning(f"No valid transactions found for wallet: {wallet_address}")
                return {
                    'zscore': 0.0,
                    'lp_category': {'score': 0.0, 'features': {}, 'tags': []},
                    'swap_category': {'score': 0.0, 'features': {}, 'tags': []}
                }
            
            # Step 2: Calculate LP features and score
            lp_features = self.calculate_lp_features(transactions)
            lp_score, lp_breakdown = self.calculate_lp_score(lp_features)
            
            # Step 3: Calculate Swap features and score
            swap_features = self.calculate_swap_features(transactions)
            swap_score, swap_breakdown = self.calculate_swap_score(swap_features)
            
            # Step 4: Calculate final score and generate tags
            result = self.calculate_final_score(lp_score, swap_score, lp_features, swap_features)
            
            logger.info(
                f"Wallet {wallet_address} processed successfully. "
                f"LP Score: {lp_score:.2f}, Swap Score: {swap_score:.2f}, "
                f"Final Z-Score: {result['zscore']}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing wallet {wallet_address}: {str(e)}")
            raise