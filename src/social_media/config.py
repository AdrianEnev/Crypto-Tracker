"""
Social Media Configuration Management

Handles configuration for all social media features with safety defaults.
All features are disabled by default and must be explicitly enabled.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import os
import re
from pathlib import Path


@dataclass
class DataSourceConfig:
    """Configuration for a single data source"""
    enabled: bool = False
    api_key: Optional[str] = None
    rate_limit: int = 100
    timeout: int = 30
    retry_count: int = 3
    cache_ttl: int = 300  # 5 minutes default cache
    priority: int = 1  # Higher number = higher priority
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.enabled and not self.api_key:
            # Try to get from environment
            self.api_key = os.environ.get(f"{self.__class__.__name__.upper()}_API_KEY")


@dataclass
class LunarCrushConfig(DataSourceConfig):
    """LunarCrush specific configuration"""
    base_url: str = "https://lunarcrush.com/api"
    features: List[str] = field(default_factory=lambda: [
        "social_volume", "sentiment_score", "influencer_activity"
    ])


@dataclass
class SantimentConfig(DataSourceConfig):
    """Santiment specific configuration"""
    base_url: str = "https://api.santiment.net"
    features: List[str] = field(default_factory=lambda: [
        "social_volume", "sentiment", "on_chain_social"
    ])


@dataclass
class GlassnodeConfig(DataSourceConfig):
    """Glassnode specific configuration"""
    base_url: str = "https://api.glassnode.com"
    features: List[str] = field(default_factory=lambda: [
        "exchange_flows", "whale_movements", "network_activity"
    ])


@dataclass
class CryptoQuantConfig(DataSourceConfig):
    """CryptoQuant specific configuration"""
    base_url: str = "https://api.cryptoquant.com"
    features: List[str] = field(default_factory=lambda: [
        "exchange_netflow", "funding_rates", "futures_basis"
    ])


@dataclass
class GoogleTrendsConfig(DataSourceConfig):
    """Google Trends specific configuration"""
    base_url: str = "https://trends.google.com/trends/api"
    features: List[str] = field(default_factory=lambda: [
        "search_volume", "regional_interest", "related_queries"
    ])
    # Google Trends doesn't need API key
    enabled: bool = True
    api_key: Optional[str] = None


@dataclass
class NewsAPIConfig(DataSourceConfig):
    """News API specific configuration"""
    base_url: str = "https://newsapi.org/v2"
    features: List[str] = field(default_factory=lambda: [
        "headline_sentiment", "mention_frequency", "source_credibility"
    ])


@dataclass
class TwitterConfig(DataSourceConfig):
    """Twitter API specific configuration"""
    base_url: str = "https://api.twitter.com/2"
    bearer_token: Optional[str] = None
    features: List[str] = field(default_factory=lambda: [
        "social_volume", "sentiment_score", "engagement_score", "influencer_activity"
    ])
    
    def __post_init__(self):
        """Validate Twitter configuration"""
        super().__post_init__()
        if self.enabled and not self.bearer_token:
            self.bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")


@dataclass
class RedditConfig(DataSourceConfig):
    """Reddit API specific configuration"""
    base_url: str = "https://oauth.reddit.com"
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    user_agent: str = "CryptoDiscoveryScanner/1.0"
    subreddits: List[str] = field(default_factory=lambda: [
        "cryptocurrency", "bitcoin", "ethereum", "cryptomarkets", "cryptocurrencytrading"
    ])
    features: List[str] = field(default_factory=lambda: [
        "post_volume", "sentiment_score", "engagement_score", "hot_topics"
    ])
    
    def __post_init__(self):
        """Validate Reddit configuration"""
        super().__post_init__()
        if self.enabled:
            if not self.client_id:
                self.client_id = os.environ.get("REDDIT_CLIENT_ID")
            if not self.client_secret:
                self.client_secret = os.environ.get("REDDIT_CLIENT_SECRET")


@dataclass
class ExchangeAPIConfig(DataSourceConfig):
    """Exchange APIs configuration for funding rates and derivatives"""
    exchanges: List[str] = field(default_factory=lambda: [
        "binance", "bybit", "okx", "deribit", "bitmex"
    ])
    features: List[str] = field(default_factory=lambda: [
        "funding_rate", "open_interest", "long_short_ratio", "exchange_flows"
    ])
    update_interval: int = 300  # 5 minutes
    max_retries: int = 3
    
    def __post_init__(self):
        """Validate Exchange API configuration"""
        super().__post_init__()
        # Exchange APIs are free, no credentials needed


@dataclass
class SocialFeatureConfig:
    """Configuration for social feature engineering"""
    enabled: bool = False
    
    # Social Momentum Score weights
    sms_weights: Dict[str, float] = field(default_factory=lambda: {
        "volume_velocity": 0.25,
        "weighted_sentiment": 0.30,
        "influencer_activity": 0.20,
        "network_centrality": 0.15,
        "bot_likeness": -0.10,  # Negative weight for bot detection
        "cross_validation": 0.20
    })
    
    # Feature calculation parameters
    volume_window: int = 24  # Hours for volume calculations
    sentiment_window: int = 6  # Hours for sentiment calculations
    influencer_threshold: int = 10000  # Minimum followers for influencer status
    
    # Safety limits
    max_social_weight: float = 0.3  # Maximum weight social signals can have
    min_data_quality: float = 0.7  # Minimum data quality score required
    max_feature_age: int = 3600  # Maximum age of features in seconds


@dataclass
class ValidationConfig:
    """Configuration for social signal validation"""
    enabled: bool = False
    
    # Cross-validation requirements
    require_onchain_confirmation: bool = True
    require_volume_confirmation: bool = True
    require_derivatives_confirmation: bool = False
    
    # Validation thresholds
    min_validation_score: float = 0.7
    min_onchain_correlation: float = 0.5
    min_volume_correlation: float = 0.3
    
    # Manipulation detection
    manipulation_detection: bool = True
    coordination_threshold: float = 0.8
    bot_likeness_threshold: float = 0.7
    
    # Safety measures
    social_signal_cooldown: int = 300  # 5 minutes between social signals
    manipulation_penalty: float = 0.5  # Reduce confidence by 50% if manipulation detected


@dataclass
class MLIntegrationConfig:
    """Configuration for ML model integration"""
    enabled: bool = False
    
    # Model configuration
    model_type: str = "ensemble"  # "technical_only", "social_enhanced", "ensemble"
    retrain_frequency: str = "daily"  # "hourly", "daily", "weekly"
    feature_importance_threshold: float = 0.05
    
    # Ensemble weights
    ensemble_weights: Dict[str, float] = field(default_factory=lambda: {
        "technical": 0.6,
        "social": 0.25,
        "onchain": 0.15
    })
    
    # Safety limits
    max_ml_weight: float = 0.4  # Maximum weight ML can have in final decision
    min_training_samples: int = 1000
    max_model_age: int = 86400  # 24 hours


@dataclass
class MonitoringConfig:
    """Configuration for monitoring and alerting"""
    enabled: bool = False
    
    # Dashboard configuration
    dashboard_enabled: bool = True
    dashboard_port: int = 8080
    dashboard_refresh_interval: int = 60  # seconds
    
    # Alerting configuration
    alerts_enabled: bool = True
    alert_channels: List[str] = field(default_factory=lambda: ["console", "log"])
    
    # Alert thresholds
    high_sentiment_threshold: float = 0.8
    manipulation_alert_threshold: float = 0.7
    volume_spike_threshold: float = 3.0  # 3x normal volume
    
    # Data retention
    log_retention_days: int = 30
    metrics_retention_days: int = 7


@dataclass
class SocialMediaConfig:
    """Main configuration class for all social media features"""
    
    # Global settings
    enabled: bool = False
    debug: bool = False
    log_level: str = "INFO"
    
    # Data sources
    lunarcrush: LunarCrushConfig = field(default_factory=LunarCrushConfig)
    santiment: SantimentConfig = field(default_factory=SantimentConfig)
    glassnode: GlassnodeConfig = field(default_factory=GlassnodeConfig)
    cryptoquant: CryptoQuantConfig = field(default_factory=CryptoQuantConfig)
    google_trends: GoogleTrendsConfig = field(default_factory=GoogleTrendsConfig)
    news_api: NewsAPIConfig = field(default_factory=NewsAPIConfig)
    twitter: TwitterConfig = field(default_factory=TwitterConfig)
    reddit: RedditConfig = field(default_factory=RedditConfig)
    exchange_api: ExchangeAPIConfig = field(default_factory=ExchangeAPIConfig)
    
    # Feature engineering
    features: SocialFeatureConfig = field(default_factory=SocialFeatureConfig)
    
    # Validation
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    
    # ML integration
    ml_integration: MLIntegrationConfig = field(default_factory=MLIntegrationConfig)
    
    # Monitoring
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    @classmethod
    def _substitute_env_vars(cls, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute environment variables in config values"""
        def substitute_value(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                return os.environ.get(env_var, value)
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value
        
        return substitute_value(config_dict)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "SocialMediaConfig":
        """Create configuration from dictionary"""
        # Substitute environment variables
        config_dict = cls._substitute_env_vars(config_dict)
        # Extract nested configurations
        lunarcrush_config = LunarCrushConfig(**config_dict.get("lunarcrush", {}))
        santiment_config = SantimentConfig(**config_dict.get("santiment", {}))
        glassnode_config = GlassnodeConfig(**config_dict.get("glassnode", {}))
        cryptoquant_config = CryptoQuantConfig(**config_dict.get("cryptoquant", {}))
        google_trends_config = GoogleTrendsConfig(**config_dict.get("google_trends", {}))
        news_api_config = NewsAPIConfig(**config_dict.get("news_api", {}))
        twitter_config = TwitterConfig(**config_dict.get("twitter", {}))
        reddit_config = RedditConfig(**config_dict.get("reddit", {}))
        exchange_api_config = ExchangeAPIConfig(**config_dict.get("exchange_api", {}))
        
        features_config = SocialFeatureConfig(**config_dict.get("features", {}))
        validation_config = ValidationConfig(**config_dict.get("validation", {}))
        ml_config = MLIntegrationConfig(**config_dict.get("ml_integration", {}))
        monitoring_config = MonitoringConfig(**config_dict.get("monitoring", {}))
        
        return cls(
            enabled=config_dict.get("enabled", False),
            debug=config_dict.get("debug", False),
            log_level=config_dict.get("log_level", "INFO"),
            lunarcrush=lunarcrush_config,
            santiment=santiment_config,
            glassnode=glassnode_config,
            cryptoquant=cryptoquant_config,
            google_trends=google_trends_config,
            news_api=news_api_config,
            twitter=twitter_config,
            reddit=reddit_config,
            exchange_api=exchange_api_config,
            features=features_config,
            validation=validation_config,
            ml_integration=ml_config,
            monitoring=monitoring_config
        )
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific feature is enabled"""
        if not self.enabled:
            return False
        
        feature_map = {
            "lunarcrush": self.lunarcrush.enabled,
            "santiment": self.santiment.enabled,
            "glassnode": self.glassnode.enabled,
            "cryptoquant": self.cryptoquant.enabled,
            "google_trends": self.google_trends.enabled,
            "news_api": self.news_api.enabled,
            "features": self.features.enabled,
            "validation": self.validation.enabled,
            "ml_integration": self.ml_integration.enabled,
            "monitoring": self.monitoring.enabled
        }
        
        return feature_map.get(feature_name, False)
    
    def get_enabled_sources(self) -> List[str]:
        """Get list of enabled data sources"""
        sources = []
        if self.lunarcrush.enabled:
            sources.append("lunarcrush")
        if self.santiment.enabled:
            sources.append("santiment")
        if self.glassnode.enabled:
            sources.append("glassnode")
        if self.cryptoquant.enabled:
            sources.append("cryptoquant")
        if self.google_trends.enabled:
            sources.append("google_trends")
        if self.news_api.enabled:
            sources.append("news_api")
        if self.twitter.enabled:
            sources.append("twitter")
        if self.reddit.enabled:
            sources.append("reddit")
        if self.exchange_api.enabled:
            sources.append("exchange_api")
        return sources
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return any issues"""
        issues = []
        
        # Check API keys for enabled sources
        if self.lunarcrush.enabled and not self.lunarcrush.api_key:
            issues.append("LunarCrush API key required when enabled")
        
        if self.santiment.enabled and not self.santiment.api_key:
            issues.append("Santiment API key required when enabled")
        
        if self.glassnode.enabled and not self.glassnode.api_key:
            issues.append("Glassnode API key required when enabled")
        
        if self.cryptoquant.enabled and not self.cryptoquant.api_key:
            issues.append("CryptoQuant API key required when enabled")
        
        if self.news_api.enabled and not self.news_api.api_key:
            issues.append("News API key required when enabled")
        
        # Validate weight sums
        sms_weight_sum = sum(self.features.sms_weights.values())
        if abs(sms_weight_sum - 1.0) > 0.01:
            issues.append(f"SMS weights must sum to 1.0, got {sms_weight_sum}")
        
        ensemble_weight_sum = sum(self.ml_integration.ensemble_weights.values())
        if abs(ensemble_weight_sum - 1.0) > 0.01:
            issues.append(f"Ensemble weights must sum to 1.0, got {ensemble_weight_sum}")
        
        # Validate thresholds
        if self.validation.min_validation_score < 0 or self.validation.min_validation_score > 1:
            issues.append("Validation score threshold must be between 0 and 1")
        
        if self.features.max_social_weight < 0 or self.features.max_social_weight > 1:
            issues.append("Max social weight must be between 0 and 1")
        
        return issues
