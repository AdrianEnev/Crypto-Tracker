"""
Execution management for the crypto tracker.
Handles order execution, exit management, and live trading operations.
"""

import os
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import yaml

from src.executor import PaperExecutor
from src.executor_ccxt import CCXTLiveExecutor
from src.logger import log_decision_csv, log_event, log_order_csv
from src.position_sizing import compute_size_usd
from src.security.secrets_config_manager import SecretsConfigManager
from src.security.security_manager import SecurityManager


class ExecutionManager:
    """Manages order execution and trading operations."""

    def __init__(self, config_manager, portfolio_manager, risk_manager):
        self.config_manager = config_manager
        self.portfolio_manager = portfolio_manager
        self.risk_manager = risk_manager

        # Initialize security components
        self.security_manager = SecurityManager(config_manager)
        self.secrets_config_manager = SecretsConfigManager(config_manager)

        # Execution configuration
        self.auto_trade_enable: bool = False
        self.auto_trade_mode: str = "paper"
        self.paper_place_orders: bool = False
        self.live_exits_enable: bool = True

        # Order execution
        self.trade_default_size_usd: float = 50.0
        self.executor_retry_count: int = 3
        self.executor_backoff_factor: float = 0.5

        # Executors
        self.paper = PaperExecutor()
        self.live_executor: Optional[CCXTLiveExecutor] = None

        # Recent orders tracking
        self.recent_orders: deque = deque(maxlen=20)
        self._last_oco_status: Optional[Dict[str, str]] = None

        # Exit management
        self._live_exit_backoff: Dict[str, Dict[str, float]] = {}
        self._breakeven_armed: Dict[str, bool] = {}
        self._live_be_armed: Dict[str, bool] = {}
        self._live_last_trail: Dict[str, float] = {}

        self._load_execution_settings()
        self._setup_live_executor()

    def _load_execution_settings(self):
        """Load execution settings from configuration."""
        try:
            config_data = self.config_manager.load_full_config()
            auto_trade_config = config_data.get("auto_trade", {})
            execution_config = config_data.get("execution", {})
            paper_config = config_data.get("paper", {})

            self.auto_trade_enable = auto_trade_config.get("enable", False)
            self.auto_trade_mode = auto_trade_config.get("mode", "paper")
            self.paper_place_orders = paper_config.get("place_orders", True)
            self.live_exits_enable = paper_config.get("exits_enable", True)

            self.trade_default_size_usd = config_data.get("trade", {}).get("default_size_usd", 50.0)
            self.executor_retry_count = execution_config.get("retry_count", 3)
            self.executor_backoff_factor = execution_config.get("backoff_factor", 0.5)

        except Exception as ex:
            log_event("execution_settings_load_error", {"error": str(ex)})

    def _setup_live_executor(self):
        """Setup live executor if configured."""
        try:
            if self.auto_trade_mode == "live":
                providers_config = self.config_manager.get_providers_config()
                exchange_name = str(providers_config.get("exchange", "binance")).lower()

                # Get API keys securely
                key = self.secrets_config_manager.get_api_key(exchange_name)
                secret = self.secrets_config_manager.get_api_secret(exchange_name)

                if key and secret:
                    # Validate API key safety before creating executor
                    if self.security_manager.is_trading_safe(exchange_name, key, secret):
                        self.live_executor = CCXTLiveExecutor(
                            exchange_name=exchange_name,
                            api_key=key,
                            secret_key=secret,
                            retry_count=self.executor_retry_count,
                            backoff_factor=self.executor_backoff_factor,
                        )
                        log_event(
                            "live_executor_created",
                            {
                                "exchange": exchange_name,
                                "security_validated": True,
                                "secrets_source": "secrets_manager",
                            },
                        )
                    else:
                        # Security validation failed - fall back to paper trading
                        from rich.console import Console

                        console = Console()
                        console.print(
                            f"[red]Security validation failed for {exchange_name}. Staying in paper mode.[/red]"
                        )
                        self.auto_trade_mode = "paper"
                        log_event(
                            "live_executor_security_failed",
                            {
                                "exchange": exchange_name,
                                "reason": "API key safety validation failed",
                            },
                        )
                else:
                    from rich.console import Console

                    console = Console()
                    console.print(
                        f"[yellow]Live mode requested but API keys not found for {exchange_name}. Staying in paper.[/]"
                    )
                    self.auto_trade_mode = "paper"

        except Exception as ex:
            log_event("live_executor_setup_error", {"error": str(ex)})
            self.live_executor = None

    def execute_buy_order(
        self, symbol: str, coin_id: str, current_price: float, confidence: float
    ) -> bool:
        """Execute a buy order for the given symbol."""
        try:
            # Check if we can enter position
            can_enter, reason = self.risk_manager.can_enter_position(symbol, coin_id)
            if not can_enter:
                log_event(
                    "buy_order_rejected",
                    {"symbol": symbol, "reason": reason, "confidence": confidence},
                )
                return False

            # Calculate position size
            size_usd = self._calculate_position_size(symbol, current_price, confidence)
            if size_usd <= 0:
                log_event(
                    "buy_order_rejected",
                    {"symbol": symbol, "reason": "invalid_size", "size_usd": size_usd},
                )
                return False

            # Execute order based on mode
            if self.auto_trade_mode == "live" and self.live_executor is not None:
                success = self._execute_live_buy_order(symbol, coin_id, size_usd, current_price)
            else:
                success = self._execute_paper_buy_order(symbol, coin_id, size_usd, current_price)

            if success:
                # Record position entry
                self.risk_manager.record_position_entry(symbol, coin_id)

                # Log order
                log_order_csv(
                    {
                        "symbol": symbol,
                        "side": "buy",
                        "size_usd": size_usd,
                        "price": current_price,
                        "mode": self.auto_trade_mode,
                        "confidence": confidence,
                    }
                )

                log_event(
                    "buy_order_executed",
                    {
                        "symbol": symbol,
                        "size_usd": size_usd,
                        "price": current_price,
                        "mode": self.auto_trade_mode,
                        "confidence": confidence,
                    },
                )

            return success

        except Exception as ex:
            log_event("buy_order_error", {"symbol": symbol, "error": str(ex)})
            return False

    def execute_sell_order(
        self, symbol: str, coin_id: str, current_price: float, reason: str = "manual"
    ) -> bool:
        """Execute a sell order for the given symbol."""
        try:
            position = self.portfolio_manager.get_position(symbol)
            if position is None:
                log_event("sell_order_rejected", {"symbol": symbol, "reason": "no_position"})
                return False

            # Calculate sell size (full position)
            size_usd = float(position.units) * current_price

            # Execute order based on mode
            if self.auto_trade_mode == "live" and self.live_executor is not None:
                success = self._execute_live_sell_order(symbol, coin_id, size_usd, current_price)
            else:
                success = self._execute_paper_sell_order(symbol, coin_id, size_usd, current_price)

            if success:
                # Log order
                log_order_csv(
                    {
                        "symbol": symbol,
                        "side": "sell",
                        "size_usd": size_usd,
                        "price": current_price,
                        "mode": self.auto_trade_mode,
                        "reason": reason,
                    }
                )

                log_event(
                    "sell_order_executed",
                    {
                        "symbol": symbol,
                        "size_usd": size_usd,
                        "price": current_price,
                        "mode": self.auto_trade_mode,
                        "reason": reason,
                    },
                )

            return success

        except Exception as ex:
            log_event("sell_order_error", {"symbol": symbol, "error": str(ex)})
            return False

    def _calculate_position_size(
        self, symbol: str, current_price: float, confidence: float
    ) -> float:
        """Calculate position size based on risk parameters."""
        try:
            # Get portfolio equity
            portfolio_summary = self.portfolio_manager.get_portfolio_summary({})
            equity = portfolio_summary["equity"]

            # Calculate size using position sizing logic
            size_usd = compute_size_usd(
                equity=equity,
                risk_budget_pct=self.risk_manager.risk_budget_pct,
                risk_factor=self.risk_manager.get_risk_factor(),
                confidence=confidence,
                max_size_usd=self.risk_manager.max_size_usd,
                min_size_usd=self.risk_manager.min_size_usd,
                default_size_usd=self.trade_default_size_usd,
            )

            return size_usd

        except Exception as ex:
            log_event("position_size_error", {"symbol": symbol, "error": str(ex)})
            return 0.0

    def _execute_paper_buy_order(
        self, symbol: str, coin_id: str, size_usd: float, price: float
    ) -> bool:
        """Execute a paper buy order."""
        try:
            if not self.paper_place_orders:
                return False

            # Place paper order
            order = self.paper.place_order(symbol, "buy", size_usd, "market")

            # Update portfolio
            units = size_usd / price
            self.portfolio_manager.portfolio.add_position(
                symbol=symbol, units=units, entry_price=price, order_id=order.id
            )

            # Save portfolio state
            self.portfolio_manager.save_portfolio_state()

            return True

        except Exception as ex:
            log_event("paper_buy_error", {"symbol": symbol, "error": str(ex)})
            return False

    def _execute_paper_sell_order(
        self, symbol: str, coin_id: str, size_usd: float, price: float
    ) -> bool:
        """Execute a paper sell order."""
        try:
            if not self.paper_place_orders:
                return False

            # Place paper order
            order = self.paper.place_order(symbol, "sell", size_usd, "market")

            # Update portfolio
            self.portfolio_manager.portfolio.close_position(symbol, price, order.id)

            # Save portfolio state
            self.portfolio_manager.save_portfolio_state()

            return True

        except Exception as ex:
            log_event("paper_sell_error", {"symbol": symbol, "error": str(ex)})
            return False

    def _execute_live_buy_order(
        self, symbol: str, coin_id: str, size_usd: float, price: float
    ) -> bool:
        """Execute a live buy order."""
        try:
            if self.live_executor is None:
                return False

            # Get market pair
            config_data = self.config_manager.load_full_config()
            tracked = config_data.get("tracked_coins", {})
            per_coin_config = tracked.get(coin_id, {})
            market_pair = per_coin_config.get("market", f"{symbol}/USDT")

            # Execute live order
            result = self.live_executor.place_market_buy(symbol=market_pair, size_usd=size_usd)

            if result.success:
                # Update portfolio
                units = size_usd / result.filled_price if result.filled_price else size_usd / price
                self.portfolio_manager.portfolio.add_position(
                    symbol=symbol,
                    units=units,
                    entry_price=result.filled_price if result.filled_price else price,
                    order_id=result.order_id,
                )

                # Save portfolio state
                self.portfolio_manager.save_portfolio_state()

                return True

            return False

        except Exception as ex:
            log_event("live_buy_error", {"symbol": symbol, "error": str(ex)})
            return False

    def _execute_live_sell_order(
        self, symbol: str, coin_id: str, size_usd: float, price: float
    ) -> bool:
        """Execute a live sell order."""
        try:
            if self.live_executor is None:
                return False

            # Get market pair
            config_data = self.config_manager.load_full_config()
            tracked = config_data.get("tracked_coins", {})
            per_coin_config = tracked.get(coin_id, {})
            market_pair = per_coin_config.get("market", f"{symbol}/USDT")

            # Execute live order
            result = self.live_executor.place_market_sell(symbol=market_pair, size_usd=size_usd)

            if result.success:
                # Update portfolio
                self.portfolio_manager.portfolio.close_position(
                    symbol, result.filled_price if result.filled_price else price, result.order_id
                )

                # Save portfolio state
                self.portfolio_manager.save_portfolio_state()

                return True

            return False

        except Exception as ex:
            log_event("live_sell_error", {"symbol": symbol, "error": str(ex)})
            return False

    def manage_exits(self, sym_to_price: Dict[str, float]):
        """Manage position exits based on stop loss and take profit levels."""
        try:
            for symbol, position in list(self.portfolio_manager.portfolio.positions.items()):
                current_price = sym_to_price.get(symbol)
                if current_price is None:
                    continue

                # Update trailing peak
                self.portfolio_manager.update_position_peak(symbol, current_price)

                # Check stop loss and take profit
                should_exit, reason = self._should_exit_position(position, current_price)
                if should_exit:
                    # Find coin_id for logging
                    coin_id = None
                    for cid, cfg in self.config_manager.load_config().tracked_coins.items():
                        if cfg.symbol.upper() == symbol:
                            coin_id = cid
                            break

                    if coin_id:
                        self.execute_sell_order(symbol, coin_id, current_price, reason)

        except Exception as ex:
            log_event("exit_management_error", {"error": str(ex)})

    def _should_exit_position(self, position, current_price: float) -> tuple[bool, str]:
        """Check if position should be exited based on stop loss or take profit."""
        try:
            # Check take profit
            if position.entry_price > 0:
                tp_pct = (current_price / position.entry_price - 1.0) * 100.0
                if tp_pct >= self.risk_manager.risk.take_profit_pct * 100.0:
                    return True, "take_profit"

            # Check stop loss
            if position.entry_price > 0:
                sl_pct = (position.entry_price / current_price - 1.0) * 100.0
                if sl_pct >= self.risk_manager.risk.stop_loss_pct * 100.0:
                    return True, "stop_loss"

            # Check trailing stop
            if hasattr(position, "peak_price") and position.peak_price > 0:
                trailing_stop_level = self.risk_manager.compute_trailing_stop_for_symbol(
                    position.symbol, position.peak_price
                )
                if trailing_stop_level and current_price <= trailing_stop_level:
                    return True, "trailing_stop"

            return False, ""

        except Exception as ex:
            log_event("exit_check_error", {"error": str(ex)})
            return False, ""

    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status."""
        return {
            "auto_trade_enable": self.auto_trade_enable,
            "auto_trade_mode": self.auto_trade_mode,
            "paper_place_orders": self.paper_place_orders,
            "live_executor_available": self.live_executor is not None,
            "recent_orders_count": len(self.recent_orders),
        }
