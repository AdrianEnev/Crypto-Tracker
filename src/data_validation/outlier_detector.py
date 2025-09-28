"""
Advanced outlier detection using multiple algorithms and consensus methods.
Implements statistical, machine learning, and domain-specific outlier detection.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class OutlierResult:
    """Outlier detection result."""
    outlier_indices: List[int]
    outlier_types: Dict[str, List[int]]
    detection_methods: Dict[str, List[int]]
    confidence_scores: Dict[str, float]
    recommendations: List[str]
    outlier_statistics: Dict[str, float]


class OutlierDetector:
    """
    Advanced outlier detection system using multiple algorithms.
    
    Features:
    - Statistical methods (Z-score, IQR, modified Z-score)
    - Machine learning methods (Isolation Forest, LOF)
    - Domain-specific detection (price/volume anomalies)
    - Consensus-based detection
    - Outlier categorization and analysis
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Detection methods
        self.methods = self.config.get("detection_methods", [
            "statistical", "isolation_forest", "lof", "domain_specific"
        ])
        
        # Statistical thresholds
        self.z_score_threshold = self.config.get("z_score_threshold", 3.0)
        self.modified_z_score_threshold = self.config.get("modified_z_score_threshold", 3.5)
        self.iqr_multiplier = self.config.get("iqr_multiplier", 1.5)
        
        # ML method parameters
        self.isolation_forest_contamination = self.config.get("isolation_forest_contamination", 0.1)
        self.lof_n_neighbors = self.config.get("lof_n_neighbors", 20)
        self.lof_contamination = self.config.get("lof_contamination", 0.1)
        
        # Consensus parameters
        self.consensus_threshold = self.config.get("consensus_threshold", 0.5)  # 50% agreement
        
        # Domain-specific thresholds
        self.price_change_threshold = self.config.get("price_change_threshold", 0.1)  # 10%
        self.volume_spike_threshold = self.config.get("volume_spike_threshold", 5.0)  # 5x normal
        
    def detect_outliers(self, data: pd.DataFrame, symbol: str) -> OutlierResult:
        """
        Detect outliers using multiple methods and consensus.
        
        Args:
            data: Price data DataFrame
            symbol: Trading symbol for context
            
        Returns:
            Comprehensive outlier detection result
        """
        outlier_results = {}
        
        for method in self.methods:
            if method == "statistical":
                outliers = self._statistical_detection(data)
            elif method == "isolation_forest":
                outliers = self._isolation_forest_detection(data)
            elif method == "lof":
                outliers = self._lof_detection(data)
            elif method == "domain_specific":
                outliers = self._domain_specific_detection(data, symbol)
            else:
                continue
            
            outlier_results[method] = outliers
        
        # Consensus-based outlier detection
        consensus_outliers = self._consensus_detection(outlier_results)
        
        # Categorize outliers by type
        categorized_outliers = self._categorize_outliers(data, consensus_outliers)
        
        # Calculate confidence scores
        confidence_scores = self._calculate_confidence_scores(outlier_results, consensus_outliers)
        
        # Generate recommendations
        recommendations = self._generate_outlier_recommendations(categorized_outliers, confidence_scores)
        
        # Calculate outlier statistics
        outlier_stats = self._calculate_outlier_statistics(data, consensus_outliers)
        
        return OutlierResult(
            outlier_indices=consensus_outliers,
            outlier_types=categorized_outliers,
            detection_methods=outlier_results,
            confidence_scores=confidence_scores,
            recommendations=recommendations,
            outlier_statistics=outlier_stats
        )
    
    def _statistical_detection(self, data: pd.DataFrame) -> List[int]:
        """Statistical outlier detection using Z-score and IQR methods."""
        outliers = []
        
        if 'close' in data.columns:
            prices = data['close'].dropna()
            
            if len(prices) < 4:  # Need minimum data
                return outliers
            
            # Z-score method
            z_scores = np.abs((prices - prices.mean()) / prices.std())
            z_outliers = prices[z_scores > self.z_score_threshold].index.tolist()
            
            # Modified Z-score method (using median absolute deviation)
            median_price = prices.median()
            mad = np.median(np.abs(prices - median_price))
            modified_z_scores = 0.6745 * (prices - median_price) / mad
            modified_z_outliers = prices[np.abs(modified_z_scores) > self.modified_z_score_threshold].index.tolist()
            
            # IQR method
            Q1 = prices.quantile(0.25)
            Q3 = prices.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - self.iqr_multiplier * IQR
            upper_bound = Q3 + self.iqr_multiplier * IQR
            iqr_outliers = prices[(prices < lower_bound) | (prices > upper_bound)].index.tolist()
            
            # Combine all statistical outliers
            outliers = list(set(z_outliers + modified_z_outliers + iqr_outliers))
        
        return outliers
    
    def _isolation_forest_detection(self, data: pd.DataFrame) -> List[int]:
        """
        Isolation Forest outlier detection.
        
        Note: In a real implementation, would use sklearn.ensemble.IsolationForest
        """
        outliers = []
        
        if 'close' in data.columns and len(data) > 10:
            # Mock implementation - in real system would use actual Isolation Forest
            prices = data['close'].dropna()
            
            if len(prices) > 10:
                # Simulate isolation forest with simple statistical method
                # In practice, would use: from sklearn.ensemble import IsolationForest
                
                # Calculate anomaly scores using simplified approach
                mean_price = prices.mean()
                std_price = prices.std()
                
                # Higher scores for points far from mean
                anomaly_scores = np.abs(prices - mean_price) / std_price
                
                # Consider top 10% as outliers (simplified contamination)
                threshold = np.percentile(anomaly_scores, 90)
                outliers = prices[anomaly_scores > threshold].index.tolist()
        
        return outliers
    
    def _lof_detection(self, data: pd.DataFrame) -> List[int]:
        """
        Local Outlier Factor (LOF) detection.
        
        Note: In a real implementation, would use sklearn.neighbors.LocalOutlierFactor
        """
        outliers = []
        
        if 'close' in data.columns and len(data) > 20:
            # Mock implementation - in real system would use actual LOF
            prices = data['close'].dropna()
            
            if len(prices) > 20:
                # Simulate LOF with local density analysis
                window_size = min(20, len(prices) // 4)
                
                lof_scores = []
                for i in range(len(prices)):
                    # Calculate local density around point i
                    start_idx = max(0, i - window_size // 2)
                    end_idx = min(len(prices), i + window_size // 2)
                    local_window = prices.iloc[start_idx:end_idx]
                    
                    # Calculate average distance to neighbors
                    distances = np.abs(prices.iloc[i] - local_window)
                    avg_distance = distances.mean()
                    
                    # Calculate local reachability density (simplified)
                    lrd = 1.0 / (avg_distance + 1e-8)  # Add small epsilon to avoid division by zero
                    lof_scores.append(lrd)
                
                lof_scores = np.array(lof_scores)
                
                # Consider points with low LOF scores as outliers
                threshold = np.percentile(lof_scores, 10)  # Bottom 10%
                outliers = prices[lof_scores < threshold].index.tolist()
        
        return outliers
    
    def _domain_specific_detection(self, data: pd.DataFrame, symbol: str) -> List[int]:
        """Domain-specific outlier detection for financial data."""
        outliers = []
        
        if 'close' in data.columns:
            prices = data['close'].dropna()
            
            if len(prices) > 5:
                # Price jump detection
                returns = prices.pct_change().dropna()
                
                # Large price jumps
                large_jumps = returns[np.abs(returns) > self.price_change_threshold]
                outliers.extend(large_jumps.index.tolist())
                
                # Consecutive large moves in same direction
                if len(returns) > 3:
                    consecutive_moves = 0
                    current_direction = None
                    
                    for i, ret in enumerate(returns):
                        if ret > self.price_change_threshold / 2:  # Significant move
                            if current_direction == 'up':
                                consecutive_moves += 1
                            else:
                                consecutive_moves = 1
                                current_direction = 'up'
                        elif ret < -self.price_change_threshold / 2:
                            if current_direction == 'down':
                                consecutive_moves += 1
                            else:
                                consecutive_moves = 1
                                current_direction = 'down'
                        else:
                            consecutive_moves = 0
                            current_direction = None
                        
                        # Flag if 3+ consecutive significant moves
                        if consecutive_moves >= 3:
                            outliers.append(returns.index[i])
        
        # Volume spike detection
        if 'volume' in data.columns:
            volumes = data['volume'].dropna()
            
            if len(volumes) > 10:
                # Calculate rolling average volume
                rolling_avg = volumes.rolling(window=10, min_periods=5).mean()
                
                # Find volume spikes
                volume_spikes = volumes[volumes > rolling_avg * self.volume_spike_threshold]
                outliers.extend(volume_spikes.index.tolist())
        
        # Price-volume relationship anomalies
        if 'close' in data.columns and 'volume' in data.columns:
            prices = data['close'].dropna()
            volumes = data['volume'].dropna()
            
            min_length = min(len(prices), len(volumes))
            if min_length > 20:
                prices_subset = prices.iloc[:min_length]
                volumes_subset = volumes.iloc[:min_length]
                
                # Calculate rolling correlation
                # Create a DataFrame with both series for correlation calculation
                combined_df = pd.DataFrame({'close': prices_subset, 'volume': volumes_subset})
                rolling_corr = combined_df['close'].rolling(20).corr(combined_df['volume'])
                
                # Find periods with extreme correlation (suspicious)
                extreme_corr = rolling_corr[np.abs(rolling_corr) > 0.95]
                outliers.extend(extreme_corr.index.tolist())
        
        return list(set(outliers))  # Remove duplicates
    
    def _consensus_detection(self, outlier_results: Dict[str, List[int]]) -> List[int]:
        """
        Consensus-based outlier detection.
        
        An outlier is considered valid if detected by multiple methods.
        """
        if not outlier_results:
            return []
        
        # Count how many methods detected each outlier
        outlier_counts = {}
        
        for method, outliers in outlier_results.items():
            for outlier_idx in outliers:
                outlier_counts[outlier_idx] = outlier_counts.get(outlier_idx, 0) + 1
        
        # Apply consensus threshold
        total_methods = len(outlier_results)
        consensus_threshold_count = math.ceil(total_methods * self.consensus_threshold)
        
        consensus_outliers = [
            idx for idx, count in outlier_counts.items() 
            if count >= consensus_threshold_count
        ]
        
        return sorted(consensus_outliers)
    
    def _categorize_outliers(self, data: pd.DataFrame, outliers: List[int]) -> Dict[str, List[int]]:
        """Categorize outliers by type."""
        categories = {
            'price_spikes': [],
            'volume_spikes': [],
            'price_gaps': [],
            'volume_gaps': [],
            'correlation_anomalies': [],
            'statistical_outliers': []
        }
        
        if not outliers or data.empty:
            return categories
        
        # Price spikes
        if 'close' in data.columns:
            prices = data['close']
            for idx in outliers:
                if idx in prices.index:
                    if idx > 0:
                        price_change = abs(prices.iloc[idx] - prices.iloc[idx-1]) / prices.iloc[idx-1]
                        if price_change > 0.05:  # 5% change
                            categories['price_spikes'].append(idx)
        
        # Volume spikes
        if 'volume' in data.columns:
            volumes = data['volume']
            avg_volume = volumes.mean()
            for idx in outliers:
                if idx in volumes.index:
                    if volumes.iloc[idx] > avg_volume * 3:  # 3x average
                        categories['volume_spikes'].append(idx)
        
        # Price gaps
        if 'close' in data.columns:
            prices = data['close']
            for i, idx in enumerate(outliers):
                if i > 0 and idx - outliers[i-1] > 1:
                    # Check for gaps between outlier indices
                    gap_size = idx - outliers[i-1]
                    if gap_size > 5:  # Gap of more than 5 periods
                        categories['price_gaps'].append(idx)
        
        # Statistical outliers (remaining uncategorized)
        categorized_indices = set()
        for category_outliers in categories.values():
            categorized_indices.update(category_outliers)
        
        categories['statistical_outliers'] = [
            idx for idx in outliers if idx not in categorized_indices
        ]
        
        return categories
    
    def _calculate_confidence_scores(self, outlier_results: Dict[str, List[int]], 
                                   consensus_outliers: List[int]) -> Dict[str, float]:
        """Calculate confidence scores for outlier detection methods."""
        confidence_scores = {}
        
        for method, outliers in outlier_results.items():
            if not outliers:
                confidence_scores[method] = 1.0  # No outliers detected - high confidence
                continue
            
            # Calculate overlap with consensus
            consensus_set = set(consensus_outliers)
            method_set = set(outliers)
            
            if method_set:
                overlap = len(consensus_set.intersection(method_set))
                precision = overlap / len(method_set)
                recall = overlap / len(consensus_set) if consensus_set else 0
                
                # F1 score as confidence measure
                if precision + recall > 0:
                    f1_score = 2 * precision * recall / (precision + recall)
                    confidence_scores[method] = f1_score
                else:
                    confidence_scores[method] = 0.0
            else:
                confidence_scores[method] = 0.0
        
        return confidence_scores
    
    def _generate_outlier_recommendations(self, categorized_outliers: Dict[str, List[int]], 
                                        confidence_scores: Dict[str, float]) -> List[str]:
        """Generate recommendations based on outlier analysis."""
        recommendations = []
        
        total_outliers = sum(len(outliers) for outliers in categorized_outliers.values())
        
        if total_outliers == 0:
            recommendations.append("No outliers detected - data quality appears good")
            return recommendations
        
        # Overall outlier rate
        if total_outliers > 50:
            recommendations.append("High number of outliers detected - consider data source review")
        elif total_outliers > 10:
            recommendations.append("Moderate number of outliers detected - investigate major anomalies")
        
        # Specific recommendations by category
        if categorized_outliers.get('price_spikes'):
            recommendations.append("Price spikes detected - verify against market events or news")
        
        if categorized_outliers.get('volume_spikes'):
            recommendations.append("Volume spikes detected - check for data feed issues or major events")
        
        if categorized_outliers.get('price_gaps'):
            recommendations.append("Price gaps detected - investigate missing data periods")
        
        if categorized_outliers.get('correlation_anomalies'):
            recommendations.append("Price-volume correlation anomalies - review data integrity")
        
        # Method confidence recommendations
        low_confidence_methods = [
            method for method, score in confidence_scores.items() 
            if score < 0.5
        ]
        
        if low_confidence_methods:
            recommendations.append(f"Low confidence in methods: {', '.join(low_confidence_methods)} - consider parameter tuning")
        
        return recommendations
    
    def _calculate_outlier_statistics(self, data: pd.DataFrame, outliers: List[int]) -> Dict[str, float]:
        """Calculate outlier statistics."""
        if not outliers or data.empty:
            return {
                'outlier_count': 0,
                'outlier_percentage': 0.0,
                'outlier_density': 0.0,
                'outlier_clustering': 0.0
            }
        
        total_points = len(data)
        outlier_count = len(outliers)
        outlier_percentage = outlier_count / total_points
        
        # Calculate outlier density (outliers per unit time if timestamp available)
        outlier_density = 0.0
        if 'timestamp' in data.columns and len(outliers) > 1:
            outlier_times = data.iloc[outliers]['timestamp']
            if len(outlier_times) > 1:
                time_span = (outlier_times.max() - outlier_times.min()).total_seconds()
                if time_span > 0:
                    outlier_density = outlier_count / (time_span / 3600)  # outliers per hour
        
        # Calculate outlier clustering (how close outliers are to each other)
        outlier_clustering = 0.0
        if len(outliers) > 1:
            outlier_indices = sorted(outliers)
            gaps = [outlier_indices[i] - outlier_indices[i-1] for i in range(1, len(outlier_indices))]
            if gaps:
                avg_gap = np.mean(gaps)
                outlier_clustering = 1.0 / (avg_gap + 1)  # Higher clustering = smaller gaps
        
        return {
            'outlier_count': outlier_count,
            'outlier_percentage': outlier_percentage,
            'outlier_density': outlier_density,
            'outlier_clustering': outlier_clustering
        }
