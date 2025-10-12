#!/usr/bin/env python3
"""
Strategy Manager - Trading Strategy Execution

Manages trading strategies and coordinates with the trading executor.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent))

from trading_executor import TradingExecutor, OrderSide


class TriggerType(Enum):
    """Strategy trigger types."""
    ALERT = "alert"
    PRICE_BREAKOUT = "price_breakout"
    TIME_BASED = "time_based"
    GRID = "grid"
    MANUAL = "manual"


class StrategyManager:
    """
    Manages trading strategies and their execution.
    """
    
    def __init__(self, config: Dict[str, Any], executor: TradingExecutor):
        """
        Initialize strategy manager.
        
        Args:
            config: Strategy configuration
            executor: Trading executor instance
        """
        self.config = config
        self.executor = executor
        self.strategies = config.get('strategies', [])
        self.alert_trading_rules = config.get('alert_trading', {}).get('rules', [])
        
        # Strategy state tracking
        self.strategy_states: Dict[str, Dict[str, Any]] = {}
        self.last_execution_times: Dict[str, datetime] = {}
        
        self._initialize_strategies()
    
    def _initialize_strategies(self):
        """Initialize strategy states."""
        for strategy in self.strategies:
            strategy_id = strategy['id']
            self.strategy_states[strategy_id] = {
                'enabled': strategy.get('enabled', True),
                'executions': 0,
                'last_execution': None,
                'active_positions': []
            }
    
    def handle_alert_trigger(self, alert_id: str, symbol: str, current_price: float):
        """
        Handle a price alert trigger and execute associated strategies.
        
        Args:
            alert_id: Alert identifier that triggered
            symbol: Trading pair symbol
            current_price: Current market price
        """
        # Find trading rules for this alert
        matching_rules = [r for r in self.alert_trading_rules if r['alert_id'] == alert_id]
        
        if not matching_rules:
            return
        
        for rule in matching_rules:
            strategy_id = rule.get('strategy_id')
            action = rule.get('action', 'BUY')
            
            if strategy_id:
                strategy = self._get_strategy(strategy_id)
                if strategy and strategy.get('enabled', True):
                    self._execute_strategy(strategy, symbol, current_price, action)
    
    def _get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get strategy by ID."""
        for strategy in self.strategies:
            if strategy['id'] == strategy_id:
                return strategy
        return None
    
    def _execute_strategy(
        self,
        strategy: Dict[str, Any],
        symbol: str,
        current_price: float,
        action: str = 'BUY'
    ):
        """
        Execute a trading strategy.
        
        Args:
            strategy: Strategy configuration
            symbol: Trading pair
            current_price: Current market price
            action: BUY or SELL
        """
        strategy_id = strategy['id']
        
        # Check if strategy is enabled
        if not self.strategy_states[strategy_id]['enabled']:
            print(f"[STRATEGY] {strategy_id} is disabled, skipping")
            return
        
        # Get entry configuration
        entry_config = strategy.get('entry', {})
        exit_config = strategy.get('exit', {})
        
        # Determine order side
        side = OrderSide.BUY if action == 'BUY' else OrderSide.SELL
        
        # Determine position size
        position_size_usd = entry_config.get('position_size_usd')
        if position_size_usd is None:
            # Use risk-based sizing
            position_size_usd = self.executor.config.get('risk', {}).get('max_position_size_usd', 100.0)
        
        # Calculate quantity
        quantity = position_size_usd / current_price
        
        # Apply minimum quantity filters (would need to check exchange info)
        # For now, simplified
        
        # Determine entry price (limit order offset)
        order_type = entry_config.get('order_type', 'limit')
        
        if order_type == 'limit':
            limit_offset_pct = entry_config.get('limit_offset_pct', 0.1)
            
            if side == OrderSide.BUY:
                # Place buy limit below current price
                entry_price = current_price * (1 - limit_offset_pct / 100.0)
            else:
                # Place sell limit above current price
                entry_price = current_price * (1 + limit_offset_pct / 100.0)
        else:
            # Market order
            entry_price = current_price
        
        # Calculate stop-loss and take-profit
        stop_loss_pct = exit_config.get('stop_loss_pct')
        take_profit_pct = exit_config.get('take_profit_pct')
        
        stop_loss_price = None
        take_profit_price = None
        
        if stop_loss_pct:
            if side == OrderSide.BUY:
                stop_loss_price = entry_price * (1 - stop_loss_pct / 100.0)
            else:
                stop_loss_price = entry_price * (1 + stop_loss_pct / 100.0)
        
        if take_profit_pct:
            if side == OrderSide.BUY:
                take_profit_price = entry_price * (1 + take_profit_pct / 100.0)
            else:
                take_profit_price = entry_price * (1 - take_profit_pct / 100.0)
        
        # Check safety limits
        if not self._check_safety_limits(position_size_usd):
            return
        
        # Execute the trade
        print(f"\n[STRATEGY] Executing: {strategy['name']}")
        print(f"  Symbol: {symbol}")
        print(f"  Action: {side.value}")
        print(f"  Entry Price: ${entry_price:.8f}")
        print(f"  Quantity: {quantity:.6f}")
        print(f"  Position Value: ${position_size_usd:.2f}")
        if stop_loss_price:
            print(f"  Stop Loss: ${stop_loss_price:.8f} (-{stop_loss_pct}%)")
        if take_profit_price:
            print(f"  Take Profit: ${take_profit_price:.8f} (+{take_profit_pct}%)")
        
        # Place the order
        order_result = self.executor.place_limit_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=entry_price,
            stop_loss=stop_loss_price,
            take_profit=take_profit_price
        )
        
        if order_result:
            # Update strategy state
            self.strategy_states[strategy_id]['executions'] += 1
            self.strategy_states[strategy_id]['last_execution'] = datetime.now()
            self.last_execution_times[strategy_id] = datetime.now()
            
            print(f"[STRATEGY] ✅ {strategy['name']} executed successfully")
        else:
            print(f"[STRATEGY] ❌ {strategy['name']} execution failed")
    
    def _check_safety_limits(self, position_size_usd: float) -> bool:
        """
        Check if trade passes safety limits.
        
        Args:
            position_size_usd: Intended position size
            
        Returns:
            True if safe to trade
        """
        risk_config = self.executor.config.get('risk', {})
        
        # Check max position size
        max_position_size = risk_config.get('max_position_size_usd', 200.0)
        if position_size_usd > max_position_size:
            print(f"[SAFETY] Position size ${position_size_usd:.2f} exceeds max ${max_position_size:.2f}")
            return False
        
        # Check max open positions
        max_open_positions = risk_config.get('max_open_positions', 5)
        open_positions = self.executor.get_open_positions()
        if len(open_positions) >= max_open_positions:
            print(f"[SAFETY] Max open positions ({max_open_positions}) reached")
            return False
        
        # Check daily loss limit
        max_daily_loss = risk_config.get('max_daily_loss_usd')
        if max_daily_loss:
            # Calculate today's PnL
            today_pnl = self._calculate_daily_pnl()
            if today_pnl < -max_daily_loss:
                print(f"[SAFETY] Daily loss limit reached: ${today_pnl:.2f}")
                return False
        
        # Check circuit breaker
        safety_config = self.executor.config.get('safety', {})
        circuit_breaker = safety_config.get('circuit_breaker', {})
        if circuit_breaker.get('enabled', False):
            # Would check portfolio drawdown here
            # For now, simplified
            pass
        
        return True
    
    def _calculate_daily_pnl(self) -> float:
        """Calculate PnL for today."""
        # Simplified - would actually track by date
        return 0.0
    
    def check_time_based_strategies(self):
        """Check and execute time-based strategies."""
        for strategy in self.strategies:
            if not strategy.get('enabled', True):
                continue
            
            trigger = strategy.get('trigger', {})
            if trigger.get('type') != 'time_based':
                continue
            
            strategy_id = strategy['id']
            interval_hours = trigger.get('interval_hours', 24)
            
            # Check if enough time has passed
            last_exec = self.last_execution_times.get(strategy_id)
            if last_exec:
                hours_since = (datetime.now() - last_exec).total_seconds() / 3600
                if hours_since < interval_hours:
                    continue
            
            # Execute the strategy
            symbol = strategy.get('entry', {}).get('symbol', 'BTCUSDT')
            current_price = self.executor.get_current_price(symbol)
            
            if current_price:
                self._execute_strategy(strategy, symbol, current_price)
    
    def check_breakout_strategies(self, symbol: str, current_price: float):
        """
        Check price breakout strategies.
        
        Args:
            symbol: Trading pair
            current_price: Current price
        """
        for strategy in self.strategies:
            if not strategy.get('enabled', True):
                continue
            
            trigger = strategy.get('trigger', {})
            if trigger.get('type') != 'price_breakout':
                continue
            
            if trigger.get('symbol') != symbol:
                continue
            
            breakout_price = trigger.get('breakout_price')
            if breakout_price is None:
                continue
            
            # Check if price broke out
            strategy_id = strategy['id']
            if strategy_id in self.strategy_states:
                # Check if already executed
                if self.strategy_states[strategy_id]['last_execution']:
                    continue
            
            if current_price >= breakout_price:
                print(f"[BREAKOUT] {symbol} broke above ${breakout_price:.8f}")
                self._execute_strategy(strategy, symbol, current_price)
    
    def update_positions(self, symbol: str, current_price: float):
        """
        Update all open positions for price changes.
        
        Args:
            symbol: Trading pair
            current_price: Current price
        """
        # Check for stop-loss and take-profit hits
        self.executor.check_position_exits(symbol, current_price)
        
        # Update trailing stops
        for position_id, position in self.executor.positions.items():
            if position['symbol'] == symbol and position['status'] == 'OPEN':
                self.executor.update_trailing_stop(position_id, current_price)
    
    def get_strategy_summary(self) -> Dict[str, Any]:
        """Get summary of all strategies."""
        summary = {
            'total_strategies': len(self.strategies),
            'enabled_strategies': len([s for s in self.strategies if s.get('enabled', True)]),
            'total_executions': sum(s['executions'] for s in self.strategy_states.values()),
            'strategies': []
        }
        
        for strategy in self.strategies:
            strategy_id = strategy['id']
            state = self.strategy_states.get(strategy_id, {})
            
            summary['strategies'].append({
                'id': strategy_id,
                'name': strategy['name'],
                'enabled': state.get('enabled', True),
                'executions': state.get('executions', 0),
                'last_execution': state.get('last_execution')
            })
        
        return summary
