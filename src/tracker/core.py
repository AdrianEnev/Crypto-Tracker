"""
Core crypto tracker orchestration.
Main class that coordinates all components of the trading system.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import schedule

from ..decision import make_decision
from ..decision_enhanced import make_enhanced_decision
from ..enhanced_reporter import EnhancedReporter
from ..logger import configure_file_logging, log_decision_csv, log_event
from ..notifier import Notifier
from ..parameter_optimizer import ParameterOptimizer
from ..performance_metrics import PerformanceMetricsTracker
from ..risk import RobustRiskManager

from .config_manager import ConfigManager
from .display_manager import DisplayManager
from .execution_manager import ExecutionManager
from .portfolio_manager import PortfolioManager
from .price_manager import PriceManager
from .risk_manager import RiskManager


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

        # Initialize robust risk manager
        self.robust_risk_manager = RobustRiskManager(self.config_manager, self.portfolio_manager)

        self.execution_manager = ExecutionManager(
            self.config_manager, self.portfolio_manager, self.risk_manager
        )
        self.price_manager = PriceManager(self.config_manager, self.config)
        self.display_manager = DisplayManager(self.config_manager)

        # Initialize notifier
        self.notifier = Notifier()

        # Initialize performance metrics tracker
        self.performance_tracker = PerformanceMetricsTracker(self.config_manager)

        # Initialize parameter optimizer
        self.parameter_optimizer = ParameterOptimizer(self.config_manager)

        # Initialize enhanced reporter
        self.enhanced_reporter = EnhancedReporter(self.config_manager)

        # Initialize enhanced components
        self.social_integration = None
        self.market_analyzer = None
        self._init_enhanced_components()

        # Initialize monitoring and error recovery
        self.monitoring_enabled = False
        self.heartbeat_interval = 300  # 5 minutes
        self.max_restarts = 10
        self.restart_count = 0
        self.last_heartbeat = datetime.now(timezone.utc)
        self.start_time = datetime.now(timezone.utc)
        self.is_running = False
        
        # LLM failure tracking
        self.llm_failure_count = 0
        self.max_llm_failures = 5  # Disable LLM after 5 consecutive failures
        self.llm_disabled = False
        self.llm_disabled_time = None  # When LLM was disabled
        self.llm_reenable_after_hours = 1  # Re-enable after 1 hour
        
        self._init_monitoring_system()

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
        configure_file_logging("logs")

    def _get_global_interval_override(self) -> Optional[int]:
        """Get global interval override from environment or config."""
        try:
            import os

            override = os.environ.get("TRACKER_INTERVAL_SECONDS")
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
            decision_config = config_data.get("decision", {})
            self.suggestion_threshold = decision_config.get("confidence_thresholds", {}).get(
                "suggestion", 0.5
            )
            self.auto_threshold = decision_config.get("confidence_thresholds", {}).get("auto", 0.8)
            self.auto_threshold_bear = decision_config.get("confidence_thresholds", {}).get(
                "auto_bear", self.auto_threshold
            )

            # Strategy settings
            strategy_config = config_data.get("strategy", {})
            self.use_regime_filter = strategy_config.get("use_regime_filter", False)

            # Testing settings
            testing_config = config_data.get("testing", {})
            self.testing_enabled = testing_config.get("enabled", False)
            self.testing_force_auto_on_suggest = testing_config.get("force_auto_on_suggest", False)
            self.testing_global_price_offset_pct = testing_config.get(
                "global_price_offset_pct", 0.0
            )
            self.testing_per_coin_price_offset_pct = testing_config.get(
                "per_coin_price_offset_pct", {}
            )

        except Exception as ex:
            log_event("optional_settings_load_error", {"error": str(ex)})

    def _init_enhanced_components(self):
        """Initialize enhanced components (social media, LLM) if enabled."""
        try:
            config_data = self.config_manager.load_full_config()
            enhanced_features = config_data.get("enhanced_features", {})
            
            # Initialize social media integration
            social_config = enhanced_features.get("social_media", {})
            if social_config.get("enabled", False):
                try:
                    from src.social_media import create_social_integration
                    self.social_integration = create_social_integration(self.config_path)
                    log_event("social_media_initialized", {"enabled": True})
                except Exception as e:
                    log_event("social_media_init_error", {"error": str(e)})
                    self.social_integration = None
            
            # Initialize LLM integration
            llm_config = enhanced_features.get("llm", {})
            if llm_config.get("enabled", False):
                try:
                    from src.llm.config_manager import LLMConfigManager
                    from src.llm.client import LLMClient
                    from src.llm.market_analyzer import ComprehensiveMarketAnalyzer
                    
                    # Initialize LLM configuration manager
                    self.llm_config_manager = LLMConfigManager(
                        self.config_manager,
                        self.config_manager.secrets_manager if hasattr(self.config_manager, 'secrets_manager') else None
                    )
                    
                    # Validate configuration
                    if self.llm_config_manager.validate_config():
                        # Create LLM client
                        llm_config_obj = self.llm_config_manager.create_llm_config()
                        self.llm_client = LLMClient(llm_config_obj, self.llm_config_manager.secrets_manager)
                        
                        # Create market analyzer
                        self.market_analyzer = ComprehensiveMarketAnalyzer(self.llm_client)
                        
                        log_event("llm_initialized", {"enabled": True, "provider": llm_config_obj.provider.value})
                    else:
                        log_event("llm_config_validation_failed", {"enabled": False})
                        self.market_analyzer = None
                        
                except Exception as e:
                    log_event("llm_init_error", {"error": str(e)})
                    self.market_analyzer = None
                    
        except Exception as ex:
            log_event("enhanced_components_init_error", {"error": str(ex)})

    def _init_monitoring_system(self):
        """Initialize monitoring and error recovery system."""
        try:
            config_data = self.config_manager.load_full_config()
            monitoring_config = config_data.get("monitoring", {})
            
            # Load monitoring settings
            self.monitoring_enabled = monitoring_config.get("enabled", False)
            self.heartbeat_interval = monitoring_config.get("heartbeat_interval_seconds", 300)
            self.max_restarts = monitoring_config.get("max_restarts", 10)
            
            if self.monitoring_enabled:
                log_event("monitoring_system_initialized", {
                    "enabled": True,
                    "heartbeat_interval": self.heartbeat_interval,
                    "max_restarts": self.max_restarts
                })
            else:
                log_event("monitoring_system_disabled", {"enabled": False})
                
        except Exception as ex:
            log_event("monitoring_system_init_error", {"error": str(ex)})

    def _make_enhanced_decision_sync(self, coin_id: str, current_price: float):
        """Synchronous wrapper for enhanced decision making."""
        try:
            import asyncio
            import signal
            
            # Try to get existing event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, we can't use run_until_complete
                    # Fall back to standard decision making
                    return make_decision(self, coin_id)
            except RuntimeError:
                # No event loop, we can create one
                pass
            
            # Run async enhanced decision making with timeout
            try:
                async def run_with_timeout():
                    return await asyncio.wait_for(
                        make_enhanced_decision(self, coin_id, current_price),
                        timeout=30.0  # 30 second timeout
                    )
                
                result = asyncio.run(run_with_timeout())
                # Reset LLM failure count on successful enhanced decision
                if self.llm_failure_count > 0:
                    self.llm_failure_count = 0
                    log_event("llm_failure_count_reset", {"reason": "successful_enhanced_decision"})
                return result
            except asyncio.TimeoutError:
                log_event("enhanced_decision_timeout", {"coin": coin_id, "timeout": 30})
                return make_decision(self, coin_id)
            
        except Exception as e:
            log_event("enhanced_decision_sync_error", {"coin": coin_id, "error": str(e)})
            # Fallback to standard decision making
            return make_decision(self, coin_id)

    def _track_llm_failure(self, error_message: str):
        """Track LLM failures and disable LLM after repeated failures."""
        self.llm_failure_count += 1
        
        log_event("llm_failure_tracked", {
            "failure_count": self.llm_failure_count,
            "max_failures": self.max_llm_failures,
            "error": error_message
        })
        
        if self.llm_failure_count >= self.max_llm_failures and not self.llm_disabled:
            self.llm_disabled = True
            self.llm_disabled_time = datetime.now(timezone.utc)
            log_event("llm_disabled_due_to_failures", {
                "failure_count": self.llm_failure_count,
                "max_failures": self.max_llm_failures,
                "reason": "Too many consecutive LLM failures",
                "disabled_at": self.llm_disabled_time.isoformat()
            })
            
            # Display warning to user
            self.display_manager.display_warning(
                f"⚠️  LLM analysis has been temporarily disabled due to {self.llm_failure_count} consecutive failures. "
                f"System will continue with standard technical analysis only. "
                f"LLM will be re-enabled after {self.llm_reenable_after_hours} hour(s)."
            )

    def _check_llm_reenable(self):
        """Check if LLM should be re-enabled after timeout."""
        if self.llm_disabled and self.llm_disabled_time:
            time_since_disabled = datetime.now(timezone.utc) - self.llm_disabled_time
            hours_since_disabled = time_since_disabled.total_seconds() / 3600
            
            if hours_since_disabled >= self.llm_reenable_after_hours:
                self.llm_disabled = False
                self.llm_failure_count = 0
                self.llm_disabled_time = None
                
                log_event("llm_reenabled_after_timeout", {
                    "hours_since_disabled": hours_since_disabled,
                    "reenable_after_hours": self.llm_reenable_after_hours
                })
                
                self.display_manager.display_info(
                    f"✅ LLM analysis has been re-enabled after {hours_since_disabled:.1f} hours. "
                    f"Enhanced decision making is now available again."
                )

    def _log_heartbeat(self):
        """Log system heartbeat with current status."""
        try:
            # Get portfolio summary
            portfolio_summary = self.portfolio_manager.get_portfolio_summary()
            
            # Calculate runtime
            runtime_hours = (datetime.now(timezone.utc) - self.start_time).total_seconds() / 3600
            
            # Get performance metrics
            performance_metrics = self._get_performance_metrics()
            
            log_event("system_heartbeat", {
                "runtime_hours": runtime_hours,
                "portfolio_value": portfolio_summary.get("total_value", 0),
                "total_return_pct": portfolio_summary.get("total_return_pct", 0),
                "total_trades": performance_metrics.get("total_trades", 0),
                "trades_per_hour": performance_metrics.get("trades_per_hour", 0),
                "active_positions": len(portfolio_summary.get("positions", {})),
                "restart_count": self.restart_count,
                "monitoring_enabled": self.monitoring_enabled
            })
            
            # Track system health metrics
            self.performance_tracker.track_system_health({
                "heartbeat": True,
                "restart_count": self.restart_count,
                "cache_stats": self.price_manager.get_cache_stats()
            })
            
            # Track portfolio performance
            self.performance_tracker.track_portfolio_performance(portfolio_summary)
            
        except Exception as ex:
            log_event("heartbeat_log_error", {"error": str(ex)})

    def _get_performance_metrics(self):
        """Get comprehensive performance metrics."""
        try:
            # Get trade history from execution manager
            recent_orders = list(self.execution_manager.recent_orders)
            total_trades = len(recent_orders)
            
            # Calculate trades per hour
            runtime_hours = (datetime.now(timezone.utc) - self.start_time).total_seconds() / 3600
            trades_per_hour = total_trades / max(1, runtime_hours)
            
            return {
                "total_trades": total_trades,
                "trades_per_hour": trades_per_hour,
                "runtime_hours": runtime_hours,
                "restart_count": self.restart_count
            }
            
        except Exception as ex:
            log_event("performance_metrics_error", {"error": str(ex)})
            return {"total_trades": 0, "trades_per_hour": 0, "runtime_hours": 0, "restart_count": 0}

    def _handle_error_recovery(self, error: Exception, context: str):
        """Handle error recovery with restart logic."""
        try:
            log_event("error_recovery_triggered", {
                "error": str(error),
                "context": context,
                "restart_count": self.restart_count,
                "max_restarts": self.max_restarts
            })
            
            # Track error in performance metrics
            self.performance_tracker.track_system_health({
                "error_occurred": True,
                "restart_count": self.restart_count
            })
            
            if self.restart_count < self.max_restarts:
                self.restart_count += 1
                log_event("error_recovery_restart", {
                    "restart_attempt": self.restart_count,
                    "max_restarts": self.max_restarts
                })
                return True
            else:
                log_event("error_recovery_max_restarts_reached", {
                    "restart_count": self.restart_count,
                    "max_restarts": self.max_restarts
                })
                return False
                
        except Exception as ex:
            log_event("error_recovery_failed", {"error": str(ex)})
            return False

    def _run_parameter_optimization(self):
        """Run parameter optimization for all coins if enabled."""
        try:
            if not self.parameter_optimizer.enabled:
                return
            
            log_event("parameter_optimization_scheduled", {"enabled": True})
            
            # Optimize parameters for each enabled coin
            for coin_id, coin_config in self.config.tracked_coins.items():
                if coin_config.disabled:
                    continue
                
                # Check if optimization is needed
                if self.parameter_optimizer.should_optimize(coin_id):
                    try:
                        # Run optimization
                        result = self.parameter_optimizer.optimize_parameters(coin_id)
                        
                        if result:
                            # Apply optimized parameters
                            self.parameter_optimizer.apply_optimized_parameters(coin_id)
                            
                            log_event("parameter_optimization_completed", {
                                "coin_id": coin_id,
                                "best_value": result.get("best_value", 0)
                            })
                        
                    except Exception as ex:
                        log_event("parameter_optimization_error", {
                            "coin_id": coin_id,
                            "error": str(ex)
                        })
                        continue
            
        except Exception as ex:
            log_event("parameter_optimization_schedule_error", {"error": str(ex)})

    def _generate_enhanced_reports(self):
        """Generate enhanced reports if enabled."""
        try:
            if not self.enhanced_reporter.enabled:
                return
            
            log_event("enhanced_reports_scheduled", {"enabled": True})
            
            # Find database file (assuming it's in the execution manager)
            db_path = None
            if hasattr(self.execution_manager, 'paper') and hasattr(self.execution_manager.paper, 'db_path'):
                db_path = Path(self.execution_manager.paper.db_path)
            else:
                # Look for common database locations
                possible_paths = [
                    Path("./demo_orderbook.db"),
                    Path("./trades.db"),
                    Path("./trading_data.db")
                ]
                
                for path in possible_paths:
                    if path.exists():
                        db_path = path
                        break
            
            if db_path and db_path.exists():
                # Generate enhanced reports
                success = self.enhanced_reporter.generate_enhanced_reports(db_path)
                
                if success:
                    log_event("enhanced_reports_generated", {
                        "db_path": str(db_path),
                        "success": True
                    })
                else:
                    log_event("enhanced_reports_generation_failed", {
                        "db_path": str(db_path),
                        "success": False
                    })
            else:
                log_event("enhanced_reports_no_database", {
                    "message": "No database file found for report generation"
                })
            
        except Exception as ex:
            log_event("enhanced_reports_schedule_error", {"error": str(ex)})

    def setup_schedules(self):
        """Setup scheduled tasks."""
        try:
            # Refresh history every 15 minutes (improved responsiveness)
            schedule.every(15).minutes.do(self._refresh_history_tail)

            # Reset stagger cycle every 5 minutes
            schedule.every(5).minutes.do(self.risk_manager.reset_stagger_cycle)

            # Save portfolio state every 10 minutes
            schedule.every(10).minutes.do(self.portfolio_manager.save_portfolio_state)
            
            # Cache warmup every 30 minutes
            schedule.every(30).minutes.do(self.price_manager._warmup_cache)
            
            # Monitoring heartbeat if enabled
            if self.monitoring_enabled:
                schedule.every(self.heartbeat_interval).seconds.do(self._log_heartbeat)
            
            # Performance metrics export
            schedule.every(60).minutes.do(self.performance_tracker.export_metrics)
            
            # Parameter optimization (if enabled)
            schedule.every(24).hours.do(self._run_parameter_optimization)
            
            # Enhanced reporting (if enabled)
            schedule.every(24).hours.do(self._generate_enhanced_reports)

        except Exception as ex:
            log_event("schedule_setup_error", {"error": str(ex)})

    def _refresh_history_tail(self):
        """Refresh historical data tail for all coins in parallel."""
        try:
            import concurrent.futures
            import threading
            
            # Get enabled coins
            enabled_coins = [
                coin_id for coin_id in self.config.tracked_coins.keys()
                if not self.config.tracked_coins[coin_id].disabled
            ]
            
            if not enabled_coins:
                return
            
            # Use ThreadPoolExecutor for parallel processing
            max_workers = min(len(enabled_coins), 5)  # Limit to 5 concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all refresh tasks
                future_to_coin = {
                    executor.submit(self.price_manager.refresh_history_tail, coin_id): coin_id
                    for coin_id in enabled_coins
                }
                
                # Process completed tasks
                for future in concurrent.futures.as_completed(future_to_coin):
                    coin_id = future_to_coin[future]
                    try:
                        result = future.result()
                        if result:
                            log_event("history_refresh_success", {"coin": coin_id})
                    except Exception as ex:
                        log_event("history_refresh_error", {"coin": coin_id, "error": str(ex)})
                        
        except Exception as ex:
            log_event("history_refresh_error", {"error": str(ex)})

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
                    threshold=coin_config.threshold,
                )

                # Display status
                if current_price > coin_config.threshold:
                    status = "[green]✓"
                else:
                    status = "[red]✗"

                price_str = self.display_manager.format_currency(current_price)
                threshold_str = self.display_manager.format_currency(coin_config.threshold)
                self.display_manager.print(
                    f"   {status} {coin_config.name}: {price_str} (Threshold: {threshold_str})[/]"
                )
            else:
                self.display_manager.print(
                    f"   [yellow]⚠ Could not fetch price for {coin_config.name}[/]"
                )

        except Exception as ex:
            log_event("coin_price_check_error", {"coin": coin_id, "error": str(ex)})

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk management summary."""
        try:
            if not hasattr(self, "robust_risk_manager") or not self.robust_risk_manager:
                return {}

            return self.robust_risk_manager.get_risk_summary()
        except Exception as e:
            log_event("risk_summary_error", {"error": str(e)})
            return {}

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
                for cid, data in config_data.get("tracked_coins", {}).items():
                    cg_id = data.get("coingecko_id")
                    if cg_id:
                        cg_ids[cid] = str(cg_id)
            except Exception:
                pass

            # Get aggregated prices
            aggregated = self.price_manager.get_aggregated_prices(
                enabled_map, cg_ids=cg_ids or None
            )
            if not aggregated:
                return

            # Process prices and make decisions
            sym_to_price: Dict[str, float] = {}
            successful_prices = 0
            total_coins = len(aggregated)
            
            for cid, pdata in aggregated.items():
                try:
                    price = pdata.get("price") if isinstance(pdata, dict) else None
                    sym = self.config.tracked_coins.get(cid).symbol.upper()
                    if price is not None and sym:
                        sym_to_price[sym] = float(price)
                        successful_prices += 1
                except Exception:
                    continue

            # Check if all providers failed to retrieve price data
            if successful_prices == 0:
                self.display_manager.display_error(
                    "❌ All price data providers failed to retrieve information. "
                    "No trading decisions can be made at this time. "
                    "Please check your internet connection and API rate limits."
                )
                log_event("all_providers_failed", {
                    "total_coins": total_coins,
                    "successful_prices": successful_prices,
                    "enabled_sources": self.price_manager.aggregator.enabled_sources
                })
                return
            
            # Warn if some providers failed (partial failure)
            elif successful_prices < total_coins:
                failed_coins = total_coins - successful_prices
                self.display_manager.display_warning(
                    f"⚠️  {failed_coins} out of {total_coins} coins failed to retrieve price data. "
                    f"Trading decisions will be made for {successful_prices} coins only."
                )
                log_event("partial_provider_failure", {
                    "total_coins": total_coins,
                    "successful_prices": successful_prices,
                    "failed_coins": failed_coins,
                    "enabled_sources": self.price_manager.aggregator.enabled_sources
                })

            # Update portfolio equity tracking
            equity_now = self.portfolio_manager.calculate_equity(sym_to_price)
            self.portfolio_manager.update_equity_tracking(equity_now)

            # Perform robust risk assessment
            risk_status = self.robust_risk_manager.perform_risk_assessment(sym_to_price)

            # Check exposure limits (legacy)
            max_exposure_hit, daily_loss_hit = self.portfolio_manager.check_exposure_limits(
                equity_now
            )

            # Apply testing price offsets if enabled
            if self.testing_enabled and (
                self.testing_global_price_offset_pct != 0.0
                or self.testing_per_coin_price_offset_pct
            ):
                for cid, pdata in aggregated.items():
                    try:
                        if not isinstance(pdata, dict):
                            continue
                        price = pdata.get("price")
                        if price is None:
                            continue

                        offset_pct = self.testing_global_price_offset_pct
                        if cid in self.testing_per_coin_price_offset_pct:
                            offset_pct = self.testing_per_coin_price_offset_pct[cid]

                        if offset_pct != 0.0:
                            pdata["price"] = price * (1.0 + offset_pct / 100.0)
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

                    current_price = pdata.get("price")
                    if current_price is None:
                        continue

                    # Make trading decision (enhanced if available)
                    try:
                        # Check if enhanced features are enabled
                        config_data = self.config_manager.load_full_config()
                        enhanced_features = config_data.get("enhanced_features", {})
                        social_enabled = enhanced_features.get("social_media", {}).get("enabled", False)
                        
                        # Check if LLM should be re-enabled
                        self._check_llm_reenable()
                        
                        llm_enabled = enhanced_features.get("llm", {}).get("enabled", False) and not self.llm_disabled
                        
                        if social_enabled or llm_enabled:
                            # Use enhanced decision making (synchronous wrapper)
                            decision = self._make_enhanced_decision_sync(coin_id, current_price)
                        else:
                            # Use standard decision making
                            decision = make_decision(self, coin_id)
                    except Exception as e:
                        log_event("decision_making_error", {"coin": coin_id, "error": str(e)})
                        # Fallback to standard decision
                        decision = make_decision(self, coin_id)

                    # Log decision
                    log_decision_csv(
                        {
                            "coin_id": coin_id,
                            "price": current_price,
                            "signal": decision.signal,
                            "confidence": decision.confidence,
                            "action": decision.action_recommended,
                            "reason": decision.reason,
                        }
                    )

                    # Execute trades based on decision
                    symbol = coin_config.symbol.upper()

                    # Check if we should execute trades
                    should_execute = (
                        self.execution_manager.auto_trade_enable
                        and not self.risk_manager.is_safe_mode_active()
                        and not max_exposure_hit
                        and not daily_loss_hit
                    )

                    if should_execute:
                        if decision.action_recommended == "Buy":
                            # Check confidence threshold
                            threshold = (
                                self.auto_threshold_bear
                                if self._is_bear_market()
                                else self.auto_threshold
                            )
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
                        "signal": decision.signal,
                        "confidence": decision.confidence,
                        "action": decision.action_recommended,
                        "reason": decision.reason,
                    }

                except Exception as ex:
                    log_event("decision_error", {"coin": coin_id, "error": str(ex)})

            # Display all decisions together (supports both table and line-by-line formats)
            if decisions:
                self.display_manager.display_decisions(decisions)

            # Manage position exits
            self.execution_manager.manage_exits(sym_to_price)

        except Exception as ex:
            log_event("price_check_error", {"error": str(ex)})

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
            log_event("display_status_error", {"error": str(ex)})
            # Handle error recovery for display status
            if self.monitoring_enabled:
                self._handle_error_recovery(ex, "display_status")

    def run(self):
        """Run the tracker main loop."""
        try:
            # Display startup banner
            providers_active = ",".join(
                sorted(list(getattr(self.price_manager.aggregator, "enabled_sources", {"cmc"})))
            )
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

                        portfolio_summary = self.portfolio_manager.get_portfolio_summary(
                            sym_to_price
                        )
                        self.display_manager.display_portfolio_summary(portfolio_summary)

                        # Display risk summary
                        self.display_manager.display_risk_summary(
                            self.risk_manager.get_risk_factor(),
                            portfolio_summary["equity_peak"],
                            portfolio_summary["equity"],
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
                    log_event("main_loop_error", {"error": str(ex)})
                    # Handle error recovery for main loop
                    if self.monitoring_enabled:
                        if not self._handle_error_recovery(ex, "main_loop"):
                            # Max restarts reached, stop the system
                            break
                    time.sleep(5)  # Brief pause before retrying

        except Exception as ex:
            log_event("tracker_run_error", {"error": str(ex)})
            # Handle error recovery for tracker startup
            if self.monitoring_enabled:
                self._handle_error_recovery(ex, "tracker_startup")
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
