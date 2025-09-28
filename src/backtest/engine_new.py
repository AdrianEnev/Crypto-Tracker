"""
Refactored backtest engine entry point.
Uses the new modular simulation structure.
"""

import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .simulation import BacktestDataLoader, TradingSimulator, MetricsCalculator
from ..risk import ATRRiskParams


def main():
    """Main entry point for backtesting."""
    parser = argparse.ArgumentParser(description='Run backtest simulation')
    parser.add_argument('--coin', type=str, required=True, help='Coin to backtest')
    parser.add_argument('--timeframe', type=str, default='1d', help='Timeframe for backtest')
    parser.add_argument('--days', type=int, default=365, help='Number of days to backtest')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--save-results', action='store_true', help='Save results to CSV')
    
    args = parser.parse_args()
    
    console = Console()
    
    try:
        # Initialize components
        config_path = args.config or str(Path(__file__).resolve().parents[2] / "config" / "config.yaml")
        data_loader = BacktestDataLoader(config_path)
        simulator = TradingSimulator()
        
        # Load data
        console.print(f"[blue]Loading data for {args.coin}...[/blue]")
        series = data_loader.load_coin_data(args.coin, args.timeframe, args.days)
        
        if series is None:
            console.print(f"[red]Failed to load data for {args.coin}[/red]")
            return 1
        
        closes, highs, lows, times = series
        console.print(f"[green]Loaded {len(closes)} candles[/green]")
        
        # Load configuration
        config = data_loader.load_config()
        tracked_coins = config.get('tracked_coins', {})
        coin_config = tracked_coins.get(args.coin, {})
        threshold = float(coin_config.get('threshold', 0.0))
        
        # Get strategy parameters
        indicators_config = config.get('indicators', {})
        ema_fast = int(indicators_config.get('ema_fast', 20))
        ema_slow = int(indicators_config.get('ema_slow', 50))
        rsi_period = int(indicators_config.get('rsi_period', 14))
        
        # Get decision parameters
        decision_config = config.get('decision', {})
        confidence_thresholds = decision_config.get('confidence_thresholds', {})
        auto_threshold = float(confidence_thresholds.get('auto', 0.8))
        auto_threshold_bear = float(confidence_thresholds.get('auto_bear', auto_threshold))
        
        # Get strategy settings
        strategy_config = config.get('strategy', {})
        use_regime_filter = bool(strategy_config.get('use_regime_filter', False))
        
        # Get volatility gate settings
        vol_gate = strategy_config.get('vol_gate', {})
        vol_min_atr_pct = vol_gate.get('min_atr_pct')
        vol_max_atr_pct = vol_gate.get('max_atr_pct')
        
        # Get risk parameters
        risk_config = config.get('risk', {})
        atr_config = risk_config.get('atr', {})
        atr_params = ATRRiskParams(
            atr_period=int(atr_config.get('period', 14)),
            sl_mult=float(atr_config.get('sl_mult', 1.5)),
            tp_mult=float(atr_config.get('tp_mult', 3.0)),
            trail_mult=float(atr_config.get('trail_mult', 2.0))
        )
        
        # Get execution parameters
        execution_config = config.get('execution', {})
        risk_budget_pct = float(execution_config.get('risk_budget_pct', 0.005))
        fee_bps = int(execution_config.get('fee_bps', 10))
        
        # Run simulation
        console.print("[blue]Running backtest simulation...[/blue]")
        result = simulator.simulate_on_series(
            closes=closes,
            highs=highs,
            lows=lows,
            times=times,
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            rsi_period=rsi_period,
            threshold=threshold,
            auto_threshold=auto_threshold,
            auto_threshold_bear=auto_threshold_bear,
            use_regime_filter=use_regime_filter,
            vol_min_atr_pct=vol_min_atr_pct,
            vol_max_atr_pct=vol_max_atr_pct,
            atr_params=atr_params,
            risk_budget_pct=risk_budget_pct,
            fee_bps=fee_bps,
            timeframe=args.timeframe
        )
        
        # Display results
        console.print("\n[bold blue]Backtest Results[/bold blue]")
        console.print(f"Coin: {args.coin}")
        console.print(f"Timeframe: {args.timeframe}")
        console.print(f"Period: {args.days} days")
        console.print(f"Total Trades: {len(result.trades)}")
        console.print(f"Win Rate: {result.win_rate:.2f}%")
        console.print(f"Profit Factor: {result.profit_factor:.2f}")
        console.print(f"Max Drawdown: {result.max_drawdown:.2f}%")
        console.print(f"CAGR: {result.cagr:.2f}%")
        console.print(f"MAR: {result.mar:.2f}")
        console.print(f"Avg Return: {result.avg_return_pct:.2f}%")
        
        # Display trade details
        if result.trades:
            console.print("\n[bold blue]Trade Details[/bold blue]")
            table = Table()
            table.add_column("Entry", style="cyan")
            table.add_column("Exit", style="cyan")
            table.add_column("Entry Price", style="green")
            table.add_column("Exit Price", style="green")
            table.add_column("P&L %", style="yellow")
            table.add_column("Reason", style="dim")
            
            for trade in result.trades[-10:]:  # Show last 10 trades
                pnl = trade.pnl_pct() or 0.0
                pnl_color = "green" if pnl > 0 else "red" if pnl < 0 else "white"
                table.add_row(
                    str(trade.entry_idx),
                    str(trade.exit_idx or "—"),
                    f"${trade.entry_price:.4f}",
                    f"${trade.exit_price or 0:.4f}",
                    f"[{pnl_color}]{pnl:.2f}%[/{pnl_color}]",
                    trade.reason
                )
            
            console.print(table)
        
        # Save results if requested
        if args.save_results:
            _save_results_to_csv(args.coin, result, args.timeframe, args.days)
            console.print("[green]Results saved to CSV[/green]")
        
        return 0
        
    except Exception as ex:
        console.print(f"[red]Backtest failed: {ex}[/red]")
        return 1


def _save_results_to_csv(coin_id: str, result, timeframe: str, days: int):
    """Save backtest results to CSV file."""
    import csv
    from datetime import datetime
    
    # Create logs directory
    logs_dir = Path(__file__).resolve().parents[3] / "logs" / "backtest"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{coin_id.lower()}_{timeframe}_{days}d_{timestamp}.csv"
    filepath = logs_dir / filename
    
    # Write results
    with open(filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow([
            'coin_id', 'timeframe', 'days', 'total_trades', 'win_rate', 
            'profit_factor', 'max_drawdown', 'cagr', 'mar', 'avg_return_pct'
        ])
        
        # Write summary
        writer.writerow([
            coin_id, timeframe, days, len(result.trades), result.win_rate,
            result.profit_factor, result.max_drawdown, result.cagr, 
            result.mar, result.avg_return_pct
        ])
        
        # Write trades
        if result.trades:
            writer.writerow([])  # Empty row
            writer.writerow(['Trade Details'])
            writer.writerow(['entry_idx', 'exit_idx', 'entry_price', 'exit_price', 'pnl_pct', 'reason'])
            
            for trade in result.trades:
                pnl = trade.pnl_pct() or 0.0
                writer.writerow([
                    trade.entry_idx, trade.exit_idx or '', trade.entry_price,
                    trade.exit_price or 0, pnl, trade.reason
                ])


if __name__ == "__main__":
    exit(main())
