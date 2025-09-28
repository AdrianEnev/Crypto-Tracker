"""
Display management for the crypto tracker.
Handles UI, status display, and user interface components.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table

from src.logger import log_event


class DisplayManager:
    """Manages display and UI components."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.console = Console()
        
        # UI formatting settings
        self.ui_thresholds = [1.0, 0.1, 0.01]
        self.ui_precisions = [2, 4, 6, 8]
        
        self._load_ui_settings()
    
    def _load_ui_settings(self):
        """Load UI formatting settings from configuration."""
        try:
            config_data = self.config_manager.load_full_config()
            ui_config = config_data.get('ui', {})
            price_format = ui_config.get('price_format', {})
            
            self.ui_thresholds = price_format.get('thresholds', [1.0, 0.1, 0.01])
            self.ui_precisions = price_format.get('precisions', [2, 4, 6, 8])
            
        except Exception as ex:
            log_event('ui_settings_load_error', {'error': str(ex)})
    
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
        """Display current status of all tracked coins."""
        try:
            table = Table(title="Crypto Tracker Status")
            table.add_column("Coin", style="cyan")
            table.add_column("Price", style="green")
            table.add_column("Threshold", style="yellow")
            table.add_column("Status", style="bold")
            table.add_column("Source", style="dim")
            table.add_column("Last Check", style="dim")
            table.add_column("Signal", style="blue")
            table.add_column("P&L", style="green")
            table.add_column("Action", style="bold")
            table.add_column("Notes", style="dim")
            
            for coin_id, coin_config in tracked_coins.items():
                if coin_config.disabled:
                    status = "[blue]Disabled"
                    table.add_row(
                        f"{coin_config.name} ({coin_config.symbol.upper()})",
                        "—",
                        self.format_currency(coin_config.threshold),
                        status,
                        "—",
                        "—",
                        "—",
                        "—",
                        "—",
                        "None",
                    )
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
                
                table.add_row(
                    f"{coin_config.name} ({coin_config.symbol.upper()})",
                    price_str,
                    threshold_str,
                    status,
                    ("CMC" if price is not None else "CMC"),
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "threshold_check",
                    ("0.00" if price is not None else "—"),
                    "Hold",
                    "None",
                )
            
            self.console.print(table)
            
        except Exception as ex:
            log_event('display_status_error', {'error': str(ex)})
    
    def display_portfolio_summary(self, portfolio_summary: Dict[str, Any]):
        """Display portfolio summary information."""
        try:
            self.console.print("\n[bold blue]Portfolio Summary[/bold blue]")
            self.console.print(f"Equity: {self.format_currency(portfolio_summary['equity'])}")
            self.console.print(f"Total Exposure: {self.format_currency(portfolio_summary['total_exposure'])}")
            
            if portfolio_summary['positions']:
                self.console.print("\n[bold blue]Positions[/bold blue]")
                for symbol, pos_data in portfolio_summary['positions'].items():
                    pnl_color = "green" if pos_data['pnl_pct'] > 0 else "red" if pos_data['pnl_pct'] < 0 else "white"
                    self.console.print(
                        f"{symbol}: {pos_data['units']:.6f} @ {self.format_currency(pos_data['entry_price'])} "
                        f"[{pnl_color}]{pos_data['pnl_pct']:+.2f}%[/{pnl_color}] "
                        f"({self.format_currency(pos_data['market_value'])})"
                    )
            else:
                self.console.print("\n[dim]No open positions[/dim]")
                
        except Exception as ex:
            log_event('display_portfolio_error', {'error': str(ex)})
    
    def display_risk_summary(self, risk_factor: float, equity_peak: Optional[float], current_equity: float):
        """Display risk management summary."""
        try:
            self.console.print("\n[bold blue]Risk Management[/bold blue]")
            self.console.print(f"Risk Factor: {risk_factor:.2f}")
            
            if equity_peak is not None:
                drawdown_pct = max(0.0, (equity_peak - current_equity) / equity_peak * 100.0)
                dd_color = "red" if drawdown_pct > 5.0 else "yellow" if drawdown_pct > 2.0 else "green"
                self.console.print(f"Drawdown: [{dd_color}]{drawdown_pct:.2f}%[/{dd_color}] (Peak: {self.format_currency(equity_peak)})")
            
        except Exception as ex:
            log_event('display_risk_error', {'error': str(ex)})
    
    def display_execution_status(self, execution_status: Dict[str, Any]):
        """Display execution system status."""
        try:
            self.console.print("\n[bold blue]Execution Status[/bold blue]")
            mode_color = "green" if execution_status['auto_trade_mode'] == 'live' else "yellow"
            self.console.print(f"Mode: [{mode_color}]{execution_status['auto_trade_mode'].upper()}[/{mode_color}]")
            self.console.print(f"Auto Trade: {'Enabled' if execution_status['auto_trade_enable'] else 'Disabled'}")
            self.console.print(f"Paper Orders: {'Enabled' if execution_status['paper_place_orders'] else 'Disabled'}")
            self.console.print(f"Live Executor: {'Available' if execution_status['live_executor_available'] else 'Not Available'}")
            
        except Exception as ex:
            log_event('display_execution_error', {'error': str(ex)})
    
    def display_startup_banner(self, providers_active: str, tracked_count: int):
        """Display startup banner."""
        try:
            self.console.print("\n[bold green]🚀 Crypto Tracker Starting[/bold green]")
            self.console.print(f"[blue]Providers: {providers_active}[/blue]")
            self.console.print(f"[blue]Tracking {tracked_count} coins[/blue]")
            self.console.print("[dim]Press Ctrl+C to exit[/dim]\n")
            
        except Exception as ex:
            log_event('display_banner_error', {'error': str(ex)})
    
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
        """Display trading decision information."""
        try:
            signal = decision_data.get('signal', 'unknown')
            confidence = decision_data.get('confidence', 0.0)
            action = decision_data.get('action_recommended', 'Hold')
            reason = decision_data.get('reason', '')
            
            action_color = "green" if action == "Buy" else "red" if action == "Sell" else "yellow"
            confidence_color = "green" if confidence >= 0.8 else "yellow" if confidence >= 0.5 else "red"
            
            self.console.print(
                f"[bold]{coin_id}[/bold]: [{action_color}]{action}[/{action_color}] "
                f"(Signal: {signal}, Confidence: [{confidence_color}]{confidence:.2f}[/{confidence_color}])"
            )
            if reason:
                self.console.print(f"  Reason: {reason}")
                
        except Exception as ex:
            log_event('display_decision_error', {'error': str(ex)})
    
    def clear_screen(self):
        """Clear the console screen."""
        self.console.clear()
    
    def print(self, *args, **kwargs):
        """Print to console with rich formatting."""
        self.console.print(*args, **kwargs)
