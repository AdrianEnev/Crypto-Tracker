#!/usr/bin/env python3
"""
Phantom Volatile Trading Strategy

Ultra-fast trading strategy specifically designed for Phantom memecoins.
Focuses on speed, volatility, and efficiency without historical analysis or ML.
"""

import asyncio
import sys
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import numpy as np

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class PhantomVolatileStrategy:
    """Ultra-fast volatile trading strategy for Phantom memecoins with micro-analysis."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Phantom-specific parameters
        self.volatility_threshold = config.get('volatility_threshold', 0.05)  # 5%
        self.momentum_window = config.get('momentum_window', 5)  # 5 minutes
        self.entry_aggression = config.get('entry_aggression', 0.8)  # 80%
        self.exit_speed = config.get('exit_speed', 0.9)  # 90%
        self.max_position_size = config.get('max_position_size', 0.1)  # 0.1 SOL
        self.stop_loss_pct = config.get('stop_loss_pct', 0.3)  # 30%
        self.take_profit_pct = config.get('take_profit_pct', 2.0)  # 200%
        self.trailing_stop = config.get('trailing_stop', True)
        self.trailing_distance = config.get('trailing_distance', 0.15)  # 15%
        
        # Micro-analysis parameters
        self.analysis_window_hours = 1.0  # Analyze past 1 hour
        self.min_data_points = 10  # Minimum data points for analysis
        self.dip_threshold = 0.15  # 15% dip from ATH to consider buying
        self.pump_threshold = 0.3  # 30% pump to avoid buying at peak
        self.support_resistance_sensitivity = 0.05  # 5% for S/R levels
        
        # Price tracking for volatility analysis
        self.price_history: List[Tuple[datetime, float]] = []
        self.max_history = 200  # Keep more data for micro-analysis
        
        # Micro-analysis cache
        self.last_analysis_time = None
        self.cached_analysis = None
        self.analysis_cache_duration = 30  # Cache analysis for 30 seconds
        
        # Position tracking
        self.current_position = None
        self.entry_price = None
        self.highest_price = None
        self.position_start_time = None
        
    def should_enter_position(self, current_price: float, volume: float = 0) -> Tuple[bool, str, float]:
        """
        Determine if we should enter a position based on micro-analysis of recent history.
        Returns: (should_enter, reason, confidence)
        """
        try:
            # Add current price to history
            self.price_history.append((datetime.now(), current_price))
            
            # Keep only recent history
            if len(self.price_history) > self.max_history:
                self.price_history = self.price_history[-self.max_history:]
            
            # Need sufficient data for micro-analysis
            if len(self.price_history) < self.min_data_points:
                return False, "insufficient_data", 0.0
            
            # Perform micro-analysis of recent price action
            micro_analysis = self._perform_micro_analysis(current_price)
            
            # Check if we should enter based on micro-analysis
            entry_signals = []
            confidence_factors = []
            
            # 1. Dip buying opportunity (ATH dip)
            if micro_analysis['is_dip_buy']:
                entry_signals.append("dip_buy_opportunity")
                confidence_factors.append(micro_analysis['dip_confidence'])
            
            # 2. Support level bounce
            if micro_analysis['is_support_bounce']:
                entry_signals.append("support_bounce")
                confidence_factors.append(micro_analysis['support_confidence'])
            
            # 3. Avoid pump peaks
            if micro_analysis['is_pump_peak']:
                return False, f"avoiding_pump_peak: {micro_analysis['pump_reason']}", 0.0
            
            # 4. Trend continuation (if not at peak)
            if micro_analysis['trend_continuation'] and not micro_analysis['is_pump_peak']:
                entry_signals.append("trend_continuation")
                confidence_factors.append(micro_analysis['trend_confidence'])
            
            # 5. Volume confirmation
            if volume > 0 and micro_analysis['volume_confirms_entry']:
                entry_signals.append("volume_confirmation")
                confidence_factors.append(0.8)
            
            # 6. Volatility sweet spot (not too low, not too high)
            if micro_analysis['volatility_sweet_spot']:
                entry_signals.append("volatility_sweet_spot")
                confidence_factors.append(micro_analysis['volatility_confidence'])
            
            # Calculate overall confidence
            if not confidence_factors:
                return False, f"no_entry_signals: {micro_analysis['analysis_summary']}", 0.0
            
            overall_confidence = np.mean(confidence_factors) * self.entry_aggression
            
            # Need at least 1 strong signal or 2 moderate signals
            strong_signals = sum(1 for cf in confidence_factors if cf > 0.7)
            moderate_signals = sum(1 for cf in confidence_factors if 0.4 <= cf <= 0.7)
            
            should_enter = (
                strong_signals >= 1 or 
                moderate_signals >= 2 or 
                (len(entry_signals) >= 2 and overall_confidence > 0.6)
            )
            
            if should_enter:
                reason = f"phantom_micro_entry: {', '.join(entry_signals)}"
                return True, reason, min(overall_confidence, 1.0)
            
            return False, f"insufficient_micro_signals: {micro_analysis['analysis_summary']}", overall_confidence
            
        except Exception as e:
            self.logger.error(f"Error in micro-analysis: {e}")
            return False, "analysis_error", 0.0
    
    def should_exit_position(self, current_price: float) -> Tuple[bool, str, float]:
        """
        Determine if we should exit a position based on volatility and profit/loss.
        Returns: (should_exit, reason, confidence)
        """
        try:
            if not self.current_position or not self.entry_price:
                return False, "no_position", 0.0
            
            # Calculate current P&L
            pnl_pct = (current_price / self.entry_price - 1) * 100
            
            # Update highest price for trailing stop
            if self.highest_price is None or current_price > self.highest_price:
                self.highest_price = current_price
            
            exit_signals = []
            confidence_factors = []
            
            # 1. Stop loss hit
            if pnl_pct <= -self.stop_loss_pct * 100:
                exit_signals.append("stop_loss")
                confidence_factors.append(1.0)
            
            # 2. Take profit hit
            if pnl_pct >= self.take_profit_pct * 100:
                exit_signals.append("take_profit")
                confidence_factors.append(1.0)
            
            # 3. Trailing stop (if enabled)
            if self.trailing_stop and self.highest_price:
                trailing_stop_price = self.highest_price * (1 - self.trailing_distance)
                if current_price <= trailing_stop_price:
                    exit_signals.append("trailing_stop")
                    confidence_factors.append(1.0)
            
            # 4. Volatility drop (memecoin losing steam)
            if len(self.price_history) >= 5:
                recent_prices = [p[1] for p in self.price_history[-5:]]
                recent_volatility = self._calculate_volatility(recent_prices)
                if recent_volatility < self.volatility_threshold * 0.5:
                    exit_signals.append("volatility_drop")
                    confidence_factors.append(0.8)
            
            # 5. Momentum reversal
            if len(self.price_history) >= 3:
                recent_prices = [p[1] for p in self.price_history[-3:]]
                momentum = self._calculate_momentum(recent_prices)
                if momentum < -0.01:  # Negative momentum
                    exit_signals.append("momentum_reversal")
                    confidence_factors.append(0.7)
            
            # 6. Time-based exit (memecoins have short lifespans)
            if self.position_start_time:
                position_duration = datetime.now() - self.position_start_time
                if position_duration.total_seconds() > 3600:  # 1 hour
                    exit_signals.append("time_limit")
                    confidence_factors.append(0.6)
            
            # Calculate overall confidence
            if not confidence_factors:
                return False, "no_exit_signals", 0.0
            
            overall_confidence = np.mean(confidence_factors) * self.exit_speed
            
            # Exit if we have any strong signal
            if len(exit_signals) >= 1 and overall_confidence > 0.6:
                reason = f"phantom_exit: {', '.join(exit_signals)}"
                return True, reason, min(overall_confidence, 1.0)
            
            return False, f"holding_position: pnl={pnl_pct:.2f}%", overall_confidence
            
        except Exception as e:
            self.logger.error(f"Error in exit analysis: {e}")
            return False, "analysis_error", 0.0
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility."""
        if len(prices) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if not returns:
            return 0.0
        
        return np.std(returns)
    
    def _calculate_momentum(self, prices: List[float]) -> float:
        """Calculate price momentum."""
        if len(prices) < 2:
            return 0.0
        
        return (prices[-1] - prices[0]) / prices[0]
    
    def _calculate_price_velocity(self, prices: List[float]) -> float:
        """Calculate price velocity (rate of change)."""
        if len(prices) < 2:
            return 0.0
        
        # Calculate average rate of change
        changes = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                changes.append(abs(prices[i] - prices[i-1]) / prices[i-1])
        
        if not changes:
            return 0.0
        
        return np.mean(changes)
    
    def _calculate_trending_strength(self, prices: List[float]) -> float:
        """Calculate trending strength (consistency of direction)."""
        if len(prices) < 3:
            return 0.0
        
        # Count consecutive moves in same direction
        consecutive_up = 0
        consecutive_down = 0
        max_consecutive_up = 0
        max_consecutive_down = 0
        
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                consecutive_up += 1
                consecutive_down = 0
                max_consecutive_up = max(max_consecutive_up, consecutive_up)
            elif prices[i] < prices[i-1]:
                consecutive_down += 1
                consecutive_up = 0
                max_consecutive_down = max(max_consecutive_down, consecutive_down)
        
        # Trending strength is based on longest consecutive move
        max_consecutive = max(max_consecutive_up, max_consecutive_down)
        return min(max_consecutive / len(prices), 1.0)
    
    def _perform_micro_analysis(self, current_price: float) -> Dict[str, Any]:
        """
        Perform micro-analysis of recent price action to identify optimal entry points.
        Analyzes the past hour of price data to determine:
        - All-time high and current position relative to it
        - Support and resistance levels
        - Trend direction and strength
        - Volatility patterns
        - Pump/dip detection
        """
        try:
            # Check cache first
            current_time = datetime.now()
            if (self.last_analysis_time and 
                (current_time - self.last_analysis_time).total_seconds() < self.analysis_cache_duration and
                self.cached_analysis):
                return self.cached_analysis
            
            # Get recent price data (past hour)
            cutoff_time = current_time - timedelta(hours=self.analysis_window_hours)
            recent_prices = [(dt, price) for dt, price in self.price_history if dt >= cutoff_time]
            
            if len(recent_prices) < self.min_data_points:
                analysis = {
                    'is_dip_buy': False,
                    'is_support_bounce': False,
                    'is_pump_peak': False,
                    'trend_continuation': False,
                    'volume_confirms_entry': False,
                    'volatility_sweet_spot': False,
                    'dip_confidence': 0.0,
                    'support_confidence': 0.0,
                    'trend_confidence': 0.0,
                    'volatility_confidence': 0.0,
                    'pump_reason': 'insufficient_data',
                    'analysis_summary': 'insufficient_data_for_analysis'
                }
                self.cached_analysis = analysis
                self.last_analysis_time = current_time
                return analysis
            
            # Extract price values and timestamps
            prices = [p[1] for p in recent_prices]
            timestamps = [p[0] for p in recent_prices]
            
            # Calculate key metrics
            ath = max(prices)  # All-time high in analysis window
            atl = min(prices)  # All-time low in analysis window
            current_position = (current_price - atl) / (ath - atl) if ath != atl else 0.5
            
            # Calculate volatility
            volatility = self._calculate_volatility(prices)
            
            # Calculate momentum
            momentum = self._calculate_momentum(prices[-5:]) if len(prices) >= 5 else 0
            
            # Detect support and resistance levels
            support_levels = self._detect_support_levels(prices)
            resistance_levels = self._detect_resistance_levels(prices)
            
            # Analyze trend
            trend_direction = self._analyze_trend_direction(prices)
            trend_strength = self._calculate_trending_strength(prices)
            
            # Initialize analysis result
            analysis = {
                'is_dip_buy': False,
                'is_support_bounce': False,
                'is_pump_peak': False,
                'trend_continuation': False,
                'volume_confirms_entry': True,  # Default to True for memecoins
                'volatility_sweet_spot': False,
                'dip_confidence': 0.0,
                'support_confidence': 0.0,
                'trend_confidence': 0.0,
                'volatility_confidence': 0.0,
                'pump_reason': '',
                'analysis_summary': ''
            }
            
            # 1. Dip buying analysis
            dip_from_ath = (ath - current_price) / ath if ath > 0 else 0
            if dip_from_ath >= self.dip_threshold:
                analysis['is_dip_buy'] = True
                analysis['dip_confidence'] = min(dip_from_ath / self.dip_threshold, 1.0)
            
            # 2. Support bounce analysis
            near_support = any(abs(current_price - support) / current_price < self.support_resistance_sensitivity 
                             for support in support_levels)
            if near_support and momentum > 0:
                analysis['is_support_bounce'] = True
                analysis['support_confidence'] = 0.8
            
            # 3. Pump peak detection
            recent_pump = (current_price - min(prices[-10:])) / min(prices[-10:]) if len(prices) >= 10 else 0
            if recent_pump >= self.pump_threshold:
                analysis['is_pump_peak'] = True
                analysis['pump_reason'] = f'recent_pump_{recent_pump:.1%}'
            
            # Also check if near resistance
            near_resistance = any(abs(current_price - resistance) / current_price < self.support_resistance_sensitivity 
                                for resistance in resistance_levels)
            if near_resistance and momentum < 0:
                analysis['is_pump_peak'] = True
                analysis['pump_reason'] = 'near_resistance_with_negative_momentum'
            
            # 4. Trend continuation analysis
            if trend_direction > 0 and trend_strength > 0.6 and not analysis['is_pump_peak']:
                analysis['trend_continuation'] = True
                analysis['trend_confidence'] = trend_strength
            
            # 5. Volatility sweet spot analysis
            # Memecoins should have moderate volatility - not too low (dead), not too high (unstable)
            if 0.02 <= volatility <= 0.15:  # 2% to 15% volatility
                analysis['volatility_sweet_spot'] = True
                analysis['volatility_confidence'] = 0.8
            
            # Generate analysis summary
            summary_parts = []
            if analysis['is_dip_buy']:
                summary_parts.append(f"dip_{dip_from_ath:.1%}")
            if analysis['is_support_bounce']:
                summary_parts.append("support_bounce")
            if analysis['is_pump_peak']:
                summary_parts.append("pump_peak")
            if analysis['trend_continuation']:
                summary_parts.append("trend_up")
            if analysis['volatility_sweet_spot']:
                summary_parts.append("vol_sweet")
            
            analysis['analysis_summary'] = ', '.join(summary_parts) if summary_parts else 'neutral'
            
            # Cache the analysis
            self.cached_analysis = analysis
            self.last_analysis_time = current_time
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in micro-analysis: {e}")
            return {
                'is_dip_buy': False,
                'is_support_bounce': False,
                'is_pump_peak': False,
                'trend_continuation': False,
                'volume_confirms_entry': False,
                'volatility_sweet_spot': False,
                'dip_confidence': 0.0,
                'support_confidence': 0.0,
                'trend_confidence': 0.0,
                'volatility_confidence': 0.0,
                'pump_reason': 'analysis_error',
                'analysis_summary': 'error'
            }
    
    def _detect_support_levels(self, prices: List[float]) -> List[float]:
        """Detect support levels in price data."""
        if len(prices) < 5:
            return []
        
        support_levels = []
        
        # Find local minima
        for i in range(2, len(prices) - 2):
            if (prices[i] < prices[i-1] and prices[i] < prices[i-2] and
                prices[i] < prices[i+1] and prices[i] < prices[i+2]):
                support_levels.append(prices[i])
        
        # Remove duplicates and sort
        support_levels = sorted(list(set(support_levels)))
        
        # Filter out levels that are too close to each other
        filtered_levels = []
        for level in support_levels:
            if not any(abs(level - existing) / level < 0.02 for existing in filtered_levels):
                filtered_levels.append(level)
        
        return filtered_levels
    
    def _detect_resistance_levels(self, prices: List[float]) -> List[float]:
        """Detect resistance levels in price data."""
        if len(prices) < 5:
            return []
        
        resistance_levels = []
        
        # Find local maxima
        for i in range(2, len(prices) - 2):
            if (prices[i] > prices[i-1] and prices[i] > prices[i-2] and
                prices[i] > prices[i+1] and prices[i] > prices[i+2]):
                resistance_levels.append(prices[i])
        
        # Remove duplicates and sort
        resistance_levels = sorted(list(set(resistance_levels)))
        
        # Filter out levels that are too close to each other
        filtered_levels = []
        for level in resistance_levels:
            if not any(abs(level - existing) / level < 0.02 for existing in filtered_levels):
                filtered_levels.append(level)
        
        return filtered_levels
    
    def _analyze_trend_direction(self, prices: List[float]) -> float:
        """Analyze trend direction (-1 to 1, where 1 is strong uptrend)."""
        if len(prices) < 3:
            return 0.0
        
        # Calculate linear regression slope
        n = len(prices)
        x = np.arange(n)
        y = np.array(prices)
        
        # Simple linear regression
        slope = np.corrcoef(x, y)[0, 1] * (np.std(y) / np.std(x))
        
        # Normalize to -1 to 1 range
        return np.clip(slope / np.std(y), -1, 1)
    
    def enter_position(self, price: float, amount: float):
        """Enter a position."""
        self.current_position = {
            'amount': amount,
            'entry_price': price,
            'entry_time': datetime.now()
        }
        self.entry_price = price
        self.highest_price = price
        self.position_start_time = datetime.now()
        
        self.logger.info(f"🔥 PHANTOM ENTRY: {amount} SOL at ${price:.8f}")
    
    def exit_position(self, price: float) -> Dict[str, Any]:
        """Exit a position and return trade summary."""
        if not self.current_position:
            return {}
        
        pnl_pct = (price / self.entry_price - 1) * 100
        pnl_sol = self.current_position['amount'] * (price / self.entry_price - 1)
        
        trade_summary = {
            'entry_price': self.entry_price,
            'exit_price': price,
            'amount': self.current_position['amount'],
            'pnl_pct': pnl_pct,
            'pnl_sol': pnl_sol,
            'duration': datetime.now() - self.position_start_time if self.position_start_time else timedelta(0),
            'entry_time': self.current_position['entry_time'],
            'exit_time': datetime.now()
        }
        
        self.logger.info(f"💰 PHANTOM EXIT: PnL {pnl_pct:.2f}% ({pnl_sol:.4f} SOL)")
        
        # Reset position
        self.current_position = None
        self.entry_price = None
        self.highest_price = None
        self.position_start_time = None
        
        return trade_summary
    
    def get_position_info(self) -> Dict[str, Any]:
        """Get current position information."""
        if not self.current_position:
            return {'has_position': False}
        
        return {
            'has_position': True,
            'amount': self.current_position['amount'],
            'entry_price': self.entry_price,
            'highest_price': self.highest_price,
            'position_start_time': self.position_start_time,
            'duration': datetime.now() - self.position_start_time if self.position_start_time else timedelta(0)
        }


