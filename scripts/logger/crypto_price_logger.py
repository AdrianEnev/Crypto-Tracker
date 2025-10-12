#!/usr/bin/env python3
"""
Crypto Price Logger - 24/7 Cryptocurrency Price Monitoring System

This script monitors cryptocurrency prices and sends email alerts via Amazon SES
when configured price targets are reached. Designed to run continuously as a
background service with minimal resource usage.

Features:
- Real-time price monitoring via CCXT
- Email alerts via Amazon SES
- Rate limiting to respect API limits
- Markdown logging for progress tracking
- Alert cooldown to prevent spam
- Graceful error handling and recovery

Usage:
    python crypto_price_logger.py [--config CONFIG_FILE] [--dry-run]
"""

import os
import sys
import time
import signal
import argparse
import yaml
import ccxt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from rate_limiter import get_global_rate_limiter, ExchangeRateLimiter
from email_notifier import EmailNotifier

# Optional trading imports
try:
    from trading_executor import TradingExecutor
    from strategy_manager import StrategyManager
    TRADING_AVAILABLE = True
except ImportError:
    TRADING_AVAILABLE = False


class CryptoPriceLogger:
    """
    Main cryptocurrency price monitoring and alerting system.
    
    Monitors configured cryptocurrencies and sends email alerts when
    price conditions are met.
    """
    
    def __init__(self, config_path: str, dry_run: bool = False):
        """
        Initialize the crypto price logger.
        
        Args:
            config_path: Path to YAML configuration file
            dry_run: If True, don't send actual emails
        """
        self.config_path = config_path
        self.dry_run = dry_run
        self.running = False
        self.config = self._load_config()
        
        # Initialize components
        self.exchange = self._init_exchange()
        self.rate_limiter = self._init_rate_limiter()
        self.email_notifier = self._init_email_notifier()
        
        # Initialize trading (optional)
        self.trading_executor = None
        self.strategy_manager = None
        self._init_trading()
        
        # Alert tracking
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.last_heartbeat = datetime.now()
        
        # Paths
        self.script_dir = Path(__file__).parent
        self.markdown_dir = self.script_dir / "markdown_logs"
        self.markdown_dir.mkdir(exist_ok=True)
        
        # Statistics
        self.stats = {
            'checks_performed': 0,
            'alerts_triggered': 0,
            'errors_encountered': 0,
            'start_time': datetime.now()
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Validate required sections
            required = ['global', 'exchange', 'alerts', 'logging']
            missing = [s for s in required if s not in config]
            if missing:
                raise ValueError(f"Missing required config sections: {missing}")
            
            return config
        except Exception as e:
            print(f"Error loading config from {self.config_path}: {e}")
            sys.exit(1)
    
    def _init_exchange(self) -> ccxt.Exchange:
        """Initialize CCXT exchange connection."""
        exchange_name = self.config['exchange']['name']
        
        try:
            exchange_class = getattr(ccxt, exchange_name)
            exchange = exchange_class({
                'enableRateLimit': self.config['exchange'].get('enable_rate_limit', True),
                'timeout': 30000,  # 30 seconds
            })
            
            # Test connection
            exchange.load_markets()
            
            return exchange
        except Exception as e:
            print(f"Error initializing {exchange_name} exchange: {e}")
            sys.exit(1)
    
    def _init_rate_limiter(self) -> ExchangeRateLimiter:
        """Initialize rate limiter."""
        exchange_name = self.config['exchange']['name']
        max_requests = self.config['exchange'].get('max_requests_per_minute', 60)
        
        custom_limits = {exchange_name: max_requests}
        return get_global_rate_limiter(custom_limits)
    
    def _init_email_notifier(self) -> Optional[EmailNotifier]:
        """Initialize email notifier."""
        if self.dry_run:
            print("DRY RUN MODE: Emails will not be sent")
            return None
        
        try:
            notifier = EmailNotifier()
            
            # Test connection
            if not notifier.test_connection():
                print("Warning: Email connection test failed. Alerts may not be sent.")
            
            return notifier
        except Exception as e:
            print(f"Error initializing email notifier: {e}")
            print("Continuing without email notifications...")
            return None
    
    def _init_trading(self):
        """Initialize trading components if enabled."""
        if not TRADING_AVAILABLE:
            return
        
        # Check if trading is enabled in config
        trading_enabled = self.config.get('trading', {}).get('enabled', False)
        
        if not trading_enabled:
            return
        
        # Load trading config
        trading_config_path = self.script_dir / "config" / "trading_config.yaml"
        
        if not trading_config_path.exists():
            print("[TRADING] trading_config.yaml not found, trading disabled")
            return
        
        try:
            import yaml
            with open(trading_config_path, 'r') as f:
                trading_config = yaml.safe_load(f)
            
            # Determine if paper trading
            paper_trading = trading_config.get('trading', {}).get('paper_trading', True)
            
            # Get email recipient from config
            email_recipient = self.config.get('global', {}).get('email_recipient')
            
            # Initialize trading executor with email notifications
            self.trading_executor = TradingExecutor(
                trading_config, 
                paper_trading=paper_trading,
                email_notifier=self.email_notifier,
                email_recipient=email_recipient
            )
            
            # Initialize strategy manager
            self.strategy_manager = StrategyManager(trading_config, self.trading_executor)
            
            mode = "PAPER TRADING" if paper_trading else "LIVE TRADING"
            print(f"[TRADING] Trading enabled - Mode: {mode}")
            print(f"[TRADING] Loaded {len(self.strategy_manager.strategies)} strategies")
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize trading: {e}")
            self.trading_executor = None
            self.strategy_manager = None
    
    def _fetch_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current price for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Current price or None if error
        """
        exchange_name = self.config['exchange']['name']
        
        # Acquire rate limit token
        self.rate_limiter.acquire(exchange_name, tokens=1, blocking=True)
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker.get('last') or ticker.get('close') or ticker.get('ask')
            
            if price is not None:
                return float(price)
            
            return None
        except Exception as e:
            self._log_error(f"Error fetching price for {symbol}: {e}")
            return None
    
    def _check_alert_condition(
        self,
        current_price: float,
        target_price: float,
        condition: str
    ) -> bool:
        """
        Check if alert condition is met.
        
        Args:
            current_price: Current market price
            target_price: Target price from config
            condition: Condition operator (>=, <=, ==)
            
        Returns:
            True if condition is met
        """
        if condition == ">=":
            return current_price >= target_price
        elif condition == "<=":
            return current_price <= target_price
        elif condition == "==":
            # For equality, use small tolerance (0.1%)
            tolerance = target_price * 0.001
            return abs(current_price - target_price) <= tolerance
        else:
            self._log_error(f"Unknown condition: {condition}")
            return False
    
    def _is_alert_on_cooldown(self, alert_id: str) -> bool:
        """
        Check if alert is on cooldown.
        
        Args:
            alert_id: Alert identifier
            
        Returns:
            True if alert is on cooldown
        """
        if alert_id not in self.alert_cooldowns:
            return False
        
        cooldown_minutes = self.config['global'].get('alert_cooldown_minutes', 60)
        cooldown_until = self.alert_cooldowns[alert_id]
        
        return datetime.now() < cooldown_until
    
    def _set_alert_cooldown(self, alert_id: str):
        """Set cooldown for an alert."""
        cooldown_minutes = self.config['global'].get('alert_cooldown_minutes', 60)
        self.alert_cooldowns[alert_id] = datetime.now() + timedelta(minutes=cooldown_minutes)
    
    def _send_alert_email(
        self,
        alert: Dict[str, Any],
        current_price: float
    ) -> bool:
        """
        Send alert email.
        
        Args:
            alert: Alert configuration
            current_price: Current price that triggered alert
            
        Returns:
            True if email sent successfully
        """
        if self.dry_run:
            print(f"[DRY RUN] Would send email for {alert['name']}")
            return True
        
        if self.email_notifier is None:
            print(f"Email notifier not available, skipping alert: {alert['name']}")
            return False
        
        recipient = self.config['global'].get('email_recipient')
        if not recipient or recipient == 'your@email.com':
            print("Error: email_recipient not configured in config file")
            return False
        
        try:
            success = self.email_notifier.send_alert(
                to_email=recipient,
                cryptocurrency=alert['cryptocurrency'],
                current_price=current_price,
                target_price=alert['target_price'],
                condition=alert['condition'],
                alert_name=alert['name']
            )
            
            return success
        except Exception as e:
            self._log_error(f"Error sending email for {alert['name']}: {e}")
            return False
    
    def _update_markdown_logs(
        self,
        alert: Optional[Dict[str, Any]] = None,
        current_price: Optional[float] = None,
        alert_sent: bool = False
    ):
        """Update markdown log files."""
        if not self.config['logging'].get('markdown_updates', True):
            return
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Update progress log
        progress_file = self.markdown_dir / "progress.md"
        
        if alert and alert_sent:
            # Log alert trigger
            with open(progress_file, 'a') as f:
                f.write(f"\n### {timestamp} - Alert Triggered\n")
                f.write(f"- **Alert**: {alert['name']}\n")
                f.write(f"- **Cryptocurrency**: {alert['cryptocurrency']}\n")
                f.write(f"- **Current Price**: ${current_price:,.8f}\n")
                f.write(f"- **Target Price**: ${alert['target_price']:,.8f}\n")
                f.write(f"- **Condition**: {alert['condition']}\n")
                f.write(f"- **Status**: ✅ Email Sent\n")
            
            # Update alerts history
            history_file = self.markdown_dir / "alerts_history.md"
            
            # Read existing content
            with open(history_file, 'r') as f:
                lines = f.readlines()
            
            # Find the table and insert new row after header
            table_start = None
            for i, line in enumerate(lines):
                if line.startswith('|--------'):
                    table_start = i + 1
                    break
            
            if table_start:
                # Remove "No alerts" row if present
                if table_start < len(lines) and '- | - | - | - | - | No alerts' in lines[table_start]:
                    lines.pop(table_start)
                
                # Insert new alert
                price_format = "${:,.8f}" if current_price < 1 else "${:,.2f}"
                new_row = f"| {timestamp} | {alert['cryptocurrency']} | {alert['condition']} | {price_format.format(alert['target_price'])} | {price_format.format(current_price)} | ✅ Sent |\n"
                lines.insert(table_start, new_row)
                
                # Write back
                with open(history_file, 'w') as f:
                    f.writelines(lines)
    
    def _log_error(self, message: str):
        """Log error to console and markdown."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[ERROR] {timestamp} - {message}")
        
        self.stats['errors_encountered'] += 1
        
        if self.config['logging'].get('markdown_updates', True):
            error_file = self.markdown_dir / "errors.md"
            
            with open(error_file, 'a') as f:
                f.write(f"\n### {timestamp}\n")
                f.write(f"- **Error**: {message}\n")
    
    def _auto_increment_target(self, alert: Dict[str, Any]):
        """
        Auto-increment the target price after an alert is triggered.
        
        Args:
            alert: Alert configuration dictionary
        """
        increment_amount = alert.get('increment_amount', 0.05)
        old_target = alert['target_price']
        condition = alert['condition']
        
        # Determine new target based on condition
        if condition == ">=":
            # For >= alerts, increment upward
            new_target = old_target + increment_amount
        elif condition == "<=":
            # For <= alerts, decrement downward
            new_target = old_target - increment_amount
        else:
            # For == alerts, don't auto-increment (doesn't make sense)
            return
        
        # Update the alert in memory
        alert['target_price'] = new_target
        
        # Update the config file
        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Find and update the alert
            for cfg_alert in config_data.get('alerts', []):
                if cfg_alert['id'] == alert['id']:
                    cfg_alert['target_price'] = new_target
                    break
            
            # Write back to file
            with open(self.config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
            
            print(f"[AUTO-INCREMENT] Target price updated: ${old_target:,.2f} → ${new_target:,.2f}")
            
            # Log to markdown
            if self.config['logging'].get('markdown_updates', True):
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                progress_file = self.markdown_dir / "progress.md"
                
                with open(progress_file, 'a') as f:
                    f.write(f"\n### {timestamp} - Auto-Increment\n")
                    f.write(f"- **Alert**: {alert['name']}\n")
                    f.write(f"- **Old Target**: ${old_target:,.2f}\n")
                    f.write(f"- **New Target**: ${new_target:,.2f}\n")
                    f.write(f"- **Increment**: ${increment_amount:,.2f}\n")
        
        except Exception as e:
            self._log_error(f"Error auto-incrementing target for {alert['id']}: {e}")
    
    def _log_heartbeat(self):
        """Log periodic heartbeat."""
        heartbeat_interval = self.config['logging'].get('heartbeat_interval_minutes', 5)
        
        if (datetime.now() - self.last_heartbeat).total_seconds() < heartbeat_interval * 60:
            return
        
        self.last_heartbeat = datetime.now()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Calculate uptime
        uptime = datetime.now() - self.stats['start_time']
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        # Log to console (if not in quiet mode)
        console_level = self.config['logging'].get('console_level', 'warning')
        if console_level in ['info', 'debug']:
            print(f"[HEARTBEAT] {timestamp} - Uptime: {uptime_str}, "
                  f"Checks: {self.stats['checks_performed']}, "
                  f"Alerts: {self.stats['alerts_triggered']}, "
                  f"Errors: {self.stats['errors_encountered']}")
        
        # Log to markdown
        if self.config['logging'].get('markdown_updates', True):
            progress_file = self.markdown_dir / "progress.md"
            
            with open(progress_file, 'a') as f:
                f.write(f"\n### {timestamp} - Heartbeat\n")
                f.write(f"- **Uptime**: {uptime_str}\n")
                f.write(f"- **Checks Performed**: {self.stats['checks_performed']}\n")
                f.write(f"- **Alerts Triggered**: {self.stats['alerts_triggered']}\n")
                f.write(f"- **Errors**: {self.stats['errors_encountered']}\n")
    
    def _check_alerts(self):
        """Check all enabled alerts."""
        alerts = self.config.get('alerts', [])
        enabled_alerts = [a for a in alerts if a.get('enabled', True)]
        
        if not enabled_alerts:
            return
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        for alert in enabled_alerts:
            try:
                # Skip if on cooldown
                if self._is_alert_on_cooldown(alert['id']):
                    continue
                
                # Fetch current price
                symbol = alert['symbol']
                current_price = self._fetch_price(symbol)
                
                if current_price is None:
                    continue
                
                # Format price for display
                price_format = "${:,.8f}" if current_price < 1 else "${:,.2f}"
                price_str = price_format.format(current_price)
                
                # Log price check
                target_price = alert['target_price']
                condition = alert['condition']
                
                # Show price update with status indicator
                if condition == ">=":
                    status = "✓" if current_price >= target_price else "○"
                    print(f"[{timestamp}] {alert['cryptocurrency']:10s} {price_str:>12s} (target: >={target_price:,.2f}) {status}")
                elif condition == "<=":
                    status = "✓" if current_price <= target_price else "○"
                    print(f"[{timestamp}] {alert['cryptocurrency']:10s} {price_str:>12s} (target: <={target_price:,.2f}) {status}")
                else:  # ==
                    tolerance = target_price * 0.001
                    status = "✓" if abs(current_price - target_price) <= tolerance else "○"
                    print(f"[{timestamp}] {alert['cryptocurrency']:10s} {price_str:>12s} (target: =={target_price:,.2f}) {status}")
                
                # Check condition
                condition_met = self._check_alert_condition(
                    current_price,
                    alert['target_price'],
                    alert['condition']
                )
                
                if condition_met:
                    # Send alert
                    alert_sent = self._send_alert_email(alert, current_price)
                    
                    if alert_sent:
                        self.stats['alerts_triggered'] += 1
                        self._set_alert_cooldown(alert['id'])
                        self._update_markdown_logs(alert, current_price, True)
                        
                        print(f"[ALERT] 🚨 {alert['name']} triggered at {price_str} - Email sent!")
                        
                        # Trigger trading strategies if enabled
                        if self.strategy_manager:
                            self.strategy_manager.handle_alert_trigger(
                                alert['id'],
                                symbol,
                                current_price
                            )
                        
                        # Auto-increment target price if enabled
                        if alert.get('auto_increment', False):
                            self._auto_increment_target(alert)
                
            except Exception as e:
                self._log_error(f"Error checking alert {alert.get('id', 'unknown')}: {e}")
        
        # Update trading positions after price checks
        if self.strategy_manager and self.trading_executor:
            for alert in enabled_alerts:
                try:
                    symbol = alert['symbol'].replace('/', '')  # Convert BTC/USDT to BTCUSDT
                    current_price = self._fetch_price(alert['symbol'])
                    
                    if current_price:
                        self.strategy_manager.update_positions(symbol, current_price)
                except Exception as e:
                    self._log_error(f"Error updating positions for {alert.get('symbol')}: {e}")
        
        self.stats['checks_performed'] += 1
    
    def _log_startup(self):
        """Log system startup."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"[INFO] Crypto Price Logger started at {timestamp}")
        print(f"[INFO] Config: {self.config_path}")
        print(f"[INFO] Exchange: {self.config['exchange']['name']}")
        print(f"[INFO] Check interval: {self.config['global']['check_interval_seconds']}s")
        
        enabled_alerts = [a for a in self.config.get('alerts', []) if a.get('enabled', True)]
        print(f"[INFO] Monitoring {len(enabled_alerts)} alert(s)")
        
        if self.config['logging'].get('markdown_updates', True):
            progress_file = self.markdown_dir / "progress.md"
            
            with open(progress_file, 'a') as f:
                f.write(f"\n\n## Session: {timestamp}\n")
                f.write(f"\n### System Started\n")
                f.write(f"- **Exchange**: {self.config['exchange']['name']}\n")
                f.write(f"- **Check Interval**: {self.config['global']['check_interval_seconds']}s\n")
                f.write(f"- **Active Alerts**: {len(enabled_alerts)}\n")
                f.write(f"- **Email Notifications**: {'Disabled (Dry Run)' if self.dry_run else 'Enabled'}\n")
    
    def run(self):
        """Main monitoring loop."""
        self.running = True
        self._log_startup()
        
        check_interval = self.config['global'].get('check_interval_seconds', 60)
        
        while self.running:
            try:
                # Check all alerts
                self._check_alerts()
                
                # Log heartbeat
                self._log_heartbeat()
                
                # Sleep until next check
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\n[INFO] Shutting down gracefully...")
                self.running = False
            except Exception as e:
                self._log_error(f"Unexpected error in main loop: {e}")
                # Sleep before retrying
                time.sleep(check_interval)
        
        self._log_shutdown()
    
    def _log_shutdown(self):
        """Log system shutdown."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        uptime = datetime.now() - self.stats['start_time']
        uptime_str = str(uptime).split('.')[0]
        
        print(f"[INFO] Crypto Price Logger stopped at {timestamp}")
        print(f"[INFO] Total uptime: {uptime_str}")
        print(f"[INFO] Checks performed: {self.stats['checks_performed']}")
        print(f"[INFO] Alerts triggered: {self.stats['alerts_triggered']}")
        print(f"[INFO] Errors encountered: {self.stats['errors_encountered']}")
        
        if self.config['logging'].get('markdown_updates', True):
            progress_file = self.markdown_dir / "progress.md"
            
            with open(progress_file, 'a') as f:
                f.write(f"\n### {timestamp} - System Stopped\n")
                f.write(f"- **Total Uptime**: {uptime_str}\n")
                f.write(f"- **Checks Performed**: {self.stats['checks_performed']}\n")
                f.write(f"- **Alerts Triggered**: {self.stats['alerts_triggered']}\n")
                f.write(f"- **Errors Encountered**: {self.stats['errors_encountered']}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Crypto Price Logger - 24/7 cryptocurrency price monitoring'
    )
    parser.add_argument(
        '--config',
        default='config/alert_config.yaml',
        help='Path to configuration file (default: config/alert_config.yaml)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without sending actual emails'
    )
    
    args = parser.parse_args()
    
    # Resolve config path relative to script directory
    script_dir = Path(__file__).parent
    config_path = script_dir / args.config
    
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)
    
    # Create and run logger
    logger = CryptoPriceLogger(str(config_path), dry_run=args.dry_run)
    
    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        logger.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run
    logger.run()


if __name__ == '__main__':
    main()
