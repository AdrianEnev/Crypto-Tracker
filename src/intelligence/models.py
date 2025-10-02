"""
Data models for the intelligence system
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List


class CrisisLevel(Enum):
    """Crisis severity levels"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    UNKNOWN = 99


class IntelligenceTier(Enum):
    """Intelligence tier levels"""
    MACRO = 1
    MARKET = 2
    TACTICAL = 3
    EXECUTION = 4


@dataclass
class CrisisStatus:
    """Crisis detection result from Tier 1"""
    level: CrisisLevel
    reason: str = ""
    confidence: float = 0.0
    risk_adjustment: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def none(cls):
        """No crisis detected"""
        return cls(
            level=CrisisLevel.NONE,
            reason="No crisis detected",
            confidence=1.0,
            risk_adjustment=1.0
        )
    
    @classmethod
    def unknown(cls):
        """Unknown crisis status (error state)"""
        return cls(
            level=CrisisLevel.UNKNOWN,
            reason="Unable to determine crisis status",
            confidence=0.0,
            risk_adjustment=0.5
        )


@dataclass
class SocialSentiment:
    """Social media sentiment analysis result"""
    score: float  # -1 to 1
    volume: int
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sources: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def default(cls):
        """Default neutral sentiment"""
        return cls(
            score=0.0,
            volume=0,
            confidence=0.0,
            sources=[]
        )


@dataclass
class OrderbookSignal:
    """Orderbook analysis result"""
    bid_ask_imbalance: float  # -1 to 1
    spread_bps: float
    bid_walls: List[Dict[str, float]]
    ask_walls: List[Dict[str, float]]
    is_liquid: bool
    is_favorable: bool
    depth_score: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def default(cls):
        """Default orderbook signal"""
        return cls(
            bid_ask_imbalance=0.0,
            spread_bps=5.0,  # More realistic 5 bps spread
            bid_walls=[],
            ask_walls=[],
            is_liquid=True,  # Assume liquid when no data available
            is_favorable=True,  # Assume favorable when no data available
            depth_score=0.5  # Neutral depth score
        )


@dataclass
class OnChainSignal:
    """On-chain data analysis result"""
    exchange_flow_score: float  # -1 to 1
    whale_activity_score: float
    miner_pressure_score: float
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def default(cls):
        """Default on-chain signal"""
        return cls(
            exchange_flow_score=0.0,
            whale_activity_score=0.0,
            miner_pressure_score=0.0,
            confidence=0.0
        )


@dataclass
class DerivativesSignal:
    """Derivatives market analysis result"""
    funding_rate: float
    open_interest_change: float
    liquidations_score: float
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def default(cls):
        """Default derivatives signal"""
        return cls(
            funding_rate=0.0,
            open_interest_change=0.0,
            liquidations_score=0.0,
            confidence=0.0
        )


@dataclass
class MarketState:
    """Market intelligence from Tier 2"""
    regime: str  # "TRENDING", "RANGING", "VOLATILE", "UNKNOWN"
    regime_confidence: float
    social_sentiment: SocialSentiment
    orderbook_signal: OrderbookSignal
    onchain_signal: OnChainSignal
    derivatives_signal: DerivativesSignal
    is_tradeable: bool
    reason: str
    confidence: float
    risk_multiplier: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def default(cls):
        """Default market state"""
        return cls(
            regime="UNKNOWN",
            regime_confidence=0.0,
            social_sentiment=SocialSentiment.default(),
            orderbook_signal=OrderbookSignal.default(),
            onchain_signal=OnChainSignal.default(),
            derivatives_signal=DerivativesSignal.default(),
            is_tradeable=False,
            reason="Unable to determine market state",
            confidence=0.0,
            risk_multiplier=0.5
        )


@dataclass
class TacticalSignal:
    """Trading signal from Tier 3"""
    action: str  # "BUY", "SELL", "HOLD"
    confidence: float
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_name: str = ""
    reason: str = ""
    features: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def hold_default(cls):
        """Default hold signal"""
        return cls(
            action="HOLD",
            confidence=0.0,
            reason="No signal generated"
        )


@dataclass
class ExecutionPlan:
    """Execution plan from Tier 4"""
    order_type: str  # "MARKET", "LIMIT", "TWAP", "VWAP"
    position_size: float
    position_size_usd: float
    limit_price: Optional[float] = None
    time_horizon_seconds: int = 0
    expected_slippage_bps: float = 0.0
    execution_strategy: str = "IMMEDIATE"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def default(cls):
        """Default execution plan"""
        return cls(
            order_type="MARKET",
            position_size=0.0,
            position_size_usd=0.0
        )


@dataclass
class TradingDecision:
    """Final trading decision from orchestrator"""
    action: str  # "BUY", "SELL", "HOLD", "EMERGENCY_HOLD"
    confidence: float
    reason: str
    signal: str = "intelligence_decision"  # Signal type for compatibility
    execution_plan: Optional[ExecutionPlan] = None
    tier_reached: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def hold_default(cls):
        """Default hold decision"""
        return cls(
            action="HOLD",
            confidence=0.0,
            reason="Default hold - no decision made",
            signal="default_hold",
            tier_reached=0
        )
    
    @classmethod
    def emergency_hold(cls, reason: str):
        """Emergency hold decision"""
        return cls(
            action="EMERGENCY_HOLD",
            confidence=1.0,
            reason=reason,
            signal="emergency_hold",
            tier_reached=1
        )