class PhantomTradingEngine:
    """Main trading engine for Phantom memecoins."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize strategy
        strategy_config = config.get('strategy', {}).get('params', {})
        self.strategy = PhantomVolatileStrategy(strategy_config)
        
        # Trading state
        self.is_trading = False
        self.trade_history: List[Dict[str, Any]] = []
        
        # Risk management
        self.max_daily_loss = config.get('risk', {}).get('max_daily_loss_pct', 0.1) * 100
        self.max_position_pct = config.get('risk', {}).get('max_position_pct', 0.05)
        self.daily_pnl = 0.0
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
    async def process_price_update(self, symbol: str, price: float, volume: float = 0) -> Dict[str, Any]:
        """Process a price update and make trading decisions."""
        try:
            # Reset daily PnL if new day
            current_time = datetime.now()
            if current_time.date() > self.daily_reset_time.date():
                self.daily_pnl = 0.0
                self.daily_reset_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Check if we're in a position
            position_info = self.strategy.get_position_info()
            
            if position_info['has_position']:
                # Check for exit signals
                should_exit, exit_reason, exit_confidence = self.strategy.should_exit_position(price)
                
                if should_exit:
                    trade_summary = self.strategy.exit_position(price)
                    self.trade_history.append(trade_summary)
                    self.daily_pnl += trade_summary.get('pnl_sol', 0)
                    
                    return {
                        'action': 'exit',
                        'reason': exit_reason,
                        'confidence': exit_confidence,
                        'trade_summary': trade_summary
                    }
                else:
                    return {
                        'action': 'hold',
                        'reason': exit_reason,
                        'confidence': exit_confidence,
                        'position_info': position_info
                    }
            else:
                # Check for entry signals
                should_enter, entry_reason, entry_confidence = self.strategy.should_enter_position(price, volume)
                
                if should_enter and self._can_enter_position():
                    # Calculate position size
                    position_size = self._calculate_position_size(price)
                    
                    if position_size > 0:
                        self.strategy.enter_position(price, position_size)
                        
                        return {
                            'action': 'enter',
                            'reason': entry_reason,
                            'confidence': entry_confidence,
                            'position_size': position_size
                        }
                
                return {
                    'action': 'wait',
                    'reason': entry_reason,
                    'confidence': entry_confidence
                }
                
        except Exception as e:
            self.logger.error(f"Error processing price update: {e}")
            return {
                'action': 'error',
                'reason': str(e),
                'confidence': 0.0
            }
    
    def process_price_update_sync(self, symbol: str, price: float, volume: float = 0) -> Dict[str, Any]:
        """Synchronous version of process_price_update for use in main trading loop."""
        import asyncio
        
        # Create a new event loop if one doesn't exist
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async method
        return loop.run_until_complete(self.process_price_update(symbol, price, volume))
    
    def _can_enter_position(self) -> bool:
        """Check if we can enter a new position."""
        # Check daily loss limit
        if self.daily_pnl <= -self.max_daily_loss:
            return False
        
        # Check if we already have a position
        if self.strategy.get_position_info()['has_position']:
            return False
        
        return True
    
    def _calculate_position_size(self, price: float) -> float:
        """Calculate position size based on risk management."""
        # Base position size from config
        base_size = self.strategy.max_position_size
        
        # Adjust based on daily PnL
        if self.daily_pnl < 0:
            # Reduce size if we're losing
            reduction_factor = max(0.5, 1 + self.daily_pnl / self.max_daily_loss)
            base_size *= reduction_factor
        
        # Adjust based on volatility
        if len(self.strategy.price_history) >= 5:
            recent_prices = [p[1] for p in self.strategy.price_history[-5:]]
            volatility = self.strategy._calculate_volatility(recent_prices)
            
            # Increase size for higher volatility (memecoin characteristic)
            volatility_multiplier = min(2.0, 1 + volatility * 10)
            base_size *= volatility_multiplier
        
        return max(0.001, min(base_size, self.strategy.max_position_size))
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get trading performance summary."""
        if not self.trade_history:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl_sol': 0.0,
                'total_pnl_pct': 0.0,
                'avg_trade_duration': timedelta(0),
                'best_trade_pct': 0.0,
                'worst_trade_pct': 0.0
            }
        
        total_trades = len(self.trade_history)
        winning_trades = sum(1 for trade in self.trade_history if trade.get('pnl_pct', 0) > 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_pnl_sol = sum(trade.get('pnl_sol', 0) for trade in self.trade_history)
        total_pnl_pct = sum(trade.get('pnl_pct', 0) for trade in self.trade_history)
        
        durations = [trade.get('duration', timedelta(0)) for trade in self.trade_history]
        avg_duration = sum(durations, timedelta(0)) / len(durations) if durations else timedelta(0)
        
        pnl_pcts = [trade.get('pnl_pct', 0) for trade in self.trade_history]
        best_trade = max(pnl_pcts) if pnl_pcts else 0
        worst_trade = min(pnl_pcts) if pnl_pcts else 0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl_sol': total_pnl_sol,
            'total_pnl_pct': total_pnl_pct,
            'avg_trade_duration': avg_duration,
            'best_trade_pct': best_trade,
            'worst_trade_pct': worst_trade,
            'daily_pnl': self.daily_pnl
        }


