"""
Intelligence Orchestrator - Main Decision Engine

Coordinates all 4 intelligence tiers with proper priority:
1. Tier 1 (Macro/Crisis) - Highest priority, can veto all trading
2. Tier 2 (Market Intelligence) - Market conditions and sentiment
3. Tier 3 (Tactical) - Strategy selection and signal generation
4. Tier 4 (Execution) - Position sizing and execution optimization
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from .models import TradingDecision, CrisisLevel
from .tier1_macro import MacroIntelligence
from .tier2_market import MarketIntelligence
from .tier3_tactical import TacticalIntelligence
from .tier4_execution import ExecutionIntelligence
from .error_handler import IntelligenceFallbackHandler


class IntelligenceOrchestrator:
    """
    Central decision engine coordinating all intelligence tiers
    
    Decision Flow:
    1. Check for crises (Tier 1) - Can halt all trading
    2. Analyze market state (Tier 2) - Determines if conditions are favorable
    3. Generate tactical signal (Tier 3) - Creates trading signal
    4. Plan execution (Tier 4) - Optimizes order execution
    
    Priority: TIER 1 > TIER 2 > TIER 3 > TIER 4
    """
    
    def __init__(
        self,
        config: dict,
        llm_client,
        data_feeds,
        ml_models=None,
        strategies=None,
        portfolio_manager=None
    ):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Debug: Log the config structure
        self.logger.info(f"Orchestrator initialized with config keys: {list(config.keys())}")
        if 'tier2_market' in config:
            tier2 = config['tier2_market']
            self.logger.info(f"Tier2 keys: {list(tier2.keys())}")
            if 'market_analyzer' in tier2:
                analyzer = tier2['market_analyzer']
                self.logger.info(f"Market analyzer keys: {list(analyzer.keys())}")
                self.logger.info(f"min_confidence_threshold: {analyzer.get('min_confidence_threshold')}")
        
        # Initialize error handler
        self.error_handler = IntelligenceFallbackHandler(
            config.get('error_handling', {})
        )
        
        # Initialize all tiers
        tier1_config = config.get('tier1_macro', {})
        tier2_config = config.get('tier2_market', {})
        tier3_config = config.get('tier3_tactical', {})
        tier4_config = config.get('tier4_execution', {})
        
        self.tier1 = MacroIntelligence(llm_client, tier1_config)
        self.tier2 = MarketIntelligence(tier2_config, data_feeds, ml_models)
        self.tier3 = TacticalIntelligence(tier3_config, ml_models, strategies)
        self.tier4 = ExecutionIntelligence(tier4_config, portfolio_manager)
        
        # Statistics
        self.decision_count = 0
        self.tier_reached_stats = {1: 0, 2: 0, 3: 0, 4: 0}
        
        self.logger.info("Intelligence Orchestrator initialized")
    
    async def make_decision(
        self,
        coin_id: str,
        current_price: float,
        symbol: Optional[str] = None
    ) -> TradingDecision:
        """
        Main decision-making method
        
        Args:
            coin_id: Coin identifier (e.g., 'bitcoin')
            current_price: Current market price
            symbol: Trading symbol (e.g., 'BTC/USDT')
            
        Returns:
            TradingDecision with action, confidence, and execution plan
        """
        self.decision_count += 1
        start_time = datetime.now(timezone.utc)
        
        try:
            # TIER 1: Crisis Detection (ABSOLUTE PRIORITY)
            crisis_status = await self._check_crisis()
            
            if crisis_status.level == CrisisLevel.CRITICAL:
                self.tier_reached_stats[1] += 1
                return TradingDecision.emergency_hold(
                    reason=f"CRITICAL CRISIS: {crisis_status.reason}"
                )
            
            # Get risk adjustment from crisis level
            risk_multiplier = crisis_status.risk_adjustment
            
            if crisis_status.level == CrisisLevel.HIGH:
                self.logger.warning(
                    f"HIGH crisis level detected: {crisis_status.reason}. "
                    f"Risk multiplier: {risk_multiplier}"
                )
            
            # TIER 2: Market Intelligence
            market_state = await self._analyze_market(coin_id, symbol)
            
            # Check if market is tradeable
            if not market_state.is_tradeable:
                self.tier_reached_stats[2] += 1
                return TradingDecision(
                    action="HOLD",
                    confidence=0.5,
                    reason=f"Unfavorable market: {market_state.reason}",
                    signal="market_unfavorable",
                    tier_reached=2,
                    metadata={
                        'crisis_level': crisis_status.level.name,
                        'market_regime': market_state.regime,
                        'orderbook_liquid': market_state.orderbook_signal.is_liquid
                    }
                )
            
            # TIER 3: Tactical Signal Generation
            tactical_signal = await self._generate_tactical_signal(
                coin_id,
                current_price,
                market_state,
                risk_multiplier
            )
            
            # Calculate final confidence
            final_confidence = (
                tactical_signal.confidence *
                risk_multiplier *
                market_state.risk_multiplier
            )
            
            # Check confidence threshold
            confidence_threshold = self.config.get('min_confidence_threshold', 
                self.config.get('tier2_market', {}).get('market_analyzer', {}).get('min_confidence_threshold', 0.2))
            
            # Debug: Log the config structure and threshold
            self.logger.info(f"Orchestrator config keys: {list(self.config.keys())}")
            self.logger.info(f"Using confidence threshold: {confidence_threshold}")
            self.logger.info(f"Final confidence: {final_confidence}")
            if final_confidence < confidence_threshold:
                self.tier_reached_stats[3] += 1
                return TradingDecision(
                    action="HOLD",
                    confidence=final_confidence,
                    reason=f"Confidence {final_confidence:.2f} below threshold {confidence_threshold}",
                    signal="low_confidence",
                    tier_reached=3,
                    metadata=self._build_metadata(
                        crisis_status, market_state, tactical_signal
                    )
                )
            
            # Only proceed to execution if we have a non-HOLD signal
            if tactical_signal.action == "HOLD":
                self.tier_reached_stats[3] += 1
                return TradingDecision(
                    action="HOLD",
                    confidence=final_confidence,
                    reason=tactical_signal.reason,
                    signal="tactical_hold",
                    tier_reached=3,
                    metadata=self._build_metadata(
                        crisis_status, market_state, tactical_signal
                    )
                )
            
            # TIER 4: Execution Planning
            execution_plan = await self._plan_execution(
                tactical_signal,
                market_state,
                current_price
            )
            
            # Build final decision
            self.tier_reached_stats[4] += 1
            
            decision = TradingDecision(
                action=tactical_signal.action,
                confidence=final_confidence,
                reason=self._build_reason(crisis_status, market_state, tactical_signal),
                signal="intelligence_decision",
                execution_plan=execution_plan,
                tier_reached=4,
                metadata=self._build_metadata(
                    crisis_status, market_state, tactical_signal, execution_plan
                )
            )
            
            # Log decision
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.logger.info(
                f"Decision #{self.decision_count} for {coin_id}: "
                f"{decision.action} (confidence: {decision.confidence:.2f}, "
                f"elapsed: {elapsed:.2f}s)"
            )
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Orchestrator error for {coin_id}: {e}", exc_info=True)
            self.error_handler.handle_failure('orchestrator', e)
            return TradingDecision.hold_default()
    
    async def _check_crisis(self):
        """TIER 1: Check for macro/political/economic crises"""
        try:
            if not self.error_handler.is_enabled('llm'):
                self.logger.debug("LLM disabled, skipping crisis detection")
                from .models import CrisisStatus
                return CrisisStatus.none()
            
            crisis_status = await self.tier1.detect_crisis()
            self.error_handler.handle_success('tier1_crisis')
            return crisis_status
            
        except Exception as e:
            self.logger.warning(f"Tier 1 (Crisis) failed: {e}")
            self.error_handler.handle_failure('tier1_crisis', e)
            from .models import CrisisStatus
            return CrisisStatus.unknown()
    
    async def _analyze_market(self, coin_id: str, symbol: Optional[str]):
        """TIER 2: Analyze market conditions, sentiment, orderbook"""
        try:
            market_state = await self.tier2.analyze(coin_id, symbol)
            self.error_handler.handle_success('tier2_market')
            return market_state
            
        except Exception as e:
            self.logger.warning(f"Tier 2 (Market) failed: {e}")
            self.error_handler.handle_failure('tier2_market', e)
            from .models import MarketState
            return MarketState.default()
    
    async def _generate_tactical_signal(
        self,
        coin_id: str,
        price: float,
        market_state,
        risk_multiplier: float
    ):
        """TIER 3: Generate ML-enhanced trading signal"""
        try:
            signal = await self.tier3.generate_signal(
                coin_id,
                price,
                market_state,
                risk_multiplier
            )
            self.error_handler.handle_success('tier3_tactical')
            return signal
            
        except Exception as e:
            self.logger.warning(f"Tier 3 (Tactical) failed: {e}")
            self.error_handler.handle_failure('tier3_tactical', e)
            from .models import TacticalSignal
            return TacticalSignal.hold_default()
    
    async def _plan_execution(self, signal, market_state, price: float):
        """TIER 4: Plan optimal execution"""
        try:
            plan = await self.tier4.plan(signal, market_state, price)
            self.error_handler.handle_success('tier4_execution')
            return plan
            
        except Exception as e:
            self.logger.warning(f"Tier 4 (Execution) failed: {e}")
            self.error_handler.handle_failure('tier4_execution', e)
            from .models import ExecutionPlan
            return ExecutionPlan.default()
    
    def _build_reason(self, crisis, market_state, signal) -> str:
        """Build human-readable reason for decision"""
        parts = []
        
        # Crisis level
        if crisis.level != CrisisLevel.NONE:
            parts.append(f"Crisis: {crisis.level.name}")
        
        # Market regime
        parts.append(f"Regime: {market_state.regime}")
        
        # Social sentiment
        if market_state.social_sentiment.volume > 0:
            sentiment = market_state.social_sentiment.score
            parts.append(f"Social: {sentiment:+.2f}")
        
        # Strategy
        if signal.strategy_name:
            parts.append(f"Strategy: {signal.strategy_name}")
        
        # Signal reason
        if signal.reason:
            parts.append(signal.reason)
        
        return " | ".join(parts)
    
    def _build_metadata(self, crisis, market_state, signal, execution=None) -> dict:
        """Build metadata dictionary for decision"""
        metadata = {
            'crisis_level': crisis.level.name,
            'crisis_confidence': crisis.confidence,
            'market_regime': market_state.regime,
            'regime_confidence': market_state.regime_confidence,
            'social_sentiment_score': market_state.social_sentiment.score,
            'social_sentiment_volume': market_state.social_sentiment.volume,
            'orderbook_imbalance': market_state.orderbook_signal.bid_ask_imbalance,
            'orderbook_spread_bps': market_state.orderbook_signal.spread_bps,
            'orderbook_liquid': market_state.orderbook_signal.is_liquid,
            'strategy_name': signal.strategy_name,
            'signal_confidence': signal.confidence
        }
        
        if execution:
            metadata.update({
                'position_size_usd': execution.position_size_usd,
                'order_type': execution.order_type,
                'expected_slippage_bps': execution.expected_slippage_bps
            })
        
        return metadata
    
    def get_statistics(self) -> dict:
        """Get orchestrator statistics"""
        return {
            'total_decisions': self.decision_count,
            'tier_reached': self.tier_reached_stats,
            'error_handler_status': self.error_handler.get_status(),
            'tier1_enabled': self.tier1.is_enabled(),
            'tier2_enabled': self.tier2.is_enabled(),
            'tier3_enabled': self.tier3.is_enabled(),
            'tier4_enabled': self.tier4.is_enabled()
        }
    
    def register_alert_callback(self, callback):
        """Register callback for alerts"""
        self.error_handler.register_alert_callback(callback)
