"""
Crisis period simulation and tail risk analysis.
Implements historical crisis modeling and extreme scenario generation.
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class CrisisSimulator:
    """
    Crisis period simulator for extreme scenario testing.
    
    Features:
    - Historical crisis modeling (2008, COVID-19, etc.)
    - Synthetic crisis generation
    - Tail risk analysis
    - Extreme value theory (EVT) modeling
    - Crisis contagion effects
    - Liquidity crisis simulation
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Crisis parameters
        self.crisis_severity_levels = self.config.get("crisis_severity_levels", [0.1, 0.2, 0.3, 0.5])
        self.crisis_duration_days = self.config.get("crisis_duration_days", [30, 60, 90, 180])
        self.recovery_speed = self.config.get("recovery_speed", 0.5)  # 0 = no recovery, 1 = full recovery
        
        # Tail risk parameters
        self.evt_threshold = self.config.get("evt_threshold", 0.95)
        self.evt_block_size = self.config.get("evt_block_size", 252)
        self.tail_dependence_alpha = self.config.get("tail_dependence_alpha", 0.5)
        
        # Historical crisis data
        self.historical_crises = self._initialize_historical_crises()
        
    def _initialize_historical_crises(self) -> Dict[str, Dict]:
        """Initialize historical crisis data."""
        return {
            "2008_financial_crisis": {
                "duration_days": 365,
                "peak_drawdown": -0.55,
                "volatility_multiplier": 3.5,
                "recovery_time_days": 730,
                "description": "Global financial crisis with banking sector collapse"
            },
            "covid_19_pandemic": {
                "duration_days": 90,
                "peak_drawdown": -0.35,
                "volatility_multiplier": 4.0,
                "recovery_time_days": 180,
                "description": "Pandemic-induced market crash with rapid recovery"
            },
            "dot_com_bubble": {
                "duration_days": 730,
                "peak_drawdown": -0.78,
                "volatility_multiplier": 2.8,
                "recovery_time_days": 1825,
                "description": "Technology bubble burst with prolonged bear market"
            },
            "black_monday_1987": {
                "duration_days": 7,
                "peak_drawdown": -0.23,
                "volatility_multiplier": 6.0,
                "recovery_time_days": 60,
                "description": "Single-day crash with rapid recovery"
            },
            "asian_financial_crisis": {
                "duration_days": 180,
                "peak_drawdown": -0.45,
                "volatility_multiplier": 3.0,
                "recovery_time_days": 365,
                "description": "Currency crisis spreading across Asian markets"
            }
        }
    
    def simulate_historical_crisis(
        self,
        strategy,
        normal_returns: np.ndarray,
        crisis_name: str,
        initial_capital: float = 10000.0
    ) -> Dict[str, Any]:
        """
        Simulate a specific historical crisis scenario.
        
        Args:
            strategy: Trading strategy to test
            normal_returns: Normal market returns for baseline
            crisis_name: Name of historical crisis to simulate
            initial_capital: Starting capital
            
        Returns:
            Crisis simulation results
        """
        if crisis_name not in self.historical_crises:
            return {"error": f"Unknown crisis: {crisis_name}"}
        
        crisis_data = self.historical_crises[crisis_name]
        
        # Generate crisis returns
        crisis_returns = self._generate_historical_crisis_returns(
            normal_returns, crisis_data
        )
        
        # Simulate strategy performance during crisis
        crisis_performance = self._simulate_crisis_performance(
            strategy, crisis_returns, initial_capital
        )
        
        return {
            "crisis_name": crisis_name,
            "crisis_data": crisis_data,
            "crisis_returns": crisis_returns,
            "performance": crisis_performance,
            "simulation_type": "historical_crisis"
        }
    
    def simulate_synthetic_crisis(
        self,
        strategy,
        normal_returns: np.ndarray,
        severity: float,
        duration_days: int,
        initial_capital: float = 10000.0
    ) -> Dict[str, Any]:
        """
        Simulate a synthetic crisis with specified parameters.
        
        Args:
            strategy: Trading strategy to test
            normal_returns: Normal market returns for baseline
            severity: Crisis severity (0.0 to 1.0)
            duration_days: Crisis duration in days
            initial_capital: Starting capital
            
        Returns:
            Synthetic crisis simulation results
        """
        # Generate synthetic crisis returns
        crisis_returns = self._generate_synthetic_crisis_returns(
            normal_returns, severity, duration_days
        )
        
        # Simulate strategy performance
        crisis_performance = self._simulate_crisis_performance(
            strategy, crisis_returns, initial_capital
        )
        
        return {
            "severity": severity,
            "duration_days": duration_days,
            "crisis_returns": crisis_returns,
            "performance": crisis_performance,
            "simulation_type": "synthetic_crisis"
        }
    
    def run_crisis_scenario_analysis(
        self,
        strategy,
        normal_returns: np.ndarray,
        initial_capital: float = 10000.0
    ) -> Dict[str, Any]:
        """
        Run comprehensive crisis scenario analysis.
        
        Args:
            strategy: Trading strategy to test
            normal_returns: Normal market returns for baseline
            initial_capital: Starting capital
            
        Returns:
            Comprehensive crisis analysis results
        """
        results = {
            "historical_crises": {},
            "synthetic_crises": {},
            "tail_risk_analysis": {},
            "crisis_summary": {}
        }
        
        # Test historical crises
        print("Testing historical crisis scenarios...")
        for crisis_name in self.historical_crises.keys():
            print(f"  Simulating {crisis_name}...")
            crisis_result = self.simulate_historical_crisis(
                strategy, normal_returns, crisis_name, initial_capital
            )
            results["historical_crises"][crisis_name] = crisis_result
        
        # Test synthetic crises
        print("Testing synthetic crisis scenarios...")
        for severity in self.crisis_severity_levels:
            for duration in self.crisis_duration_days:
                print(f"  Simulating crisis: severity={severity}, duration={duration} days...")
                synthetic_result = self.simulate_synthetic_crisis(
                    strategy, normal_returns, severity, duration, initial_capital
                )
                key = f"severity_{severity}_duration_{duration}"
                results["synthetic_crises"][key] = synthetic_result
        
        # Tail risk analysis
        print("Performing tail risk analysis...")
        results["tail_risk_analysis"] = self._analyze_tail_risk(
            normal_returns, results
        )
        
        # Crisis summary
        results["crisis_summary"] = self._generate_crisis_summary(results)
        
        return results
    
    def _generate_historical_crisis_returns(
        self, normal_returns: np.ndarray, crisis_data: Dict
    ) -> np.ndarray:
        """Generate returns based on historical crisis parameters."""
        duration = crisis_data["duration_days"]
        peak_drawdown = crisis_data["peak_drawdown"]
        vol_multiplier = crisis_data["volatility_multiplier"]
        
        # Calculate crisis parameters from normal returns
        normal_vol = np.std(normal_returns)
        normal_mean = np.mean(normal_returns)
        
        # Crisis phase parameters
        crisis_mean = normal_mean + peak_drawdown / duration  # Average daily decline
        crisis_vol = normal_vol * vol_multiplier
        
        # Generate crisis returns
        crisis_returns = np.random.normal(crisis_mean, crisis_vol, duration)
        
        # Add recovery phase
        if self.recovery_speed > 0:
            recovery_days = int(crisis_data["recovery_time_days"] * self.recovery_speed)
            recovery_returns = np.random.normal(
                normal_mean + abs(crisis_mean) * 0.5,  # Partial recovery
                normal_vol * 1.5,  # Elevated volatility during recovery
                recovery_days
            )
            crisis_returns = np.concatenate([crisis_returns, recovery_returns])
        
        return crisis_returns
    
    def _generate_synthetic_crisis_returns(
        self, normal_returns: np.ndarray, severity: float, duration_days: int
    ) -> np.ndarray:
        """Generate synthetic crisis returns with specified severity."""
        normal_vol = np.std(normal_returns)
        normal_mean = np.mean(normal_returns)
        
        # Scale crisis parameters by severity
        crisis_mean = normal_mean - (severity * abs(normal_mean) * 5)  # Severe negative returns
        crisis_vol = normal_vol * (1 + severity * 3)  # Increased volatility
        
        # Generate crisis returns
        crisis_returns = np.random.normal(crisis_mean, crisis_vol, duration_days)
        
        # Add recovery phase
        if self.recovery_speed > 0:
            recovery_days = int(duration_days * self.recovery_speed)
            recovery_returns = np.random.normal(
                normal_mean + abs(crisis_mean) * severity * 0.3,
                normal_vol * (1 + severity),
                recovery_days
            )
            crisis_returns = np.concatenate([crisis_returns, recovery_returns])
        
        return crisis_returns
    
    def _simulate_crisis_performance(
        self, strategy, crisis_returns: np.ndarray, initial_capital: float
    ) -> Dict[str, float]:
        """Simulate strategy performance during crisis."""
        try:
            # Convert returns to prices
            prices = initial_capital * np.cumprod(1 + crisis_returns)
            
            # Create price DataFrame
            price_data = pd.DataFrame({
                'close': prices,
                'volume': np.random.randint(1000000, 5000000, len(prices))
            })
            
            # Generate signals
            signals = strategy.generate_signals(price_data)
            
            # Simulate trading
            capital = initial_capital
            position = 0
            equity_curve = [capital]
            
            for i, (idx, row) in enumerate(signals.iterrows()):
                signal = row.get('signal', 0)
                current_price = prices[i]
                
                if signal == 1 and position == 0:  # Buy signal
                    position = capital * 0.95 / current_price
                    capital = capital * 0.05
                elif signal == -1 and position > 0:  # Sell signal
                    capital += position * current_price
                    position = 0
                
                current_equity = capital + (position * current_price if position > 0 else 0)
                equity_curve.append(current_equity)
            
            # Calculate performance metrics
            final_value = equity_curve[-1]
            total_return = (final_value / initial_capital - 1) * 100
            
            # Calculate max drawdown during crisis
            peak = equity_curve[0]
            max_dd = 0
            for value in equity_curve:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak
                max_dd = max(max_dd, dd)
            
            # Calculate crisis-specific metrics
            crisis_volatility = np.std(crisis_returns) * np.sqrt(252)
            crisis_sharpe = np.mean(crisis_returns) / np.std(crisis_returns) * np.sqrt(252) if np.std(crisis_returns) > 0 else 0
            
            return {
                "final_value": final_value,
                "total_return": total_return,
                "max_drawdown": max_dd * 100,
                "crisis_volatility": crisis_volatility,
                "crisis_sharpe": crisis_sharpe,
                "crisis_duration": len(crisis_returns),
                "survival_rate": 1.0 if final_value > 0 else 0.0,
                "equity_curve": equity_curve
            }
            
        except Exception as e:
            return {
                "final_value": initial_capital,
                "total_return": 0,
                "max_drawdown": 0,
                "error": str(e)
            }
    
    def _analyze_tail_risk(
        self, normal_returns: np.ndarray, crisis_results: Dict
    ) -> Dict[str, Any]:
        """Perform tail risk analysis using extreme value theory."""
        # Extract crisis returns from results
        all_crisis_returns = []
        
        for crisis_type, crises in crisis_results.items():
            if crisis_type in ["historical_crises", "synthetic_crises"]:
                for crisis_name, crisis_result in crises.items():
                    if "crisis_returns" in crisis_result:
                        all_crisis_returns.extend(crisis_result["crisis_returns"])
        
        if not all_crisis_returns:
            return {"error": "No crisis returns available for analysis"}
        
        crisis_returns_array = np.array(all_crisis_returns)
        
        # Extreme Value Theory analysis
        evt_results = self._perform_evt_analysis(crisis_returns_array)
        
        # Tail dependence analysis
        tail_dependence = self._analyze_tail_dependence(crisis_returns_array)
        
        # Tail risk metrics
        tail_risk_metrics = {
            "var_99": np.percentile(crisis_returns_array, 1),
            "var_99_5": np.percentile(crisis_returns_array, 0.5),
            "var_99_9": np.percentile(crisis_returns_array, 0.1),
            "cvar_99": np.mean(crisis_returns_array[crisis_returns_array <= np.percentile(crisis_returns_array, 1)]),
            "tail_expectation": np.mean(crisis_returns_array[crisis_returns_array <= np.percentile(crisis_returns_array, 5)]),
            "tail_ratio": np.percentile(crisis_returns_array, 95) / abs(np.percentile(crisis_returns_array, 5))
        }
        
        return {
            "evt_analysis": evt_results,
            "tail_dependence": tail_dependence,
            "tail_risk_metrics": tail_risk_metrics,
            "crisis_return_statistics": {
                "mean": np.mean(crisis_returns_array),
                "std": np.std(crisis_returns_array),
                "skewness": self._calculate_skewness(crisis_returns_array),
                "kurtosis": self._calculate_kurtosis(crisis_returns_array)
            }
        }
    
    def _perform_evt_analysis(self, returns: np.ndarray) -> Dict[str, float]:
        """Perform Extreme Value Theory analysis."""
        # Sort returns
        sorted_returns = np.sort(returns)
        
        # Calculate threshold
        threshold = np.percentile(returns, self.evt_threshold * 100)
        
        # Extract excesses over threshold
        excesses = sorted_returns[sorted_returns < threshold] - threshold
        
        if len(excesses) == 0:
            return {"error": "No excesses found for EVT analysis"}
        
        # Estimate Generalized Pareto Distribution parameters
        # Simplified estimation (in practice, use MLE or method of moments)
        excess_mean = np.mean(excesses)
        excess_var = np.var(excesses)
        
        # Shape parameter (simplified)
        shape_param = -0.5 + 0.5 * np.sqrt(1 + 4 * excess_var / (excess_mean ** 2)) if excess_mean != 0 else 0
        
        # Scale parameter
        scale_param = excess_mean * (1 - shape_param) if shape_param != 1 else excess_mean
        
        return {
            "threshold": threshold,
            "shape_parameter": shape_param,
            "scale_parameter": scale_param,
            "num_excesses": len(excesses),
            "excess_mean": excess_mean,
            "excess_variance": excess_var
        }
    
    def _analyze_tail_dependence(self, returns: np.ndarray) -> Dict[str, float]:
        """Analyze tail dependence in crisis returns."""
        # Simplified tail dependence analysis
        # In practice, use more sophisticated methods like copulas
        
        # Calculate tail correlation
        lower_tail_threshold = np.percentile(returns, 5)
        upper_tail_threshold = np.percentile(returns, 95)
        
        lower_tail_returns = returns[returns <= lower_tail_threshold]
        upper_tail_returns = returns[returns >= upper_tail_threshold]
        
        # Tail dependence coefficient (simplified)
        tail_dependence_lower = len(lower_tail_returns) / len(returns)
        tail_dependence_upper = len(upper_tail_returns) / len(returns)
        
        return {
            "lower_tail_dependence": tail_dependence_lower,
            "upper_tail_dependence": tail_dependence_upper,
            "tail_asymmetry": tail_dependence_lower - tail_dependence_upper,
            "extreme_correlation": np.corrcoef(
                returns[:-1], returns[1:]
            )[0, 1] if len(returns) > 1 else 0
        }
    
    def _calculate_skewness(self, returns: np.ndarray) -> float:
        """Calculate skewness of returns."""
        if len(returns) < 3:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        skewness = np.mean(((returns - mean_return) / std_return) ** 3)
        return skewness
    
    def _calculate_kurtosis(self, returns: np.ndarray) -> float:
        """Calculate excess kurtosis of returns."""
        if len(returns) < 4:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        kurtosis = np.mean(((returns - mean_return) / std_return) ** 4) - 3
        return kurtosis
    
    def _generate_crisis_summary(self, crisis_results: Dict) -> Dict[str, Any]:
        """Generate summary of crisis simulation results."""
        summary = {
            "total_crises_tested": 0,
            "average_crisis_return": 0,
            "worst_crisis_return": 0,
            "crisis_survival_rate": 0,
            "most_severe_crisis": "",
            "crisis_recommendations": []
        }
        
        all_performances = []
        crisis_names = []
        
        # Collect performance data
        for crisis_type, crises in crisis_results.items():
            if crisis_type in ["historical_crises", "synthetic_crises"]:
                for crisis_name, crisis_result in crises.items():
                    if "performance" in crisis_result:
                        performance = crisis_result["performance"]
                        if "total_return" in performance:
                            all_performances.append(performance["total_return"])
                            crisis_names.append(crisis_name)
        
        if all_performances:
            summary["total_crises_tested"] = len(all_performances)
            summary["average_crisis_return"] = np.mean(all_performances)
            summary["worst_crisis_return"] = np.min(all_performances)
            summary["crisis_survival_rate"] = np.mean([1 if p > -100 else 0 for p in all_performances]) * 100
            
            # Find most severe crisis
            worst_idx = np.argmin(all_performances)
            summary["most_severe_crisis"] = crisis_names[worst_idx]
            
            # Generate recommendations
            if summary["crisis_survival_rate"] < 50:
                summary["crisis_recommendations"].append("Strategy shows poor crisis resilience - consider reducing position sizes")
            if summary["worst_crisis_return"] < -50:
                summary["crisis_recommendations"].append("Extreme losses detected - implement stricter risk management")
            if summary["average_crisis_return"] < -20:
                summary["crisis_recommendations"].append("Strategy consistently underperforms during crises - review strategy logic")
        
        return summary
    
    def generate_crisis_report(self, crisis_results: Dict) -> str:
        """Generate comprehensive crisis simulation report."""
        report = []
        report.append("=" * 80)
        report.append("CRISIS SIMULATION REPORT")
        report.append("=" * 80)
        
        # Historical crises summary
        report.append("\nHISTORICAL CRISIS SIMULATIONS:")
        report.append("-" * 50)
        
        historical_crises = crisis_results.get("historical_crises", {})
        for crisis_name, crisis_result in historical_crises.items():
            if "performance" in crisis_result:
                perf = crisis_result["performance"]
                report.append(f"{crisis_name.replace('_', ' ').title()}:")
                report.append(f"  Total Return: {perf.get('total_return', 0):.2f}%")
                report.append(f"  Max Drawdown: {perf.get('max_drawdown', 0):.2f}%")
                report.append(f"  Survival Rate: {perf.get('survival_rate', 0)*100:.1f}%")
                report.append("")
        
        # Synthetic crises summary
        report.append("\nSYNTHETIC CRISIS SIMULATIONS:")
        report.append("-" * 50)
        
        synthetic_crises = crisis_results.get("synthetic_crises", {})
        severity_performance = {}
        
        for crisis_key, crisis_result in synthetic_crises.items():
            if "performance" in crisis_result:
                perf = crisis_result["performance"]
                severity = crisis_result.get("severity", 0)
                
                if severity not in severity_performance:
                    severity_performance[severity] = []
                severity_performance[severity].append(perf.get('total_return', 0))
        
        for severity in sorted(severity_performance.keys()):
            returns = severity_performance[severity]
            report.append(f"Severity {severity:.1f}:")
            report.append(f"  Average Return: {np.mean(returns):.2f}%")
            report.append(f"  Worst Return: {np.min(returns):.2f}%")
            report.append(f"  Survival Rate: {np.mean([1 if r > -100 else 0 for r in returns])*100:.1f}%")
            report.append("")
        
        # Tail risk analysis
        tail_risk = crisis_results.get("tail_risk_analysis", {})
        if tail_risk:
            report.append("\nTAIL RISK ANALYSIS:")
            report.append("-" * 50)
            
            tail_metrics = tail_risk.get("tail_risk_metrics", {})
            report.append(f"VaR (99%): {tail_metrics.get('var_99', 0):.2f}%")
            report.append(f"VaR (99.5%): {tail_metrics.get('var_99_5', 0):.2f}%")
            report.append(f"CVaR (99%): {tail_metrics.get('cvar_99', 0):.2f}%")
            report.append(f"Tail Ratio: {tail_metrics.get('tail_ratio', 0):.2f}")
            report.append("")
        
        # Crisis summary
        crisis_summary = crisis_results.get("crisis_summary", {})
        if crisis_summary:
            report.append("\nCRISIS SIMULATION SUMMARY:")
            report.append("-" * 50)
            report.append(f"Total Crises Tested: {crisis_summary.get('total_crises_tested', 0)}")
            report.append(f"Average Crisis Return: {crisis_summary.get('average_crisis_return', 0):.2f}%")
            report.append(f"Worst Crisis Return: {crisis_summary.get('worst_crisis_return', 0):.2f}%")
            report.append(f"Crisis Survival Rate: {crisis_summary.get('crisis_survival_rate', 0):.1f}%")
            report.append(f"Most Severe Crisis: {crisis_summary.get('most_severe_crisis', 'N/A')}")
            
            recommendations = crisis_summary.get("crisis_recommendations", [])
            if recommendations:
                report.append("\nRecommendations:")
                for rec in recommendations:
                    report.append(f"  - {rec}")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)
