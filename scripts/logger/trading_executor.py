#!/usr/bin/env python3
"""
Trading Executor - Automated Trade Execution with Risk Management

This module provides automated trading capabilities integrated with the
price logger system. It supports limit orders, stop-loss, take-profit,
and various trading strategies.

Features:
- Limit order execution (not market orders)
- Stop-loss and take-profit management
- Position tracking
- Risk management (position sizing, max loss)
- Multiple order types (OCO, trailing stop)
- Paper trading mode
- Comprehensive logging

"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import time

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from binance.enums import *

# Import email notifier for trade notifications
try:
    from email_notifier import EmailNotifier
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False


class OrderSide(Enum):
    """Order side enum."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order type enum."""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"
    TAKE_PROFIT_LIMIT = "TAKE_PROFIT_LIMIT"
    OCO = "OCO"


class PositionSide(Enum):
    """Position side."""
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


class TradingExecutor:
    """
    Main trading execution engine.
    
    Handles order placement, position tracking, and risk management.
    """
    
    def __init__(self, config: Dict[str, Any], paper_trading: bool = True, email_notifier=None, email_recipient: str = None):
        """
        Initialize trading executor.
        
        Args:
            config: Trading configuration dictionary
            paper_trading: If True, simulates trades without real execution
            email_notifier: EmailNotifier instance for trade notifications
            email_recipient: Email address to send trade notifications
        """
        self.config = config
        self.paper_trading = paper_trading
        self.email_recipient = email_recipient
        
        # Initialize Binance client
        self.client = self._init_binance_client()
        
        # Initialize email notifier
        self.email_notifier = email_notifier
        if self.email_notifier is None and EMAIL_AVAILABLE and not paper_trading:
            try:
                self.email_notifier = EmailNotifier()
            except Exception as e:
                print(f"[WARNING] Failed to initialize email notifier: {e}")
        
        # Position tracking
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.open_orders: Dict[str, Dict[str, Any]] = {}
        
        # Risk management
        self.max_position_size_usd = config.get('risk', {}).get('max_position_size_usd', 200.0)
        self.max_loss_per_trade_pct = config.get('risk', {}).get('max_loss_per_trade_pct', 2.0)
        self.max_open_positions = config.get('risk', {}).get('max_open_positions', 5)
        
        # Statistics
        self.stats = {
            'trades_executed': 0,
            'orders_placed': 0,
            'orders_filled': 0,
            'orders_cancelled': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
        }
        
        # Paths
        self.script_dir = Path(__file__).parent
        self.positions_file = self.script_dir / "trading_positions.json"
        self.trades_log = self.script_dir / "markdown_logs" / "trades.md"
        
        # Load existing positions
        self._load_positions()
    
    def _init_binance_client(self) -> Optional[Client]:
        """Initialize Binance API client."""
        if self.paper_trading:
            print("[TRADING] Paper trading mode - no real orders will be placed")
            return None
        
        # Load environment variables
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / '.env'
        
        if not env_file.exists():
            raise ValueError(f".env file not found at {env_file}")
        
        load_dotenv(env_file)
        
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_SECRET')
        
        if not api_key or not api_secret:
            raise ValueError("BINANCE_API_KEY and BINANCE_SECRET must be set in .env file")
        
        try:
            client = Client(api_key, api_secret)
            
            # Test connection
            client.get_account()
            
            print("[TRADING] Connected to Binance API")
            return client
        except Exception as e:
            raise ValueError(f"Failed to initialize Binance client: {e}")
    
    def _load_positions(self):
        """Load existing positions from file."""
        if not self.positions_file.exists():
            return
        
        try:
            import json
            with open(self.positions_file, 'r') as f:
                self.positions = json.load(f)
            
            print(f"[TRADING] Loaded {len(self.positions)} existing positions")
        except Exception as e:
            print(f"[WARNING] Failed to load positions: {e}")
    
    def _save_positions(self):
        """Save positions to file."""
        try:
            import json
            with open(self.positions_file, 'w') as f:
                json.dump(self.positions, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save positions: {e}")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'ASTERUSDT')
            
        Returns:
            Current price or None
        """
        if self.paper_trading:
            # In paper trading, we'd use the logger's price data
            # For now, return a mock price
            return None
        
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            print(f"[ERROR] Failed to get price for {symbol}: {e}")
            return None
    
    def get_account_balance(self, asset: str) -> float:
        """
        Get account balance for an asset.
        
        Args:
            asset: Asset symbol (e.g., 'USDT', 'BTC')
            
        Returns:
            Available balance
        """
        if self.paper_trading:
            # Return paper trading balance
            paper_balances = self.config.get('paper_trading', {}).get('balances', {})
            return paper_balances.get(asset, 0.0)
        
        try:
            balance = self.client.get_asset_balance(asset=asset)
            return float(balance['free'])
        except Exception as e:
            print(f"[ERROR] Failed to get balance for {asset}: {e}")
            return 0.0
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss_price: float,
        risk_amount_usd: Optional[float] = None
    ) -> float:
        """
        Calculate position size based on risk management rules.
        
        Args:
            symbol: Trading pair
            entry_price: Intended entry price
            stop_loss_price: Stop loss price
            risk_amount_usd: Max USD to risk (optional)
            
        Returns:
            Position size in base currency units
        """
        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_loss_price)
        
        if risk_per_unit == 0:
            print("[WARNING] Stop loss equals entry price")
            return 0.0
        
        # Determine risk amount
        if risk_amount_usd is None:
            # Use percentage of balance
            quote_asset = symbol.replace(symbol[:len(symbol)-4], '')  # Get quote (e.g., USDT)
            balance = self.get_account_balance(quote_asset)
            risk_amount_usd = balance * (self.max_loss_per_trade_pct / 100.0)
        
        # Calculate position size
        position_size = risk_amount_usd / risk_per_unit
        
        # Check against max position size
        position_value = position_size * entry_price
        if position_value > self.max_position_size_usd:
            position_size = self.max_position_size_usd / entry_price
        
        return position_size
    
    def place_limit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        time_in_force: str = TIME_IN_FORCE_GTC
    ) -> Optional[Dict[str, Any]]:
        """
        Place a limit order with optional stop-loss and take-profit.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            side: OrderSide.BUY or OrderSide.SELL
            quantity: Order quantity
            price: Limit price
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            time_in_force: Time in force (GTC, IOC, FOK)
            
        Returns:
            Order result dictionary
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Validate quantity and price
        if quantity <= 0 or price <= 0:
            print(f"[ERROR] Invalid quantity ({quantity}) or price ({price})")
            return None
        
        # Check if we can open more positions
        if len(self.positions) >= self.max_open_positions:
            print(f"[WARNING] Max open positions ({self.max_open_positions}) reached")
            return None
        
        if self.paper_trading:
            # Paper trading simulation
            order_id = f"paper_{int(time.time())}_{symbol}"
            
            order_result = {
                'symbol': symbol,
                'orderId': order_id,
                'side': side.value,
                'type': 'LIMIT',
                'quantity': quantity,
                'price': price,
                'status': 'FILLED',  # Simulate immediate fill for testing
                'timestamp': timestamp,
                'paper_trading': True
            }
            
            print(f"[PAPER TRADE] {side.value} {quantity} {symbol} @ {price}")
            
            # Create position
            self._create_position(
                symbol=symbol,
                side=side,
                entry_price=price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                order_id=order_id
            )
            
            return order_result
        
        try:
            # Place real limit order
            order = self.client.create_order(
                symbol=symbol,
                side=side.value,
                type=ORDER_TYPE_LIMIT,
                timeInForce=time_in_force,
                quantity=quantity,
                price=str(price)
            )
            
            print(f"[ORDER PLACED] {side.value} {quantity} {symbol} @ {price} (Order ID: {order['orderId']})")
            
            self.stats['orders_placed'] += 1
            
            # If stop-loss and take-profit are provided, place OCO order after fill
            # For now, we'll track the order and handle SL/TP separately
            
            self.open_orders[order['orderId']] = {
                'order': order,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'symbol': symbol,
                'side': side,
                'entry_price': price,
                'quantity': quantity
            }
            
            return order
            
        except BinanceAPIException as e:
            print(f"[ERROR] Binance API error placing order: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Failed to place order: {e}")
            return None
    
    def _create_position(
        self,
        symbol: str,
        side: OrderSide,
        entry_price: float,
        quantity: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        order_id: str
    ):
        """Create a new position entry."""
        position_id = f"{symbol}_{int(time.time())}"
        
        self.positions[position_id] = {
            'symbol': symbol,
            'side': side.value,
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'entry_order_id': order_id,
            'entry_time': datetime.now().isoformat(),
            'status': 'OPEN',
            'pnl': 0.0
        }
        
        self._save_positions()
        self._log_trade('ENTRY', symbol, side.value, entry_price, quantity, stop_loss, take_profit)
        
        # Send email notification for position opened
        self._send_trade_email('ENTRY', symbol, side.value, entry_price, quantity, stop_loss, take_profit)
    
    def place_stop_loss_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        stop_price: float,
        limit_price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Place a stop-loss order.
        
        Args:
            symbol: Trading pair
            side: OrderSide (opposite of entry)
            quantity: Order quantity
            stop_price: Stop trigger price
            limit_price: Limit price (if None, uses stop_price)
            
        Returns:
            Order result
        """
        if limit_price is None:
            limit_price = stop_price * 0.999 if side == OrderSide.SELL else stop_price * 1.001
        
        if self.paper_trading:
            print(f"[PAPER TRADE] Stop-loss: {side.value} {quantity} {symbol} @ stop={stop_price}")
            return {'orderId': f"paper_sl_{int(time.time())}", 'status': 'NEW'}
        
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side.value,
                type=ORDER_TYPE_STOP_LOSS_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=str(limit_price),
                stopPrice=str(stop_price)
            )
            
            print(f"[STOP-LOSS PLACED] {side.value} {quantity} {symbol} @ stop={stop_price}")
            return order
            
        except Exception as e:
            print(f"[ERROR] Failed to place stop-loss: {e}")
            return None
    
    def update_trailing_stop(self, position_id: str, current_price: float):
        """
        Update trailing stop-loss for a position.
        
        Args:
            position_id: Position identifier
            current_price: Current market price
        """
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        
        if position['status'] != 'OPEN':
            return
        
        # Get trailing stop configuration
        trailing_config = self.config.get('trading', {}).get('trailing_stop', {})
        if not trailing_config.get('enabled', False):
            return
        
        trail_percent = trailing_config.get('trail_percent', 2.0)
        
        # Calculate new stop-loss
        if position['side'] == 'BUY':
            # Long position - trail up
            new_stop = current_price * (1 - trail_percent / 100.0)
            
            if position['stop_loss'] is None or new_stop > position['stop_loss']:
                old_stop = position['stop_loss']
                position['stop_loss'] = new_stop
                self._save_positions()
                print(f"[TRAILING STOP] {position['symbol']}: {old_stop} → {new_stop:.8f}")
        else:
            # Short position - trail down
            new_stop = current_price * (1 + trail_percent / 100.0)
            
            if position['stop_loss'] is None or new_stop < position['stop_loss']:
                old_stop = position['stop_loss']
                position['stop_loss'] = new_stop
                self._save_positions()
                print(f"[TRAILING STOP] {position['symbol']}: {old_stop} → {new_stop:.8f}")
    
    def check_position_exits(self, symbol: str, current_price: float):
        """
        Check if any positions should be closed (stop-loss or take-profit hit).
        
        Args:
            symbol: Trading pair
            current_price: Current market price
        """
        for position_id, position in list(self.positions.items()):
            if position['symbol'] != symbol or position['status'] != 'OPEN':
                continue
            
            should_close = False
            close_reason = None
            
            # Check stop-loss
            if position['stop_loss'] is not None:
                if position['side'] == 'BUY' and current_price <= position['stop_loss']:
                    should_close = True
                    close_reason = 'STOP_LOSS'
                elif position['side'] == 'SELL' and current_price >= position['stop_loss']:
                    should_close = True
                    close_reason = 'STOP_LOSS'
            
            # Check take-profit
            if position['take_profit'] is not None:
                if position['side'] == 'BUY' and current_price >= position['take_profit']:
                    should_close = True
                    close_reason = 'TAKE_PROFIT'
                elif position['side'] == 'SELL' and current_price <= position['take_profit']:
                    should_close = True
                    close_reason = 'TAKE_PROFIT'
            
            if should_close:
                self.close_position(position_id, current_price, close_reason)
    
    def close_position(
        self,
        position_id: str,
        close_price: float,
        reason: str = 'MANUAL'
    ) -> bool:
        """
        Close an open position.
        
        Args:
            position_id: Position identifier
            close_price: Closing price
            reason: Reason for closing (MANUAL, STOP_LOSS, TAKE_PROFIT)
            
        Returns:
            True if successfully closed
        """
        if position_id not in self.positions:
            print(f"[ERROR] Position {position_id} not found")
            return False
        
        position = self.positions[position_id]
        
        if position['status'] != 'OPEN':
            print(f"[WARNING] Position {position_id} is not open")
            return False
        
        # Calculate PnL
        entry_price = position['entry_price']
        quantity = position['quantity']
        
        if position['side'] == 'BUY':
            pnl = (close_price - entry_price) * quantity
        else:
            pnl = (entry_price - close_price) * quantity
        
        # Update position
        position['status'] = 'CLOSED'
        position['close_price'] = close_price
        position['close_time'] = datetime.now().isoformat()
        position['close_reason'] = reason
        position['pnl'] = pnl
        
        self._save_positions()
        
        # Close order logic
        if not self.paper_trading:
            # Place opposite side order to close
            close_side = OrderSide.SELL if position['side'] == 'BUY' else OrderSide.BUY
            
            try:
                order = self.client.create_order(
                    symbol=position['symbol'],
                    side=close_side.value,
                    type=ORDER_TYPE_MARKET,
                    quantity=quantity
                )
                
                print(f"[POSITION CLOSED] {position['symbol']} at {close_price} - Reason: {reason} - PnL: ${pnl:.2f}")
                
            except Exception as e:
                print(f"[ERROR] Failed to close position: {e}")
                return False
        else:
            print(f"[PAPER TRADE CLOSED] {position['symbol']} at {close_price} - Reason: {reason} - PnL: ${pnl:.2f}")
        
        # Update stats
        self.stats['trades_executed'] += 1
        self.stats['total_pnl'] += pnl
        
        # Log the trade
        self._log_trade('EXIT', position['symbol'], position['side'], close_price, quantity, None, None, pnl, reason)
        
        # Send email notification for position closed
        self._send_trade_email('EXIT', position['symbol'], position['side'], close_price, quantity, None, None, pnl, reason)
        
        return True
    
    def _log_trade(
        self,
        action: str,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        pnl: Optional[float] = None,
        reason: Optional[str] = None
    ):
        """Log trade to markdown file."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            with open(self.trades_log, 'a') as f:
                f.write(f"\n### {timestamp} - {action}\n")
                f.write(f"- **Symbol**: {symbol}\n")
                f.write(f"- **Side**: {side}\n")
                f.write(f"- **Price**: ${price:.8f}\n")
                f.write(f"- **Quantity**: {quantity}\n")
                
                if stop_loss:
                    f.write(f"- **Stop Loss**: ${stop_loss:.8f}\n")
                if take_profit:
                    f.write(f"- **Take Profit**: ${take_profit:.8f}\n")
                if pnl is not None:
                    emoji = "📈" if pnl > 0 else "📉"
                    f.write(f"- **PnL**: {emoji} ${pnl:.2f}\n")
                if reason:
                    f.write(f"- **Reason**: {reason}\n")
        except Exception as e:
            print(f"[ERROR] Failed to log trade: {e}")
    
    def _send_trade_email(
        self,
        action: str,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        pnl: Optional[float] = None,
        reason: Optional[str] = None
    ):
        """Send email notification for trade execution."""
        if not self.email_notifier or not self.email_recipient:
            return
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Create email subject and body based on action
            if action == 'ENTRY':
                subject = f"🚀 Trade Opened: {side} {symbol}"
                
                # Create HTML body
                html_body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px 10px 0 0;">
                        <h2 style="color: white; margin: 0;">🚀 Position Opened</h2>
                    </div>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 10px 10px;">
                        <h3 style="color: #333; margin-top: 0;">Trade Details</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr><td style="padding: 8px 0; color: #666;"><strong>Symbol:</strong></td><td style="padding: 8px 0;">{symbol}</td></tr>
                            <tr><td style="padding: 8px 0; color: #666;"><strong>Action:</strong></td><td style="padding: 8px 0; color: #28a745;"><strong>{side}</strong></td></tr>
                            <tr><td style="padding: 8px 0; color: #666;"><strong>Entry Price:</strong></td><td style="padding: 8px 0;">${price:.8f}</td></tr>
                            <tr><td style="padding: 8px 0; color: #666;"><strong>Quantity:</strong></td><td style="padding: 8px 0;">{quantity:.6f}</td></tr>
                            <tr><td style="padding: 8px 0; color: #666;"><strong>Position Value:</strong></td><td style="padding: 8px 0;">${price * quantity:.2f}</td></tr>
                """
                
                if stop_loss:
                    html_body += f'<tr><td style="padding: 8px 0; color: #666;"><strong>Stop Loss:</strong></td><td style="padding: 8px 0; color: #dc3545;">${stop_loss:.8f}</td></tr>'
                
                if take_profit:
                    html_body += f'<tr><td style="padding: 8px 0; color: #666;"><strong>Take Profit:</strong></td><td style="padding: 8px 0; color: #28a745;">${take_profit:.8f}</td></tr>'
                
                html_body += f"""
                        </table>
                        <p style="color: #666; margin-top: 20px; font-size: 14px;">
                            <strong>Timestamp:</strong> {timestamp}
                        </p>
                        <div style="margin-top: 20px; padding: 15px; background: #fff; border-left: 4px solid #28a745; border-radius: 4px;">
                            <p style="margin: 0; color: #666;">✅ Position is being monitored for stop-loss and take-profit levels.</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                # Plain text version
                text_body = f"""
                Position Opened
                
                Trade Details:
                Symbol: {symbol}
                Action: {side}
                Entry Price: ${price:.8f}
                Quantity: {quantity:.6f}
                Position Value: ${price * quantity:.2f}
                """
                
                if stop_loss:
                    text_body += f"\nStop Loss: ${stop_loss:.8f}"
                if take_profit:
                    text_body += f"\nTake Profit: ${take_profit:.8f}"
                
                text_body += f"\n\nTimestamp: {timestamp}\n\nPosition is being monitored for stop-loss and take-profit levels."
                
            else:  # EXIT
                # Determine if profit or loss
                is_profit = pnl and pnl > 0
                emoji = "📈" if is_profit else "📉"
                color = "#28a745" if is_profit else "#dc3545"
                
                subject = f"{emoji} Trade Closed: {symbol} - PnL: ${pnl:.2f}" if pnl is not None else f"Trade Closed: {symbol}"
                
                # Create HTML body
                html_body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: linear-gradient(135deg, {'#28a745' if is_profit else '#dc3545'} 0%, {'#20c997' if is_profit else '#bd2130'} 100%); padding: 20px; border-radius: 10px 10px 0 0;">
                        <h2 style="color: white; margin: 0;">{emoji} Position Closed</h2>
                    </div>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 10px 10px;">
                        <h3 style="color: #333; margin-top: 0;">Trade Results</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr><td style="padding: 8px 0; color: #666;"><strong>Symbol:</strong></td><td style="padding: 8px 0;">{symbol}</td></tr>
                            <tr><td style="padding: 8px 0; color: #666;"><strong>Side:</strong></td><td style="padding: 8px 0;">{side}</td></tr>
                            <tr><td style="padding: 8px 0; color: #666;"><strong>Exit Price:</strong></td><td style="padding: 8px 0;">${price:.8f}</td></tr>
                            <tr><td style="padding: 8px 0; color: #666;"><strong>Quantity:</strong></td><td style="padding: 8px 0;">{quantity:.6f}</td></tr>
                """
                
                if pnl is not None:
                    html_body += f'<tr><td style="padding: 8px 0; color: #666;"><strong>P&L:</strong></td><td style="padding: 8px 0; color: {color}; font-size: 18px;"><strong>${pnl:.2f}</strong></td></tr>'
                
                if reason:
                    html_body += f'<tr><td style="padding: 8px 0; color: #666;"><strong>Exit Reason:</strong></td><td style="padding: 8px 0;">{reason}</td></tr>'
                
                html_body += f"""
                        </table>
                        <p style="color: #666; margin-top: 20px; font-size: 14px;">
                            <strong>Timestamp:</strong> {timestamp}
                        </p>
                        <div style="margin-top: 20px; padding: 15px; background: #fff; border-left: 4px solid {color}; border-radius: 4px;">
                            <p style="margin: 0; color: #666;">{'🎉 Congratulations on the profit!' if is_profit else '📊 Trade closed. Review your strategy and risk management.'}</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                # Plain text version
                text_body = f"""
                Position Closed
                
                Trade Results:
                Symbol: {symbol}
                Side: {side}
                Exit Price: ${price:.8f}
                Quantity: {quantity:.6f}
                """
                
                if pnl is not None:
                    text_body += f"\nP&L: ${pnl:.2f}"
                if reason:
                    text_body += f"\nExit Reason: {reason}"
                
                text_body += f"\n\nTimestamp: {timestamp}"
            
            # Send the email
            self.email_notifier.send_email(
                to_email=self.email_recipient,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
            print(f"[EMAIL] Trade notification sent to {self.email_recipient}")
            
        except Exception as e:
            print(f"[WARNING] Failed to send trade email: {e}")
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get list of all open positions."""
        return [p for p in self.positions.values() if p['status'] == 'OPEN']
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of all positions."""
        open_positions = self.get_open_positions()
        
        total_exposure = sum(p['entry_price'] * p['quantity'] for p in open_positions)
        total_pnl = self.stats['total_pnl']
        
        return {
            'open_positions': len(open_positions),
            'total_exposure_usd': total_exposure,
            'total_pnl': total_pnl,
            'trades_executed': self.stats['trades_executed'],
            'positions': open_positions
        }
