#!/usr/bin/env python3
"""
Simple Phantom Paper Trading Test

Standalone test that simulates real memecoin price patterns for paper trading validation.
"""

import asyncio
import sys
import os
import time
import json
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.phantom_volatile_strategy import PhantomTradingEngine


class SimplePhantomPaperTrader:
    """Simple paper trading system for testing Phantom memecoin strategies."""
    
    def __init__(self, initial_sol: float = 1.0):
        self.initial_sol = initial_sol
        self.current_sol = initial_sol
        self.current_memecoin = None
        self.current_memecoin_amount = 0.0
        self.current_memecoin_price = 0.0
        
        # Trading history
        self.trade_history = []
        self.price_history = []
        
        # Performance metrics
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl_sol': 0.0,
            'max_drawdown': 0.0,
            'peak_equity': initial_sol,
            'current_equity': initial_sol
        }
        
        # Strategy engine
        self.strategy_engine = None
        
        self.logger = logging.getLogger(__name__)
        
    def setup_strategy(self):
        """Setup the Phantom strategy engine."""
        strategy_config = {
            'strategy': {
                'params': {
                    'volatility_threshold': 0.05,
                    'momentum_window': 5,
                    'entry_aggression': 0.8,
                    'exit_speed': 0.9,
                    'max_position_size': 0.1,  # 0.1 SOL per trade
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
        
        self.strategy_engine = PhantomTradingEngine(strategy_config)
        
    def get_current_equity(self) -> float:
        """Calculate current equity in SOL."""
        if self.current_memecoin and self.current_memecoin_amount > 0:
            # Convert memecoin back to SOL value
            memecoin_value_sol = self.current_memecoin_amount * self.current_memecoin_price
            return self.current_sol + memecoin_value_sol
        return self.current_sol
    
    def execute_buy(self, memecoin: str, price: float, amount_sol: float) -> bool:
        """Execute a paper buy order."""
        if self.current_sol < amount_sol:
            self.logger.warning(f"Insufficient SOL for buy: {self.current_sol} < {amount_sol}")
            return False
        
        # Convert SOL to memecoin
        memecoin_amount = amount_sol / price
        
        # Update balances
        self.current_sol -= amount_sol
        self.current_memecoin = memecoin
        self.current_memecoin_amount = memecoin_amount
        self.current_memecoin_price = price
        
        # Record trade
        trade = {
            'timestamp': datetime.now(),
            'action': 'BUY',
            'memecoin': memecoin,
            'price': price,
            'amount_sol': amount_sol,
            'amount_memecoin': memecoin_amount,
            'balance_sol': self.current_sol,
            'balance_memecoin': memecoin_amount
        }
        self.trade_history.append(trade)
        
        self.logger.info(f"📈 PAPER BUY: {amount_sol:.4f} SOL → {memecoin_amount:.2f} {memecoin} @ ${price:.8f}")
        return True
    
    def execute_sell(self, memecoin: str, price: float) -> bool:
        """Execute a paper sell order."""
        if not self.current_memecoin or self.current_memecoin_amount <= 0:
            self.logger.warning("No memecoin position to sell")
            return False
        
        # Convert memecoin back to SOL
        sol_received = self.current_memecoin_amount * price
        
        # Calculate P&L
        original_sol_invested = self.trade_history[-1]['amount_sol'] if self.trade_history else 0
        pnl_sol = sol_received - original_sol_invested
        pnl_pct = (pnl_sol / original_sol_invested * 100) if original_sol_invested > 0 else 0
        
        # Update balances
        self.current_sol += sol_received
        self.current_memecoin = None
        self.current_memecoin_amount = 0.0
        self.current_memecoin_price = 0.0
        
        # Record trade
        trade = {
            'timestamp': datetime.now(),
            'action': 'SELL',
            'memecoin': memecoin,
            'price': price,
            'amount_sol': sol_received,
            'amount_memecoin': self.current_memecoin_amount,
            'pnl_sol': pnl_sol,
            'pnl_pct': pnl_pct,
            'balance_sol': self.current_sol,
            'balance_memecoin': 0
        }
        self.trade_history.append(trade)
        
        # Update performance metrics
        self.performance_metrics['total_trades'] += 1
        if pnl_sol > 0:
            self.performance_metrics['winning_trades'] += 1
        else:
            self.performance_metrics['losing_trades'] += 1
        
        self.performance_metrics['total_pnl_sol'] += pnl_sol
        self.performance_metrics['current_equity'] = self.get_current_equity()
        
        if self.performance_metrics['current_equity'] > self.performance_metrics['peak_equity']:
            self.performance_metrics['peak_equity'] = self.performance_metrics['current_equity']
        
        # Calculate drawdown
        drawdown = (self.performance_metrics['peak_equity'] - self.performance_metrics['current_equity']) / self.performance_metrics['peak_equity']
        if drawdown > self.performance_metrics['max_drawdown']:
            self.performance_metrics['max_drawdown'] = drawdown
        
        self.logger.info(f"📉 PAPER SELL: {self.current_memecoin_amount:.2f} {memecoin} → {sol_received:.4f} SOL @ ${price:.8f}")
        self.logger.info(f"💰 P&L: {pnl_pct:+.2f}% ({pnl_sol:+.4f} SOL)")
        
        return True
    
    def generate_realistic_memecoin_pattern(self, pattern_type: str) -> List[float]:
        """Generate realistic memecoin price patterns."""
        base_price = 0.001
        
        if pattern_type == "pump_dip_recovery":
            # Pattern: Initial pump, dip, recovery (good for dip buying)
            return [
                base_price,
                base_price * 1.1,   # +10%
                base_price * 1.3,   # +30%
                base_price * 1.6,   # +60%
                base_price * 2.0,   # +100%
                base_price * 2.5,   # +150%
                base_price * 2.8,   # +180% (ATH)
                base_price * 2.5,   # -10% from ATH
                base_price * 2.0,   # -28% from ATH
                base_price * 1.8,   # -35% from ATH (DIP BUY OPPORTUNITY)
                base_price * 1.5,   # -46% from ATH
                base_price * 1.2,   # -57% from ATH
                base_price * 1.0,   # -64% from ATH
                base_price * 1.1,   # Recovery starts
                base_price * 1.3,   # +30%
                base_price * 1.6,   # +60%
                base_price * 2.0,   # +100%
                base_price * 2.2,   # +120%
            ]
        
        elif pattern_type == "rapid_pump_avoid":
            # Pattern: Rapid pump to peak (avoid buying)
            return [
                base_price,
                base_price * 1.2,   # +20%
                base_price * 1.5,   # +50%
                base_price * 2.0,   # +100%
                base_price * 2.8,   # +180%
                base_price * 3.5,   # +250%
                base_price * 4.0,   # +300%
                base_price * 4.5,   # +350%
                base_price * 5.0,   # +400% (PEAK - AVOID)
                base_price * 4.8,   # -4% from peak
                base_price * 4.5,   # -10% from peak
                base_price * 4.0,   # -20% from peak
                base_price * 3.5,   # -30% from peak
                base_price * 3.0,   # -40% from peak
                base_price * 2.5,   # -50% from peak
                base_price * 2.0,   # -60% from peak
                base_price * 1.8,   # -64% from peak
                base_price * 1.5,   # -70% from peak
            ]
        
        elif pattern_type == "support_bounce":
            # Pattern: Support bounce (good entry)
            return [
                base_price,
                base_price * 1.2,   # +20%
                base_price * 1.5,   # +50%
                base_price * 1.8,   # +80%
                base_price * 1.5,   # -16% (pullback)
                base_price * 1.2,   # -33% (pullback)
                base_price * 1.0,   # -44% (pullback)
                base_price * 0.9,   # -50% (pullback)
                base_price * 0.8,   # -55% (SUPPORT LEVEL)
                base_price * 0.9,   # Bounce starts
                base_price * 1.0,   # +25% from support
                base_price * 1.2,   # +50% from support
                base_price * 1.5,   # +87% from support
                base_price * 1.8,   # +125% from support
                base_price * 2.0,   # +150% from support
                base_price * 2.2,   # +175% from support
                base_price * 2.5,   # +212% from support
                base_price * 2.8,   # +250% from support
            ]
        
        else:  # random_walk
            # Random walk pattern
            prices = [base_price]
            for i in range(17):
                change = random.uniform(-0.1, 0.15)  # -10% to +15% change
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, base_price * 0.5))  # Floor at 50% of base
            return prices
    
    async def test_pattern(self, pattern_name: str, pattern_type: str, duration_minutes: int = 5):
        """Test the strategy with a specific pattern."""
        self.logger.info(f"🔥 Testing pattern: {pattern_name}")
        self.logger.info(f"⏱️  Duration: {duration_minutes} minutes")
        self.logger.info(f"💰 Initial SOL: {self.initial_sol}")
        
        # Reset for new test
        self.current_sol = self.initial_sol
        self.current_memecoin = None
        self.current_memecoin_amount = 0.0
        self.current_memecoin_price = 0.0
        self.trade_history = []
        self.price_history = []
        
        # Setup strategy
        self.setup_strategy()
        
        # Generate price pattern
        prices = self.generate_realistic_memecoin_pattern(pattern_type)
        
        self.logger.info("📊 Starting pattern simulation...")
        
        # Simulate price updates
        for i, price in enumerate(prices):
            try:
                # Add some randomness to make it more realistic
                price_variation = random.uniform(0.98, 1.02)  # ±2% variation
                current_price = price * price_variation
                
                # Record price
                self.price_history.append({
                    'timestamp': datetime.now(),
                    'price': current_price,
                    'step': i
                })
                
                # Process price update with strategy
                result = await self.strategy_engine.process_price_update("TESTMEME", current_price, 1000)
                
                # Get micro-analysis details
                strategy = self.strategy_engine.strategy
                if len(strategy.price_history) >= strategy.min_data_points:
                    analysis = strategy._perform_micro_analysis(current_price)
                    analysis_summary = analysis['analysis_summary']
                else:
                    analysis_summary = "insufficient_data"
                
                # Execute trades based on strategy decision
                if result['action'] == 'enter' and not self.current_memecoin:
                    # Execute buy
                    amount_sol = min(0.1, self.current_sol * 0.1)  # Use 10% of SOL or 0.1 SOL max
                    if self.execute_buy("TESTMEME", current_price, amount_sol):
                        self.logger.info(f"🎯 Strategy triggered BUY at ${current_price:.8f}")
                
                elif result['action'] == 'exit' and self.current_memecoin:
                    # Execute sell
                    if self.execute_sell("TESTMEME", current_price):
                        self.logger.info(f"🎯 Strategy triggered SELL at ${current_price:.8f}")
                
                # Log current status
                equity = self.get_current_equity()
                self.logger.info(f"📊 Step {i+1}: ${current_price:.8f} | Action: {result['action']} | Analysis: {analysis_summary} | Equity: {equity:.4f} SOL")
                
                # Wait between updates (simulate real-time)
                await asyncio.sleep(1)  # 1 second between updates
                
            except Exception as e:
                self.logger.error(f"Error in pattern simulation: {e}")
                await asyncio.sleep(0.5)
        
        # Final summary
        self.logger.info("🏁 Pattern test completed!")
        self.print_performance_summary(pattern_name)
        
        return {
            'pattern_name': pattern_name,
            'pattern_type': pattern_type,
            'price_history': self.price_history,
            'trade_history': self.trade_history,
            'performance_metrics': self.performance_metrics.copy()
        }
    
    def print_performance_summary(self, pattern_name: str):
        """Print detailed performance summary."""
        print("\n" + "="*60)
        print(f"📊 PHANTOM PAPER TRADING RESULTS - {pattern_name}")
        print("="*60)
        
        # Basic metrics
        total_return = (self.performance_metrics['current_equity'] - self.initial_sol) / self.initial_sol * 100
        win_rate = (self.performance_metrics['winning_trades'] / self.performance_metrics['total_trades'] * 100) if self.performance_metrics['total_trades'] > 0 else 0
        
        print(f"💰 Initial SOL: {self.initial_sol:.4f}")
        print(f"💰 Final SOL: {self.performance_metrics['current_equity']:.4f}")
        print(f"📈 Total Return: {total_return:+.2f}%")
        print(f"📊 Total Trades: {self.performance_metrics['total_trades']}")
        print(f"✅ Winning Trades: {self.performance_metrics['winning_trades']}")
        print(f"❌ Losing Trades: {self.performance_metrics['losing_trades']}")
        print(f"🎯 Win Rate: {win_rate:.1f}%")
        print(f"📉 Max Drawdown: {self.performance_metrics['max_drawdown']:.2%}")
        
        # Trade details
        if self.trade_history:
            print(f"\n📋 TRADE HISTORY:")
            for i, trade in enumerate(self.trade_history, 1):
                timestamp = trade['timestamp'].strftime('%H:%M:%S')
                if trade['action'] == 'BUY':
                    print(f"  {i}. {timestamp} | BUY {trade['memecoin']} @ ${trade['price']:.8f} | {trade['amount_sol']:.4f} SOL")
                else:
                    pnl = trade.get('pnl_pct', 0)
                    print(f"  {i}. {timestamp} | SELL {trade['memecoin']} @ ${trade['price']:.8f} | P&L: {pnl:+.2f}%")
        
        print("="*60)


async def main():
    """Main function to run paper trading tests."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🔥 Phantom Micro-Analysis Paper Trading Test")
    print("="*60)
    
    # Test patterns
    test_patterns = [
        ("Pump-Dip-Recovery", "pump_dip_recovery"),
        ("Rapid Pump (Avoid)", "rapid_pump_avoid"),
        ("Support Bounce", "support_bounce"),
        ("Random Walk", "random_walk")
    ]
    
    all_results = []
    
    for pattern_name, pattern_type in test_patterns:
        print(f"\n🎯 Testing: {pattern_name}")
        print("-" * 40)
        
        # Create paper trader
        trader = SimplePhantomPaperTrader(initial_sol=1.0)
        
        # Run test
        try:
            results = await trader.test_pattern(pattern_name, pattern_type, duration_minutes=2)
            all_results.append(results)
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            trader.print_performance_summary(pattern_name)
    
    # Overall summary
    print("\n" + "="*80)
    print("📊 OVERALL PERFORMANCE SUMMARY")
    print("="*80)
    
    total_trades = sum(r['performance_metrics']['total_trades'] for r in all_results)
    total_wins = sum(r['performance_metrics']['winning_trades'] for r in all_results)
    total_pnl = sum(r['performance_metrics']['total_pnl_sol'] for r in all_results)
    
    print(f"📊 Total Trades Across All Patterns: {total_trades}")
    print(f"✅ Total Winning Trades: {total_wins}")
    print(f"💰 Total P&L: {total_pnl:+.4f} SOL")
    print(f"🎯 Overall Win Rate: {(total_wins/total_trades*100) if total_trades > 0 else 0:.1f}%")
    
    # Pattern-by-pattern breakdown
    print(f"\n📋 PATTERN BREAKDOWN:")
    for result in all_results:
        metrics = result['performance_metrics']
        return_pct = (metrics['current_equity'] - 1.0) / 1.0 * 100
        win_rate = (metrics['winning_trades'] / metrics['total_trades'] * 100) if metrics['total_trades'] > 0 else 0
        print(f"  {result['pattern_name']}: {metrics['total_trades']} trades, {win_rate:.0f}% win rate, {return_pct:+.1f}% return")
    
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
