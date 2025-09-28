"""
Market microstructure feature engineering.
Creates features from order book data, trade flow, and market microstructure.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta


class MicrostructureFeatures:
    """
    Market microstructure feature generator.
    
    Creates features from order book dynamics, trade flow patterns,
    and market microstructure indicators that complement our existing
    execution and routing systems.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.feature_cache = {}
        
        # Mock microstructure data for demonstration
        self.mock_microstructure_data = self._generate_mock_microstructure_data()
    
    def create_features(self, microstructure_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Create microstructure features from order book and trade data.
        
        Args:
            microstructure_data: DataFrame with microstructure data (optional)
            
        Returns:
            DataFrame with microstructure features
        """
        if microstructure_data is None:
            # Use mock data for demonstration
            microstructure_data = self.mock_microstructure_data
        
        features_df = pd.DataFrame(index=microstructure_data.index)
        
        # Order book features
        features_df = self._create_orderbook_features(features_df, microstructure_data)
        
        # Trade flow features
        features_df = self._create_trade_flow_features(features_df, microstructure_data)
        
        # Market impact features
        features_df = self._create_market_impact_features(features_df, microstructure_data)
        
        # Liquidity features
        features_df = self._create_liquidity_features(features_df, microstructure_data)
        
        # Cross-exchange features
        features_df = self._create_cross_exchange_features(features_df, microstructure_data)
        
        # Market maker features
        features_df = self._create_market_maker_features(features_df, microstructure_data)
        
        return features_df
    
    def _create_orderbook_features(self, features_df: pd.DataFrame,
                                 microstructure_data: pd.DataFrame) -> pd.DataFrame:
        """Create order book dynamics features."""
        
        # Spread features
        if 'bid_price' in microstructure_data.columns and 'ask_price' in microstructure_data.columns:
            features_df['bid_ask_spread'] = microstructure_data['ask_price'] - microstructure_data['bid_price']
            features_df['relative_spread'] = features_df['bid_ask_spread'] / microstructure_data['mid_price']
            features_df['spread_7d_ma'] = features_df['relative_spread'].rolling(7).mean()
            features_df['spread_30d_ma'] = features_df['relative_spread'].rolling(30).mean()
            features_df['wide_spread'] = (features_df['relative_spread'] > features_df['spread_7d_ma'] * 1.5).astype(int)
            features_df['tight_spread'] = (features_df['relative_spread'] < features_df['spread_7d_ma'] * 0.5).astype(int)
        
        # Order book imbalance
        if 'bid_volume' in microstructure_data.columns and 'ask_volume' in microstructure_data.columns:
            total_volume = microstructure_data['bid_volume'] + microstructure_data['ask_volume']
            features_df['orderbook_imbalance'] = (microstructure_data['bid_volume'] - microstructure_data['ask_volume']) / total_volume
            features_df['orderbook_imbalance_7d_ma'] = features_df['orderbook_imbalance'].rolling(7).mean()
            features_df['strong_bid_imbalance'] = (features_df['orderbook_imbalance'] > 0.3).astype(int)
            features_df['strong_ask_imbalance'] = (features_df['orderbook_imbalance'] < -0.3).astype(int)
        
        # Order book depth
        if 'bid_depth_5' in microstructure_data.columns and 'ask_depth_5' in microstructure_data.columns:
            features_df['total_depth_5'] = microstructure_data['bid_depth_5'] + microstructure_data['ask_depth_5']
            features_df['depth_imbalance_5'] = (microstructure_data['bid_depth_5'] - microstructure_data['ask_depth_5']) / features_df['total_depth_5']
            features_df['depth_7d_ma'] = features_df['total_depth_5'].rolling(7).mean()
            features_df['low_depth'] = (features_df['total_depth_5'] < features_df['depth_7d_ma'] * 0.5).astype(int)
        
        # Order book volatility
        if 'mid_price' in microstructure_data.columns:
            features_df['mid_price_volatility'] = microstructure_data['mid_price'].rolling(5).std()
            features_df['mid_price_volatility_7d_ma'] = features_df['mid_price_volatility'].rolling(7).mean()
            features_df['high_mid_price_volatility'] = (features_df['mid_price_volatility'] > features_df['mid_price_volatility_7d_ma'] * 2).astype(int)
        
        return features_df
    
    def _create_trade_flow_features(self, features_df: pd.DataFrame,
                                  microstructure_data: pd.DataFrame) -> pd.DataFrame:
        """Create trade flow and execution features."""
        
        # Trade size features
        if 'trade_size' in microstructure_data.columns:
            features_df['avg_trade_size'] = microstructure_data['trade_size'].rolling(10).mean()
            features_df['trade_size_7d_ma'] = features_df['avg_trade_size'].rolling(7).mean()
            features_df['large_trades'] = (microstructure_data['trade_size'] > features_df['avg_trade_size'] * 2).astype(int)
            features_df['small_trades'] = (microstructure_data['trade_size'] < features_df['avg_trade_size'] * 0.5).astype(int)
        
        # Trade frequency
        if 'trade_count' in microstructure_data.columns:
            features_df['trade_frequency'] = microstructure_data['trade_count']
            features_df['trade_frequency_7d_ma'] = features_df['trade_frequency'].rolling(7).mean()
            features_df['high_trade_frequency'] = (features_df['trade_frequency'] > features_df['trade_frequency_7d_ma'] * 1.5).astype(int)
        
        # Trade direction
        if 'buy_trades' in microstructure_data.columns and 'sell_trades' in microstructure_data.columns:
            total_trades = microstructure_data['buy_trades'] + microstructure_data['sell_trades']
            features_df['buy_ratio'] = microstructure_data['buy_trades'] / total_trades
            features_df['sell_ratio'] = microstructure_data['sell_trades'] / total_trades
            features_df['trade_imbalance'] = features_df['buy_ratio'] - features_df['sell_ratio']
            features_df['buy_imbalance'] = (features_df['trade_imbalance'] > 0.2).astype(int)
            features_df['sell_imbalance'] = (features_df['trade_imbalance'] < -0.2).astype(int)
        
        # Trade clustering
        if 'trade_size' in microstructure_data.columns and 'trade_count' in microstructure_data.columns:
            features_df['trade_clustering'] = microstructure_data['trade_count'] / microstructure_data['trade_size']
            features_df['trade_clustering_7d_ma'] = features_df['trade_clustering'].rolling(7).mean()
            features_df['high_clustering'] = (features_df['trade_clustering'] > features_df['trade_clustering_7d_ma'] * 1.5).astype(int)
        
        return features_df
    
    def _create_market_impact_features(self, features_df: pd.DataFrame,
                                     microstructure_data: pd.DataFrame) -> pd.DataFrame:
        """Create market impact and price impact features."""
        
        # Price impact
        if 'price_impact_1pct' in microstructure_data.columns:
            features_df['price_impact_1pct_7d_ma'] = microstructure_data['price_impact_1pct'].rolling(7).mean()
            features_df['price_impact_1pct_30d_ma'] = microstructure_data['price_impact_1pct'].rolling(30).mean()
            features_df['high_price_impact'] = (microstructure_data['price_impact_1pct'] > features_df['price_impact_1pct_7d_ma'] * 1.5).astype(int)
        
        if 'price_impact_5pct' in microstructure_data.columns:
            features_df['price_impact_5pct_7d_ma'] = microstructure_data['price_impact_5pct'].rolling(7).mean()
            features_df['price_impact_5pct_30d_ma'] = microstructure_data['price_impact_5pct'].rolling(30).mean()
        
        # Temporary vs permanent impact
        if 'temporary_impact' in microstructure_data.columns and 'permanent_impact' in microstructure_data.columns:
            features_df['impact_ratio'] = microstructure_data['temporary_impact'] / microstructure_data['permanent_impact']
            features_df['impact_ratio_7d_ma'] = features_df['impact_ratio'].rolling(7).mean()
            features_df['high_temp_impact'] = (features_df['impact_ratio'] > 2).astype(int)
            features_df['high_perm_impact'] = (features_df['impact_ratio'] < 0.5).astype(int)
        
        # Market resilience
        if 'resilience_time' in microstructure_data.columns:
            features_df['resilience_time_7d_ma'] = microstructure_data['resilience_time'].rolling(7).mean()
            features_df['resilience_time_30d_ma'] = microstructure_data['resilience_time'].rolling(30).mean()
            features_df['fast_resilience'] = (microstructure_data['resilience_time'] < features_df['resilience_time_7d_ma'] * 0.5).astype(int)
            features_df['slow_resilience'] = (microstructure_data['resilience_time'] > features_df['resilience_time_7d_ma'] * 2).astype(int)
        
        return features_df
    
    def _create_liquidity_features(self, features_df: pd.DataFrame,
                                 microstructure_data: pd.DataFrame) -> pd.DataFrame:
        """Create liquidity and market depth features."""
        
        # Liquidity ratios
        if 'liquidity_score' in microstructure_data.columns:
            features_df['liquidity_score_7d_ma'] = microstructure_data['liquidity_score'].rolling(7).mean()
            features_df['liquidity_score_30d_ma'] = microstructure_data['liquidity_score'].rolling(30).mean()
            features_df['high_liquidity'] = (microstructure_data['liquidity_score'] > features_df['liquidity_score_7d_ma'] * 1.2).astype(int)
            features_df['low_liquidity'] = (microstructure_data['liquidity_score'] < features_df['liquidity_score_7d_ma'] * 0.8).astype(int)
        
        # Market depth at different levels
        depth_columns = [col for col in microstructure_data.columns if 'depth_' in col]
        for col in depth_columns:
            level = col.split('_')[-1]
            features_df[f'{col}_7d_ma'] = microstructure_data[col].rolling(7).mean()
            features_df[f'{col}_30d_ma'] = microstructure_data[col].rolling(30).mean()
            features_df[f'{col}_ratio_7d'] = microstructure_data[col] / features_df[f'{col}_7d_ma']
        
        # Liquidity fragmentation
        if 'venue_count' in microstructure_data.columns:
            features_df['venue_count_7d_ma'] = microstructure_data['venue_count'].rolling(7).mean()
            features_df['high_fragmentation'] = (microstructure_data['venue_count'] > features_df['venue_count_7d_ma'] * 1.2).astype(int)
            features_df['low_fragmentation'] = (microstructure_data['venue_count'] < features_df['venue_count_7d_ma'] * 0.8).astype(int)
        
        # Liquidity concentration
        if 'top_3_venue_share' in microstructure_data.columns:
            features_df['liquidity_concentration'] = microstructure_data['top_3_venue_share']
            features_df['liquidity_concentration_7d_ma'] = features_df['liquidity_concentration'].rolling(7).mean()
            features_df['high_concentration'] = (features_df['liquidity_concentration'] > 0.8).astype(int)
            features_df['low_concentration'] = (features_df['liquidity_concentration'] < 0.6).astype(int)
        
        return features_df
    
    def _create_cross_exchange_features(self, features_df: pd.DataFrame,
                                      microstructure_data: pd.DataFrame) -> pd.DataFrame:
        """Create cross-exchange arbitrage and spread features."""
        
        # Cross-exchange spreads
        if 'cross_exchange_spread' in microstructure_data.columns:
            features_df['cross_exchange_spread_7d_ma'] = microstructure_data['cross_exchange_spread'].rolling(7).mean()
            features_df['cross_exchange_spread_30d_ma'] = microstructure_data['cross_exchange_spread'].rolling(30).mean()
            features_df['arbitrage_opportunity'] = (microstructure_data['cross_exchange_spread'] > features_df['cross_exchange_spread_7d_ma'] * 1.5).astype(int)
        
        # Funding rate spreads
        if 'funding_rate_spread' in microstructure_data.columns:
            features_df['funding_rate_spread_7d_ma'] = microstructure_data['funding_rate_spread'].rolling(7).mean()
            features_df['funding_rate_spread_30d_ma'] = microstructure_data['funding_rate_spread'].rolling(30).mean()
            features_df['funding_arbitrage'] = (abs(microstructure_data['funding_rate_spread']) > 0.01).astype(int)
        
        # Basis spreads
        if 'basis_spread' in microstructure_data.columns:
            features_df['basis_spread_7d_ma'] = microstructure_data['basis_spread'].rolling(7).mean()
            features_df['basis_spread_30d_ma'] = microstructure_data['basis_spread'].rolling(30).mean()
            features_df['basis_arbitrage'] = (abs(microstructure_data['basis_spread']) > features_df['basis_spread_7d_ma'] * 2).astype(int)
        
        # Exchange flow patterns
        if 'exchange_flow_imbalance' in microstructure_data.columns:
            features_df['exchange_flow_imbalance_7d_ma'] = microstructure_data['exchange_flow_imbalance'].rolling(7).mean()
            features_df['strong_exchange_flow'] = (abs(microstructure_data['exchange_flow_imbalance']) > 0.3).astype(int)
        
        return features_df
    
    def _create_market_maker_features(self, features_df: pd.DataFrame,
                                    microstructure_data: pd.DataFrame) -> pd.DataFrame:
        """Create market maker behavior features."""
        
        # Market maker activity
        if 'market_maker_ratio' in microstructure_data.columns:
            features_df['market_maker_ratio_7d_ma'] = microstructure_data['market_maker_ratio'].rolling(7).mean()
            features_df['market_maker_ratio_30d_ma'] = microstructure_data['market_maker_ratio'].rolling(30).mean()
            features_df['high_mm_activity'] = (microstructure_data['market_maker_ratio'] > features_df['market_maker_ratio_7d_ma'] * 1.2).astype(int)
            features_df['low_mm_activity'] = (microstructure_data['market_maker_ratio'] < features_df['market_maker_ratio_7d_ma'] * 0.8).astype(int)
        
        # Market maker profitability
        if 'mm_profitability' in microstructure_data.columns:
            features_df['mm_profitability_7d_ma'] = microstructure_data['mm_profitability'].rolling(7).mean()
            features_df['mm_profitability_30d_ma'] = microstructure_data['mm_profitability'].rolling(30).mean()
            features_df['high_mm_profit'] = (microstructure_data['mm_profitability'] > features_df['mm_profitability_7d_ma'] * 1.5).astype(int)
        
        # Market maker inventory
        if 'mm_inventory_imbalance' in microstructure_data.columns:
            features_df['mm_inventory_imbalance_7d_ma'] = microstructure_data['mm_inventory_imbalance'].rolling(7).mean()
            features_df['mm_inventory_imbalance_30d_ma'] = microstructure_data['mm_inventory_imbalance'].rolling(30).mean()
            features_df['mm_long_inventory'] = (microstructure_data['mm_inventory_imbalance'] > 0.2).astype(int)
            features_df['mm_short_inventory'] = (microstructure_data['mm_inventory_imbalance'] < -0.2).astype(int)
        
        # Market maker competition
        if 'mm_competition_index' in microstructure_data.columns:
            features_df['mm_competition_index_7d_ma'] = microstructure_data['mm_competition_index'].rolling(7).mean()
            features_df['high_mm_competition'] = (microstructure_data['mm_competition_index'] > features_df['mm_competition_index_7d_ma'] * 1.2).astype(int)
            features_df['low_mm_competition'] = (microstructure_data['mm_competition_index'] < features_df['mm_competition_index_7d_ma'] * 0.8).astype(int)
        
        return features_df
    
    def _generate_mock_microstructure_data(self) -> pd.DataFrame:
        """Generate mock microstructure data for demonstration."""
        dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='H')
        
        # Generate realistic mock data
        np.random.seed(42)
        n_points = len(dates)
        
        mock_data = pd.DataFrame(index=dates)
        
        # Order book data
        base_price = 50000.0
        mock_data['mid_price'] = base_price + np.cumsum(np.random.normal(0, 10, n_points))
        mock_data['bid_price'] = mock_data['mid_price'] - np.random.uniform(0.5, 2.0, n_points)
        mock_data['ask_price'] = mock_data['mid_price'] + np.random.uniform(0.5, 2.0, n_points)
        
        # Order book volumes
        mock_data['bid_volume'] = np.random.uniform(10, 100, n_points)
        mock_data['ask_volume'] = np.random.uniform(10, 100, n_points)
        mock_data['bid_depth_5'] = np.random.uniform(50, 500, n_points)
        mock_data['ask_depth_5'] = np.random.uniform(50, 500, n_points)
        
        # Trade data
        mock_data['trade_size'] = np.random.uniform(0.1, 10.0, n_points)
        mock_data['trade_count'] = np.random.poisson(100, n_points)
        mock_data['buy_trades'] = np.random.binomial(mock_data['trade_count'], 0.5)
        mock_data['sell_trades'] = mock_data['trade_count'] - mock_data['buy_trades']
        
        # Market impact
        mock_data['price_impact_1pct'] = np.random.uniform(0.001, 0.01, n_points)
        mock_data['price_impact_5pct'] = np.random.uniform(0.005, 0.05, n_points)
        mock_data['temporary_impact'] = np.random.uniform(0.002, 0.02, n_points)
        mock_data['permanent_impact'] = np.random.uniform(0.001, 0.01, n_points)
        mock_data['resilience_time'] = np.random.uniform(1, 60, n_points)  # seconds
        
        # Liquidity metrics
        mock_data['liquidity_score'] = np.random.uniform(0.5, 1.0, n_points)
        mock_data['venue_count'] = np.random.poisson(15, n_points)
        mock_data['top_3_venue_share'] = np.random.uniform(0.6, 0.9, n_points)
        
        # Cross-exchange data
        mock_data['cross_exchange_spread'] = np.random.uniform(0, 0.005, n_points)
        mock_data['funding_rate_spread'] = np.random.normal(0, 0.002, n_points)
        mock_data['basis_spread'] = np.random.normal(0, 0.001, n_points)
        mock_data['exchange_flow_imbalance'] = np.random.normal(0, 0.2, n_points)
        
        # Market maker data
        mock_data['market_maker_ratio'] = np.random.uniform(0.3, 0.7, n_points)
        mock_data['mm_profitability'] = np.random.uniform(-0.001, 0.005, n_points)
        mock_data['mm_inventory_imbalance'] = np.random.normal(0, 0.3, n_points)
        mock_data['mm_competition_index'] = np.random.uniform(0.5, 1.0, n_points)
        
        return mock_data
    
    def get_feature_summary(self, features_df: pd.DataFrame) -> Dict:
        """Get summary statistics of microstructure features."""
        numeric_features = features_df.select_dtypes(include=[np.number])
        
        return {
            'total_features': len(numeric_features.columns),
            'missing_values': numeric_features.isnull().sum().sum(),
            'feature_types': {
                'orderbook_features': len([col for col in numeric_features.columns if any(x in col for x in ['spread', 'imbalance', 'depth'])]),
                'trade_flow_features': len([col for col in numeric_features.columns if any(x in col for x in ['trade', 'buy', 'sell', 'clustering'])]),
                'market_impact_features': len([col for col in numeric_features.columns if any(x in col for x in ['impact', 'resilience'])]),
                'liquidity_features': len([col for col in numeric_features.columns if any(x in col for x in ['liquidity', 'depth', 'fragmentation', 'concentration'])]),
                'cross_exchange_features': len([col for col in numeric_features.columns if any(x in col for x in ['cross_exchange', 'funding', 'basis', 'arbitrage'])]),
                'market_maker_features': len([col for col in numeric_features.columns if any(x in col for x in ['mm_', 'market_maker'])])
            }
        }