async def main():
    """Test the Phantom volatile trading strategy with realistic memecoin patterns."""
    # Test configuration
    test_config = {
        'strategy': {
            'params': {
                'volatility_threshold': 0.05,
                'momentum_window': 5,
                'entry_aggression': 0.8,
                'exit_speed': 0.9,
                'max_position_size': 0.1,
                'stop_loss_pct': 0.3,
                'take_profit_pct': 2.0,
                'trailing_stop': True,
                'trailing_distance': 0.15
            }
        },
        'risk': {
            'max_daily_loss_pct': 0.1,
            'max_position_pct': 0.05
        }
    }
    
    engine = PhantomTradingEngine(test_config)
    
    # Simulate realistic memecoin price patterns
    # Pattern 1: Initial pump, dip, recovery (good entry)
    pattern1 = [0.001, 0.0011, 0.0013, 0.0016, 0.0020, 0.0025, 0.0028, 0.0025, 0.0020, 0.0018, 0.0015, 0.0012, 0.0010, 0.0011, 0.0013, 0.0016, 0.0018, 0.0020]
    
    # Pattern 2: Rapid pump to peak (avoid buying)
    pattern2 = [0.001, 0.0012, 0.0015, 0.0020, 0.0028, 0.0035, 0.0040, 0.0045, 0.0050, 0.0048, 0.0045, 0.0040, 0.0035, 0.0030, 0.0025, 0.0020, 0.0018, 0.0015]
    
    # Pattern 3: Support bounce (good entry)
    pattern3 = [0.001, 0.0012, 0.0015, 0.0018, 0.0015, 0.0012, 0.0010, 0.0009, 0.0008, 0.0009, 0.0010, 0.0012, 0.0015, 0.0018, 0.0020, 0.0022, 0.0025, 0.0028]
    
    test_patterns = [
        ("Pattern 1: Pump-Dip-Recovery", pattern1),
        ("Pattern 2: Rapid Pump (Avoid)", pattern2),
        ("Pattern 3: Support Bounce", pattern3)
    ]
    
    print("🔥 Testing Phantom Micro-Analysis Trading Strategy")
    print("=" * 60)
    
    for pattern_name, prices in test_patterns:
        print(f"\n📈 {pattern_name}")
        print("-" * 40)
        
        # Reset engine for each pattern
        engine = PhantomTradingEngine(test_config)
        
        for i, price in enumerate(prices):
            result = await engine.process_price_update("TESTMEME", price, 1000)
            
            # Get micro-analysis details
            strategy = engine.strategy
            if len(strategy.price_history) >= strategy.min_data_points:
                analysis = strategy._perform_micro_analysis(price)
                analysis_summary = analysis['analysis_summary']
            else:
                analysis_summary = "insufficient_data"
            
            print(f"Price: ${price:.6f} | Action: {result['action']} | Analysis: {analysis_summary}")
            print(f"  Reason: {result['reason']}")
            
            if result['action'] in ['enter', 'exit']:
                print(f"  Confidence: {result['confidence']:.2f}")
                if 'trade_summary' in result:
                    trade = result['trade_summary']
                    print(f"  PnL: {trade['pnl_pct']:.2f}% ({trade['pnl_sol']:.4f} SOL)")
        
        # Show performance summary for this pattern
        summary = engine.get_performance_summary()
        print(f"\n📊 {pattern_name} Results:")
        print(f"Total Trades: {summary['total_trades']}")
        print(f"Win Rate: {summary['win_rate']:.2%}")
        print(f"Total PnL: {summary['total_pnl_sol']:.4f} SOL ({summary['total_pnl_pct']:.2f}%)")


if __name__ == "__main__":
    asyncio.run(main())
