"""
Technical indicator features for ML models.
Enhances existing technical indicators with ML-optimized features.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import talib


class TechnicalFeatures:
    """
    Technical indicator feature generator.
    
    Creates features from technical indicators that complement
    our existing strategy indicators but with ML-optimized parameters.
    """
    
    def __init__(self):
        self.feature_cache = {}
    
    def create_features(self, market_data: pd.DataFrame, 
                       lookbacks: List[int] = [5, 10, 20, 50]) -> pd.DataFrame:
        """
        Create technical indicator features.
        
        Args:
            market_data: OHLCV DataFrame
            lookbacks: List of lookback periods for indicators
            
        Returns:
            DataFrame with technical features
        """
        features_df = pd.DataFrame(index=market_data.index)
        
        # Price-based features
        features_df = self._create_price_features(features_df, market_data, lookbacks)
        
        # Volume-based features
        features_df = self._create_volume_features(features_df, market_data, lookbacks)
        
        # Momentum features
        features_df = self._create_momentum_features(features_df, market_data, lookbacks)
        
        # Volatility features
        features_df = self._create_volatility_features(features_df, market_data, lookbacks)
        
        # Trend features
        features_df = self._create_trend_features(features_df, market_data, lookbacks)
        
        # Pattern recognition features
        features_df = self._create_pattern_features(features_df, market_data)
        
        return features_df
    
    def _create_price_features(self, features_df: pd.DataFrame, 
                             market_data: pd.DataFrame, 
                             lookbacks: List[int]) -> pd.DataFrame:
        """Create price-based technical features."""
        
        # Price ratios
        features_df['price_to_high'] = market_data['close'] / market_data['high']
        features_df['price_to_low'] = market_data['close'] / market_data['low']
        features_df['high_to_low'] = market_data['high'] / market_data['low']
        
        # Price position within range
        features_df['price_position'] = (
            (market_data['close'] - market_data['low']) / 
            (market_data['high'] - market_data['low'])
        )
        
        # Price changes
        features_df['price_change_1d'] = market_data['close'].pct_change()
        features_df['price_change_5d'] = market_data['close'].pct_change(5)
        features_df['price_change_20d'] = market_data['close'].pct_change(20)
        
        # Price gaps
        features_df['gap_up'] = (market_data['open'] > market_data['close'].shift(1)).astype(int)
        features_df['gap_down'] = (market_data['open'] < market_data['close'].shift(1)).astype(int)
        
        # Multiple timeframe moving averages
        for period in lookbacks:
            ma = market_data['close'].rolling(period).mean()
            features_df[f'price_vs_ma_{period}'] = market_data['close'] / ma - 1
            features_df[f'ma_{period}_slope'] = ma.pct_change()
        
        # Exponential moving averages
        for period in [12, 26, 50]:
            ema = market_data['close'].ewm(span=period).mean()
            features_df[f'price_vs_ema_{period}'] = market_data['close'] / ema - 1
            features_df[f'ema_{period}_slope'] = ema.pct_change()
        
        return features_df
    
    def _create_volume_features(self, features_df: pd.DataFrame,
                              market_data: pd.DataFrame,
                              lookbacks: List[int]) -> pd.DataFrame:
        """Create volume-based technical features."""
        
        # Volume ratios
        for period in lookbacks:
            avg_volume = market_data['volume'].rolling(period).mean()
            features_df[f'volume_ratio_{period}d'] = market_data['volume'] / avg_volume
        
        # Volume-price trend
        features_df['volume_price_trend'] = (
            market_data['volume'] * np.sign(market_data['close'].pct_change())
        )
        
        # On-Balance Volume (OBV)
        obv = self._calculate_obv(market_data)
        features_df['obv'] = obv
        features_df['obv_slope'] = obv.pct_change()
        
        # Volume-weighted average price (VWAP)
        vwap = self._calculate_vwap(market_data)
        features_df['price_vs_vwap'] = market_data['close'] / vwap - 1
        
        # Volume momentum
        for period in lookbacks:
            features_df[f'volume_momentum_{period}'] = (
                market_data['volume'].pct_change(period)
            )
        
        return features_df
    
    def _create_momentum_features(self, features_df: pd.DataFrame,
                                market_data: pd.DataFrame,
                                lookbacks: List[int]) -> pd.DataFrame:
        """Create momentum indicator features."""
        
        # RSI (Relative Strength Index)
        for period in [14, 21]:
            rsi = talib.RSI(market_data['close'].values, timeperiod=period)
            features_df[f'rsi_{period}'] = rsi
            features_df[f'rsi_{period}_overbought'] = (rsi > 70).astype(int)
            features_df[f'rsi_{period}_oversold'] = (rsi < 30).astype(int)
        
        # Stochastic Oscillator
        slowk, slowd = talib.STOCH(
            market_data['high'].values,
            market_data['low'].values,
            market_data['close'].values,
            fastk_period=14,
            slowk_period=3,
            slowd_period=3
        )
        features_df['stoch_k'] = slowk
        features_df['stoch_d'] = slowd
        features_df['stoch_overbought'] = (slowk > 80).astype(int)
        features_df['stoch_oversold'] = (slowk < 20).astype(int)
        
        # MACD (Moving Average Convergence Divergence)
        macd, macd_signal, macd_hist = talib.MACD(
            market_data['close'].values,
            fastperiod=12,
            slowperiod=26,
            signalperiod=9
        )
        features_df['macd'] = macd
        features_df['macd_signal'] = macd_signal
        features_df['macd_histogram'] = macd_hist
        features_df['macd_bullish'] = (macd > macd_signal).astype(int)
        features_df['macd_bearish'] = (macd < macd_signal).astype(int)
        
        # Momentum indicators
        for period in lookbacks:
            momentum = market_data['close'] / market_data['close'].shift(period) - 1
            features_df[f'momentum_{period}d'] = momentum
            
            # Rate of Change (ROC)
            roc = talib.ROC(market_data['close'].values, timeperiod=period)
            features_df[f'roc_{period}d'] = roc
        
        return features_df
    
    def _create_volatility_features(self, features_df: pd.DataFrame,
                                  market_data: pd.DataFrame,
                                  lookbacks: List[int]) -> pd.DataFrame:
        """Create volatility indicator features."""
        
        # ATR (Average True Range)
        for period in [14, 21]:
            atr = talib.ATR(
                market_data['high'].values,
                market_data['low'].values,
                market_data['close'].values,
                timeperiod=period
            )
            features_df[f'atr_{period}'] = atr
            features_df[f'atr_{period}_normalized'] = atr / market_data['close']
        
        # Bollinger Bands
        for period in [20, 50]:
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                market_data['close'].values,
                timeperiod=period,
                nbdevup=2,
                nbdevdn=2
            )
            features_df[f'bb_position_{period}'] = (
                (market_data['close'] - bb_lower) / (bb_upper - bb_lower)
            )
            bb_width = (bb_upper - bb_lower) / bb_middle
            features_df[f'bb_width_{period}'] = bb_width
            # Convert to pandas Series for rolling calculation
            bb_width_series = pd.Series(bb_width, index=market_data.index)
            features_df[f'bb_squeeze_{period}'] = (bb_width_series < bb_width_series.rolling(20).mean()).astype(int)
        
        # Historical volatility
        returns = market_data['close'].pct_change()
        for period in lookbacks:
            vol = returns.rolling(period).std() * np.sqrt(252)  # Annualized
            features_df[f'volatility_{period}d'] = vol
            features_df[f'volatility_ratio_{period}d'] = vol / vol.rolling(50).mean()
        
        # Parkinson volatility (uses high-low)
        for period in lookbacks:
            park_vol = np.sqrt(
                (1/(4*np.log(2))) * 
                ((np.log(market_data['high'] / market_data['low']))**2).rolling(period).mean() * 252
            )
            features_df[f'parkinson_vol_{period}d'] = park_vol
        
        return features_df
    
    def _create_trend_features(self, features_df: pd.DataFrame,
                             market_data: pd.DataFrame,
                             lookbacks: List[int]) -> pd.DataFrame:
        """Create trend indicator features."""
        
        # ADX (Average Directional Index)
        adx = talib.ADX(
            market_data['high'].values,
            market_data['low'].values,
            market_data['close'].values,
            timeperiod=14
        )
        features_df['adx'] = adx
        features_df['strong_trend'] = (adx > 25).astype(int)
        features_df['weak_trend'] = (adx < 20).astype(int)
        
        # Directional Movement
        plus_di = talib.PLUS_DI(
            market_data['high'].values,
            market_data['low'].values,
            market_data['close'].values,
            timeperiod=14
        )
        minus_di = talib.MINUS_DI(
            market_data['high'].values,
            market_data['low'].values,
            market_data['close'].values,
            timeperiod=14
        )
        features_df['plus_di'] = plus_di
        features_df['minus_di'] = minus_di
        features_df['di_bullish'] = (plus_di > minus_di).astype(int)
        
        # Parabolic SAR
        sar = talib.SAR(
            market_data['high'].values,
            market_data['low'].values,
            acceleration=0.02,
            maximum=0.2
        )
        features_df['sar'] = sar
        features_df['price_above_sar'] = (market_data['close'] > sar).astype(int)
        
        # Linear regression slope
        for period in lookbacks:
            slope = talib.LINEARREG_SLOPE(market_data['close'].values, timeperiod=period)
            features_df[f'trend_slope_{period}d'] = slope
            features_df[f'trend_strength_{period}d'] = abs(slope)
        
        return features_df
    
    def _create_pattern_features(self, features_df: pd.DataFrame,
                               market_data: pd.DataFrame) -> pd.DataFrame:
        """Create candlestick pattern features."""
        
        # Doji patterns
        doji = talib.CDLDOJI(
            market_data['open'].values,
            market_data['high'].values,
            market_data['low'].values,
            market_data['close'].values
        )
        features_df['doji'] = (doji != 0).astype(int)
        
        # Hammer patterns
        hammer = talib.CDLHAMMER(
            market_data['open'].values,
            market_data['high'].values,
            market_data['low'].values,
            market_data['close'].values
        )
        features_df['hammer'] = (hammer != 0).astype(int)
        
        # Engulfing patterns
        engulfing = talib.CDLENGULFING(
            market_data['open'].values,
            market_data['high'].values,
            market_data['low'].values,
            market_data['close'].values
        )
        features_df['engulfing'] = (engulfing != 0).astype(int)
        
        # Morning/Evening star
        morning_star = talib.CDLMORNINGSTAR(
            market_data['open'].values,
            market_data['high'].values,
            market_data['low'].values,
            market_data['close'].values
        )
        evening_star = talib.CDLEVENINGSTAR(
            market_data['open'].values,
            market_data['high'].values,
            market_data['low'].values,
            market_data['close'].values
        )
        features_df['morning_star'] = (morning_star != 0).astype(int)
        features_df['evening_star'] = (evening_star != 0).astype(int)
        
        return features_df
    
    def _calculate_obv(self, market_data: pd.DataFrame) -> pd.Series:
        """Calculate On-Balance Volume."""
        price_change = market_data['close'].diff()
        obv = np.where(
            price_change > 0, market_data['volume'],
            np.where(price_change < 0, -market_data['volume'], 0)
        )
        return pd.Series(obv, index=market_data.index).cumsum()
    
    def _calculate_vwap(self, market_data: pd.DataFrame) -> pd.Series:
        """Calculate Volume Weighted Average Price."""
        typical_price = (market_data['high'] + market_data['low'] + market_data['close']) / 3
        vwap = (typical_price * market_data['volume']).cumsum() / market_data['volume'].cumsum()
        return vwap
    
    def get_feature_summary(self, features_df: pd.DataFrame) -> Dict:
        """Get summary statistics of technical features."""
        numeric_features = features_df.select_dtypes(include=[np.number])
        
        return {
            'total_features': len(numeric_features.columns),
            'missing_values': numeric_features.isnull().sum().sum(),
            'feature_types': {
                'price_features': len([col for col in numeric_features.columns if 'price' in col]),
                'volume_features': len([col for col in numeric_features.columns if 'volume' in col]),
                'momentum_features': len([col for col in numeric_features.columns if any(x in col for x in ['rsi', 'stoch', 'macd', 'momentum'])]),
                'volatility_features': len([col for col in numeric_features.columns if any(x in col for x in ['atr', 'bb', 'volatility'])]),
                'trend_features': len([col for col in numeric_features.columns if any(x in col for x in ['adx', 'sar', 'trend', 'ma', 'ema'])]),
                'pattern_features': len([col for col in numeric_features.columns if any(x in col for x in ['doji', 'hammer', 'engulfing', 'star'])])
            },
            'correlation_stats': {
                'max_correlation': numeric_features.corr().abs().max().max(),
                'high_correlation_pairs': len(numeric_features.corr().abs() > 0.8)
            }
        }
