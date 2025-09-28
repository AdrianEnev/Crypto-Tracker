"""
Advanced anomaly detection for financial time series data.
Implements pattern-based anomaly detection and data quality monitoring.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class AnomalyResult:
    """Anomaly detection result."""
    anomaly_indices: List[int]
    anomaly_types: Dict[str, List[int]]
    anomaly_scores: Dict[int, float]
    confidence_scores: Dict[str, float]
    recommendations: List[str]
    anomaly_statistics: Dict[str, float]


class AnomalyDetector:
    """
    Advanced anomaly detection system for financial time series data.
    
    Features:
    - Pattern-based anomaly detection
    - Price-volume relationship analysis
    - Time series anomaly detection
    - Data gap detection
    - Market microstructure anomalies
    - Confidence scoring and recommendations
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Detection parameters
        self.correlation_threshold = self.config.get("correlation_threshold", 0.95)
        self.volume_spike_threshold = self.config.get("volume_spike_threshold", 5.0)
        self.price_gap_threshold = self.config.get("price_gap_threshold", 0.02)
        self.time_gap_threshold_hours = self.config.get("time_gap_threshold_hours", 2.0)
        self.pattern_window = self.config.get("pattern_window", 20)
        self.anomaly_score_threshold = self.config.get("anomaly_score_threshold", 0.7)
        
    def detect_anomalies(self, data: pd.DataFrame, symbol: str) -> AnomalyResult:
        """
        Detect anomalies in financial time series data.
        
        Args:
            data: Price data DataFrame
            symbol: Trading symbol for context
            
        Returns:
            Comprehensive anomaly detection result
        """
        anomaly_indices = []
        anomaly_types = {
            'price_volume_correlation': [],
            'volume_spikes': [],
            'price_gaps': [],
            'time_gaps': [],
            'pattern_anomalies': [],
            'microstructure_anomalies': []
        }
        
        if len(data) < 10:
            return AnomalyResult(
                anomaly_indices=[],
                anomaly_types=anomaly_types,
                anomaly_scores={},
                confidence_scores={},
                recommendations=["Insufficient data for anomaly detection"],
                anomaly_statistics={}
            )
        
        # Detect different types of anomalies
        if 'close' in data.columns and 'volume' in data.columns:
            # Price-volume correlation anomalies
            pv_anomalies = self._detect_price_volume_anomalies(data)
            anomaly_types['price_volume_correlation'] = pv_anomalies
            anomaly_indices.extend(pv_anomalies)
            
            # Volume spike anomalies
            volume_anomalies = self._detect_volume_spike_anomalies(data)
            anomaly_types['volume_spikes'] = volume_anomalies
            anomaly_indices.extend(volume_anomalies)
            
            # Price gap anomalies
            price_gap_anomalies = self._detect_price_gap_anomalies(data)
            anomaly_types['price_gaps'] = price_gap_anomalies
            anomaly_indices.extend(price_gap_anomalies)
        
        # Time gap anomalies
        if 'timestamp' in data.columns:
            time_gap_anomalies = self._detect_time_gap_anomalies(data)
            anomaly_types['time_gaps'] = time_gap_anomalies
            anomaly_indices.extend(time_gap_anomalies)
        
        # Pattern anomalies
        if 'close' in data.columns:
            pattern_anomalies = self._detect_pattern_anomalies(data)
            anomaly_types['pattern_anomalies'] = pattern_anomalies
            anomaly_indices.extend(pattern_anomalies)
        
        # Market microstructure anomalies
        if 'close' in data.columns and 'volume' in data.columns:
            microstructure_anomalies = self._detect_microstructure_anomalies(data)
            anomaly_types['microstructure_anomalies'] = microstructure_anomalies
            anomaly_indices.extend(microstructure_anomalies)
        
        # Remove duplicates
        anomaly_indices = list(set(anomaly_indices))
        
        # Calculate anomaly scores
        anomaly_scores = self._calculate_anomaly_scores(data, anomaly_indices)
        
        # Calculate confidence scores
        confidence_scores = self._calculate_confidence_scores(anomaly_types, anomaly_scores)
        
        # Generate recommendations
        recommendations = self._generate_anomaly_recommendations(anomaly_types, confidence_scores)
        
        # Calculate anomaly statistics
        anomaly_stats = self._calculate_anomaly_statistics(data, anomaly_indices, anomaly_types)
        
        return AnomalyResult(
            anomaly_indices=anomaly_indices,
            anomaly_types=anomaly_types,
            anomaly_scores=anomaly_scores,
            confidence_scores=confidence_scores,
            recommendations=recommendations,
            anomaly_statistics=anomaly_stats
        )
    
    def _detect_price_volume_anomalies(self, data: pd.DataFrame) -> List[int]:
        """Detect price-volume relationship anomalies."""
        anomalies = []
        
        if len(data) < self.pattern_window + 5:
            return anomalies
        
        prices = data['close'].dropna()
        volumes = data['volume'].dropna()
        
        min_length = min(len(prices), len(volumes))
        if min_length < self.pattern_window + 5:
            return anomalies
        
        prices_subset = prices.iloc[:min_length]
        volumes_subset = volumes.iloc[:min_length]
        
        # Calculate rolling correlation
        # Create a DataFrame with both series for correlation calculation
        combined_df = pd.DataFrame({'close': prices_subset, 'volume': volumes_subset})
        rolling_corr = combined_df['close'].rolling(self.pattern_window).corr(combined_df['volume'])
        
        # Find periods with extreme correlation (suspicious)
        extreme_corr_indices = rolling_corr[
            (rolling_corr > self.correlation_threshold) | 
            (rolling_corr < -self.correlation_threshold)
        ].index.tolist()
        
        # Also check for correlation breakdowns (sudden drops in correlation)
        if len(rolling_corr) > 10:
            corr_changes = rolling_corr.diff().abs()
            correlation_breakdowns = corr_changes[corr_changes > 0.5].index.tolist()
            extreme_corr_indices.extend(correlation_breakdowns)
        
        anomalies.extend(extreme_corr_indices)
        
        return list(set(anomalies))
    
    def _detect_volume_spike_anomalies(self, data: pd.DataFrame) -> List[int]:
        """Detect unusual volume spikes."""
        anomalies = []
        
        if 'volume' not in data.columns or len(data) < 10:
            return anomalies
        
        volumes = data['volume'].dropna()
        
        if len(volumes) < 10:
            return anomalies
        
        # Calculate rolling statistics
        rolling_mean = volumes.rolling(window=self.pattern_window, min_periods=5).mean()
        rolling_std = volumes.rolling(window=self.pattern_window, min_periods=5).std()
        
        # Find volume spikes
        volume_spikes = volumes[
            volumes > rolling_mean + self.volume_spike_threshold * rolling_std
        ].index.tolist()
        
        # Also detect volume drops (unusual low volume)
        volume_drops = volumes[
            volumes < rolling_mean - 2 * rolling_std
        ].index.tolist()
        
        anomalies.extend(volume_spikes)
        anomalies.extend(volume_drops)
        
        return list(set(anomalies))
    
    def _detect_price_gap_anomalies(self, data: pd.DataFrame) -> List[int]:
        """Detect price gap anomalies."""
        anomalies = []
        
        if 'close' not in data.columns or len(data) < 2:
            return anomalies
        
        prices = data['close'].dropna()
        
        if len(prices) < 2:
            return anomalies
        
        # Calculate price changes
        price_changes = prices.pct_change().dropna()
        
        # Find large price gaps
        large_gaps = price_changes[abs(price_changes) > self.price_gap_threshold].index.tolist()
        
        # Find consecutive large moves (potential manipulation)
        consecutive_moves = []
        current_consecutive = 0
        last_direction = None
        
        for i, change in enumerate(price_changes):
            if abs(change) > self.price_gap_threshold / 2:  # Significant move
                direction = 'up' if change > 0 else 'down'
                
                if direction == last_direction:
                    current_consecutive += 1
                else:
                    current_consecutive = 1
                    last_direction = direction
                
                # Flag if 3+ consecutive significant moves in same direction
                if current_consecutive >= 3:
                    consecutive_moves.append(price_changes.index[i])
            else:
                current_consecutive = 0
                last_direction = None
        
        anomalies.extend(large_gaps)
        anomalies.extend(consecutive_moves)
        
        return list(set(anomalies))
    
    def _detect_time_gap_anomalies(self, data: pd.DataFrame) -> List[int]:
        """Detect time gap anomalies."""
        anomalies = []
        
        if 'timestamp' not in data.columns or len(data) < 2:
            return anomalies
        
        timestamps = data['timestamp']
        
        if len(timestamps) < 2:
            return anomalies
        
        # Calculate time differences
        time_diffs = timestamps.diff().dropna()
        
        # Convert to hours
        time_diffs_hours = time_diffs.dt.total_seconds() / 3600
        
        # Find large time gaps
        large_gaps = time_diffs_hours[time_diffs_hours > self.time_gap_threshold_hours]
        
        # Find the indices where these gaps occur
        for gap_time in large_gaps.index:
            anomalies.append(gap_time)
        
        # Also detect irregular time intervals
        if len(time_diffs_hours) > 5:
            median_interval = time_diffs_hours.median()
            irregular_intervals = time_diffs_hours[
                (time_diffs_hours > median_interval * 3) | 
                (time_diffs_hours < median_interval * 0.3)
            ]
            
            for irregular_time in irregular_intervals.index:
                anomalies.append(irregular_time)
        
        return list(set(anomalies))
    
    def _detect_pattern_anomalies(self, data: pd.DataFrame) -> List[int]:
        """Detect pattern-based anomalies in price series."""
        anomalies = []
        
        if 'close' not in data.columns or len(data) < self.pattern_window * 2:
            return anomalies
        
        prices = data['close'].dropna()
        
        if len(prices) < self.pattern_window * 2:
            return anomalies
        
        # Detect unusual price patterns
        for i in range(self.pattern_window, len(prices) - self.pattern_window):
            # Get current window
            current_window = prices.iloc[i:i + self.pattern_window]
            
            # Get previous window for comparison
            previous_window = prices.iloc[i - self.pattern_window:i]
            
            # Calculate pattern similarity
            current_trend = np.polyfit(range(len(current_window)), current_window, 1)[0]
            previous_trend = np.polyfit(range(len(previous_window)), previous_window, 1)[0]
            
            # Check for trend reversal anomalies
            if abs(current_trend - previous_trend) > 2 * abs(previous_trend):
                anomalies.append(prices.index[i])
            
            # Check for volatility anomalies
            current_volatility = current_window.std()
            previous_volatility = previous_window.std()
            
            if current_volatility > 3 * previous_volatility or current_volatility < previous_volatility / 3:
                anomalies.append(prices.index[i])
        
        return list(set(anomalies))
    
    def _detect_microstructure_anomalies(self, data: pd.DataFrame) -> List[int]:
        """Detect market microstructure anomalies."""
        anomalies = []
        
        if 'close' not in data.columns or 'volume' not in data.columns:
            return anomalies
        
        prices = data['close'].dropna()
        volumes = data['volume'].dropna()
        
        min_length = min(len(prices), len(volumes))
        if min_length < 10:
            return anomalies
        
        prices_subset = prices.iloc[:min_length]
        volumes_subset = volumes.iloc[:min_length]
        
        # Detect price jumps without volume
        if len(prices_subset) > 1:
            price_changes = prices_subset.pct_change().abs()
            volume_changes = volumes_subset.pct_change().abs()
            
            # Large price moves with small volume changes
            large_price_moves = price_changes > 0.05  # 5%+ moves
            small_volume_changes = volume_changes < 0.1  # <10% volume change
            
            suspicious_moves = large_price_moves & small_volume_changes
            anomalies.extend(suspicious_moves[suspicious_moves].index.tolist())
        
        # Detect volume spikes without price movement
        if len(volumes_subset) > 5:
            volume_mean = volumes_subset.rolling(window=5, min_periods=3).mean()
            volume_spikes = volumes_subset > volume_mean * 5  # 5x average volume
            
            # Check if price didn't move much during volume spikes
            # Get indices where volume spikes occur
            spike_indices = volumes_subset[volume_spikes].index
            if len(spike_indices) > 0:
                # Get corresponding price changes for spike periods
                price_changes = prices_subset.pct_change().abs()
                price_changes_during_spikes = price_changes[price_changes.index.isin(spike_indices)]
                suspicious_volume = price_changes_during_spikes[price_changes_during_spikes < 0.01]  # <1% price change
                
                anomalies.extend(suspicious_volume.index.tolist())
        
        return list(set(anomalies))
    
    def _calculate_anomaly_scores(self, data: pd.DataFrame, anomaly_indices: List[int]) -> Dict[int, float]:
        """Calculate anomaly scores for detected anomalies."""
        anomaly_scores = {}
        
        if not anomaly_indices or data.empty:
            return anomaly_scores
        
        for idx in anomaly_indices:
            if idx not in data.index:
                continue
            
            score = 0.0
            
            # Base score from index position (more recent = higher score)
            position_score = (idx - data.index.min()) / (data.index.max() - data.index.min())
            score += position_score * 0.2
            
            # Price-based score
            if 'close' in data.columns and idx in data.index:
                price = data.loc[idx, 'close']
                if not pd.isna(price):
                    # Compare to surrounding prices
                    surrounding_prices = data['close'].iloc[max(0, idx-5):min(len(data), idx+6)]
                    if len(surrounding_prices) > 1:
                        price_deviation = abs(price - surrounding_prices.mean()) / surrounding_prices.std()
                        score += min(price_deviation * 0.3, 0.5)
            
            # Volume-based score
            if 'volume' in data.columns and idx in data.index:
                volume = data.loc[idx, 'volume']
                if not pd.isna(volume):
                    surrounding_volumes = data['volume'].iloc[max(0, idx-5):min(len(data), idx+6)]
                    if len(surrounding_volumes) > 1:
                        volume_deviation = abs(volume - surrounding_volumes.mean()) / surrounding_volumes.std()
                        score += min(volume_deviation * 0.2, 0.3)
            
            anomaly_scores[idx] = min(1.0, score)
        
        return anomaly_scores
    
    def _calculate_confidence_scores(self, anomaly_types: Dict[str, List[int]], 
                                   anomaly_scores: Dict[int, float]) -> Dict[str, float]:
        """Calculate confidence scores for anomaly detection methods."""
        confidence_scores = {}
        
        for anomaly_type, anomalies in anomaly_types.items():
            if not anomalies:
                confidence_scores[anomaly_type] = 1.0  # No anomalies = high confidence
                continue
            
            # Calculate average anomaly score for this type
            type_scores = [anomaly_scores.get(idx, 0) for idx in anomalies]
            avg_score = np.mean(type_scores) if type_scores else 0
            
            # Higher scores = higher confidence (more obvious anomalies)
            confidence_scores[anomaly_type] = min(1.0, avg_score)
        
        return confidence_scores
    
    def _generate_anomaly_recommendations(self, anomaly_types: Dict[str, List[int]], 
                                        confidence_scores: Dict[str, float]) -> List[str]:
        """Generate recommendations based on anomaly analysis."""
        recommendations = []
        
        total_anomalies = sum(len(anomalies) for anomalies in anomaly_types.values())
        
        if total_anomalies == 0:
            recommendations.append("No anomalies detected - data quality appears good")
            return recommendations
        
        # Overall anomaly assessment
        if total_anomalies > 20:
            recommendations.append("High number of anomalies detected - investigate data source and collection process")
        elif total_anomalies > 10:
            recommendations.append("Moderate number of anomalies detected - review major anomalies")
        else:
            recommendations.append("Low number of anomalies detected - investigate specific cases")
        
        # Type-specific recommendations
        if anomaly_types.get('price_volume_correlation'):
            recommendations.append("Price-volume correlation anomalies detected - verify data integrity and market events")
        
        if anomaly_types.get('volume_spikes'):
            recommendations.append("Volume spike anomalies detected - check for data feed issues or major market events")
        
        if anomaly_types.get('price_gaps'):
            recommendations.append("Price gap anomalies detected - verify against market events and news")
        
        if anomaly_types.get('time_gaps'):
            recommendations.append("Time gap anomalies detected - check data collection schedule and network connectivity")
        
        if anomaly_types.get('pattern_anomalies'):
            recommendations.append("Pattern anomalies detected - review for market regime changes or data issues")
        
        if anomaly_types.get('microstructure_anomalies'):
            recommendations.append("Market microstructure anomalies detected - investigate for potential manipulation or data errors")
        
        # Confidence-based recommendations
        low_confidence_types = [
            anomaly_type for anomaly_type, confidence in confidence_scores.items()
            if confidence < 0.5
        ]
        
        if low_confidence_types:
            recommendations.append(f"Low confidence in anomaly detection for: {', '.join(low_confidence_types)} - consider parameter adjustment")
        
        return recommendations
    
    def _calculate_anomaly_statistics(self, data: pd.DataFrame, anomaly_indices: List[int], 
                                    anomaly_types: Dict[str, List[int]]) -> Dict[str, float]:
        """Calculate anomaly statistics."""
        if not anomaly_indices or data.empty:
            return {
                'anomaly_count': 0,
                'anomaly_percentage': 0.0,
                'anomaly_density': 0.0,
                'anomaly_clustering': 0.0,
                'type_distribution': {}
            }
        
        total_points = len(data)
        anomaly_count = len(anomaly_indices)
        anomaly_percentage = anomaly_count / total_points
        
        # Calculate anomaly density
        anomaly_density = 0.0
        if 'timestamp' in data.columns and len(anomaly_indices) > 1:
            anomaly_times = data.iloc[anomaly_indices]['timestamp']
            if len(anomaly_times) > 1:
                time_span = (anomaly_times.max() - anomaly_times.min()).total_seconds()
                if time_span > 0:
                    anomaly_density = anomaly_count / (time_span / 3600)  # anomalies per hour
        
        # Calculate anomaly clustering
        anomaly_clustering = 0.0
        if len(anomaly_indices) > 1:
            anomaly_positions = sorted(anomaly_indices)
            gaps = [anomaly_positions[i] - anomaly_positions[i-1] for i in range(1, len(anomaly_positions))]
            if gaps:
                avg_gap = np.mean(gaps)
                anomaly_clustering = 1.0 / (avg_gap + 1)  # Higher clustering = smaller gaps
        
        # Calculate type distribution
        type_distribution = {
            anomaly_type: len(anomalies) / anomaly_count if anomaly_count > 0 else 0
            for anomaly_type, anomalies in anomaly_types.items()
        }
        
        return {
            'anomaly_count': anomaly_count,
            'anomaly_percentage': anomaly_percentage,
            'anomaly_density': anomaly_density,
            'anomaly_clustering': anomaly_clustering,
            'type_distribution': type_distribution
        }
