"""
Social Media Integration Main Module

Main integration point for social media features with the trading system.
Provides easy-to-use interface for integrating social signals into trading decisions.
All features are configurable and can be disabled independently.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import yaml

from .config import SocialMediaConfig
from .data_sources import SocialDataManager
from .features import SocialFeatureEngine, SocialFeatureSet
from .validation import SocialSignalValidator, ValidationResult
from .monitoring import SocialMonitoringDashboard


logger = logging.getLogger(__name__)


class SocialMediaIntegration:
    """Main integration class for social media features"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize social media integration
        
        Args:
            config_path: Path to social media config file. If None, uses default config.
        """
        self.config = self._load_config(config_path)
        self.enabled = self.config.enabled
        
        # Initialize components
        self.data_manager: Optional[SocialDataManager] = None
        self.feature_engine: Optional[SocialFeatureEngine] = None
        self.validator: Optional[SocialSignalValidator] = None
        self.monitoring: Optional[SocialMonitoringDashboard] = None
        
        if self.enabled:
            self._initialize_components()
            logger.info("Social media integration initialized successfully")
        else:
            logger.info("Social media integration disabled")
    
    def _load_config(self, config_path: Optional[str] = None) -> SocialMediaConfig:
        """Load configuration from file or create default"""
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    config_dict = yaml.safe_load(f) or {}
                return SocialMediaConfig.from_dict(config_dict)
            except Exception as e:
                logger.error(f"Failed to load config from {config_path}: {e}")
                return SocialMediaConfig()
        else:
            # Try to load from default location
            default_config_path = Path(__file__).parent.parent.parent / "config" / "social_media.yaml"
            if default_config_path.exists():
                try:
                    with open(default_config_path, 'r') as f:
                        config_dict = yaml.safe_load(f) or {}
                    return SocialMediaConfig.from_dict(config_dict)
                except Exception as e:
                    logger.error(f"Failed to load default config: {e}")
            
            # Return default config
            return SocialMediaConfig()
    
    def _initialize_components(self):
        """Initialize all social media components"""
        try:
            # Validate configuration
            config_issues = self.config.validate_config()
            if config_issues:
                logger.warning(f"Configuration issues: {config_issues}")
            
            # Initialize data manager
            self.data_manager = SocialDataManager(self.config)
            
            # Initialize feature engine
            self.feature_engine = SocialFeatureEngine(self.config, self.data_manager)
            
            # Initialize validator
            self.validator = SocialSignalValidator(self.config)
            
            # Initialize monitoring dashboard
            self.monitoring = SocialMonitoringDashboard(self.config)
            
            logger.info(f"Initialized components: data_manager={self.data_manager is not None}, "
                       f"feature_engine={self.feature_engine is not None}, "
                       f"validator={self.validator is not None}, "
                       f"monitoring={self.monitoring is not None}")
            
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            self.enabled = False
    
    async def get_social_signal(self, coin_id: str, 
                              data_types: List[str] = None) -> Dict[str, Any]:
        """
        Get complete social signal for a coin
        
        Args:
            coin_id: Coin identifier
            data_types: Types of data to fetch (optional)
            
        Returns:
            Dictionary containing social features, validation results, and recommendations
        """
        if not self.enabled:
            return self._get_disabled_response(coin_id)
        
        try:
            # Generate social features
            social_features = await self.feature_engine.generate_features(coin_id, data_types)
            
            # Validate social signal
            validation_result = await self.validator.validate_signal(coin_id, social_features)
            
            # Update monitoring
            if self.monitoring:
                self.monitoring.update_metrics(coin_id, social_features, validation_result)
            
            # Create response
            response = {
                "coin_id": coin_id,
                "timestamp": datetime.now().isoformat(),
                "enabled": True,
                "social_features": {
                    "sms": social_features.features.get("sms", 0),
                    "volume_velocity": social_features.features.get("volume_velocity", 0),
                    "weighted_sentiment": social_features.features.get("weighted_sentiment", 0),
                    "influencer_activity": social_features.features.get("influencer_activity", 0),
                    "network_centrality": social_features.features.get("network_centrality", 0),
                    "bot_likeness": social_features.features.get("bot_likeness", 0),
                    "cross_validation": social_features.features.get("cross_validation", 0)
                },
                "validation": {
                    "is_valid": validation_result.is_valid,
                    "validation_score": validation_result.validation_score,
                    "confidence": validation_result.confidence,
                    "recommendation": validation_result.recommendation,
                    "risk_level": validation_result.risk_level,
                    "details": validation_result.details
                },
                "quality": {
                    "quality_score": social_features.quality_score,
                    "confidence": social_features.confidence,
                    "data_sources": social_features.metadata.get("data_sources", [])
                },
                "metadata": {
                    "feature_confidences": social_features.metadata.get("feature_confidences", {}),
                    "raw_data_quality": social_features.metadata.get("raw_data_quality", {})
                }
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Social signal generation failed for {coin_id}: {e}")
            return self._get_error_response(coin_id, str(e))
    
    def _get_disabled_response(self, coin_id: str) -> Dict[str, Any]:
        """Get response when social media integration is disabled"""
        return {
            "coin_id": coin_id,
            "timestamp": datetime.now().isoformat(),
            "enabled": False,
            "social_features": {},
            "validation": {
                "is_valid": True,
                "validation_score": 1.0,
                "confidence": 1.0,
                "recommendation": "proceed",
                "risk_level": "low",
                "details": {"reason": "Social media integration disabled"}
            },
            "quality": {
                "quality_score": 1.0,
                "confidence": 1.0,
                "data_sources": []
            },
            "metadata": {}
        }
    
    def _get_error_response(self, coin_id: str, error: str) -> Dict[str, Any]:
        """Get response when an error occurs"""
        return {
            "coin_id": coin_id,
            "timestamp": datetime.now().isoformat(),
            "enabled": True,
            "error": error,
            "social_features": {},
            "validation": {
                "is_valid": False,
                "validation_score": 0.0,
                "confidence": 0.0,
                "recommendation": "hold",
                "risk_level": "high",
                "details": {"error": error}
            },
            "quality": {
                "quality_score": 0.0,
                "confidence": 0.0,
                "data_sources": []
            },
            "metadata": {}
        }
    
    async def get_batch_signals(self, coin_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get social signals for multiple coins"""
        if not self.enabled:
            return {coin_id: self._get_disabled_response(coin_id) for coin_id in coin_ids}
        
        try:
            # Process coins concurrently
            tasks = [self.get_social_signal(coin_id) for coin_id in coin_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            batch_results = {}
            for i, result in enumerate(results):
                coin_id = coin_ids[i]
                if isinstance(result, Exception):
                    batch_results[coin_id] = self._get_error_response(coin_id, str(result))
                else:
                    batch_results[coin_id] = result
            
            return batch_results
            
        except Exception as e:
            logger.error(f"Batch signal generation failed: {e}")
            return {coin_id: self._get_error_response(coin_id, str(e)) for coin_id in coin_ids}
    
    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Get monitoring dashboard data"""
        if not self.enabled or not self.monitoring:
            return {"enabled": False, "reason": "Monitoring disabled"}
        
        try:
            return self.monitoring.get_dashboard_data()
        except Exception as e:
            logger.error(f"Dashboard data generation failed: {e}")
            return {"enabled": False, "error": str(e)}
    
    def export_monitoring_data(self, output_dir: str) -> Dict[str, str]:
        """Export monitoring data to files"""
        if not self.enabled or not self.monitoring:
            return {"error": "Monitoring not available"}
        
        try:
            return self.monitoring.export_data(output_dir)
        except Exception as e:
            logger.error(f"Data export failed: {e}")
            return {"error": str(e)}
    
    def get_configuration_status(self) -> Dict[str, Any]:
        """Get current configuration status"""
        return {
            "enabled": self.enabled,
            "config_issues": self.config.validate_config(),
            "enabled_sources": self.config.get_enabled_sources(),
            "feature_status": {
                "features_enabled": self.config.is_feature_enabled("features"),
                "validation_enabled": self.config.is_feature_enabled("validation"),
                "ml_integration_enabled": self.config.is_feature_enabled("ml_integration"),
                "monitoring_enabled": self.config.is_feature_enabled("monitoring")
            },
            "components_initialized": {
                "data_manager": self.data_manager is not None,
                "feature_engine": self.feature_engine is not None,
                "validator": self.validator is not None,
                "monitoring": self.monitoring is not None
            }
        }
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific feature is enabled"""
        return self.enabled and self.config.is_feature_enabled(feature_name)
    
    def get_enabled_sources(self) -> List[str]:
        """Get list of enabled data sources"""
        if not self.enabled:
            return []
        return self.config.get_enabled_sources()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components"""
        health_status = {
            "overall": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        if not self.enabled:
            health_status["overall"] = "disabled"
            return health_status
        
        try:
            # Check data manager
            if self.data_manager:
                enabled_sources = self.data_manager.get_enabled_sources()
                health_status["components"]["data_manager"] = {
                    "status": "healthy",
                    "enabled_sources": enabled_sources,
                    "source_count": len(enabled_sources)
                }
            else:
                health_status["components"]["data_manager"] = {"status": "not_initialized"}
            
            # Check feature engine
            if self.feature_engine:
                feature_names = self.feature_engine.get_feature_names()
                health_status["components"]["feature_engine"] = {
                    "status": "healthy",
                    "feature_count": len(feature_names),
                    "features": feature_names
                }
            else:
                health_status["components"]["feature_engine"] = {"status": "not_initialized"}
            
            # Check validator
            if self.validator:
                health_status["components"]["validator"] = {
                    "status": "healthy",
                    "validation_enabled": self.config.validation.enabled
                }
            else:
                health_status["components"]["validator"] = {"status": "not_initialized"}
            
            # Check monitoring
            if self.monitoring:
                dashboard_data = self.monitoring.get_dashboard_data()
                health_status["components"]["monitoring"] = {
                    "status": "healthy",
                    "monitoring_enabled": dashboard_data.get("enabled", False),
                    "active_alerts": len(self.monitoring.active_alerts)
                }
            else:
                health_status["components"]["monitoring"] = {"status": "not_initialized"}
            
            # Determine overall health
            component_statuses = [comp["status"] for comp in health_status["components"].values()]
            if "not_initialized" in component_statuses:
                health_status["overall"] = "degraded"
            elif all(status == "healthy" for status in component_statuses):
                health_status["overall"] = "healthy"
            else:
                health_status["overall"] = "unhealthy"
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_status["overall"] = "error"
            health_status["error"] = str(e)
        
        return health_status
    
    def clear_alerts(self, alert_type: Optional[str] = None):
        """Clear monitoring alerts"""
        if self.monitoring:
            self.monitoring.clear_alerts(alert_type)
    
    def get_coin_metrics(self, coin_id: str, hours: int = 24) -> Optional[List[Dict[str, Any]]]:
        """Get historical metrics for a coin"""
        if not self.monitoring:
            return None
        
        metrics = self.monitoring.get_coin_metrics(coin_id, hours)
        if metrics:
            return [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "sms": m.sms,
                    "volume_velocity": m.volume_velocity,
                    "weighted_sentiment": m.weighted_sentiment,
                    "influencer_activity": m.influencer_activity,
                    "network_centrality": m.network_centrality,
                    "bot_likeness": m.bot_likeness,
                    "cross_validation": m.cross_validation,
                    "quality_score": m.quality_score,
                    "confidence": m.confidence,
                    "risk_level": m.risk_level
                }
                for m in metrics
            ]
        return None


# Convenience function for easy integration
def create_social_integration(config_path: Optional[str] = None) -> SocialMediaIntegration:
    """Create and return a SocialMediaIntegration instance"""
    return SocialMediaIntegration(config_path)
