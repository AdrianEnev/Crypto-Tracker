"""
Social Media Monitoring Dashboard

Provides real-time monitoring of social media signals, narratives, and alerts.
Includes manipulation detection alerts and cross-validation status.
All monitoring features are configurable and can be disabled independently.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
import json
from pathlib import Path
import statistics

from .config import SocialMediaConfig
from .features import SocialFeatureSet
from .validation import ValidationResult


logger = logging.getLogger(__name__)


@dataclass
class NarrativeAlert:
    """Alert for significant narrative changes"""
    coin_id: str
    narrative: str
    sentiment_change: float
    volume_change: float
    confidence: float
    timestamp: datetime
    alert_type: str  # "volume_spike", "sentiment_shift", "manipulation", "validation_failure"
    severity: str  # "low", "medium", "high", "critical"


@dataclass
class InfluencerActivity:
    """Influencer activity tracking"""
    influencer_id: str
    influencer_name: str
    platform: str
    coin_mentioned: str
    sentiment: float
    engagement: int
    followers: int
    timestamp: datetime
    post_content: str = ""


@dataclass
class SocialMetrics:
    """Aggregated social metrics for monitoring"""
    coin_id: str
    timestamp: datetime
    sms: float
    volume_velocity: float
    weighted_sentiment: float
    influencer_activity: float
    network_centrality: float
    bot_likeness: float
    cross_validation: float
    quality_score: float
    confidence: float
    risk_level: str


class SocialMonitoringDashboard:
    """Main dashboard for social media monitoring"""
    
    def __init__(self, config: SocialMediaConfig):
        self.config = config
        self.monitoring_config = config.monitoring
        
        # Data storage
        self.metrics_history: Dict[str, List[SocialMetrics]] = {}
        self.active_alerts: List[NarrativeAlert] = []
        self.influencer_activities: List[InfluencerActivity] = []
        
        # Alert thresholds
        self.thresholds = {
            "high_sentiment": self.monitoring_config.high_sentiment_threshold,
            "manipulation_alert": self.monitoring_config.manipulation_alert_threshold,
            "volume_spike": self.monitoring_config.volume_spike_threshold
        }
        
        # Data retention
        self.max_history_days = self.monitoring_config.metrics_retention_days
        self.max_alerts_days = self.monitoring_config.log_retention_days
    
    def update_metrics(self, coin_id: str, social_features: SocialFeatureSet, 
                      validation_result: ValidationResult):
        """Update metrics for a coin"""
        if not self.monitoring_config.enabled:
            return
        
        try:
            # Create metrics object
            metrics = SocialMetrics(
                coin_id=coin_id,
                timestamp=datetime.now(),
                sms=social_features.features.get("sms", 0),
                volume_velocity=social_features.features.get("volume_velocity", 0),
                weighted_sentiment=social_features.features.get("weighted_sentiment", 0),
                influencer_activity=social_features.features.get("influencer_activity", 0),
                network_centrality=social_features.features.get("network_centrality", 0),
                bot_likeness=social_features.features.get("bot_likeness", 0),
                cross_validation=social_features.features.get("cross_validation", 0),
                quality_score=social_features.quality_score,
                confidence=social_features.confidence,
                risk_level=validation_result.risk_level
            )
            
            # Store metrics
            if coin_id not in self.metrics_history:
                self.metrics_history[coin_id] = []
            
            self.metrics_history[coin_id].append(metrics)
            
            # Clean old data
            self._cleanup_old_data()
            
            # Check for alerts
            self._check_alerts(coin_id, metrics, validation_result)
            
        except Exception as e:
            logger.error(f"Failed to update metrics for {coin_id}: {e}")
    
    def _cleanup_old_data(self):
        """Clean up old data based on retention policies"""
        try:
            cutoff_time = datetime.now() - timedelta(days=self.max_history_days)
            
            # Clean metrics history
            for coin_id in list(self.metrics_history.keys()):
                self.metrics_history[coin_id] = [
                    m for m in self.metrics_history[coin_id] 
                    if m.timestamp > cutoff_time
                ]
                
                # Remove empty entries
                if not self.metrics_history[coin_id]:
                    del self.metrics_history[coin_id]
            
            # Clean alerts
            alert_cutoff = datetime.now() - timedelta(days=self.max_alerts_days)
            self.active_alerts = [
                alert for alert in self.active_alerts 
                if alert.timestamp > alert_cutoff
            ]
            
            # Clean influencer activities
            self.influencer_activities = [
                activity for activity in self.influencer_activities
                if activity.timestamp > alert_cutoff
            ]
            
        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")
    
    def _check_alerts(self, coin_id: str, metrics: SocialMetrics, validation_result: ValidationResult):
        """Check for alert conditions"""
        try:
            # Check sentiment threshold
            if abs(metrics.weighted_sentiment) >= self.thresholds["high_sentiment"]:
                alert = NarrativeAlert(
                    coin_id=coin_id,
                    narrative=f"High sentiment detected: {metrics.weighted_sentiment:.2f}",
                    sentiment_change=metrics.weighted_sentiment,
                    volume_change=metrics.volume_velocity,
                    confidence=metrics.confidence,
                    timestamp=datetime.now(),
                    alert_type="sentiment_shift",
                    severity="high" if abs(metrics.weighted_sentiment) > 0.9 else "medium"
                )
                self.active_alerts.append(alert)
            
            # Check volume spike
            if metrics.volume_velocity >= self.thresholds["volume_spike"]:
                alert = NarrativeAlert(
                    coin_id=coin_id,
                    narrative=f"Volume spike detected: {metrics.volume_velocity:.2f}x normal",
                    sentiment_change=metrics.weighted_sentiment,
                    volume_change=metrics.volume_velocity,
                    confidence=metrics.confidence,
                    timestamp=datetime.now(),
                    alert_type="volume_spike",
                    severity="high" if metrics.volume_velocity > 5.0 else "medium"
                )
                self.active_alerts.append(alert)
            
            # Check manipulation
            if metrics.bot_likeness >= self.thresholds["manipulation_alert"]:
                alert = NarrativeAlert(
                    coin_id=coin_id,
                    narrative=f"Potential manipulation detected: bot_likeness={metrics.bot_likeness:.2f}",
                    sentiment_change=metrics.weighted_sentiment,
                    volume_change=metrics.volume_velocity,
                    confidence=metrics.confidence,
                    timestamp=datetime.now(),
                    alert_type="manipulation",
                    severity="critical"
                )
                self.active_alerts.append(alert)
            
            # Check validation failure
            if not validation_result.is_valid:
                alert = NarrativeAlert(
                    coin_id=coin_id,
                    narrative=f"Validation failed: score={validation_result.validation_score:.2f}",
                    sentiment_change=metrics.weighted_sentiment,
                    volume_change=metrics.volume_velocity,
                    confidence=validation_result.confidence,
                    timestamp=datetime.now(),
                    alert_type="validation_failure",
                    severity="high"
                )
                self.active_alerts.append(alert)
            
        except Exception as e:
            logger.error(f"Alert checking failed: {e}")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        if not self.monitoring_config.enabled:
            return {"enabled": False}
        
        try:
            # Get top narratives
            top_narratives = self._get_top_narratives()
            
            # Get recent alerts
            recent_alerts = self._get_recent_alerts()
            
            # Get influencer activity
            influencer_activity = self._get_influencer_activity()
            
            # Get sentiment trends
            sentiment_trends = self._get_sentiment_trends()
            
            # Get manipulation alerts
            manipulation_alerts = self._get_manipulation_alerts()
            
            # Get cross-validation status
            validation_status = self._get_validation_status()
            
            # Get overall metrics summary
            metrics_summary = self._get_metrics_summary()
            
            return {
                "enabled": True,
                "timestamp": datetime.now().isoformat(),
                "top_narratives": top_narratives,
                "recent_alerts": recent_alerts,
                "influencer_activity": influencer_activity,
                "sentiment_trends": sentiment_trends,
                "manipulation_alerts": manipulation_alerts,
                "validation_status": validation_status,
                "metrics_summary": metrics_summary,
                "configuration": {
                    "alert_thresholds": self.thresholds,
                    "retention_days": self.max_history_days,
                    "monitoring_enabled": self.monitoring_config.enabled
                }
            }
            
        except Exception as e:
            logger.error(f"Dashboard data generation failed: {e}")
            return {"enabled": False, "error": str(e)}
    
    def _get_top_narratives(self) -> List[Dict[str, Any]]:
        """Get top narratives by volume and sentiment"""
        try:
            narratives = []
            
            for coin_id, metrics_list in self.metrics_history.items():
                if not metrics_list:
                    continue
                
                # Get latest metrics
                latest_metrics = max(metrics_list, key=lambda x: x.timestamp)
                
                # Calculate narrative strength
                narrative_strength = (
                    abs(latest_metrics.weighted_sentiment) * 0.4 +
                    latest_metrics.volume_velocity * 0.3 +
                    latest_metrics.influencer_activity * 0.3
                )
                
                narratives.append({
                    "coin_id": coin_id,
                    "narrative_strength": narrative_strength,
                    "sentiment": latest_metrics.weighted_sentiment,
                    "volume_velocity": latest_metrics.volume_velocity,
                    "influencer_activity": latest_metrics.influencer_activity,
                    "sms": latest_metrics.sms,
                    "risk_level": latest_metrics.risk_level,
                    "timestamp": latest_metrics.timestamp.isoformat()
                })
            
            # Sort by narrative strength
            narratives.sort(key=lambda x: x["narrative_strength"], reverse=True)
            
            return narratives[:10]  # Top 10 narratives
            
        except Exception as e:
            logger.error(f"Top narratives generation failed: {e}")
            return []
    
    def _get_recent_alerts(self) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        try:
            # Sort alerts by timestamp (most recent first)
            sorted_alerts = sorted(self.active_alerts, key=lambda x: x.timestamp, reverse=True)
            
            # Convert to dict format
            alert_dicts = []
            for alert in sorted_alerts[:20]:  # Last 20 alerts
                alert_dict = asdict(alert)
                alert_dict["timestamp"] = alert.timestamp.isoformat()
                alert_dicts.append(alert_dict)
            
            return alert_dicts
            
        except Exception as e:
            logger.error(f"Recent alerts generation failed: {e}")
            return []
    
    def _get_influencer_activity(self) -> List[Dict[str, Any]]:
        """Get recent influencer activity"""
        try:
            # Sort by timestamp (most recent first)
            sorted_activities = sorted(self.influencer_activities, key=lambda x: x.timestamp, reverse=True)
            
            # Convert to dict format
            activity_dicts = []
            for activity in sorted_activities[:10]:  # Last 10 activities
                activity_dict = asdict(activity)
                activity_dict["timestamp"] = activity.timestamp.isoformat()
                activity_dicts.append(activity_dict)
            
            return activity_dicts
            
        except Exception as e:
            logger.error(f"Influencer activity generation failed: {e}")
            return []
    
    def _get_sentiment_trends(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get sentiment trends for all coins"""
        try:
            trends = {}
            
            for coin_id, metrics_list in self.metrics_history.items():
                if not metrics_list:
                    continue
                
                # Sort by timestamp
                sorted_metrics = sorted(metrics_list, key=lambda x: x.timestamp)
                
                # Create trend data
                trend_data = []
                for metrics in sorted_metrics[-24:]:  # Last 24 data points
                    trend_data.append({
                        "timestamp": metrics.timestamp.isoformat(),
                        "sentiment": metrics.weighted_sentiment,
                        "volume_velocity": metrics.volume_velocity,
                        "sms": metrics.sms
                    })
                
                trends[coin_id] = trend_data
            
            return trends
            
        except Exception as e:
            logger.error(f"Sentiment trends generation failed: {e}")
            return {}
    
    def _get_manipulation_alerts(self) -> List[Dict[str, Any]]:
        """Get manipulation-related alerts"""
        try:
            manipulation_alerts = [
                alert for alert in self.active_alerts 
                if alert.alert_type == "manipulation"
            ]
            
            # Sort by timestamp (most recent first)
            manipulation_alerts.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Convert to dict format
            alert_dicts = []
            for alert in manipulation_alerts[:10]:  # Last 10 manipulation alerts
                alert_dict = asdict(alert)
                alert_dict["timestamp"] = alert.timestamp.isoformat()
                alert_dicts.append(alert_dict)
            
            return alert_dicts
            
        except Exception as e:
            logger.error(f"Manipulation alerts generation failed: {e}")
            return []
    
    def _get_validation_status(self) -> Dict[str, Any]:
        """Get overall validation status"""
        try:
            total_coins = len(self.metrics_history)
            if total_coins == 0:
                return {"status": "no_data", "validated_coins": 0, "total_coins": 0}
            
            validated_coins = 0
            high_risk_coins = 0
            
            for coin_id, metrics_list in self.metrics_history.items():
                if not metrics_list:
                    continue
                
                latest_metrics = max(metrics_list, key=lambda x: x.timestamp)
                
                if latest_metrics.risk_level == "low":
                    validated_coins += 1
                elif latest_metrics.risk_level == "high":
                    high_risk_coins += 1
            
            validation_rate = validated_coins / total_coins if total_coins > 0 else 0
            
            return {
                "status": "healthy" if validation_rate > 0.7 else "warning" if validation_rate > 0.4 else "critical",
                "validation_rate": validation_rate,
                "validated_coins": validated_coins,
                "high_risk_coins": high_risk_coins,
                "total_coins": total_coins
            }
            
        except Exception as e:
            logger.error(f"Validation status generation failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def _get_metrics_summary(self) -> Dict[str, Any]:
        """Get overall metrics summary"""
        try:
            all_metrics = []
            for metrics_list in self.metrics_history.values():
                all_metrics.extend(metrics_list)
            
            if not all_metrics:
                return {"total_data_points": 0}
            
            # Calculate summary statistics
            sms_values = [m.sms for m in all_metrics]
            sentiment_values = [m.weighted_sentiment for m in all_metrics]
            volume_values = [m.volume_velocity for m in all_metrics]
            quality_values = [m.quality_score for m in all_metrics]
            
            return {
                "total_data_points": len(all_metrics),
                "avg_sms": statistics.mean(sms_values),
                "avg_sentiment": statistics.mean(sentiment_values),
                "avg_volume_velocity": statistics.mean(volume_values),
                "avg_quality_score": statistics.mean(quality_values),
                "total_coins_tracked": len(self.metrics_history),
                "active_alerts": len(self.active_alerts),
                "last_update": max(m.timestamp for m in all_metrics).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Metrics summary generation failed: {e}")
            return {"error": str(e)}
    
    def export_data(self, output_dir: str) -> Dict[str, str]:
        """Export monitoring data to files"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            exported_files = {}
            
            # Export dashboard data
            dashboard_data = self.get_dashboard_data()
            dashboard_file = output_path / f"social_dashboard_{timestamp}.json"
            with open(dashboard_file, 'w') as f:
                json.dump(dashboard_data, f, indent=2, default=str)
            exported_files["dashboard"] = str(dashboard_file)
            
            # Export metrics history
            metrics_file = output_path / f"social_metrics_{timestamp}.json"
            metrics_data = {
                coin_id: [asdict(m) for m in metrics_list] 
                for coin_id, metrics_list in self.metrics_history.items()
            }
            with open(metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2, default=str)
            exported_files["metrics"] = str(metrics_file)
            
            # Export alerts
            alerts_file = output_path / f"social_alerts_{timestamp}.json"
            alerts_data = [asdict(alert) for alert in self.active_alerts]
            with open(alerts_file, 'w') as f:
                json.dump(alerts_data, f, indent=2, default=str)
            exported_files["alerts"] = str(alerts_file)
            
            return exported_files
            
        except Exception as e:
            logger.error(f"Data export failed: {e}")
            return {"error": str(e)}
    
    def clear_alerts(self, alert_type: Optional[str] = None):
        """Clear alerts, optionally filtered by type"""
        try:
            if alert_type:
                self.active_alerts = [
                    alert for alert in self.active_alerts 
                    if alert.alert_type != alert_type
                ]
            else:
                self.active_alerts = []
                
        except Exception as e:
            logger.error(f"Alert clearing failed: {e}")
    
    def get_coin_metrics(self, coin_id: str, hours: int = 24) -> Optional[List[SocialMetrics]]:
        """Get metrics for a specific coin within the last N hours"""
        try:
            if coin_id not in self.metrics_history:
                return None
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            return [
                metrics for metrics in self.metrics_history[coin_id]
                if metrics.timestamp > cutoff_time
            ]
            
        except Exception as e:
            logger.error(f"Coin metrics retrieval failed for {coin_id}: {e}")
            return None
