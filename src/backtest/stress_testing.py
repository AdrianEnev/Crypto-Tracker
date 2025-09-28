"""
Monte Carlo stress testing and bootstrapping for trading strategies.
Implements multiple stress testing methodologies for robust strategy validation.
"""

import math
import random
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..strategies.base import BaseStrategy
from ..backtest.simulation.models import BacktestResult, Trade


class MonteCarloStressTest:
    """
    Monte Carlo stress testing engine for trading strategies.
    
    Features:
    - Bootstrap resampling of historical returns
    - Monte Carlo simulation of strategy performance
    - Tail risk analysis and VaR calculations
    - Crisis period simulation
    - Correlation stress testing
    - Regime change simulation
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Monte Carlo parameters
        self.num_simulations = int(self.config.get("num_simulations", 1000))
        self.confidence_levels = self.config.get("confidence_levels", [0.95, 0.99, 0.999])
        self.bootstrap_samples = int(self.config.get("bootstrap_samples", 10000))
        
        # Stress testing parameters
        self.crisis_probability = float(self.config.get("crisis_probability", 0.05))
        self.crisis_severity = float(self.config.get("crisis_severity", 0.3))
        self.correlation_stress = float(self.config.get("correlation_stress", 0.8))
        
        # Regime change parameters
        self.regime_change_probability = float(self.config.get("regime_change_probability", 0.1))
        self.regime_volatility_mult = float(self.config.get("regime_volatility_mult", 2.0))
        
        # Results storage
        self.stress_test_results = {}
        
    def run_bootstrap_stress_test(
        self,
        strategy: BaseStrategy,
        returns_data: pd.DataFrame,
        initial_capital: float = 10000.0,
        num_periods: int = 252
    ) -> Dict[str, Any]:
        """
        Run bootstrap stress test by resampling historical returns.
        
        Args:
            strategy: Trading strategy to test
            returns_data: Historical returns data
            initial_capital: Starting capital
            num_periods: Number of periods to simulate
            
        Returns:
            Stress test results with confidence intervals
        """
        print(f"Running bootstrap stress test with {self.num_simulations} simulations...")
        
        # Extract returns
        returns = returns_data.values.flatten()
        returns = returns[~np.isnan(returns)]  # Remove NaN values
        
        if len(returns) == 0:
            return {"error": "No valid returns data"}
        
        # Run bootstrap simulations
        simulation_results = []
        
        for i in range(self.num_simulations):
            # Bootstrap sample
            bootstrap_returns = np.random.choice(returns, size=num_periods, replace=True)
            
            # Simulate strategy performance
            result = self._simulate_strategy_performance(
                strategy, bootstrap_returns, initial_capital
            )
            
            simulation_results.append(result)
        
        # Calculate statistics
        final_values = [result["final_value"] for result in simulation_results]
        total_returns = [result["total_return"] for result in simulation_results]
        max_drawdowns = [result["max_drawdown"] for result in simulation_results]
        sharpe_ratios = [result["sharpe_ratio"] for result in simulation_results]
        
        # Calculate confidence intervals
        confidence_intervals = self._calculate_confidence_intervals(
            final_values, total_returns, max_drawdowns, sharpe_ratios
        )
        
        # Calculate tail risk metrics
        tail_risk = self._calculate_tail_risk_metrics(simulation_results)
        
        return {
            "test_type": "bootstrap",
            "num_simulations": self.num_simulations,
            "simulation_results": simulation_results,
            "confidence_intervals": confidence_intervals,
            "tail_risk_metrics": tail_risk,
            "summary_statistics": {
                "mean_final_value": np.mean(final_values),
                "median_final_value": np.median(final_values),
                "std_final_value": np.std(final_values),
                "mean_total_return": np.mean(total_returns),
                "mean_max_drawdown": np.mean(max_drawdowns),
                "mean_sharpe_ratio": np.mean(sharpe_ratios),
                "worst_case_return": np.percentile(total_returns, 1),
                "best_case_return": np.percentile(total_returns, 99)
            }
        }
    
    def run_crisis_stress_test(
        self,
        strategy: BaseStrategy,
        returns_data: pd.DataFrame,
        initial_capital: float = 10000.0,
        num_periods: int = 252
    ) -> Dict[str, Any]:
        """
        Run crisis stress test by simulating extreme market conditions.
        
        Args:
            strategy: Trading strategy to test
            returns_data: Historical returns data
            initial_capital: Starting capital
            num_periods: Number of periods to simulate
            
        Returns:
            Crisis stress test results
        """
        print(f"Running crisis stress test with {self.num_simulations} simulations...")
        
        # Extract returns and calculate crisis parameters
        returns = returns_data.values.flatten()
        returns = returns[~np.isnan(returns)]
        
        if len(returns) == 0:
            return {"error": "No valid returns data"}
        
        # Calculate crisis return distribution
        crisis_returns = self._generate_crisis_returns(returns)
        
        # Run crisis simulations
        crisis_results = []
        
        for i in range(self.num_simulations):
            # Generate crisis scenario
            crisis_scenario = self._generate_crisis_scenario(
                returns, crisis_returns, num_periods
            )
            
            # Simulate strategy performance
            result = self._simulate_strategy_performance(
                strategy, crisis_scenario, initial_capital
            )
            
            crisis_results.append(result)
        
        # Calculate crisis-specific metrics
        crisis_metrics = self._analyze_crisis_results(crisis_results)
        
        return {
            "test_type": "crisis",
            "num_simulations": self.num_simulations,
            "crisis_results": crisis_results,
            "crisis_metrics": crisis_metrics,
            "crisis_parameters": {
                "crisis_probability": self.crisis_probability,
                "crisis_severity": self.crisis_severity,
                "crisis_return_std": np.std(crisis_returns)
            }
        }
    
    def run_correlation_stress_test(
        self,
        strategy: BaseStrategy,
        returns_data: pd.DataFrame,
        correlation_stress_levels: List[float],
        initial_capital: float = 10000.0
    ) -> Dict[str, Any]:
        """
        Run correlation stress test by varying asset correlations.
        
        Args:
            strategy: Trading strategy to test
            returns_data: Multi-asset returns data
            correlation_stress_levels: List of correlation levels to test
            initial_capital: Starting capital
            
        Returns:
            Correlation stress test results
        """
        print(f"Running correlation stress test with {len(correlation_stress_levels)} correlation levels...")
        
        correlation_results = {}
        
        for correlation_level in correlation_stress_levels:
            print(f"Testing correlation level: {correlation_level}")
            
            # Generate correlated returns
            stressed_returns = self._generate_correlated_returns(
                returns_data, correlation_level
            )
            
            # Run simulations
            correlation_sims = []
            for i in range(self.num_simulations // len(correlation_stress_levels)):
                result = self._simulate_strategy_performance(
                    strategy, stressed_returns.iloc[i].values, initial_capital
                )
                correlation_sims.append(result)
            
            # Calculate metrics for this correlation level
            final_values = [r["final_value"] for r in correlation_sims]
            total_returns = [r["total_return"] for r in correlation_sims]
            max_drawdowns = [r["max_drawdown"] for r in correlation_sims]
            
            correlation_results[correlation_level] = {
                "mean_final_value": np.mean(final_values),
                "mean_total_return": np.mean(total_returns),
                "mean_max_drawdown": np.mean(max_drawdowns),
                "var_95": np.percentile(total_returns, 5),
                "var_99": np.percentile(total_returns, 1),
                "simulation_results": correlation_sims
            }
        
        return {
            "test_type": "correlation_stress",
            "correlation_results": correlation_results,
            "correlation_levels_tested": correlation_stress_levels
        }
    
    def run_regime_change_stress_test(
        self,
        strategy: BaseStrategy,
        returns_data: pd.DataFrame,
        regime_types: List[str],
        initial_capital: float = 10000.0,
        num_periods: int = 252
    ) -> Dict[str, Any]:
        """
        Run regime change stress test by simulating different market regimes.
        
        Args:
            strategy: Trading strategy to test
            returns_data: Historical returns data
            regime_types: List of regime types to simulate
            initial_capital: Starting capital
            num_periods: Number of periods to simulate
            
        Returns:
            Regime change stress test results
        """
        print(f"Running regime change stress test with {len(regime_types)} regime types...")
        
        regime_results = {}
        
        for regime_type in regime_types:
            print(f"Testing regime: {regime_type}")
            
            # Generate regime-specific returns
            regime_returns = self._generate_regime_returns(
                returns_data, regime_type, num_periods
            )
            
            # Run simulations for this regime
            regime_sims = []
            for i in range(self.num_simulations // len(regime_types)):
                result = self._simulate_strategy_performance(
                    strategy, regime_returns, initial_capital
                )
                regime_sims.append(result)
            
            # Calculate regime-specific metrics
            final_values = [r["final_value"] for r in regime_sims]
            total_returns = [r["total_return"] for r in regime_sims]
            max_drawdowns = [r["max_drawdown"] for r in regime_sims]
            
            regime_results[regime_type] = {
                "mean_final_value": np.mean(final_values),
                "mean_total_return": np.mean(total_returns),
                "mean_max_drawdown": np.mean(max_drawdowns),
                "regime_volatility": np.std(regime_returns),
                "regime_mean_return": np.mean(regime_returns),
                "simulation_results": regime_sims
            }
        
        return {
            "test_type": "regime_change",
            "regime_results": regime_results,
            "regime_types_tested": regime_types
        }
    
    def _simulate_strategy_performance(
        self,
        strategy: BaseStrategy,
        returns: np.ndarray,
        initial_capital: float
    ) -> Dict[str, float]:
        """Simulate strategy performance on given returns."""
        try:
            # Convert returns to prices
            prices = initial_capital * np.cumprod(1 + returns)
            
            # Create price DataFrame
            price_data = pd.DataFrame({
                'close': prices,
                'volume': np.random.randint(1000000, 5000000, len(prices))
            })
            
            # Generate signals
            signals = strategy.generate_signals(price_data)
            
            # Simulate trading based on signals
            capital = initial_capital
            position = 0
            equity_curve = [capital]
            trades = []
            
            for i, (idx, row) in enumerate(signals.iterrows()):
                signal = row.get('signal', 0)
                current_price = prices[i]
                
                if signal == 1 and position == 0:  # Buy signal
                    position = capital * 0.95 / current_price  # 95% allocation
                    capital = capital * 0.05  # Keep 5% cash
                elif signal == -1 and position > 0:  # Sell signal
                    capital += position * current_price
                    trades.append({
                        'entry_price': prices[max(0, i-10)],  # Approximate entry
                        'exit_price': current_price,
                        'units': position
                    })
                    position = 0
                
                # Update equity
                current_equity = capital + (position * current_price if position > 0 else 0)
                equity_curve.append(current_equity)
            
            # Calculate metrics
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
            
            # Calculate Sharpe ratio
            if len(equity_curve) > 1:
                equity_returns = np.diff(equity_curve) / equity_curve[:-1]
                sharpe_ratio = np.mean(equity_returns) / np.std(equity_returns) * np.sqrt(252) if np.std(equity_returns) > 0 else 0
            else:
                sharpe_ratio = 0
            
            return {
                "final_value": final_value,
                "total_return": total_return,
                "max_drawdown": max_dd * 100,
                "sharpe_ratio": sharpe_ratio,
                "num_trades": len(trades),
                "equity_curve": equity_curve
            }
            
        except Exception as e:
            return {
                "final_value": initial_capital,
                "total_return": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "num_trades": 0,
                "error": str(e)
            }
    
    def _calculate_confidence_intervals(
        self,
        final_values: List[float],
        total_returns: List[float],
        max_drawdowns: List[float],
        sharpe_ratios: List[float]
    ) -> Dict[str, Any]:
        """Calculate confidence intervals for key metrics."""
        confidence_intervals = {}
        
        for confidence_level in self.confidence_levels:
            alpha = 1 - confidence_level
            lower_percentile = (alpha / 2) * 100
            upper_percentile = (1 - alpha / 2) * 100
            
            confidence_intervals[f"{confidence_level:.1%}"] = {
                "final_value": {
                    "lower": np.percentile(final_values, lower_percentile),
                    "upper": np.percentile(final_values, upper_percentile)
                },
                "total_return": {
                    "lower": np.percentile(total_returns, lower_percentile),
                    "upper": np.percentile(total_returns, upper_percentile)
                },
                "max_drawdown": {
                    "lower": np.percentile(max_drawdowns, lower_percentile),
                    "upper": np.percentile(max_drawdowns, upper_percentile)
                },
                "sharpe_ratio": {
                    "lower": np.percentile(sharpe_ratios, lower_percentile),
                    "upper": np.percentile(sharpe_ratios, upper_percentile)
                }
            }
        
        return confidence_intervals
    
    def _calculate_tail_risk_metrics(self, simulation_results: List[Dict]) -> Dict[str, float]:
        """Calculate tail risk metrics from simulation results."""
        total_returns = [r["total_return"] for r in simulation_results]
        max_drawdowns = [r["max_drawdown"] for r in simulation_results]
        
        # Value at Risk (VaR)
        var_95 = np.percentile(total_returns, 5)
        var_99 = np.percentile(total_returns, 1)
        var_999 = np.percentile(total_returns, 0.1)
        
        # Conditional Value at Risk (CVaR)
        cvar_95 = np.mean([r for r in total_returns if r <= var_95])
        cvar_99 = np.mean([r for r in total_returns if r <= var_99])
        cvar_999 = np.mean([r for r in total_returns if r <= var_999])
        
        # Maximum Drawdown statistics
        max_dd_95 = np.percentile(max_drawdowns, 95)
        max_dd_99 = np.percentile(max_drawdowns, 99)
        worst_drawdown = np.min(max_drawdowns)
        
        # Tail ratio (ratio of 95th percentile to 5th percentile)
        tail_ratio = np.percentile(total_returns, 95) / abs(np.percentile(total_returns, 5)) if np.percentile(total_returns, 5) != 0 else float('inf')
        
        return {
            "var_95": var_95,
            "var_99": var_99,
            "var_999": var_999,
            "cvar_95": cvar_95,
            "cvar_99": cvar_99,
            "cvar_999": cvar_999,
            "max_drawdown_95": max_dd_95,
            "max_drawdown_99": max_dd_99,
            "worst_drawdown": worst_drawdown,
            "tail_ratio": tail_ratio
        }
    
    def _generate_crisis_returns(self, returns: np.ndarray) -> np.ndarray:
        """Generate crisis return distribution."""
        # Identify extreme negative returns
        crisis_threshold = np.percentile(returns, 5)  # Bottom 5%
        crisis_returns = returns[returns <= crisis_threshold]
        
        # If no crisis returns, create synthetic ones
        if len(crisis_returns) == 0:
            crisis_returns = np.random.normal(
                np.mean(returns) - 3 * np.std(returns),
                np.std(returns) * 2,
                100
            )
        
        return crisis_returns
    
    def _generate_crisis_scenario(
        self, normal_returns: np.ndarray, crisis_returns: np.ndarray, num_periods: int
    ) -> np.ndarray:
        """Generate a crisis scenario with crisis periods."""
        scenario = []
        
        for i in range(num_periods):
            if random.random() < self.crisis_probability:
                # Crisis period
                crisis_return = np.random.choice(crisis_returns)
                scenario.append(crisis_return * self.crisis_severity)
            else:
                # Normal period
                normal_return = np.random.choice(normal_returns)
                scenario.append(normal_return)
        
        return np.array(scenario)
    
    def _generate_correlated_returns(
        self, returns_data: pd.DataFrame, target_correlation: float
    ) -> pd.DataFrame:
        """Generate returns with specified correlation."""
        # This is a simplified implementation
        # In practice, you would use more sophisticated correlation modeling
        
        n_assets = len(returns_data.columns)
        n_periods = len(returns_data)
        
        # Generate correlated random numbers
        correlation_matrix = np.full((n_assets, n_assets), target_correlation)
        np.fill_diagonal(correlation_matrix, 1.0)
        
        # Generate correlated returns
        correlated_returns = np.random.multivariate_normal(
            np.zeros(n_assets), correlation_matrix, n_periods
        )
        
        # Scale to match original return statistics
        for i, col in enumerate(returns_data.columns):
            original_returns = returns_data[col].dropna()
            if len(original_returns) > 0:
                correlated_returns[:, i] *= np.std(original_returns)
                correlated_returns[:, i] += np.mean(original_returns)
        
        return pd.DataFrame(correlated_returns, columns=returns_data.columns)
    
    def _generate_regime_returns(
        self, returns_data: pd.DataFrame, regime_type: str, num_periods: int
    ) -> np.ndarray:
        """Generate returns for specific market regime."""
        returns = returns_data.values.flatten()
        returns = returns[~np.isnan(returns)]
        
        if len(returns) == 0:
            return np.random.normal(0, 0.02, num_periods)
        
        base_mean = np.mean(returns)
        base_std = np.std(returns)
        
        if regime_type == "bull_market":
            regime_mean = base_mean + 0.01  # Higher returns
            regime_std = base_std * 0.8     # Lower volatility
        elif regime_type == "bear_market":
            regime_mean = base_mean - 0.01  # Lower returns
            regime_std = base_std * 1.2     # Higher volatility
        elif regime_type == "high_volatility":
            regime_mean = base_mean
            regime_std = base_std * self.regime_volatility_mult
        elif regime_type == "crisis":
            regime_mean = base_mean - 0.02  # Much lower returns
            regime_std = base_std * self.regime_volatility_mult * 1.5
        else:  # normal or sideways
            regime_mean = base_mean
            regime_std = base_std
        
        return np.random.normal(regime_mean, regime_std, num_periods)
    
    def _analyze_crisis_results(self, crisis_results: List[Dict]) -> Dict[str, float]:
        """Analyze crisis stress test results."""
        final_values = [r["final_value"] for r in crisis_results]
        total_returns = [r["total_return"] for r in crisis_results]
        max_drawdowns = [r["max_drawdown"] for r in crisis_results]
        
        return {
            "crisis_survival_rate": np.mean([r > 0 for r in total_returns]) * 100,
            "mean_crisis_return": np.mean(total_returns),
            "worst_crisis_return": np.min(total_returns),
            "mean_crisis_drawdown": np.mean(max_drawdowns),
            "worst_crisis_drawdown": np.min(max_drawdowns),
            "crisis_var_95": np.percentile(total_returns, 5),
            "crisis_var_99": np.percentile(total_returns, 1)
        }
    
    def generate_stress_test_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive stress test report."""
        report = []
        report.append("=" * 60)
        report.append("STRESS TEST REPORT")
        report.append("=" * 60)
        
        test_type = results.get("test_type", "unknown")
        report.append(f"Test Type: {test_type.upper()}")
        report.append(f"Number of Simulations: {results.get('num_simulations', 0)}")
        report.append("")
        
        if test_type == "bootstrap":
            summary = results.get("summary_statistics", {})
            report.append("SUMMARY STATISTICS:")
            report.append(f"  Mean Final Value: ${summary.get('mean_final_value', 0):.2f}")
            report.append(f"  Mean Total Return: {summary.get('mean_total_return', 0):.2f}%")
            report.append(f"  Mean Max Drawdown: {summary.get('mean_max_drawdown', 0):.2f}%")
            report.append(f"  Worst Case Return: {summary.get('worst_case_return', 0):.2f}%")
            report.append(f"  Best Case Return: {summary.get('best_case_return', 0):.2f}%")
            report.append("")
            
            # Confidence intervals
            ci = results.get("confidence_intervals", {})
            for level, intervals in ci.items():
                report.append(f"CONFIDENCE INTERVALS ({level}):")
                report.append(f"  Final Value: ${intervals['final_value']['lower']:.2f} - ${intervals['final_value']['upper']:.2f}")
                report.append(f"  Total Return: {intervals['total_return']['lower']:.2f}% - {intervals['total_return']['upper']:.2f}%")
                report.append(f"  Max Drawdown: {intervals['max_drawdown']['lower']:.2f}% - {intervals['max_drawdown']['upper']:.2f}%")
                report.append("")
            
            # Tail risk
            tail_risk = results.get("tail_risk_metrics", {})
            report.append("TAIL RISK METRICS:")
            report.append(f"  VaR (95%): {tail_risk.get('var_95', 0):.2f}%")
            report.append(f"  VaR (99%): {tail_risk.get('var_99', 0):.2f}%")
            report.append(f"  CVaR (95%): {tail_risk.get('cvar_95', 0):.2f}%")
            report.append(f"  Worst Drawdown: {tail_risk.get('worst_drawdown', 0):.2f}%")
            report.append("")
        
        elif test_type == "crisis":
            crisis_metrics = results.get("crisis_metrics", {})
            report.append("CRISIS STRESS TEST RESULTS:")
            report.append(f"  Crisis Survival Rate: {crisis_metrics.get('crisis_survival_rate', 0):.1f}%")
            report.append(f"  Mean Crisis Return: {crisis_metrics.get('mean_crisis_return', 0):.2f}%")
            report.append(f"  Worst Crisis Return: {crisis_metrics.get('worst_crisis_return', 0):.2f}%")
            report.append(f"  Mean Crisis Drawdown: {crisis_metrics.get('mean_crisis_drawdown', 0):.2f}%")
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)
