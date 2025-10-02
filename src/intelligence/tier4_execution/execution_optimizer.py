"""
Tier 4: Execution Intelligence

Optimizes trade execution:
- Position sizing based on confidence and risk
- Order type selection
- Slippage prediction
- Execution timing
"""

import logging
from typing import Optional

from ..base import BaseIntelligence
from ..models import ExecutionPlan, TacticalSignal, MarketState


class ExecutionIntelligence(BaseIntelligence):
    """
    Optimizes trade execution
    
    Features:
    - Dynamic position sizing
    - Order type selection
    - Slippage estimation
    - Execution timing
    """
    
    def __init__(self, config: dict, portfolio_manager=None):
        super().__init__(config, logger_name=__name__)
        
        self.portfolio_manager = portfolio_manager
        
        # Configuration
        self.max_position_size_pct = config.get('max_position_size_pct', 10.0)
        self.base_position_size_usd = config.get('base_position_size_usd', 1000.0)
        self.use_rl_sizing = config.get('rl_position_sizing', False)
        self.slippage_model_enabled = config.get('slippage_model_enabled', False)
    
    async def analyze(
        self,
        signal: TacticalSignal,
        market_state: MarketState,
        current_price: float
    ) -> ExecutionPlan:
        """
        Create execution plan
        
        Args:
            signal: Tactical signal from Tier 3
            market_state: Market state from Tier 2
            current_price: Current market price
            
        Returns:
            ExecutionPlan
        """
        return await self.plan(signal, market_state, current_price)
    
    async def plan(
        self,
        signal: TacticalSignal,
        market_state: MarketState,
        current_price: float
    ) -> ExecutionPlan:
        """
        Plan optimal execution
        
        Returns:
            ExecutionPlan with order details
        """
        try:
            # Calculate position size
            position_size_usd = self._calculate_position_size(
                signal, market_state
            )
            
            # Convert to coin units
            position_size = position_size_usd / current_price
            
            # Select order type
            order_type = self._select_order_type(market_state, signal)
            
            # Calculate limit price if needed
            limit_price = self._calculate_limit_price(
                current_price, signal.action, market_state
            ) if order_type == "LIMIT" else None
            
            # Estimate slippage
            expected_slippage = self._estimate_slippage(
                position_size_usd, market_state
            )
            
            # Determine execution strategy
            execution_strategy = self._select_execution_strategy(
                position_size_usd, market_state
            )
            
            self.record_success()
            
            return ExecutionPlan(
                order_type=order_type,
                position_size=position_size,
                position_size_usd=position_size_usd,
                limit_price=limit_price,
                expected_slippage_bps=expected_slippage,
                execution_strategy=execution_strategy
            )
            
        except Exception as e:
            self.logger.error(f"Execution planning failed: {e}")
            self.record_failure(e)
            return ExecutionPlan.default()
    
    def _calculate_position_size(
        self,
        signal: TacticalSignal,
        market_state: MarketState
    ) -> float:
        """
        Calculate position size in USD
        
        Uses confidence-based sizing with risk adjustments
        
        Returns:
            Position size in USD
        """
        # Base size
        base_size = self.base_position_size_usd
        
        # Adjust by confidence
        confidence_multiplier = signal.confidence
        
        # Adjust by market risk
        risk_multiplier = market_state.risk_multiplier
        
        # Calculate final size
        position_size = base_size * confidence_multiplier * risk_multiplier
        
        # Apply maximum limit
        if self.portfolio_manager:
            portfolio_value = self._get_portfolio_value()
            max_size = portfolio_value * (self.max_position_size_pct / 100.0)
            position_size = min(position_size, max_size)
        
        # Minimum size check
        min_size = 100.0  # $100 minimum
        if position_size < min_size:
            position_size = 0.0
        
        return position_size
    
    def _select_order_type(
        self,
        market_state: MarketState,
        signal: TacticalSignal
    ) -> str:
        """
        Select appropriate order type
        
        Returns:
            Order type: "MARKET", "LIMIT", "TWAP", "VWAP"
        """
        # Use MARKET for liquid markets with tight spreads
        if market_state.orderbook_signal.is_liquid and \
           market_state.orderbook_signal.spread_bps < 20:
            return "MARKET"
        
        # Use LIMIT for wider spreads
        if market_state.orderbook_signal.spread_bps > 20:
            return "LIMIT"
        
        # Default to MARKET
        return "MARKET"
    
    def _calculate_limit_price(
        self,
        current_price: float,
        action: str,
        market_state: MarketState
    ) -> Optional[float]:
        """
        Calculate limit price for LIMIT orders
        
        Places order inside the spread to get better execution
        """
        spread_bps = market_state.orderbook_signal.spread_bps
        
        # Place order at midpoint or slightly better
        if action == "BUY":
            # Buy slightly above best bid
            adjustment = -spread_bps / 2 / 10000  # Half spread
            return current_price * (1 + adjustment)
        elif action == "SELL":
            # Sell slightly below best ask
            adjustment = spread_bps / 2 / 10000
            return current_price * (1 + adjustment)
        
        return None
    
    def _estimate_slippage(
        self,
        position_size_usd: float,
        market_state: MarketState
    ) -> float:
        """
        Estimate expected slippage in basis points
        
        Returns:
            Expected slippage in bps
        """
        if self.slippage_model_enabled:
            # Use ML model to predict slippage
            # For now, use simple heuristic
            pass
        
        # Simple slippage estimation
        base_slippage = market_state.orderbook_signal.spread_bps / 2
        
        # Adjust for order size
        if position_size_usd > 10000:
            base_slippage *= 1.5
        elif position_size_usd > 50000:
            base_slippage *= 2.0
        
        # Adjust for liquidity
        if not market_state.orderbook_signal.is_liquid:
            base_slippage *= 2.0
        
        return base_slippage
    
    def _select_execution_strategy(
        self,
        position_size_usd: float,
        market_state: MarketState
    ) -> str:
        """
        Select execution strategy
        
        Returns:
            Strategy: "IMMEDIATE", "TWAP", "VWAP", "ICEBERG"
        """
        # Large orders use TWAP
        if position_size_usd > 50000:
            return "TWAP"
        
        # Medium orders in illiquid markets use VWAP
        if position_size_usd > 10000 and not market_state.orderbook_signal.is_liquid:
            return "VWAP"
        
        # Default to immediate execution
        return "IMMEDIATE"
    
    def _get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        if self.portfolio_manager:
            try:
                return self.portfolio_manager.get_total_value()
            except Exception:
                pass
        
        # Default value
        return 10000.0
