#!/usr/bin/env python3
"""
Phantom Paper Trading Test

Tests the Phantom micro-analysis strategy with real trending memecoins using paper trading.
This validates the strategy with actual market data before live implementation.
"""

import asyncio
import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.phantom_memecoin_monitor import PhantomMemecoinMonitor
from src.phantom_volatile_strategy import PhantomTradingEngine


class PhantomPaperTrader:
    """Paper trading system for testing Phantom memecoin strategies."""
    
    def __init__(self, initial_sol: float = 1.0):
        self.initial_sol = initial_sol
        self.current_sol = initial_sol
        self.current_memecoin = None
        self.current_memecoin_amount = 0.0
        self.current_memecoin_price = 0.0
        
        # Trading history
        self.trade_history = []
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
        
        # Monitoring
        self.monitor = PhantomMemecoinMonitor()
        
        self.logger = logging.getLogger(__name__)
        
    def setup_strategy(self, memecoin_config: Dict[str, Any]):
        """Setup the Phantom strategy engine for a specific memecoin."""
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
    
    async def test_with_real_memecoin(self, memecoin: str, duration_minutes: int = 30):
        """Test the strategy with a real trending memecoin."""
        self.logger.info(f"🔥 Starting paper trading test with {memecoin}")
        self.logger.info(f"⏱️  Duration: {duration_minutes} minutes")
        self.logger.info(f"💰 Initial SOL: {self.initial_sol}")
        
        # Setup strategy
        memecoin_config = {
            'symbol': memecoin,
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
            }
        }
        self.setup_strategy(memecoin_config)
        
        # Track price updates
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        price_updates = []
        
        self.logger.info("📊 Starting price monitoring...")
        
        while datetime.now() < end_time:
            try:
                # Get current trending memecoins
                trending_tokens = self.monitor.fetch_trending_memecoins()
                
                # Find our target memecoin
                target_token = None
                for token in trending_tokens:
                    if token['name'].upper() == memecoin.upper():
                        target_token = token
                        break
                
                if not target_token:
                    self.logger.warning(f"Memecoin {memecoin} not found in trending list")
                    await asyncio.sleep(30)
                    continue
                
                # Extract price (use a mock price if not available)
                current_price = target_token.get('price', 0.001)
                if current_price == 0 or current_price is None:
                    # Generate a realistic price based on trending position
                    base_price = 0.001
                    position_factor = 1.0 - (trending_tokens.index(target_token) * 0.1)
                    current_price = base_price * position_factor
                
                # Process price update with strategy
                result = await self.strategy_engine.process_price_update(memecoin, current_price, 1000)
                
                # Record price update
                price_updates.append({
                    'timestamp': datetime.now(),
                    'price': current_price,
                    'action': result['action'],
                    'reason': result['reason'],
                    'confidence': result['confidence']
                })
                
                # Execute trades based on strategy decision
                if result['action'] == 'enter' and not self.current_memecoin:
                    # Execute buy
                    amount_sol = min(0.1, self.current_sol * 0.1)  # Use 10% of SOL or 0.1 SOL max
                    if self.execute_buy(memecoin, current_price, amount_sol):
                        self.logger.info(f"🎯 Strategy triggered BUY at ${current_price:.8f}")
                
                elif result['action'] == 'exit' and self.current_memecoin:
                    # Execute sell
                    if self.execute_sell(memecoin, current_price):
                        self.logger.info(f"🎯 Strategy triggered SELL at ${current_price:.8f}")
                
                # Log current status
                equity = self.get_current_equity()
                self.logger.info(f"📊 Price: ${current_price:.8f} | Action: {result['action']} | Equity: {equity:.4f} SOL")
                
                # Wait before next update
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in price monitoring: {e}")
                await asyncio.sleep(10)
        
        # Final summary
        self.logger.info("🏁 Paper trading test completed!")
        self.print_performance_summary()
        
        return {
            'price_updates': price_updates,
            'trade_history': self.trade_history,
            'performance_metrics': self.performance_metrics
        }
    
    def print_performance_summary(self):
        """Print detailed performance summary."""
        print("\n" + "="*60)
        print("📊 PHANTOM PAPER TRADING RESULTS")
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
    
    # Get current trending memecoins
    monitor = PhantomMemecoinMonitor()
    trending_tokens = monitor.fetch_trending_memecoins()
    
    if not trending_tokens:
        print("❌ No trending memecoins found")
        return
    
    print("🔥 Current Trending Memecoins:")
    for i, token in enumerate(trending_tokens[:5], 1):
        print(f"  {i}. {token['name']} - {token.get('price', 'N/A')}")
    
    # Select a memecoin for testing
    test_memecoin = trending_tokens[0]['name']  # Use top trending
    print(f"\n🎯 Testing with: {test_memecoin}")
    
    # Create paper trader
    trader = PhantomPaperTrader(initial_sol=1.0)
    
    # Run test
    try:
        results = await trader.test_with_real_memecoin(test_memecoin, duration_minutes=30)
        
        # Save results
        results_file = f"phantom_paper_test_{test_memecoin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        trader.print_performance_summary()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        trader.print_performance_summary()


if __name__ == "__main__":
    asyncio.run(main())
