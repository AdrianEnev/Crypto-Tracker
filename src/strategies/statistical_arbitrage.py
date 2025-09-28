"""
Statistical arbitrage and pairs trading strategy.
Implements cointegration tests, mean reversion signals, and dynamic hedging.
"""

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from .base import BaseStrategy


class StatisticalArbitrageStrategy(BaseStrategy):
    """
    Statistical arbitrage strategy based on cointegration and mean reversion.
    
    Config params:
    - lookback_period: int = 252 (trading days for analysis)
    - z_score_threshold: float = 2.0 (entry threshold)
    - z_score_exit: float = 0.5 (exit threshold)
    - cointegration_threshold: float = 0.05 (p-value threshold for cointegration)
    - adf_threshold: float = 0.05 (p-value threshold for stationarity)
    - max_pairs: int = 5 (maximum number of pairs to trade)
    - hedge_ratio_method: str = "ols" | "kalman" | "rolling"
    - position_size_method: str = "fixed" | "volatility_adjusted" | "kelly"
    - rebalance_frequency: int = 5 (days between hedge ratio updates)
    - stop_loss_mult: float = 3.0 (stop loss as multiple of entry z-score)
    - take_profit_mult: float = 2.0 (take profit as multiple of entry z-score)
    """
    
    def __init__(self, strategy_config: dict):
        super().__init__(strategy_config)
        
        # Core parameters
        self.lookback_period = int(self.config.get("lookback_period", 252))
        self.z_score_threshold = float(self.config.get("z_score_threshold", 2.0))
        self.z_score_exit = float(self.config.get("z_score_exit", 0.5))
        self.cointegration_threshold = float(self.config.get("cointegration_threshold", 0.05))
        self.adf_threshold = float(self.config.get("adf_threshold", 0.05))
        self.max_pairs = int(self.config.get("max_pairs", 5))
        
        # Hedge ratio calculation
        self.hedge_ratio_method = self.config.get("hedge_ratio_method", "ols")
        self.position_size_method = self.config.get("position_size_method", "fixed")
        self.rebalance_frequency = int(self.config.get("rebalance_frequency", 5))
        
        # Risk management
        self.stop_loss_mult = float(self.config.get("stop_loss_mult", 3.0))
        self.take_profit_mult = float(self.config.get("take_profit_mult", 2.0))
        
        # Internal state
        self.pairs_data = {}
        self.hedge_ratios = {}
        self.last_rebalance = 0
        
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate statistical arbitrage signals for multiple asset pairs.
        
        Args:
            data: DataFrame with columns for different assets (OHLCV data)
            
        Returns:
            DataFrame with signals for each asset pair
        """
        signals = pd.DataFrame(index=data.index)
        signals["signal"] = 0
        
        if len(data) < self.lookback_period:
            return signals
        
        # Identify potential pairs (simplified - in practice, use correlation analysis)
        asset_columns = [col for col in data.columns if col.startswith(('close_', 'price_'))]
        
        if len(asset_columns) < 2:
            return signals
        
        # For demo purposes, use first two assets as a pair
        if len(asset_columns) >= 2:
            asset1_col = asset_columns[0]
            asset2_col = asset_columns[1]
            
            pair_signals = self._analyze_pair(
                data[asset1_col].values,
                data[asset2_col].values,
                data.index
            )
            
            # Combine signals (simplified approach)
            signals["signal"] = pair_signals
        
        return signals
    
    def _analyze_pair(
        self, 
        asset1_prices: np.ndarray, 
        asset2_prices: np.ndarray, 
        timestamps: pd.Index
    ) -> pd.Series:
        """Analyze a single asset pair for statistical arbitrage opportunities."""
        signals = pd.Series(0, index=timestamps)
        
        if len(asset1_prices) < self.lookback_period:
            return signals
        
        # Calculate returns
        asset1_returns = np.diff(np.log(asset1_prices))
        asset2_returns = np.diff(np.log(asset2_prices))
        
        # Test for cointegration
        if not self._test_cointegration(asset1_prices, asset2_prices):
            return signals
        
        # Calculate hedge ratio
        hedge_ratio = self._calculate_hedge_ratio(asset1_prices, asset2_prices)
        
        if hedge_ratio is None:
            return signals
        
        # Calculate spread
        spread = asset1_prices - hedge_ratio * asset2_prices
        
        # Test for stationarity
        if not self._test_stationarity(spread):
            return signals
        
        # Calculate z-scores
        z_scores = self._calculate_z_scores(spread)
        
        # Generate signals based on z-scores
        for i, z_score in enumerate(z_scores):
            if i < len(signals):
                if abs(z_score) > self.z_score_threshold:
                    # Entry signal
                    signals.iloc[i] = -1 if z_score > 0 else 1
                elif abs(z_score) < self.z_score_exit:
                    # Exit signal
                    signals.iloc[i] = 0
        
        return signals
    
    def _test_cointegration(self, prices1: np.ndarray, prices2: np.ndarray) -> bool:
        """Test for cointegration between two price series."""
        try:
            # Engle-Granger cointegration test
            # Step 1: Run OLS regression
            X = np.column_stack([np.ones(len(prices2)), prices2])
            beta = np.linalg.lstsq(X, prices1, rcond=None)[0]
            
            # Step 2: Calculate residuals
            residuals = prices1 - beta[0] - beta[1] * prices2
            
            # Step 3: ADF test on residuals
            adf_stat, p_value, _, _, _, _ = stats.adfuller(residuals, maxlag=1)
            
            return p_value < self.cointegration_threshold
            
        except Exception:
            return False
    
    def _test_stationarity(self, series: np.ndarray) -> bool:
        """Test for stationarity using ADF test."""
        try:
            adf_stat, p_value, _, _, _, _ = stats.adfuller(series, maxlag=1)
            return p_value < self.adf_threshold
        except Exception:
            return False
    
    def _calculate_hedge_ratio(self, prices1: np.ndarray, prices2: np.ndarray) -> Optional[float]:
        """Calculate hedge ratio using specified method."""
        try:
            if self.hedge_ratio_method == "ols":
                return self._ols_hedge_ratio(prices1, prices2)
            elif self.hedge_ratio_method == "rolling":
                return self._rolling_hedge_ratio(prices1, prices2)
            else:
                return self._ols_hedge_ratio(prices1, prices2)
        except Exception:
            return None
    
    def _ols_hedge_ratio(self, prices1: np.ndarray, prices2: np.ndarray) -> float:
        """Calculate hedge ratio using OLS regression."""
        try:
            # Ensure prices are positive
            prices1 = np.maximum(prices1, 1e-8)
            prices2 = np.maximum(prices2, 1e-8)
            
            # Use log prices for better numerical stability
            log_prices1 = np.log(prices1)
            log_prices2 = np.log(prices2)
            
            # OLS regression: log(p1) = alpha + beta * log(p2) + error
            X = np.column_stack([np.ones(len(log_prices2)), log_prices2])
            
            # Use more robust regression
            try:
                beta = np.linalg.lstsq(X, log_prices1, rcond=None)[0]
                hedge_ratio = beta[1]
                
                # Validate hedge ratio
                if np.isnan(hedge_ratio) or np.isinf(hedge_ratio):
                    return 1.0  # Default hedge ratio
                
                return float(hedge_ratio)
                
            except np.linalg.LinAlgError:
                # Fallback: use price ratio
                return float(np.mean(prices1) / np.mean(prices2))
                
        except Exception:
            return 1.0  # Default hedge ratio
    
    def _rolling_hedge_ratio(self, prices1: np.ndarray, prices2: np.ndarray) -> float:
        """Calculate rolling hedge ratio."""
        # Use a rolling window for dynamic hedge ratios
        window = min(60, len(prices1) // 4)
        
        if len(prices1) < window:
            return self._ols_hedge_ratio(prices1, prices2)
        
        # Use most recent window
        recent_prices1 = prices1[-window:]
        recent_prices2 = prices2[-window:]
        
        return self._ols_hedge_ratio(recent_prices1, recent_prices2)
    
    def _calculate_z_scores(self, spread: np.ndarray) -> np.ndarray:
        """Calculate rolling z-scores of the spread."""
        z_scores = np.full(len(spread), np.nan)
        
        window = min(60, len(spread) // 4)
        
        for i in range(window, len(spread)):
            window_spread = spread[i-window:i]
            mean_spread = np.mean(window_spread)
            std_spread = np.std(window_spread)
            
            if std_spread > 0:
                z_scores[i] = (spread[i] - mean_spread) / std_spread
        
        return z_scores
    
    def calculate_position_size(
        self, 
        z_score: float, 
        volatility: float, 
        available_capital: float
    ) -> float:
        """Calculate position size based on z-score and risk parameters."""
        if self.position_size_method == "fixed":
            return available_capital * 0.1  # 10% of capital
        
        elif self.position_size_method == "volatility_adjusted":
            # Adjust position size based on volatility
            base_size = available_capital * 0.1
            vol_adjustment = min(2.0, max(0.5, 0.15 / volatility))  # Target 15% volatility
            return base_size * vol_adjustment
        
        elif self.position_size_method == "kelly":
            # Kelly criterion based on z-score
            # Simplified: higher z-score = higher conviction = larger position
            conviction = min(1.0, abs(z_score) / self.z_score_threshold)
            kelly_fraction = conviction * 0.1  # Max 10% Kelly fraction
            return available_capital * kelly_fraction
        
        else:
            return available_capital * 0.1
    
    def get_risk_metrics(self, positions: Dict[str, float], prices: Dict[str, float]) -> Dict[str, float]:
        """Calculate risk metrics for current positions."""
        try:
            # Calculate portfolio value
            portfolio_value = sum(abs(pos * price) for pos, price in zip(positions.values(), prices.values()))
            
            # Calculate net exposure
            net_exposure = sum(positions.values())
            
            # Calculate gross exposure
            gross_exposure = sum(abs(pos) for pos in positions.values())
            
            # Calculate leverage
            leverage = gross_exposure / portfolio_value if portfolio_value > 0 else 0
            
            return {
                "portfolio_value": portfolio_value,
                "net_exposure": net_exposure,
                "gross_exposure": gross_exposure,
                "leverage": leverage,
                "net_gross_ratio": abs(net_exposure) / gross_exposure if gross_exposure > 0 else 0
            }
            
        except Exception:
            return {}
    
    def should_rebalance(self, current_step: int) -> bool:
        """Check if hedge ratios should be recalculated."""
        return (current_step - self.last_rebalance) >= self.rebalance_frequency
    
    def update_hedge_ratios(self, prices1: np.ndarray, prices2: np.ndarray, current_step: int):
        """Update hedge ratios if rebalancing is needed."""
        if self.should_rebalance(current_step):
            self.hedge_ratios["hedge_ratio"] = self._calculate_hedge_ratio(prices1, prices2)
            self.last_rebalance = current_step
    
    def get_strategy_info(self) -> dict:
        """Get strategy information and parameters."""
        return {
            "name": "Statistical Arbitrage Strategy",
            "description": f"Pairs trading based on cointegration with {self.hedge_ratio_method} hedge ratios",
            "parameters": {
                "lookback_period": self.lookback_period,
                "z_score_threshold": self.z_score_threshold,
                "z_score_exit": self.z_score_exit,
                "cointegration_threshold": self.cointegration_threshold,
                "hedge_ratio_method": self.hedge_ratio_method,
                "position_size_method": self.position_size_method,
                "rebalance_frequency": self.rebalance_frequency,
                "stop_loss_mult": self.stop_loss_mult,
                "take_profit_mult": self.take_profit_mult,
            },
            "risk_management": {
                "max_pairs": self.max_pairs,
                "stop_loss": f"{self.stop_loss_mult}x entry z-score",
                "take_profit": f"{self.take_profit_mult}x entry z-score",
            }
        }


class PairsTradingStrategy(StatisticalArbitrageStrategy):
    """
    Specialized pairs trading strategy with enhanced pair selection.
    
    Extends StatisticalArbitrageStrategy with:
    - Correlation-based pair selection
    - Dynamic pair monitoring
    - Multi-pair portfolio management
    """
    
    def __init__(self, strategy_config: dict):
        super().__init__(strategy_config)
        
        # Pair selection parameters
        self.min_correlation = float(self.config.get("min_correlation", 0.7))
        self.max_correlation = float(self.config.get("max_correlation", 0.95))
        self.pair_lookback = int(self.config.get("pair_lookback", 252))
        
        # Portfolio parameters
        self.max_portfolio_pairs = int(self.config.get("max_portfolio_pairs", 10))
        self.pair_allocation = float(self.config.get("pair_allocation", 0.1))  # 10% per pair
        
    def find_pairs(self, price_data: pd.DataFrame) -> List[Tuple[str, str, float]]:
        """Find potential trading pairs based on correlation analysis."""
        pairs = []
        
        if len(price_data.columns) < 2:
            return pairs
        
        # Calculate correlation matrix
        returns_data = price_data.pct_change().dropna()
        correlation_matrix = returns_data.corr()
        
        # Find highly correlated pairs
        for i, asset1 in enumerate(correlation_matrix.columns):
            for j, asset2 in enumerate(correlation_matrix.columns):
                if i < j:  # Avoid duplicates
                    correlation = abs(correlation_matrix.loc[asset1, asset2])
                    
                    if self.min_correlation <= correlation <= self.max_correlation:
                        pairs.append((asset1, asset2, correlation))
        
        # Sort by correlation strength
        pairs.sort(key=lambda x: x[2], reverse=True)
        
        return pairs[:self.max_portfolio_pairs]
    
    def generate_multi_pair_signals(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Generate signals for multiple pairs."""
        signals = {}
        
        # Find potential pairs
        pairs = self.find_pairs(data)
        
        if not pairs:
            return signals
        
        # Generate signals for each pair
        for asset1, asset2, correlation in pairs:
            if asset1 in data.columns and asset2 in data.columns:
                pair_signals = self._analyze_pair(
                    data[asset1].values,
                    data[asset2].values,
                    data.index
                )
                
                signals[f"{asset1}_{asset2}"] = pair_signals
        
        return signals
    
    def get_strategy_info(self) -> dict:
        """Get enhanced strategy information."""
        base_info = super().get_strategy_info()
        base_info["name"] = "Pairs Trading Strategy"
        base_info["description"] = "Multi-pair statistical arbitrage with correlation-based pair selection"
        
        base_info["parameters"].update({
            "min_correlation": self.min_correlation,
            "max_correlation": self.max_correlation,
            "pair_lookback": self.pair_lookback,
            "max_portfolio_pairs": self.max_portfolio_pairs,
            "pair_allocation": self.pair_allocation,
        })
        
        return base_info
