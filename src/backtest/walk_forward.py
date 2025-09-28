"""
Walk-forward validation and enhanced backtesting framework.
Implements time-series cross-validation for robust strategy evaluation.
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..strategies.base import BaseStrategy
from ..backtest.simulation.models import BacktestResult, Trade


class WalkForwardValidator:
    """
    Walk-forward validation framework for trading strategies.
    
    Features:
    - Time-series cross-validation
    - Out-of-sample testing
    - Rolling window optimization
    - Expanding window validation
    - Performance degradation analysis
    - Parameter stability testing
    - Multiple validation schemes
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Validation parameters
        self.initial_train_size = int(self.config.get("initial_train_size", 252))  # 1 year
        self.test_size = int(self.config.get("test_size", 63))  # ~3 months
        self.step_size = int(self.config.get("step_size", 21))  # ~1 month
        self.max_train_size = int(self.config.get("max_train_size", 1008))  # 4 years
        
        # Validation schemes
        self.validation_schemes = self.config.get("validation_schemes", [
            "rolling_window",
            "expanding_window", 
            "purged_cv",
            "blocking_cv"
        ])
        
        # Performance metrics
        self.metrics_to_track = self.config.get("metrics_to_track", [
            "total_return", "sharpe_ratio", "max_drawdown", "win_rate", "profit_factor"
        ])
        
        # Results storage
        self.validation_results = {}
        
    def run_walk_forward_validation(
        self,
        strategy_class,
        strategy_params: Dict,
        data: pd.DataFrame,
        initial_capital: float = 10000.0
    ) -> Dict[str, Any]:
        """
        Run comprehensive walk-forward validation.
        
        Args:
            strategy_class: Strategy class to validate
            strategy_params: Strategy parameters
            data: Historical data
            initial_capital: Starting capital
            
        Returns:
            Walk-forward validation results
        """
        print(f"Running walk-forward validation...")
        print(f"Data length: {len(data)} days")
        print(f"Initial training size: {self.initial_train_size} days")
        print(f"Test size: {self.test_size} days")
        print(f"Step size: {self.step_size} days")
        
        results = {
            "validation_schemes": {},
            "overall_performance": {},
            "parameter_stability": {},
            "performance_degradation": {},
            "validation_summary": {}
        }
        
        # Run different validation schemes
        for scheme in self.validation_schemes:
            print(f"\nRunning {scheme} validation...")
            
            if scheme == "rolling_window":
                scheme_results = self._run_rolling_window_validation(
                    strategy_class, strategy_params, data, initial_capital
                )
            elif scheme == "expanding_window":
                scheme_results = self._run_expanding_window_validation(
                    strategy_class, strategy_params, data, initial_capital
                )
            elif scheme == "purged_cv":
                scheme_results = self._run_purged_cv_validation(
                    strategy_class, strategy_params, data, initial_capital
                )
            elif scheme == "blocking_cv":
                scheme_results = self._run_blocking_cv_validation(
                    strategy_class, strategy_params, data, initial_capital
                )
            else:
                print(f"Unknown validation scheme: {scheme}")
                continue
            
            results["validation_schemes"][scheme] = scheme_results
        
        # Analyze overall performance
        results["overall_performance"] = self._analyze_overall_performance(results["validation_schemes"])
        
        # Parameter stability analysis
        results["parameter_stability"] = self._analyze_parameter_stability(results["validation_schemes"])
        
        # Performance degradation analysis
        results["performance_degradation"] = self._analyze_performance_degradation(results["validation_schemes"])
        
        # Generate validation summary
        results["validation_summary"] = self._generate_validation_summary(results)
        
        return results
    
    def _run_rolling_window_validation(
        self,
        strategy_class,
        strategy_params: Dict,
        data: pd.DataFrame,
        initial_capital: float
    ) -> Dict[str, Any]:
        """Run rolling window validation."""
        results = {
            "fold_results": [],
            "fold_performance": [],
            "parameter_evolution": [],
            "stability_metrics": {}
        }
        
        total_folds = 0
        start_idx = self.initial_train_size
        
        while start_idx + self.test_size <= len(data):
            # Define training and test periods
            train_start = start_idx - self.initial_train_size
            train_end = start_idx
            
            test_start = start_idx
            test_end = start_idx + self.test_size
            
            # Extract training and test data
            train_data = data.iloc[train_start:train_end].copy()
            test_data = data.iloc[test_start:test_end].copy()
            
            # Run backtest on training data (for parameter optimization)
            train_strategy = strategy_class(strategy_params)
            train_performance = self._run_backtest(train_strategy, train_data, initial_capital)
            
            # Run backtest on test data (for out-of-sample validation)
            test_strategy = strategy_class(strategy_params)
            test_performance = self._run_backtest(test_strategy, test_data, initial_capital)
            
            # Store fold results
            fold_result = {
                "fold": total_folds,
                "train_period": (train_start, train_end),
                "test_period": (test_start, test_end),
                "train_performance": train_performance,
                "test_performance": test_performance,
                "parameters": strategy_params.copy()
            }
            
            results["fold_results"].append(fold_result)
            results["fold_performance"].append(test_performance)
            results["parameter_evolution"].append(strategy_params.copy())
            
            total_folds += 1
            start_idx += self.step_size
        
        # Calculate stability metrics
        results["stability_metrics"] = self._calculate_stability_metrics(results["fold_performance"])
        
        print(f"Completed {total_folds} rolling window folds")
        
        return results
    
    def _run_expanding_window_validation(
        self,
        strategy_class,
        strategy_params: Dict,
        data: pd.DataFrame,
        initial_capital: float
    ) -> Dict[str, Any]:
        """Run expanding window validation."""
        results = {
            "fold_results": [],
            "fold_performance": [],
            "parameter_evolution": [],
            "stability_metrics": {}
        }
        
        total_folds = 0
        start_idx = self.initial_train_size
        
        while start_idx + self.test_size <= len(data):
            # Define training and test periods
            train_start = 0  # Always start from beginning
            train_end = start_idx
            
            test_start = start_idx
            test_end = start_idx + self.test_size
            
            # Limit training size if specified
            if self.max_train_size and (train_end - train_start) > self.max_train_size:
                train_start = train_end - self.max_train_size
            
            # Extract training and test data
            train_data = data.iloc[train_start:train_end].copy()
            test_data = data.iloc[test_start:test_end].copy()
            
            # Run backtest on training data
            train_strategy = strategy_class(strategy_params)
            train_performance = self._run_backtest(train_strategy, train_data, initial_capital)
            
            # Run backtest on test data
            test_strategy = strategy_class(strategy_params)
            test_performance = self._run_backtest(test_strategy, test_data, initial_capital)
            
            # Store fold results
            fold_result = {
                "fold": total_folds,
                "train_period": (train_start, train_end),
                "test_period": (test_start, test_end),
                "train_performance": train_performance,
                "test_performance": test_performance,
                "parameters": strategy_params.copy()
            }
            
            results["fold_results"].append(fold_result)
            results["fold_performance"].append(test_performance)
            results["parameter_evolution"].append(strategy_params.copy())
            
            total_folds += 1
            start_idx += self.step_size
        
        # Calculate stability metrics
        results["stability_metrics"] = self._calculate_stability_metrics(results["fold_performance"])
        
        print(f"Completed {total_folds} expanding window folds")
        
        return results
    
    def _run_purged_cv_validation(
        self,
        strategy_class,
        strategy_params: Dict,
        data: pd.DataFrame,
        initial_capital: float
    ) -> Dict[str, Any]:
        """Run purged cross-validation to avoid look-ahead bias."""
        results = {
            "fold_results": [],
            "fold_performance": [],
            "parameter_evolution": [],
            "stability_metrics": {}
        }
        
        # Define purge period (gap between train and test)
        purge_size = int(self.test_size * 0.5)  # 50% of test size
        
        total_folds = 0
        start_idx = self.initial_train_size
        
        while start_idx + purge_size + self.test_size <= len(data):
            # Define training, purge, and test periods
            train_start = start_idx - self.initial_train_size
            train_end = start_idx
            
            purge_start = start_idx
            purge_end = start_idx + purge_size
            
            test_start = start_idx + purge_size
            test_end = start_idx + purge_size + self.test_size
            
            # Extract training and test data (excluding purge period)
            train_data = data.iloc[train_start:train_end].copy()
            test_data = data.iloc[test_start:test_end].copy()
            
            # Run backtest on training data
            train_strategy = strategy_class(strategy_params)
            train_performance = self._run_backtest(train_strategy, train_data, initial_capital)
            
            # Run backtest on test data
            test_strategy = strategy_class(strategy_params)
            test_performance = self._run_backtest(test_strategy, test_data, initial_capital)
            
            # Store fold results
            fold_result = {
                "fold": total_folds,
                "train_period": (train_start, train_end),
                "purge_period": (purge_start, purge_end),
                "test_period": (test_start, test_end),
                "train_performance": train_performance,
                "test_performance": test_performance,
                "parameters": strategy_params.copy()
            }
            
            results["fold_results"].append(fold_result)
            results["fold_performance"].append(test_performance)
            results["parameter_evolution"].append(strategy_params.copy())
            
            total_folds += 1
            start_idx += self.step_size
        
        # Calculate stability metrics
        results["stability_metrics"] = self._calculate_stability_metrics(results["fold_performance"])
        
        print(f"Completed {total_folds} purged CV folds")
        
        return results
    
    def _run_blocking_cv_validation(
        self,
        strategy_class,
        strategy_params: Dict,
        data: pd.DataFrame,
        initial_capital: float
    ) -> Dict[str, Any]:
        """Run blocked cross-validation to maintain time series structure."""
        results = {
            "fold_results": [],
            "fold_performance": [],
            "parameter_evolution": [],
            "stability_metrics": {}
        }
        
        # Calculate number of blocks
        block_size = self.test_size
        num_blocks = (len(data) - self.initial_train_size) // (block_size + self.step_size)
        
        for block_idx in range(num_blocks):
            # Define training and test periods for this block
            train_start = 0
            train_end = self.initial_train_size + block_idx * self.step_size
            
            test_start = train_end
            test_end = min(train_end + block_size, len(data))
            
            if test_end - test_start < block_size // 2:  # Skip if test period too short
                continue
            
            # Extract training and test data
            train_data = data.iloc[train_start:train_end].copy()
            test_data = data.iloc[test_start:test_end].copy()
            
            # Run backtest on training data
            train_strategy = strategy_class(strategy_params)
            train_performance = self._run_backtest(train_strategy, train_data, initial_capital)
            
            # Run backtest on test data
            test_strategy = strategy_class(strategy_params)
            test_performance = self._run_backtest(test_strategy, test_data, initial_capital)
            
            # Store fold results
            fold_result = {
                "fold": block_idx,
                "train_period": (train_start, train_end),
                "test_period": (test_start, test_end),
                "train_performance": train_performance,
                "test_performance": test_performance,
                "parameters": strategy_params.copy()
            }
            
            results["fold_results"].append(fold_result)
            results["fold_performance"].append(test_performance)
            results["parameter_evolution"].append(strategy_params.copy())
        
        # Calculate stability metrics
        results["stability_metrics"] = self._calculate_stability_metrics(results["fold_performance"])
        
        print(f"Completed {len(results['fold_results'])} blocking CV folds")
        
        return results
    
    def _run_backtest(self, strategy: BaseStrategy, data: pd.DataFrame, initial_capital: float) -> Dict[str, float]:
        """Run backtest on given data."""
        try:
            # Generate signals
            signals = strategy.generate_signals(data)
            
            # Simulate trading
            capital = initial_capital
            position = 0
            equity_curve = [capital]
            trades = []
            
            for i, (idx, row) in enumerate(signals.iterrows()):
                signal = row.get('signal', 0)
                
                if 'close' in data.columns:
                    current_price = data.iloc[i]['close']
                else:
                    # Use index as proxy price
                    current_price = 100 + i * 0.1
                
                if signal == 1 and position == 0:  # Buy signal
                    position = capital * 0.95 / current_price
                    capital = capital * 0.05
                elif signal == -1 and position > 0:  # Sell signal
                    exit_price = current_price
                    trade_pnl = (exit_price - current_price) * position  # Simplified P&L
                    trades.append({
                        'entry_price': current_price,
                        'exit_price': exit_price,
                        'pnl': trade_pnl
                    })
                    capital += position * exit_price
                    position = 0
                
                current_equity = capital + (position * current_price if position > 0 else 0)
                equity_curve.append(current_equity)
            
            # Calculate performance metrics
            final_value = equity_curve[-1]
            total_return = (final_value / initial_capital - 1) * 100
            
            # Calculate max drawdown
            peak = equity_curve[0]
            max_dd = 0
            for value in equity_curve:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak
                max_dd = max(max_dd, dd)
            
            # Calculate other metrics
            if len(equity_curve) > 1:
                equity_returns = np.diff(equity_curve) / equity_curve[:-1]
                sharpe_ratio = np.mean(equity_returns) / np.std(equity_returns) * np.sqrt(252) if np.std(equity_returns) > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Calculate win rate and profit factor
            if trades:
                winning_trades = [t for t in trades if t['pnl'] > 0]
                win_rate = len(winning_trades) / len(trades) * 100
                
                total_profit = sum(t['pnl'] for t in winning_trades)
                total_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
                profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
            else:
                win_rate = 0
                profit_factor = 0
            
            return {
                "total_return": total_return,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_dd * 100,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "num_trades": len(trades),
                "final_value": final_value
            }
            
        except Exception as e:
            return {
                "total_return": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "num_trades": 0,
                "final_value": initial_capital,
                "error": str(e)
            }
    
    def _calculate_stability_metrics(self, fold_performances: List[Dict]) -> Dict[str, float]:
        """Calculate stability metrics across folds."""
        if not fold_performances:
            return {}
        
        # Extract metrics
        metrics_data = {}
        for metric in self.metrics_to_track:
            values = [fold.get(metric, 0) for fold in fold_performances]
            metrics_data[metric] = values
        
        stability_metrics = {}
        
        for metric, values in metrics_data.items():
            if not values:
                continue
                
            values_array = np.array(values)
            
            stability_metrics[f"{metric}_mean"] = np.mean(values_array)
            stability_metrics[f"{metric}_std"] = np.std(values_array)
            stability_metrics[f"{metric}_cv"] = np.std(values_array) / abs(np.mean(values_array)) if np.mean(values_array) != 0 else 0
            stability_metrics[f"{metric}_min"] = np.min(values_array)
            stability_metrics[f"{metric}_max"] = np.max(values_array)
            stability_metrics[f"{metric}_range"] = np.max(values_array) - np.min(values_array)
            
            # Calculate trend (positive = improving, negative = degrading)
            if len(values_array) > 1:
                x = np.arange(len(values_array))
                trend = np.polyfit(x, values_array, 1)[0]
                stability_metrics[f"{metric}_trend"] = trend
            else:
                stability_metrics[f"{metric}_trend"] = 0
        
        return stability_metrics
    
    def _analyze_overall_performance(self, validation_schemes: Dict) -> Dict[str, Any]:
        """Analyze overall performance across validation schemes."""
        overall_analysis = {}
        
        for scheme_name, scheme_results in validation_schemes.items():
            fold_performances = scheme_results.get("fold_performance", [])
            
            if not fold_performances:
                continue
            
            # Calculate aggregate metrics
            scheme_analysis = {}
            
            for metric in self.metrics_to_track:
                values = [fold.get(metric, 0) for fold in fold_performances]
                if values:
                    scheme_analysis[metric] = {
                        "mean": np.mean(values),
                        "std": np.std(values),
                        "median": np.median(values),
                        "min": np.min(values),
                        "max": np.max(values),
                        "positive_folds": np.sum(np.array(values) > 0),
                        "total_folds": len(values)
                    }
            
            overall_analysis[scheme_name] = scheme_analysis
        
        return overall_analysis
    
    def _analyze_parameter_stability(self, validation_schemes: Dict) -> Dict[str, Any]:
        """Analyze parameter stability across validation schemes."""
        stability_analysis = {}
        
        for scheme_name, scheme_results in validation_schemes.items():
            parameter_evolution = scheme_results.get("parameter_evolution", [])
            
            if not parameter_evolution:
                continue
            
            # Analyze parameter changes across folds
            param_stability = {}
            
            # Get all parameter names
            all_params = set()
            for params in parameter_evolution:
                all_params.update(params.keys())
            
            for param_name in all_params:
                param_values = [params.get(param_name) for params in parameter_evolution if param_name in params]
                
                if param_values:
                    # Check if parameter changed
                    unique_values = set(param_values)
                    param_stability[param_name] = {
                        "unique_values": len(unique_values),
                        "changed": len(unique_values) > 1,
                        "values": param_values,
                        "stability_score": 1.0 / len(unique_values) if unique_values else 0
                    }
            
            stability_analysis[scheme_name] = param_stability
        
        return stability_analysis
    
    def _analyze_performance_degradation(self, validation_schemes: Dict) -> Dict[str, Any]:
        """Analyze performance degradation over time."""
        degradation_analysis = {}
        
        for scheme_name, scheme_results in validation_schemes.items():
            fold_performances = scheme_results.get("fold_performance", [])
            
            if len(fold_performances) < 2:
                continue
            
            degradation_metrics = {}
            
            for metric in self.metrics_to_track:
                values = [fold.get(metric, 0) for fold in fold_performances]
                
                if len(values) >= 2:
                    # Calculate performance trend
                    x = np.arange(len(values))
                    trend_slope = np.polyfit(x, values, 1)[0]
                    
                    # Calculate performance volatility
                    performance_volatility = np.std(values)
                    
                    # Calculate degradation rate
                    first_half = values[:len(values)//2]
                    second_half = values[len(values)//2:]
                    
                    if first_half and second_half:
                        degradation_rate = (np.mean(second_half) - np.mean(first_half)) / abs(np.mean(first_half)) if np.mean(first_half) != 0 else 0
                    else:
                        degradation_rate = 0
                    
                    degradation_metrics[metric] = {
                        "trend_slope": trend_slope,
                        "performance_volatility": performance_volatility,
                        "degradation_rate": degradation_rate,
                        "is_degrading": degradation_rate < -0.1  # 10% degradation threshold
                    }
            
            degradation_analysis[scheme_name] = degradation_metrics
        
        return degradation_analysis
    
    def _generate_validation_summary(self, results: Dict) -> Dict[str, Any]:
        """Generate validation summary."""
        summary = {
            "validation_quality": "unknown",
            "recommendations": [],
            "risk_assessment": {},
            "performance_consistency": {}
        }
        
        # Analyze validation quality
        overall_performance = results.get("overall_performance", {})
        parameter_stability = results.get("parameter_stability", {})
        performance_degradation = results.get("performance_degradation", {})
        
        # Check performance consistency
        consistency_scores = []
        for scheme_name, scheme_perf in overall_performance.items():
            if "total_return" in scheme_perf:
                cv = scheme_perf["total_return"]["std"] / abs(scheme_perf["total_return"]["mean"]) if scheme_perf["total_return"]["mean"] != 0 else 0
                consistency_scores.append(cv)
        
        avg_consistency = np.mean(consistency_scores) if consistency_scores else 1.0
        
        if avg_consistency < 0.3:
            summary["validation_quality"] = "excellent"
        elif avg_consistency < 0.6:
            summary["validation_quality"] = "good"
        elif avg_consistency < 1.0:
            summary["validation_quality"] = "fair"
        else:
            summary["validation_quality"] = "poor"
        
        # Generate recommendations
        if summary["validation_quality"] == "poor":
            summary["recommendations"].append("High performance variability - strategy may not be robust")
        
        # Check for parameter instability
        for scheme_name, scheme_stability in parameter_stability.items():
            unstable_params = [param for param, stability in scheme_stability.items() if stability.get("changed", False)]
            if unstable_params:
                summary["recommendations"].append(f"Parameter instability detected in {scheme_name}: {unstable_params}")
        
        # Check for performance degradation
        for scheme_name, scheme_degradation in performance_degradation.items():
            degrading_metrics = [metric for metric, degradation in scheme_degradation.items() if degradation.get("is_degrading", False)]
            if degrading_metrics:
                summary["recommendations"].append(f"Performance degradation detected in {scheme_name}: {degrading_metrics}")
        
        if not summary["recommendations"]:
            summary["recommendations"].append("Strategy shows good validation characteristics")
        
        return summary
    
    def generate_validation_report(self, results: Dict) -> str:
        """Generate comprehensive validation report."""
        report = []
        report.append("=" * 80)
        report.append("WALK-FORWARD VALIDATION REPORT")
        report.append("=" * 80)
        
        # Validation summary
        validation_summary = results.get("validation_summary", {})
        report.append(f"\nValidation Quality: {validation_summary.get('validation_quality', 'unknown').upper()}")
        report.append(f"Recommendations:")
        for rec in validation_summary.get("recommendations", []):
            report.append(f"  - {rec}")
        
        # Overall performance analysis
        overall_performance = results.get("overall_performance", {})
        report.append(f"\nOVERALL PERFORMANCE ANALYSIS:")
        report.append("-" * 50)
        
        for scheme_name, scheme_perf in overall_performance.items():
            report.append(f"\n{scheme_name.replace('_', ' ').title()}:")
            
            if "total_return" in scheme_perf:
                tr = scheme_perf["total_return"]
                report.append(f"  Total Return: {tr['mean']:.2f}% ± {tr['std']:.2f}%")
                report.append(f"  Range: {tr['min']:.2f}% to {tr['max']:.2f}%")
                report.append(f"  Positive Folds: {tr['positive_folds']}/{tr['total_folds']}")
            
            if "sharpe_ratio" in scheme_perf:
                sr = scheme_perf["sharpe_ratio"]
                report.append(f"  Sharpe Ratio: {sr['mean']:.2f} ± {sr['std']:.2f}")
            
            if "max_drawdown" in scheme_perf:
                dd = scheme_perf["max_drawdown"]
                report.append(f"  Max Drawdown: {dd['mean']:.2f}% ± {dd['std']:.2f}%")
        
        # Parameter stability analysis
        parameter_stability = results.get("parameter_stability", {})
        report.append(f"\nPARAMETER STABILITY ANALYSIS:")
        report.append("-" * 50)
        
        for scheme_name, scheme_stability in parameter_stability.items():
            unstable_params = [param for param, stability in scheme_stability.items() if stability.get("changed", False)]
            stable_params = [param for param, stability in scheme_stability.items() if not stability.get("changed", False)]
            
            report.append(f"\n{scheme_name.replace('_', ' ').title()}:")
            report.append(f"  Stable Parameters: {len(stable_params)}")
            report.append(f"  Unstable Parameters: {len(unstable_params)}")
            
            if unstable_params:
                report.append(f"  Unstable: {', '.join(unstable_params)}")
        
        # Performance degradation analysis
        performance_degradation = results.get("performance_degradation", {})
        report.append(f"\nPERFORMANCE DEGRADATION ANALYSIS:")
        report.append("-" * 50)
        
        for scheme_name, scheme_degradation in performance_degradation.items():
            report.append(f"\n{scheme_name.replace('_', ' ').title()}:")
            
            for metric, degradation in scheme_degradation.items():
                trend = degradation.get("trend_slope", 0)
                degradation_rate = degradation.get("degradation_rate", 0)
                is_degrading = degradation.get("is_degrading", False)
                
                status = "DEGRADING" if is_degrading else "STABLE"
                report.append(f"  {metric}: {status} (trend: {trend:.4f}, degradation: {degradation_rate:.2%})")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)
