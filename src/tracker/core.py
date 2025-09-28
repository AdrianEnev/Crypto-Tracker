"""
Core crypto tracker orchestration.
Main class that coordinates all components of the trading system.
"""

import schedule
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .config_manager import ConfigManager
from .price_manager import PriceManager
from .portfolio_manager import PortfolioManager
from .risk_manager import RiskManager
from .execution_manager import ExecutionManager
from .display_manager import DisplayManager
from src.notifier import Notifier
from src.decision import make_decision
from src.logger import log_event, configure_file_logging, log_decision_csv


class CryptoTracker:
    """Main crypto tracker orchestration class."""
    
    def __init__(self, config_path: str = "../config/config.yaml"):
        """Initialize the crypto tracker with configuration."""
        # Initialize configuration manager
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_config()
        
        # Initialize core components
        self.portfolio_manager = PortfolioManager(self.config_manager, self.config)
        self.risk_manager = RiskManager(self.config_manager, self.portfolio_manager)
        self.execution_manager = ExecutionManager(
            self.config_manager, 
            self.portfolio_manager, 
            self.risk_manager
        )
        self.price_manager = PriceManager(self.config_manager, self.config)
        self.display_manager = DisplayManager(self.config_manager)
        
        # Initialize notifier
        self.notifier = Notifier()
        
        # Global settings
        self.global_interval_override = self._get_global_interval_override()
        
        # Decision settings
        self.suggestion_threshold: float = 0.5
        self.auto_threshold: float = 0.8
        self.auto_threshold_bear: float = self.auto_threshold
        
        # Testing settings
        self.testing_enabled: bool = False
        self.testing_force_auto_on_suggest: bool = False
        self.testing_global_price_offset_pct: float = 0.0
        self.testing_per_coin_price_offset_pct: Dict[str, float] = {}
        
        # Strategy settings
        self.use_regime_filter: bool = False
        
        # Load additional settings
        self._load_optional_settings()
        
        # Setup schedules
        self.setup_schedules()
        
        # Configure logging
        configure_file_logging('logs')
    
    def _get_global_interval_override(self) -> Optional[int]:
        """Get global interval override from environment or config."""
        try:
            import os
            override = os.environ.get('TRACKER_INTERVAL_SECONDS')
            if override:
                return int(override)
        except Exception:
            pass
        return None
    
    def _load_optional_settings(self):
        """Load optional configuration settings."""
        try:
            config_data = self.config_manager.load_full_config()
            
            # Decision thresholds
            decision_config = config_data.get('decision', {})
            self.suggestion_threshold = decision_config.get('confidence_thresholds', {}).get('suggestion', 0.5)
            self.auto_threshold = decision_config.get('confidence_thresholds', {}).get('auto', 0.8)
            self.auto_threshold_bear = decision_config.get('confidence_thresholds', {}).get('auto_bear', self.auto_threshold)
            
            # Strategy settings
            strategy_config = config_data.get('strategy', {})
            self.use_regime_filter = strategy_config.get('use_regime_filter', False)
            
            # Testing settings
            testing_config = config_data.get('testing', {})
            self.testing_enabled = testing_config.get('enabled', False)
            self.testing_force_auto_on_suggest = testing_config.get('force_auto_on_suggest', False)
            self.testing_global_price_offset_pct = testing_config.get('global_price_offset_pct', 0.0)
            self.testing_per_coin_price_offset_pct = testing_config.get('per_coin_price_offset_pct', {})
            
        except Exception as ex:
            log_event('optional_settings_load_error', {'error': str(ex)})
    
    def setup_schedules(self):
        """Setup scheduled tasks."""
        try:
            # Refresh history every hour
            schedule.every(1).hours.do(self._refresh_history_tail)
            
            # Reset stagger cycle every 5 minutes
            schedule.every(5).minutes.do(self.risk_manager.reset_stagger_cycle)
            
            # Save portfolio state every 10 minutes
            schedule.every(10).minutes.do(self.portfolio_manager.save_portfolio_state)
            
        except Exception as ex:
            log_event('schedule_setup_error', {'error': str(ex)})
    
    def _refresh_history_tail(self):
        """Refresh historical data tail for all coins."""
        try:
            for coin_id in self.config.tracked_coins.keys():
                if not self.config.tracked_coins[coin_id].disabled:
                    self.price_manager.refresh_history_tail(coin_id)
        except Exception as ex:
            log_event('history_refresh_error', {'error': str(ex)})
    
    def check_coin_price(self, coin_id: str, coin_config):
        """Check price for a single coin and process alerts."""
        try:
            current_price = self.price_manager.fetcher.get_price(coin_config.symbol)
            if current_price is not None:
                # Check thresholds and send notifications
                self.notifier.check_thresholds(
                    coin_id=coin_id,
                    coin_name=coin_config.name,
                    current_price=current_price,
                    threshold=coin_config.threshold
                )
                
                # Display status
                if current_price > coin_config.threshold:
                    status = "[green]✓"
                else:
                    status = "[red]✗"
                
                price_str = self.display_manager.format_currency(current_price)
                threshold_str = self.display_manager.format_currency(coin_config.threshold)
                self.display_manager.print(f"   {status} {coin_config.name}: {price_str} (Threshold: {threshold_str})[/]")
            else:
                self.display_manager.print(f"   [yellow]⚠ Could not fetch price for {coin_config.name}[/]")
                
        except Exception as ex:
            log_event('coin_price_check_error', {'coin': coin_id, 'error': str(ex)})
    
    def check_all_prices(self):
        """Check prices for all enabled coins and make trading decisions."""
        try:
            # Get enabled coins
            enabled_map = {
                cid: cfg.symbol 
                for cid, cfg in self.config.tracked_coins.items() 
                if not cfg.disabled
            }
            
            if not enabled_map:
                return
            
            # Build CoinGecko ID mapping
            cg_ids = {}
            try:
                config_data = self.config_manager.load_full_config()
                for cid, data in config_data.get('tracked_coins', {}).items():
                    cg_id = data.get('coingecko_id')
                    if cg_id:
                        cg_ids[cid] = str(cg_id)
            except Exception:
                pass
            
            # Get aggregated prices
            aggregated = self.price_manager.get_aggregated_prices(enabled_map, cg_ids=cg_ids or None)
            if not aggregated:
                return
            
            # Process prices and make decisions
            sym_to_price: Dict[str, float] = {}
            for cid, pdata in aggregated.items():
                try:
                    price = pdata.get('price') if isinstance(pdata, dict) else None
                    sym = self.config.tracked_coins.get(cid).symbol.upper()
                    if price is not None and sym:
                        sym_to_price[sym] = float(price)
                except Exception:
                    continue
            
            # Update portfolio equity tracking
            equity_now = self.portfolio_manager.calculate_equity(sym_to_price)
            self.portfolio_manager.update_equity_tracking(equity_now)
            
            # Check exposure limits
            max_exposure_hit, daily_loss_hit = self.portfolio_manager.check_exposure_limits(equity_now)
            
            # Apply testing price offsets if enabled
            if self.testing_enabled and (self.testing_global_price_offset_pct != 0.0 or self.testing_per_coin_price_offset_pct):
                for cid, pdata in aggregated.items():
                    try:
                        if not isinstance(pdata, dict):
                            continue
                        price = pdata.get('price')
                        if price is None:
                            continue
                        
                        offset_pct = self.testing_global_price_offset_pct
                        if cid in self.testing_per_coin_price_offset_pct:
                            offset_pct = self.testing_per_coin_price_offset_pct[cid]
                        
                        if offset_pct != 0.0:
                            pdata['price'] = price * (1.0 + offset_pct / 100.0)
                    except Exception:
                        continue
            
            # Make trading decisions for each coin
            decisions = {}  # Collect all decisions for batch display
            for coin_id, coin_config in self.config.tracked_coins.items():
                if coin_config.disabled:
                    continue
                
                try:
                    pdata = aggregated.get(coin_id)
                    if not isinstance(pdata, dict):
                        continue
                    
                    current_price = pdata.get('price')
                    if current_price is None:
                        continue
                    
                    # Make trading decision
                    decision = make_decision(self, coin_id)
                    
                    # Log decision
                    log_decision_csv({
                        'coin_id': coin_id,
                        'price': current_price,
                        'signal': decision.signal,
                        'confidence': decision.confidence,
                        'action': decision.action_recommended,
                        'reason': decision.reason
                    })
                    
                    # Execute trades based on decision
                    symbol = coin_config.symbol.upper()
                    
                    # Check if we should execute trades
                    should_execute = (
                        self.execution_manager.auto_trade_enable and
                        not self.risk_manager.is_safe_mode_active() and
                        not max_exposure_hit and
                        not daily_loss_hit
                    )
                    
                    if should_execute:
                        if decision.action_recommended == "Buy":
                            # Check confidence threshold
                            threshold = self.auto_threshold_bear if self._is_bear_market() else self.auto_threshold
                            if decision.confidence >= threshold:
                                self.execution_manager.execute_buy_order(
                                    symbol, coin_id, current_price, decision.confidence
                                )
                        
                        elif decision.action_recommended == "Sell":
                            # Execute sell if in position
                            position = self.portfolio_manager.get_position(symbol)
                            if position is not None:
                                self.execution_manager.execute_sell_order(
                                    symbol, coin_id, current_price, decision.reason
                                )
                    
                    # Collect decision for batch display
                    decisions[coin_id] = {
                        'signal': decision.signal,
                        'confidence': decision.confidence,
                        'action': decision.action_recommended,
                        'reason': decision.reason
                    }
                    
                except Exception as ex:
                    log_event('decision_error', {'coin': coin_id, 'error': str(ex)})
            
            # Display all decisions together (supports both table and line-by-line formats)
            if decisions:
                self.display_manager.display_decisions(decisions)
            
            # Manage position exits
            self.execution_manager.manage_exits(sym_to_price)
            
        except Exception as ex:
            log_event('price_check_error', {'error': str(ex)})
    
    def _is_bear_market(self) -> bool:
        """Simple bear market detection based on recent performance."""
        try:
            # This is a placeholder - could be enhanced with more sophisticated logic
            return False
        except Exception:
            return False
    
    def display_status(self):
        """Display current status of all tracked coins."""
        try:
            # Get current prices
            prices = {}
            for coin_id, coin_config in self.config.tracked_coins.items():
                if not coin_config.disabled:
                    try:
                        price = self.price_manager.fetcher.get_price(coin_config.symbol)
                        if price is not None:
                            prices[coin_id] = price
                    except Exception:
                        continue
            
            self.display_manager.display_status(self.config.tracked_coins, prices)
            
        except Exception as ex:
            log_event('display_status_error', {'error': str(ex)})
    
    def run(self):
        """Run the tracker main loop."""
        try:
            # Display startup banner
            providers_active = ",".join(sorted(list(getattr(self.price_manager.aggregator, 'enabled_sources', {"cmc"}))))
            tracked_count = len([c for c in self.config.tracked_coins.values() if not c.disabled])
            self.display_manager.display_startup_banner(providers_active, tracked_count)
            
            # Main loop
            while True:
                try:
                    # Run scheduled tasks
                    schedule.run_pending()
                    
                    # Check all prices and make decisions
                    self.check_all_prices()
                    
                    # Display status periodically
                    current_time = datetime.now(timezone.utc)
                    if current_time.second == 0:  # Every minute
                        self.display_status()
                        
                        # Display portfolio summary
                        sym_to_price = {}
                        for coin_id, coin_config in self.config.tracked_coins.items():
                            if not coin_config.disabled:
                                try:
                                    price = self.price_manager.fetcher.get_price(coin_config.symbol)
                                    if price is not None:
                                        sym_to_price[coin_config.symbol.upper()] = price
                                except Exception:
                                    continue
                        
                        portfolio_summary = self.portfolio_manager.get_portfolio_summary(sym_to_price)
                        self.display_manager.display_portfolio_summary(portfolio_summary)
                        
                        # Display risk summary
                        self.display_manager.display_risk_summary(
                            self.risk_manager.get_risk_factor(),
                            portfolio_summary['equity_peak'],
                            portfolio_summary['equity']
                        )
                        
                        # Display execution status
                        execution_status = self.execution_manager.get_execution_status()
                        self.display_manager.display_execution_status(execution_status)
                    
                    # Sleep for a short interval
                    time.sleep(1)
                    
                except KeyboardInterrupt:
                    self.display_manager.print("\n[blue]Shutting down gracefully...\n[/]")
                    break
                except Exception as ex:
                    log_event('main_loop_error', {'error': str(ex)})
                    time.sleep(5)  # Brief pause before retrying
                    
        except Exception as ex:
            log_event('tracker_run_error', {'error': str(ex)})
            self.display_manager.display_error(f"Tracker failed to start: {ex}")
    
    # Delegate methods to components for backward compatibility
    @property
    def history(self):
        """Access to price manager's history."""
        return self.price_manager.history
    
    @property
    def portfolio(self):
        """Access to portfolio manager's portfolio."""
        return self.portfolio_manager.portfolio
    
    @property
    def config_path(self):
        """Access to config manager's config path."""
        return self.config_manager.config_path
