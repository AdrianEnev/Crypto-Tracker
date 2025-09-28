"""
Main optimization runner for backtest optimization.
"""

import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.progress import track

from .config_loader import ConfigLoader
from .data_fetcher import DataFetcher
from .parameter_generator import ParameterGenerator
from .evaluator import ParameterEvaluator, EvalResult


class OptimizationRunner:
    """Main class for running parameter optimization."""
    
    def __init__(self, config_path: str = None):
        self.config_loader = ConfigLoader(config_path)
        self.data_fetcher = DataFetcher(self.config_loader)
        self.parameter_generator = ParameterGenerator(self.config_loader)
        self.evaluator = ParameterEvaluator(self.config_loader)
        self.console = Console()
    
    def optimize_coin(self, coin_id: str, max_combinations: int = None) -> List[EvalResult]:
        """Optimize parameters for a single coin."""
        try:
            cfg_all = self.config_loader.load_config()
            optimize_config = cfg_all.get("optimize", {})
            
            # Get optimization settings
            timeframe = str(cfg_all.get("data", {}).get("timeframe", "1d"))
            days = int(cfg_all.get("data", {}).get("days", 365))
            folds = int(optimize_config.get("folds", 3))
            use_price_as_threshold = bool(optimize_config.get("use_price_as_threshold", True))
            disable_regime_filter = bool(optimize_config.get("disable_regime_filter", False))
            disable_vol_gate = bool(optimize_config.get("disable_vol_gate", False))
            
            # Skip symbols if configured
            skip_symbols = optimize_config.get("skip_symbols", [])
            tracked_coins = cfg_all.get("tracked_coins", {})
            coin_config = tracked_coins.get(coin_id, {})
            if coin_config.get("symbol", "").upper() in skip_symbols:
                self.console.print(f"[yellow]Skipping {coin_id} (in skip_symbols)[/yellow]")
                return []
            
            # Fetch data
            self.console.print(f"[blue]Fetching data for {coin_id}...[/blue]")
            series = self.data_fetcher.fetch_series(coin_id, timeframe, days)
            if series is None:
                self.console.print(f"[red]Failed to fetch data for {coin_id}[/red]")
                return []
            
            closes, highs, lows, times = series
            self.console.print(f"[green]Loaded {len(closes)} candles for {coin_id}[/green]")
            
            # Generate parameter combinations
            total_combinations = self.parameter_generator.get_total_combinations(coin_id)
            if max_combinations:
                total_combinations = min(total_combinations, max_combinations)
            
            self.console.print(f"[blue]Testing {total_combinations} parameter combinations for {coin_id}...[/blue]")
            
            # Run optimization
            results = []
            combinations = self.parameter_generator.generate_parameter_combinations(coin_id)
            
            for i, params in enumerate(track(combinations, description=f"Optimizing {coin_id}")):
                if max_combinations and i >= max_combinations:
                    break
                
                try:
                    # Evaluate parameters
                    result = self.evaluator.evaluate_parameters(
                        coin_id=coin_id,
                        closes=closes,
                        highs=highs,
                        lows=lows,
                        times=times,
                        params=params,
                        timeframe=timeframe,
                        use_price_as_threshold=use_price_as_threshold,
                        disable_regime_filter=disable_regime_filter,
                        disable_vol_gate=disable_vol_gate
                    )
                    
                    results.append(result)
                    
                except Exception as ex:
                    self.console.print(f"[red]Error evaluating parameters for {coin_id}: {ex}[/red]")
                    continue
            
            # Sort results by MAR (risk-adjusted return)
            results.sort(key=lambda x: x.mar, reverse=True)
            
            # Save results
            self._save_results(coin_id, results)
            
            # Display top results
            self._display_top_results(coin_id, results[:5])
            
            return results
            
        except Exception as ex:
            self.console.print(f"[red]Optimization failed for {coin_id}: {ex}[/red]")
            return []
    
    def optimize_all_coins(self, max_combinations_per_coin: int = None) -> Dict[str, List[EvalResult]]:
        """Optimize parameters for all tracked coins."""
        try:
            cfg_all = self.config_loader.load_config()
            tracked_coins = cfg_all.get("tracked_coins", {})
            
            results = {}
            
            for coin_id in tracked_coins.keys():
                try:
                    coin_results = self.optimize_coin(coin_id, max_combinations_per_coin)
                    results[coin_id] = coin_results
                except Exception as ex:
                    self.console.print(f"[red]Failed to optimize {coin_id}: {ex}[/red]")
                    continue
            
            return results
            
        except Exception as ex:
            self.console.print(f"[red]Global optimization failed: {ex}[/red]")
            return {}
    
    def _save_results(self, coin_id: str, results: List[EvalResult]):
        """Save optimization results to CSV file."""
        try:
            # Create logs directory if it doesn't exist
            logs_dir = Path(__file__).resolve().parents[4] / "logs" / "backtest"
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            filename = f"optimizer_{coin_id.lower()}.csv"
            filepath = logs_dir / filename
            
            # Write results to CSV
            with open(filepath, 'w', newline='') as csvfile:
                if not results:
                    return
                
                # Get fieldnames from first result
                fieldnames = list(results[0].params.keys()) + [
                    'trades', 'win_rate', 'profit_factor', 'max_drawdown', 'cagr', 'mar', 'avg_return_pct'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in results:
                    row = result.params.copy()
                    row.update({
                        'trades': result.trades,
                        'win_rate': result.win_rate,
                        'profit_factor': result.profit_factor,
                        'max_drawdown': result.max_drawdown,
                        'cagr': result.cagr,
                        'mar': result.mar,
                        'avg_return_pct': result.avg_return_pct
                    })
                    writer.writerow(row)
            
            self.console.print(f"[green]Results saved to {filepath}[/green]")
            
        except Exception as ex:
            self.console.print(f"[red]Failed to save results for {coin_id}: {ex}[/red]")
    
    def _display_top_results(self, coin_id: str, top_results: List[EvalResult]):
        """Display top optimization results."""
        if not top_results:
            self.console.print(f"[yellow]No results for {coin_id}[/yellow]")
            return
        
        self.console.print(f"\n[bold blue]Top 5 results for {coin_id}:[/bold blue]")
        
        for i, result in enumerate(top_results, 1):
            self.console.print(f"\n[bold]#{i}[/bold]")
            self.console.print(f"  Parameters: {result.params}")
            self.console.print(f"  Trades: {result.trades}")
            self.console.print(f"  Win Rate: {result.win_rate:.2f}%")
            self.console.print(f"  Profit Factor: {result.profit_factor:.2f}")
            self.console.print(f"  Max Drawdown: {result.max_drawdown:.2f}%")
            self.console.print(f"  CAGR: {result.cagr:.2f}%")
            self.console.print(f"  MAR: {result.mar:.2f}")
            self.console.print(f"  Avg Return: {result.avg_return_pct:.2f}%")
    
    def run_walk_forward_optimization(self, coin_id: str, folds: int = 3) -> List[EvalResult]:
        """Run walk-forward optimization for a coin."""
        try:
            cfg_all = self.config_loader.load_config()
            timeframe = str(cfg_all.get("data", {}).get("timeframe", "1d"))
            days = int(cfg_all.get("data", {}).get("days", 365))
            
            # Fetch full dataset
            series = self.data_fetcher.fetch_series(coin_id, timeframe, days)
            if series is None:
                return []
            
            closes, highs, lows, times = series
            n = len(closes)
            
            # Generate walk-forward splits
            splits = self._generate_walk_forward_splits(n, folds)
            
            all_results = []
            
            for i, (train_start, train_end, test_start, test_end) in enumerate(splits):
                self.console.print(f"[blue]Walk-forward fold {i+1}/{len(splits)} for {coin_id}[/blue]")
                
                # Split data
                train_closes = closes[train_start:train_end]
                train_highs = highs[train_start:train_end]
                train_lows = lows[train_start:train_end]
                train_times = times[train_start:train_end]
                
                test_closes = closes[test_start:test_end]
                test_highs = highs[test_start:test_end]
                test_lows = lows[test_start:test_end]
                test_times = times[test_start:test_end]
                
                # Optimize on training data
                train_results = []
                combinations = self.parameter_generator.generate_parameter_combinations(coin_id)
                
                for params in combinations:
                    result = self.evaluator.evaluate_parameters(
                        coin_id=coin_id,
                        closes=train_closes,
                        highs=train_highs,
                        lows=train_lows,
                        times=train_times,
                        params=params,
                        timeframe=timeframe
                    )
                    train_results.append(result)
                
                # Get best parameters
                if train_results:
                    best_params = max(train_results, key=lambda x: x.mar).params
                    
                    # Test on out-of-sample data
                    test_result = self.evaluator.evaluate_parameters(
                        coin_id=coin_id,
                        closes=test_closes,
                        highs=test_highs,
                        lows=test_lows,
                        times=test_times,
                        params=best_params,
                        timeframe=timeframe
                    )
                    
                    test_result.params['fold'] = i + 1
                    all_results.append(test_result)
            
            return all_results
            
        except Exception as ex:
            self.console.print(f"[red]Walk-forward optimization failed for {coin_id}: {ex}[/red]")
            return []
    
    def _generate_walk_forward_splits(self, n: int, folds: int = 3):
        """Generate walk-forward validation splits."""
        if folds < 2:
            folds = 2
        
        seg = n // folds
        splits = []
        
        for i in range(folds - 1):
            train_start = i * seg
            train_end = (i + 1) * seg
            test_start = train_end
            test_end = min(n, test_start + seg)
            
            if test_end - test_start >= max(60, seg // 4):  # ensure enough bars
                splits.append((train_start, train_end, test_start, test_end))
        
        return splits
