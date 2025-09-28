"""
On-chain blockchain feature engineering.
Creates features from blockchain data for crypto trading strategies.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import requests
import time
from datetime import datetime, timezone, timedelta


class OnChainFeatures:
    """
    On-chain blockchain feature generator.
    
    Creates features from blockchain metrics that provide insights
    into network activity, holder behavior, and market sentiment.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.api_cache = {}
        self.cache_duration = 300  # 5 minutes
        
        # Mock data for demonstration (replace with real APIs in production)
        self.mock_onchain_data = self._generate_mock_onchain_data()
    
    def create_features(self, onchain_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Create on-chain features from blockchain data.
        
        Args:
            onchain_data: DataFrame with on-chain metrics (optional)
            
        Returns:
            DataFrame with on-chain features
        """
        if onchain_data is None:
            # Use mock data for demonstration
            onchain_data = self.mock_onchain_data
        
        features_df = pd.DataFrame(index=onchain_data.index)
        
        # Network activity features
        features_df = self._create_network_activity_features(features_df, onchain_data)
        
        # Holder behavior features
        features_df = self._create_holder_behavior_features(features_df, onchain_data)
        
        # Exchange flow features
        features_df = self._create_exchange_flow_features(features_df, onchain_data)
        
        # Mining features
        features_df = self._create_mining_features(features_df, onchain_data)
        
        # DeFi features
        features_df = self._create_defi_features(features_df, onchain_data)
        
        # Market sentiment features
        features_df = self._create_market_sentiment_features(features_df, onchain_data)
        
        return features_df
    
    def _create_network_activity_features(self, features_df: pd.DataFrame,
                                        onchain_data: pd.DataFrame) -> pd.DataFrame:
        """Create network activity features."""
        
        # Transaction volume features
        if 'transaction_count' in onchain_data.columns:
            features_df['tx_count_7d_ma'] = onchain_data['transaction_count'].rolling(7).mean()
            features_df['tx_count_30d_ma'] = onchain_data['transaction_count'].rolling(30).mean()
            features_df['tx_count_ratio_7d'] = onchain_data['transaction_count'] / features_df['tx_count_7d_ma']
            features_df['tx_count_ratio_30d'] = onchain_data['transaction_count'] / features_df['tx_count_30d_ma']
        
        # Transaction value features
        if 'transaction_volume_usd' in onchain_data.columns:
            features_df['tx_volume_7d_ma'] = onchain_data['transaction_volume_usd'].rolling(7).mean()
            features_df['tx_volume_30d_ma'] = onchain_data['transaction_volume_usd'].rolling(30).mean()
            features_df['tx_volume_ratio_7d'] = onchain_data['transaction_volume_usd'] / features_df['tx_volume_7d_ma']
            features_df['tx_volume_ratio_30d'] = onchain_data['transaction_volume_usd'] / features_df['tx_volume_30d_ma']
        
        # Active addresses
        if 'active_addresses' in onchain_data.columns:
            features_df['active_addresses_7d_ma'] = onchain_data['active_addresses'].rolling(7).mean()
            features_df['active_addresses_30d_ma'] = onchain_data['active_addresses'].rolling(30).mean()
            features_df['active_addresses_ratio_7d'] = onchain_data['active_addresses'] / features_df['active_addresses_7d_ma']
            features_df['active_addresses_ratio_30d'] = onchain_data['active_addresses'] / features_df['active_addresses_30d_ma']
        
        # Network utilization
        if 'transaction_count' in onchain_data.columns and 'active_addresses' in onchain_data.columns:
            features_df['tx_per_address'] = onchain_data['transaction_count'] / onchain_data['active_addresses']
            features_df['tx_per_address_7d_ma'] = features_df['tx_per_address'].rolling(7).mean()
        
        return features_df
    
    def _create_holder_behavior_features(self, features_df: pd.DataFrame,
                                       onchain_data: pd.DataFrame) -> pd.DataFrame:
        """Create holder behavior features."""
        
        # Address distribution
        if 'addresses_1k_plus' in onchain_data.columns:
            features_df['whale_addresses_7d_ma'] = onchain_data['addresses_1k_plus'].rolling(7).mean()
            features_df['whale_addresses_change'] = onchain_data['addresses_1k_plus'].pct_change()
        
        if 'addresses_10k_plus' in onchain_data.columns:
            features_df['mega_whale_addresses_7d_ma'] = onchain_data['addresses_10k_plus'].rolling(7).mean()
            features_df['mega_whale_addresses_change'] = onchain_data['addresses_10k_plus'].pct_change()
        
        # HODL waves (simplified)
        if 'addresses_1k_plus' in onchain_data.columns and 'active_addresses' in onchain_data.columns:
            features_df['whale_ratio'] = onchain_data['addresses_1k_plus'] / onchain_data['active_addresses']
            features_df['whale_ratio_7d_ma'] = features_df['whale_ratio'].rolling(7).mean()
        
        # Long-term holder metrics
        if 'hodl_waves_1y_plus' in onchain_data.columns:
            features_df['long_term_hodl_ratio'] = onchain_data['hodl_waves_1y_plus']
            features_df['long_term_hodl_7d_ma'] = features_df['long_term_hodl_ratio'].rolling(7).mean()
        
        # Supply in profit/loss
        if 'supply_in_profit' in onchain_data.columns:
            features_df['supply_profit_ratio'] = onchain_data['supply_in_profit']
            features_df['supply_profit_7d_ma'] = features_df['supply_profit_ratio'].rolling(7).mean()
            features_df['supply_profit_change'] = features_df['supply_profit_ratio'].pct_change()
        
        return features_df
    
    def _create_exchange_flow_features(self, features_df: pd.DataFrame,
                                     onchain_data: pd.DataFrame) -> pd.DataFrame:
        """Create exchange flow features."""
        
        # Exchange inflows/outflows
        if 'exchange_inflow' in onchain_data.columns:
            features_df['exchange_inflow_7d_ma'] = onchain_data['exchange_inflow'].rolling(7).mean()
            features_df['exchange_inflow_30d_ma'] = onchain_data['exchange_inflow'].rolling(30).mean()
            features_df['exchange_inflow_ratio_7d'] = onchain_data['exchange_inflow'] / features_df['exchange_inflow_7d_ma']
        
        if 'exchange_outflow' in onchain_data.columns:
            features_df['exchange_outflow_7d_ma'] = onchain_data['exchange_outflow'].rolling(7).mean()
            features_df['exchange_outflow_30d_ma'] = onchain_data['exchange_outflow'].rolling(30).mean()
            features_df['exchange_outflow_ratio_7d'] = onchain_data['exchange_outflow'] / features_df['exchange_outflow_7d_ma']
        
        # Net exchange flow
        if 'exchange_inflow' in onchain_data.columns and 'exchange_outflow' in onchain_data.columns:
            features_df['net_exchange_flow'] = onchain_data['exchange_outflow'] - onchain_data['exchange_inflow']
            features_df['net_exchange_flow_7d_ma'] = features_df['net_exchange_flow'].rolling(7).mean()
            features_df['positive_exchange_flow'] = (features_df['net_exchange_flow'] > 0).astype(int)
        
        # Exchange balance
        if 'exchange_balance' in onchain_data.columns:
            features_df['exchange_balance_7d_ma'] = onchain_data['exchange_balance'].rolling(7).mean()
            features_df['exchange_balance_change'] = onchain_data['exchange_balance'].pct_change()
            features_df['exchange_balance_ratio'] = onchain_data['exchange_balance'] / onchain_data.get('total_supply', 1)
        
        return features_df
    
    def _create_mining_features(self, features_df: pd.DataFrame,
                              onchain_data: pd.DataFrame) -> pd.DataFrame:
        """Create mining-related features."""
        
        # Hash rate
        if 'hash_rate' in onchain_data.columns:
            features_df['hash_rate_7d_ma'] = onchain_data['hash_rate'].rolling(7).mean()
            features_df['hash_rate_30d_ma'] = onchain_data['hash_rate'].rolling(30).mean()
            features_df['hash_rate_ratio_7d'] = onchain_data['hash_rate'] / features_df['hash_rate_7d_ma']
            features_df['hash_rate_ratio_30d'] = onchain_data['hash_rate'] / features_df['hash_rate_30d_ma']
        
        # Mining difficulty
        if 'difficulty' in onchain_data.columns:
            features_df['difficulty_7d_ma'] = onchain_data['difficulty'].rolling(7).mean()
            features_df['difficulty_30d_ma'] = onchain_data['difficulty'].rolling(30).mean()
            features_df['difficulty_change'] = onchain_data['difficulty'].pct_change()
        
        # Mining revenue
        if 'mining_revenue_usd' in onchain_data.columns:
            features_df['mining_revenue_7d_ma'] = onchain_data['mining_revenue_usd'].rolling(7).mean()
            features_df['mining_revenue_30d_ma'] = onchain_data['mining_revenue_usd'].rolling(30).mean()
            features_df['mining_revenue_ratio_7d'] = onchain_data['mining_revenue_usd'] / features_df['mining_revenue_7d_ma']
        
        # Hash price (revenue per hash)
        if 'hash_rate' in onchain_data.columns and 'mining_revenue_usd' in onchain_data.columns:
            features_df['hash_price'] = onchain_data['mining_revenue_usd'] / onchain_data['hash_rate']
            features_df['hash_price_7d_ma'] = features_df['hash_price'].rolling(7).mean()
        
        return features_df
    
    def _create_defi_features(self, features_df: pd.DataFrame,
                            onchain_data: pd.DataFrame) -> pd.DataFrame:
        """Create DeFi-related features."""
        
        # Total Value Locked (TVL)
        if 'defi_tvl_usd' in onchain_data.columns:
            features_df['defi_tvl_7d_ma'] = onchain_data['defi_tvl_usd'].rolling(7).mean()
            features_df['defi_tvl_30d_ma'] = onchain_data['defi_tvl_usd'].rolling(30).mean()
            features_df['defi_tvl_ratio_7d'] = onchain_data['defi_tvl_usd'] / features_df['defi_tvl_7d_ma']
            features_df['defi_tvl_ratio_30d'] = onchain_data['defi_tvl_usd'] / features_df['defi_tvl_30d_ma']
            features_df['defi_tvl_change'] = onchain_data['defi_tvl_usd'].pct_change()
        
        # DeFi protocol count
        if 'defi_protocol_count' in onchain_data.columns:
            features_df['defi_protocol_count_7d_ma'] = onchain_data['defi_protocol_count'].rolling(7).mean()
            features_df['defi_protocol_growth'] = onchain_data['defi_protocol_count'].pct_change()
        
        # Stablecoin supply
        if 'stablecoin_supply' in onchain_data.columns:
            features_df['stablecoin_supply_7d_ma'] = onchain_data['stablecoin_supply'].rolling(7).mean()
            features_df['stablecoin_supply_ratio_7d'] = onchain_data['stablecoin_supply'] / features_df['stablecoin_supply_7d_ma']
            features_df['stablecoin_supply_change'] = onchain_data['stablecoin_supply'].pct_change()
        
        return features_df
    
    def _create_market_sentiment_features(self, features_df: pd.DataFrame,
                                        onchain_data: pd.DataFrame) -> pd.DataFrame:
        """Create market sentiment features from on-chain data."""
        
        # Fear and Greed indicators
        if 'fear_greed_index' in onchain_data.columns:
            features_df['fear_greed_7d_ma'] = onchain_data['fear_greed_index'].rolling(7).mean()
            features_df['fear_greed_30d_ma'] = onchain_data['fear_greed_index'].rolling(30).mean()
            features_df['extreme_fear'] = (onchain_data['fear_greed_index'] < 20).astype(int)
            features_df['extreme_greed'] = (onchain_data['fear_greed_index'] > 80).astype(int)
        
        # Network value to transaction ratio (NVT)
        if 'network_value_usd' in onchain_data.columns and 'transaction_volume_usd' in onchain_data.columns:
            features_df['nvt_ratio'] = onchain_data['network_value_usd'] / onchain_data['transaction_volume_usd']
            features_df['nvt_7d_ma'] = features_df['nvt_ratio'].rolling(7).mean()
            features_df['nvt_30d_ma'] = features_df['nvt_ratio'].rolling(30).mean()
        
        # Market cap to realized value (MVRV)
        if 'market_cap_usd' in onchain_data.columns and 'realized_cap_usd' in onchain_data.columns:
            features_df['mvrv_ratio'] = onchain_data['market_cap_usd'] / onchain_data['realized_cap_usd']
            features_df['mvrv_7d_ma'] = features_df['mvrv_ratio'].rolling(7).mean()
            features_df['mvrv_30d_ma'] = features_df['mvrv_ratio'].rolling(30).mean()
            features_df['mvrv_overvalued'] = (features_df['mvrv_ratio'] > 3).astype(int)
            features_df['mvrv_undervalued'] = (features_df['mvrv_ratio'] < 1).astype(int)
        
        # Puell Multiple
        if 'mining_revenue_usd' in onchain_data.columns and 'market_cap_usd' in onchain_data.columns:
            features_df['puell_multiple'] = onchain_data['market_cap_usd'] / onchain_data['mining_revenue_usd']
            features_df['puell_7d_ma'] = features_df['puell_multiple'].rolling(7).mean()
            features_df['puell_30d_ma'] = features_df['puell_multiple'].rolling(30).mean()
        
        return features_df
    
    def _generate_mock_onchain_data(self) -> pd.DataFrame:
        """Generate mock on-chain data for demonstration."""
        dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
        
        # Generate realistic mock data
        np.random.seed(42)
        n_days = len(dates)
        
        mock_data = pd.DataFrame(index=dates)
        
        # Network activity
        mock_data['transaction_count'] = np.random.normal(300000, 50000, n_days)
        mock_data['transaction_volume_usd'] = np.random.normal(10_000_000_000, 2_000_000_000, n_days)
        mock_data['active_addresses'] = np.random.normal(800000, 100000, n_days)
        
        # Holder behavior
        mock_data['addresses_1k_plus'] = np.random.normal(2000, 200, n_days)
        mock_data['addresses_10k_plus'] = np.random.normal(500, 50, n_days)
        mock_data['hodl_waves_1y_plus'] = np.random.uniform(0.6, 0.8, n_days)
        mock_data['supply_in_profit'] = np.random.uniform(0.4, 0.9, n_days)
        
        # Exchange flows
        mock_data['exchange_inflow'] = np.random.normal(5000, 1000, n_days)
        mock_data['exchange_outflow'] = np.random.normal(4800, 1000, n_days)
        mock_data['exchange_balance'] = np.random.normal(2_500_000, 100_000, n_days)
        
        # Mining
        mock_data['hash_rate'] = np.random.normal(150_000_000, 10_000_000, n_days)
        mock_data['difficulty'] = np.random.normal(20_000_000_000_000, 1_000_000_000_000, n_days)
        mock_data['mining_revenue_usd'] = np.random.normal(15_000_000, 3_000_000, n_days)
        
        # DeFi
        mock_data['defi_tvl_usd'] = np.random.normal(50_000_000_000, 5_000_000_000, n_days)
        mock_data['defi_protocol_count'] = np.random.normal(200, 20, n_days)
        mock_data['stablecoin_supply'] = np.random.normal(120_000_000_000, 10_000_000_000, n_days)
        
        # Market metrics
        mock_data['fear_greed_index'] = np.random.uniform(20, 80, n_days)
        mock_data['network_value_usd'] = np.random.normal(800_000_000_000, 100_000_000_000, n_days)
        mock_data['market_cap_usd'] = np.random.normal(800_000_000_000, 100_000_000_000, n_days)
        mock_data['realized_cap_usd'] = np.random.normal(400_000_000_000, 50_000_000_000, n_days)
        mock_data['total_supply'] = np.random.normal(19_500_000, 1000, n_days)
        
        # Ensure positive values
        mock_data = mock_data.abs()
        
        return mock_data
    
    def fetch_real_onchain_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch real on-chain data from APIs (placeholder implementation).
        
        In production, this would integrate with:
        - Glassnode API
        - CoinMetrics API
        - Blockchain.info API
        - Custom blockchain node queries
        """
        # This is a placeholder - in production you would:
        # 1. Make API calls to data providers
        # 2. Parse and clean the data
        # 3. Return structured DataFrame
        
        print(f"Fetching real on-chain data for {symbol} from {start_date} to {end_date}")
        print("Note: Using mock data for demonstration")
        
        return self.mock_onchain_data
    
    def get_feature_summary(self, features_df: pd.DataFrame) -> Dict:
        """Get summary statistics of on-chain features."""
        numeric_features = features_df.select_dtypes(include=[np.number])
        
        return {
            'total_features': len(numeric_features.columns),
            'missing_values': numeric_features.isnull().sum().sum(),
            'feature_types': {
                'network_features': len([col for col in numeric_features.columns if any(x in col for x in ['tx_', 'active_', 'addresses'])]),
                'holder_features': len([col for col in numeric_features.columns if any(x in col for x in ['whale', 'hodl', 'supply_profit'])]),
                'exchange_features': len([col for col in numeric_features.columns if 'exchange' in col]),
                'mining_features': len([col for col in numeric_features.columns if any(x in col for x in ['hash_', 'difficulty', 'mining'])]),
                'defi_features': len([col for col in numeric_features.columns if 'defi' in col]),
                'sentiment_features': len([col for col in numeric_features.columns if any(x in col for x in ['fear_greed', 'nvt', 'mvrv', 'puell'])])
            }
        }
