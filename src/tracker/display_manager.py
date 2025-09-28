"""
Display management for the crypto tracker.
Handles UI, status display, and user interface components.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.logger import log_event


class DisplayManager:
    """Manages display and UI components with configurable display modes."""

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.console = Console()

        # Load UI configuration
        self._load_ui_settings()

        # Display state tracking
        self._last_display_time = {}
        self._refresh_intervals = {}

    def _load_ui_settings(self):
        """Load UI configuration settings."""
        try:
            config_data = self.config_manager.load_full_config()
            ui_config = config_data.get("ui", {})

            # Display mode and options
            self.display_mode = ui_config.get("display_mode", "standard")
            self.show_indicators = ui_config.get("show_indicators", True)
            self.show_market_structure = ui_config.get("show_market_structure", False)
            self.show_mtf_confirmation = ui_config.get("show_mtf_confirmation", False)
            self.show_adaptive_baseline = ui_config.get("show_adaptive_baseline", False)
            self.show_oco_details = ui_config.get("show_oco_details", False)
            self.show_vol_gate_status = ui_config.get("show_vol_gate_status", True)
            self.show_regime_filter = ui_config.get("show_regime_filter", True)

            # Decision display options
            decision_config = ui_config.get("decision_display", {})
            self.show_confidence = decision_config.get("show_confidence", True)
            self.show_reasoning = decision_config.get("show_reasoning", True)
            self.show_strategy_details = decision_config.get("show_strategy_details", False)
            self.max_reason_length = decision_config.get("max_reason_length", 100)

            # Table display options
            table_config = ui_config.get("table_display", {})
            self.table_display_enabled = table_config.get("enabled", True)
            self.show_portfolio_summary = table_config.get("show_portfolio_summary", True)
            self.show_risk_summary = table_config.get("show_risk_summary", True)
            self.show_execution_status = table_config.get("show_execution_status", True)
            self.compact_mode = table_config.get("compact_mode", False)
            self.show_pnl_details = table_config.get("show_pnl_details", True)
            self.table_format = table_config.get("table_format", "standard")

            # Output options
            output_config = ui_config.get("output", {})
            self.log_level = output_config.get("log_level", "info")
            self.show_timestamps = output_config.get("show_timestamps", False)
            self.color_output = output_config.get("color_output", True)
            self.progress_bars = output_config.get("progress_bars", True)

            # Refresh intervals
            refresh_config = ui_config.get("refresh", {})
            self.status_table_interval = refresh_config.get("status_table_interval", 60)
            self.decision_display_interval = refresh_config.get("decision_display_interval", 5)
            self.portfolio_summary_interval = refresh_config.get("portfolio_summary_interval", 300)

            # Price formatting
            price_format = ui_config.get("price_format", {})
            self.ui_thresholds = price_format.get("thresholds", [1.0, 0.1, 0.01])
            self.ui_precisions = price_format.get("precisions", [2, 4, 6, 8])

            # Set up display mode presets
            self._apply_display_mode_preset()

        except Exception as ex:
            log_event("ui_settings_load_error", {"error": str(ex)})
            # Fallback to defaults
            self._set_default_settings()

    def _apply_display_mode_preset(self):
        """Apply preset configurations based on display mode."""
        presets = {
            "minimal": {
                "show_indicators": False,
                "show_market_structure": False,
                "show_mtf_confirmation": False,
                "show_adaptive_baseline": False,
                "show_oco_details": False,
                "show_vol_gate_status": False,
                "show_regime_filter": False,
                "show_confidence": False,
                "show_reasoning": False,
                "show_strategy_details": False,
                "show_portfolio_summary": False,
                "show_risk_summary": False,
                "show_execution_status": False,
                "compact_mode": True,
                "max_reason_length": 50,
            },
            "standard": {
                "show_indicators": True,
                "show_market_structure": False,
                "show_mtf_confirmation": False,
                "show_adaptive_baseline": False,
                "show_oco_details": False,
                "show_vol_gate_status": True,
                "show_regime_filter": True,
                "show_confidence": True,
                "show_reasoning": True,
                "show_strategy_details": False,
                "show_portfolio_summary": True,
                "show_risk_summary": True,
                "show_execution_status": True,
                "compact_mode": False,
                "max_reason_length": 100,
            },
            "detailed": {
                "show_indicators": True,
                "show_market_structure": True,
                "show_mtf_confirmation": True,
                "show_adaptive_baseline": True,
                "show_oco_details": False,
                "show_vol_gate_status": True,
                "show_regime_filter": True,
                "show_confidence": True,
                "show_reasoning": True,
                "show_strategy_details": True,
                "show_portfolio_summary": True,
                "show_risk_summary": True,
                "show_execution_status": True,
                "compact_mode": False,
                "max_reason_length": 150,
            },
            "verbose": {
                "show_indicators": True,
                "show_market_structure": True,
                "show_mtf_confirmation": True,
                "show_adaptive_baseline": True,
                "show_oco_details": True,
                "show_vol_gate_status": True,
                "show_regime_filter": True,
                "show_confidence": True,
                "show_reasoning": True,
                "show_strategy_details": True,
                "show_portfolio_summary": True,
                "show_risk_summary": True,
                "show_execution_status": True,
                "compact_mode": False,
                "max_reason_length": 200,
            },
        }

        if self.display_mode in presets:
            preset = presets[self.display_mode]
            for key, value in preset.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    def _set_default_settings(self):
        """Set default settings if config loading fails."""
        self.display_mode = "standard"
        self.show_indicators = True
        self.show_market_structure = False
        self.show_mtf_confirmation = False
        self.show_adaptive_baseline = False
        self.show_oco_details = False
        self.show_vol_gate_status = True
        self.show_regime_filter = True
        self.show_confidence = True
        self.show_reasoning = True
        self.show_strategy_details = False
        self.max_reason_length = 100
        self.table_display_enabled = True
        self.show_portfolio_summary = True
        self.show_risk_summary = True
        self.show_execution_status = True
        self.compact_mode = False
        self.show_pnl_details = True
        self.table_format = "standard"
        self.ui_thresholds = [1.0, 0.1, 0.01]
        self.ui_precisions = [2, 4, 6, 8]

    def format_currency(self, value: float) -> str:
        """Format currency value with appropriate precision."""
        try:
            abs_value = abs(float(value))
            t0, t1, t2 = self.ui_thresholds
            p0, p1, p2, p3 = self.ui_precisions

            if abs_value >= t0:
                return f"${value:,.{p0}f}"
            elif abs_value >= t1:
                return f"${value:,.{p1}f}"
            elif abs_value >= t2:
                return f"${value:,.{p2}f}"
            else:
                return f"${value:,.{p3}f}"
        except Exception:
            return "—"

    def display_status(self, tracked_coins: Dict[str, Any], prices: Dict[str, float]):
        """Display status table for tracked coins with configurable detail."""
        try:
            # If table display is disabled, skip showing status tables
            if not self.table_display_enabled:
                return

            # Check if we should display status based on refresh interval
            current_time = datetime.now(timezone.utc).timestamp()
            last_display = self._last_display_time.get("status", 0)

            if current_time - last_display < self.status_table_interval:
                return

            self._last_display_time["status"] = current_time

            # Display header with mode indicator
            mode_colors = {
                "minimal": "dim",
                "standard": "blue",
                "detailed": "cyan",
                "verbose": "bright_blue",
            }
            mode_color = mode_colors.get(self.display_mode, "blue")
            title = f"Crypto Tracker Status [{self.display_mode.upper()}]"

            if self.table_format == "per_coin":
                self._display_per_coin_status(tracked_coins, prices, title)
            elif self.compact_mode:
                self._display_compact_status(tracked_coins, prices, title)
            else:
                self._display_detailed_status(tracked_coins, prices, title)

        except Exception as ex:
            log_event("display_status_error", {"error": str(ex)})

    def _display_per_coin_status(
        self, tracked_coins: Dict[str, Any], prices: Dict[str, float], title: str
    ):
        """Display individual table for each cryptocurrency."""
        try:
            self.console.print(f"\n[bold blue]{title} - Per Coin View[/bold blue]")

            for coin_id, coin_config in tracked_coins.items():
                if coin_config is None:
                    continue

                # Create individual table for each coin
                coin_table = Table(
                    title=f"{coin_config.name} ({coin_config.symbol.upper()})",
                    show_header=True,
                    header_style="bold magenta",
                    box=None,
                )

                # Define columns based on configuration
                coin_table.add_column("Metric", style="cyan", no_wrap=True)
                coin_table.add_column("Value", style="green", justify="right")

                # Get price data
                price = prices.get(coin_id)
                price_str = self.format_currency(price) if price is not None else "N/A"

                # Add basic information
                coin_table.add_row("Current Price", price_str)
                coin_table.add_row("Threshold", self.format_currency(coin_config.threshold))

                # Calculate and display status
                if price is None:
                    status = "Error"
                    status_color = "yellow"
                else:
                    eps = 1e-9
                    if abs(price - coin_config.threshold) <= eps:
                        status = "Equal to Threshold"
                        status_color = "yellow"
                    elif price < coin_config.threshold:
                        status = "Below Threshold"
                        status_color = "red"
                    else:
                        status = "Above Threshold"
                        status_color = "green"

                coin_table.add_row("Status", f"[{status_color}]{status}[/{status_color}]")

                # Add percentage change from threshold
                if price is not None and coin_config.threshold > 0:
                    change_pct = ((price - coin_config.threshold) / coin_config.threshold) * 100
                    change_color = (
                        "green" if change_pct > 0 else "red" if change_pct < 0 else "yellow"
                    )
                    coin_table.add_row(
                        "Change from Threshold",
                        f"[{change_color}]{change_pct:+.2f}%[/{change_color}]",
                    )

                # Add additional metrics based on configuration
                if self.show_indicators:
                    # Placeholder for indicator values - would be populated from actual data
                    coin_table.add_row("RSI", "—")
                    coin_table.add_row("EMA Fast", "—")
                    coin_table.add_row("EMA Slow", "—")

                if self.show_vol_gate_status:
                    coin_table.add_row("Vol Gate Status", "—")

                if self.show_regime_filter:
                    coin_table.add_row("Regime Filter", "—")

                if self.show_pnl_details:
                    coin_table.add_row("P&L", "0.00")

                # Add timestamp
                from datetime import datetime, timezone

                coin_table.add_row("Last Update", datetime.now(timezone.utc).strftime("%H:%M:%S"))

                # Display the table
                self.console.print(coin_table)

                # Add separator between coins
                if coin_id != list(tracked_coins.keys())[-1]:  # Not the last coin
                    self.console.print("")  # Empty line separator

        except Exception as ex:
            log_event("display_per_coin_status_error", {"error": str(ex)})

    def _display_compact_status(
        self, tracked_coins: Dict[str, Any], prices: Dict[str, float], title: str
    ):
        """Display compact status table."""
        try:
            table = Table(title=title, show_header=True, header_style="bold magenta", box=None)
            table.add_column("Coin", style="cyan", no_wrap=True)
            table.add_column("Price", justify="right", style="green")
            table.add_column("Status", justify="center")

            for coin_id, coin_config in tracked_coins.items():
                if coin_config.disabled:
                    table.add_row(
                        f"{coin_config.name} ({coin_config.symbol.upper()})",
                        "—",
                        "[blue]Disabled[/blue]",
                    )
                    continue

                price = prices.get(coin_id)
                price_str = self.format_currency(price) if price is not None else "N/A"

                if price is None:
                    status = "[yellow]Error"
                else:
                    eps = 1e-9
                    if abs(price - coin_config.threshold) <= eps:
                        status = "[yellow]Equal"
                    elif price < coin_config.threshold:
                        status = "[red]Below"
                    else:
                        status = "[green]Above"

                table.add_row(
                    f"{coin_config.name} ({coin_config.symbol.upper()})", price_str, status
                )

            self.console.print(table)

        except Exception as ex:
            log_event("display_compact_status_error", {"error": str(ex)})

    def _display_detailed_status(
        self, tracked_coins: Dict[str, Any], prices: Dict[str, float], title: str
    ):
        """Display detailed status table."""
        try:
            table = Table(title=title, show_header=True, header_style="bold magenta")
            table.add_column("Coin", style="cyan")
            table.add_column("Price", style="green")
            table.add_column("Threshold", style="yellow")
            table.add_column("Status", style="bold")

            # Add optional columns based on configuration
            if self.show_indicators:
                table.add_column("RSI", justify="center", style="dim")
                table.add_column("EMA", justify="center", style="dim")

            table.add_column("Source", style="dim")
            table.add_column("Last Check", style="dim")
            table.add_column("Signal", style="blue")

            if self.show_pnl_details:
                table.add_column("P&L", style="green")

            table.add_column("Action", style="bold")

            if self.display_mode in ["detailed", "verbose"]:
                table.add_column("Notes", style="dim")

            for coin_id, coin_config in tracked_coins.items():
                if coin_config.disabled:
                    status = "[blue]Disabled"
                    row_data = [
                        f"{coin_config.name} ({coin_config.symbol.upper()})",
                        "—",
                        self.format_currency(coin_config.threshold),
                        status,
                    ]

                    # Add optional columns
                    if self.show_indicators:
                        row_data.extend(["—", "—"])

                    row_data.extend(["—", "—", "—"])

                    if self.show_pnl_details:
                        row_data.append("—")

                    row_data.append("—")

                    if self.display_mode in ["detailed", "verbose"]:
                        row_data.append("Disabled")

                    table.add_row(*row_data)
                    continue

                price = prices.get(coin_id)
                price_str = self.format_currency(price) if price is not None else "N/A"
                threshold_str = self.format_currency(coin_config.threshold)

                if price is None:
                    status = "[yellow]Error"
                else:
                    eps = 1e-9
                    if abs(price - coin_config.threshold) <= eps:
                        status = "[yellow]Equal"
                    elif price < coin_config.threshold:
                        status = "[red]Below"
                    else:
                        status = "[green]Above"

                # Build row data
                row_data = [
                    f"{coin_config.name} ({coin_config.symbol.upper()})",
                    price_str,
                    threshold_str,
                    status,
                ]

                # Add optional columns
                if self.show_indicators:
                    # These would be populated from actual indicator data
                    row_data.extend(["—", "—"])

                row_data.extend(
                    [
                        ("CMC" if price is not None else "CMC"),
                        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                        "threshold_check",
                    ]
                )

                if self.show_pnl_details:
                    row_data.append("0.00" if price is not None else "—")

                row_data.append("Hold")

                if self.display_mode in ["detailed", "verbose"]:
                    row_data.append("None")

                table.add_row(*row_data)

            self.console.print(table)

        except Exception as ex:
            log_event("display_detailed_status_error", {"error": str(ex)})

    def display_portfolio_summary(self, portfolio_summary: Dict[str, Any]):
        """Display portfolio summary information."""
        try:
            self.console.print("\n[bold blue]Portfolio Summary[/bold blue]")
            self.console.print(f"Equity: {self.format_currency(portfolio_summary['equity'])}")
            self.console.print(
                f"Total Exposure: {self.format_currency(portfolio_summary['total_exposure'])}"
            )

            if portfolio_summary["positions"]:
                self.console.print("\n[bold blue]Positions[/bold blue]")
                for symbol, pos_data in portfolio_summary["positions"].items():
                    pnl_color = (
                        "green"
                        if pos_data["pnl_pct"] > 0
                        else "red" if pos_data["pnl_pct"] < 0 else "white"
                    )
                    self.console.print(
                        f"{symbol}: {pos_data['units']:.6f} @ {self.format_currency(pos_data['entry_price'])} "
                        f"[{pnl_color}]{pos_data['pnl_pct']:+.2f}%[/{pnl_color}] "
                        f"({self.format_currency(pos_data['market_value'])})"
                    )
            else:
                self.console.print("\n[dim]No open positions[/dim]")

        except Exception as ex:
            log_event("display_portfolio_error", {"error": str(ex)})

    def display_risk_summary(
        self, risk_factor: float, equity_peak: Optional[float], current_equity: float
    ):
        """Display risk management summary."""
        try:
            self.console.print("\n[bold blue]Risk Management[/bold blue]")
            self.console.print(f"Risk Factor: {risk_factor:.2f}")

            if equity_peak is not None:
                drawdown_pct = max(0.0, (equity_peak - current_equity) / equity_peak * 100.0)
                dd_color = (
                    "red" if drawdown_pct > 5.0 else "yellow" if drawdown_pct > 2.0 else "green"
                )
                self.console.print(
                    f"Drawdown: [{dd_color}]{drawdown_pct:.2f}%[/{dd_color}] (Peak: {self.format_currency(equity_peak)})"
                )

        except Exception as ex:
            log_event("display_risk_error", {"error": str(ex)})

    def display_execution_status(self, execution_status: Dict[str, Any]):
        """Display execution system status."""
        try:
            self.console.print("\n[bold blue]Execution Status[/bold blue]")
            mode_color = "green" if execution_status["auto_trade_mode"] == "live" else "yellow"
            self.console.print(
                f"Mode: [{mode_color}]{execution_status['auto_trade_mode'].upper()}[/{mode_color}]"
            )
            self.console.print(
                f"Auto Trade: {'Enabled' if execution_status['auto_trade_enable'] else 'Disabled'}"
            )
            self.console.print(
                f"Paper Orders: {'Enabled' if execution_status['paper_place_orders'] else 'Disabled'}"
            )
            self.console.print(
                f"Live Executor: {'Available' if execution_status['live_executor_available'] else 'Not Available'}"
            )

        except Exception as ex:
            log_event("display_execution_error", {"error": str(ex)})

    def display_startup_banner(self, providers_active: str, tracked_count: int):
        """Display startup banner."""
        try:
            self.console.print("\n[bold green]🚀 Crypto Tracker Starting[/bold green]")
            self.console.print(f"[blue]Providers: {providers_active}[/blue]")
            self.console.print(f"[blue]Tracking {tracked_count} coins[/blue]")
            self.console.print("[dim]Press Ctrl+C to exit[/dim]\n")

        except Exception as ex:
            log_event("display_banner_error", {"error": str(ex)})

    def display_error(self, message: str):
        """Display error message."""
        self.console.print(f"[red]Error: {message}[/red]")

    def display_warning(self, message: str):
        """Display warning message."""
        self.console.print(f"[yellow]Warning: {message}[/yellow]")

    def display_success(self, message: str):
        """Display success message."""
        self.console.print(f"[green]Success: {message}[/green]")

    def display_info(self, message: str):
        """Display info message."""
        self.console.print(f"[blue]Info: {message}[/blue]")

    def display_decision(self, coin_id: str, decision_data: Dict[str, Any]):
        """Display trading decision information with configurable detail."""
        try:
            signal = decision_data.get("signal", "unknown")
            confidence = decision_data.get("confidence", 0.0)
            action = decision_data.get("action_recommended", "Hold")
            reason = decision_data.get("reason", "")

            self._display_single_decision(
                coin_id,
                {"action": action, "signal": signal, "confidence": confidence, "reason": reason},
            )

        except Exception as ex:
            log_event("display_decision_error", {"error": str(ex)})

    def display_decisions(self, decisions: Dict[str, Any]):
        """Display trading decisions with configurable detail levels."""
        try:
            # Check if we should display decisions based on refresh interval
            current_time = datetime.now(timezone.utc).timestamp()
            last_display = self._last_display_time.get("decisions", 0)

            if current_time - last_display < self.decision_display_interval:
                return

            self._last_display_time["decisions"] = current_time

            if not decisions:
                return

            # If table display is disabled, show line-by-line format (original behavior)
            if not self.table_display_enabled:
                self._display_decisions_line_by_line(decisions)
                return

            # Display decisions in table format
            self._display_decisions_table(decisions)

        except Exception as ex:
            log_event("display_decisions_error", {"error": str(ex)})

    def _display_decisions_line_by_line(self, decisions: Dict[str, Any]):
        """Display decisions in the original line-by-line format."""
        try:
            for coin_id, decision in decisions.items():
                if decision is None:
                    continue

                action = decision.get("action", "Hold")
                signal = decision.get("signal", "unknown")
                confidence = decision.get("confidence", 0.0)
                reason = decision.get("reason", "No reason provided")

                # Color coding for actions
                action_colors = {"Buy": "green", "Sell": "red", "Hold": "yellow", "Close": "red"}
                color = action_colors.get(action, "white")

                # Display decision line
                signal_text = f" Signal: {signal}" if signal != "unknown" else ""
                confidence_text = (
                    f" Confidence: {confidence:.2f}" if isinstance(confidence, (int, float)) else ""
                )

                self.console.print(
                    f"{coin_id}: [{color}]{action}[/{color}]{signal_text}{confidence_text}"
                )

                # Display reason if available
                if reason and reason != "No reason provided":
                    self.console.print(f"  Reason: {reason}")

        except Exception as ex:
            log_event("display_decisions_line_by_line_error", {"error": str(ex)})

    def _display_decisions_table(self, decisions: Dict[str, Any]):
        """Display decisions in table format."""
        try:
            # Display header with mode indicator
            mode_colors = {
                "minimal": "dim",
                "standard": "blue",
                "detailed": "cyan",
                "verbose": "bright_blue",
            }
            mode_color = mode_colors.get(self.display_mode, "blue")
            self.console.print(
                f"\n[bold {mode_color}]Trading Decisions [{self.display_mode.upper()}][/bold {mode_color}]"
            )

            # Create decisions table
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Coin", style="cyan", no_wrap=True)
            table.add_column("Action", justify="center", style="bold")
            table.add_column("Signal", style="blue")

            if self.show_confidence:
                table.add_column("Confidence", justify="center", style="magenta")

            if self.show_reasoning:
                table.add_column("Reason", style="dim")

            # Add rows to table
            for coin_id, decision in decisions.items():
                if decision is None:
                    continue

                action = decision.get("action", "Hold")
                signal = decision.get("signal", "unknown")
                confidence = decision.get("confidence", 0.0)
                reason = decision.get("reason", "No reason provided")

                # Color code actions
                action_colors = {"Buy": "green", "Sell": "red", "Hold": "yellow", "Close": "red"}
                action_color = action_colors.get(action, "white")
                action_display = f"[{action_color}]{action}[/{action_color}]"

                # Build row data
                row_data = [coin_id, action_display, signal]

                if self.show_confidence:
                    if isinstance(confidence, (int, float)):
                        confidence_color = (
                            "green"
                            if confidence >= 0.8
                            else "yellow" if confidence >= 0.5 else "red"
                        )
                        row_data.append(
                            f"[{confidence_color}]{confidence:.2f}[/{confidence_color}]"
                        )
                    else:
                        row_data.append("—")

                if self.show_reasoning:
                    # Truncate reason if too long
                    if len(reason) > self.max_reason_length:
                        reason = reason[: self.max_reason_length] + "..."
                    row_data.append(reason)

                table.add_row(*row_data)

            self.console.print(table)

        except Exception as ex:
            log_event("display_decisions_table_error", {"error": str(ex)})

    def _display_single_decision(self, coin_id: str, decision: Dict[str, Any]):
        """Display a single trading decision with configurable detail."""
        try:
            action = decision.get("action", "Hold")
            signal = decision.get("signal", "unknown")
            confidence = decision.get("confidence", 0.0)
            reason = decision.get("reason", "No reason provided")

            # Color coding for actions
            action_colors = {"Buy": "green", "Sell": "red", "Hold": "yellow", "Close": "red"}
            color = action_colors.get(action, "white")

            # Build decision line
            decision_parts = []
            decision_parts.append(f"[{color}]{coin_id}: {action}[/{color}]")

            # Add signal if enabled
            if signal != "unknown":
                decision_parts.append(f"Signal: {signal}")

            # Add confidence if enabled
            if self.show_confidence and isinstance(confidence, (int, float)):
                conf_str = f"{confidence:.2f}"
                confidence_color = (
                    "green" if confidence >= 0.8 else "yellow" if confidence >= 0.5 else "red"
                )
                decision_parts.append(
                    f"Confidence: [{confidence_color}]{conf_str}[/{confidence_color}]"
                )

            # Display main decision line
            self.console.print(" ".join(decision_parts))

            # Display detailed reasoning if enabled
            if self.show_reasoning and reason and reason != "No reason provided":
                self._display_reasoning(decision)

            # Display strategy details if enabled
            if self.show_strategy_details:
                self._display_strategy_details(coin_id, decision)

        except Exception as ex:
            log_event("display_single_decision_error", {"error": str(ex)})

    def _display_reasoning(self, decision: Dict[str, Any]):
        """Display decision reasoning with configurable detail."""
        try:
            reason = decision.get("reason", "")
            if not reason:
                return

            # Truncate reason if too long
            if len(reason) > self.max_reason_length:
                reason = reason[: self.max_reason_length] + "..."

            # Parse and display structured reasoning
            if self.display_mode in ["detailed", "verbose"]:
                self._display_structured_reasoning(reason)
            else:
                self.console.print(f"  Reason: {reason}")

        except Exception as ex:
            log_event("display_reasoning_error", {"error": str(ex)})

    def _display_structured_reasoning(self, reason: str):
        """Display structured reasoning for detailed/verbose modes."""
        try:
            # Split reason into components
            components = reason.split(",")

            for component in components:
                component = component.strip()
                if not component:
                    continue

                # Color code different types of reasoning
                if "strat=" in component:
                    self.console.print(
                        f"  [cyan]Strategy:[/cyan] {component.replace('strat=', '')}"
                    )
                elif "signal=" in component:
                    self.console.print(
                        f"  [yellow]Signal:[/yellow] {component.replace('signal=', '')}"
                    )
                elif "vol_gate" in component:
                    self.console.print(f"  [red]Vol Gate:[/red] {component}")
                elif "regime" in component:
                    self.console.print(f"  [blue]Regime:[/blue] {component}")
                else:
                    self.console.print(f"  {component}")

        except Exception as ex:
            log_event("display_structured_reasoning_error", {"error": str(ex)})

    def _display_strategy_details(self, coin_id: str, decision: Dict[str, Any]):
        """Display detailed strategy analysis if enabled."""
        try:
            # This would integrate with the original detailed display logic
            # For now, show basic strategy info
            signal = decision.get("signal", "unknown")
            confidence = decision.get("confidence", 0.0)

            if self.show_indicators:
                # Show indicator values if available in decision
                indicators = decision.get("indicators", {})
                if indicators:
                    self.console.print(f"  [dim]Indicators:[/dim] {indicators}")

            if self.show_vol_gate_status:
                vol_gate = decision.get("vol_gate_status", {})
                if vol_gate:
                    self.console.print(f"  [dim]Vol Gate:[/dim] {vol_gate}")

            if self.show_regime_filter:
                regime = decision.get("regime_status", {})
                if regime:
                    self.console.print(f"  [dim]Regime:[/dim] {regime}")

        except Exception as ex:
            log_event("display_strategy_details_error", {"error": str(ex)})

    def clear_screen(self):
        """Clear the console screen."""
        self.console.clear()

    def print(self, *args, **kwargs):
        """Print to console with rich formatting."""
        self.console.print(*args, **kwargs)
