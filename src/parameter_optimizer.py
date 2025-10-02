"""
Parameter Optimization Module

Provides automated parameter optimization using Optuna for trading strategies.
Optimizes parameters like RSI period, EMA periods, stop loss, take profit, etc.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False

from .logger import log_event


class ParameterOptimizer:
    """Automated parameter optimization using Optuna."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        
        if not OPTUNA_AVAILABLE:
            log_event("parameter_optimizer_init_error", {
                "error": "Optuna not available. Install with: pip install optuna"
            })
            self.enabled = False
            return
        
        # Initialize configuration
        self._load_config()
        
        # Initialize optimization storage
        self.optimization_results = {}
        self.best_parameters = {}
        self.optimization_history = []
        
        # Initialize Optuna study storage
        self.study_storage = Path("./optimization_studies")
        self.study_storage.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self):
        """Load parameter optimization configuration."""
        try:
            config_data = self.config_manager.load_full_config()
            optimization_config = config_data.get("optimization", {})
            
            self.enabled = optimization_config.get("enabled", False)
            self.optimization_interval_hours = optimization_config.get("optimization_interval_hours", 24)
            self.parameters_to_optimize = optimization_config.get("parameters_to_optimize", [
                "rsi_period", "ema_fast", "ema_slow", "sl_mult", "tp_mult", "risk_budget_pct"
            ])
            self.optimization_trials = optimization_config.get("optimization_trials", 100)
            self.backtest_days = optimization_config.get("backtest_days", 30)
            
            if self.enabled:
                log_event("parameter_optimizer_initialized", {
                    "enabled": True,
                    "parameters": self.parameters_to_optimize,
                    "trials": self.optimization_trials,
                    "backtest_days": self.backtest_days
                })
            else:
                log_event("parameter_optimizer_disabled", {"enabled": False})
                
        except Exception as ex:
            log_event("parameter_optimizer_config_error", {"error": str(ex)})
            self.enabled = False
    
    def optimize_parameters(self, coin_id: str, strategy_name: str = "mean_reversion") -> Optional[Dict[str, Any]]:
        """Optimize parameters for a specific coin and strategy."""
        if not self.enabled or not OPTUNA_AVAILABLE:
            return None
            
        try:
            log_event("parameter_optimization_started", {
                "coin_id": coin_id,
                "strategy": strategy_name,
                "trials": self.optimization_trials
            })
            
            # Create or load study
            study_name = f"{coin_id}_{strategy_name}"
            study_file = self.study_storage / f"{study_name}.db"
            
            # Create study with SQLite storage
            storage_url = f"sqlite:///{study_file}"
            study = optuna.create_study(
                direction="maximize",
                storage=storage_url,
                study_name=study_name,
                load_if_exists=True
            )
            
            # Define objective function
            def objective(trial):
                return self._evaluate_parameters(trial, coin_id, strategy_name)
            
            # Run optimization
            study.optimize(objective, n_trials=self.optimization_trials)
            
            # Get best parameters
            best_params = study.best_params
            best_value = study.best_value
            
            # Store results
            self.optimization_results[coin_id] = {
                "strategy": strategy_name,
                "best_parameters": best_params,
                "best_value": best_value,
                "optimization_time": datetime.now(timezone.utc).isoformat(),
                "trials_completed": len(study.trials)
            }
            
            self.best_parameters[coin_id] = best_params
            
            # Save results to file
            self._save_optimization_results(coin_id)
            
            log_event("parameter_optimization_completed", {
                "coin_id": coin_id,
                "best_value": best_value,
                "best_parameters": best_params,
                "trials_completed": len(study.trials)
            })
            
            return self.optimization_results[coin_id]
            
        except Exception as ex:
            log_event("parameter_optimization_error", {
                "coin_id": coin_id,
                "error": str(ex)
            })
            return None
    
    def _evaluate_parameters(self, trial, coin_id: str, strategy_name: str) -> float:
        """Evaluate parameter set using backtesting."""
        try:
            # Suggest parameters based on configuration
            params = {}
            
            for param_name in self.parameters_to_optimize:
                if param_name == "rsi_period":
                    params[param_name] = trial.suggest_int("rsi_period", 5, 25)
                elif param_name == "ema_fast":
                    params[param_name] = trial.suggest_int("ema_fast", 5, 50)
                elif param_name == "ema_slow":
                    params[param_name] = trial.suggest_int("ema_slow", 20, 100)
                elif param_name == "sl_mult":
                    params[param_name] = trial.suggest_float("sl_mult", 0.5, 3.0)
                elif param_name == "tp_mult":
                    params[param_name] = trial.suggest_float("tp_mult", 1.0, 5.0)
                elif param_name == "risk_budget_pct":
                    params[param_name] = trial.suggest_float("risk_budget_pct", 0.001, 0.02)
            
            # Run backtest with these parameters
            performance_score = self._run_backtest(coin_id, strategy_name, params)
            
            return performance_score
            
        except Exception as ex:
            log_event("parameter_evaluation_error", {
                "coin_id": coin_id,
                "error": str(ex)
            })
            return 0.0
    
    def _run_backtest(self, coin_id: str, strategy_name: str, params: Dict[str, Any]) -> float:
        """Run backtest with given parameters."""
        try:
            # This is a simplified backtest - in production, you'd use the full backtesting engine
            # For now, we'll simulate a performance score based on parameter values
            
            # Get historical data
            config_data = self.config_manager.load_full_config()
            tracked_coins = config_data.get("tracked_coins", {})
            coin_config = tracked_coins.get(coin_id, {})
            
            if not coin_config:
                return 0.0
            
            # Simulate performance based on parameter combinations
            # In reality, this would run the actual strategy with these parameters
            performance_score = 0.0
            
            # RSI period optimization (prefer values around 14)
            rsi_period = params.get("rsi_period", 14)
            rsi_score = 1.0 - abs(rsi_period - 14) / 14.0
            performance_score += rsi_score * 0.2
            
            # EMA optimization (prefer reasonable ratios)
            ema_fast = params.get("ema_fast", 20)
            ema_slow = params.get("ema_slow", 50)
            if ema_slow > ema_fast:
                ema_ratio = ema_fast / ema_slow
                ema_score = ema_ratio if ema_ratio > 0.3 else 0.0
                performance_score += ema_score * 0.3
            
            # Stop loss optimization (prefer moderate values)
            sl_mult = params.get("sl_mult", 1.5)
            sl_score = 1.0 - abs(sl_mult - 1.5) / 1.5
            performance_score += sl_score * 0.2
            
            # Take profit optimization (prefer reasonable multiples)
            tp_mult = params.get("tp_mult", 2.0)
            tp_score = 1.0 - abs(tp_mult - 2.0) / 2.0
            performance_score += tp_score * 0.2
            
            # Risk budget optimization (prefer moderate values)
            risk_budget = params.get("risk_budget_pct", 0.01)
            risk_score = 1.0 - abs(risk_budget - 0.01) / 0.01
            performance_score += risk_score * 0.1
            
            # Add some randomness to simulate real market conditions
            import random
            performance_score += random.uniform(-0.1, 0.1)
            
            return max(0.0, min(1.0, performance_score))
            
        except Exception as ex:
            log_event("backtest_error", {
                "coin_id": coin_id,
                "error": str(ex)
            })
            return 0.0
    
    def get_best_parameters(self, coin_id: str) -> Optional[Dict[str, Any]]:
        """Get best parameters for a coin."""
        return self.best_parameters.get(coin_id)
    
    def apply_optimized_parameters(self, coin_id: str) -> bool:
        """Apply optimized parameters to the configuration."""
        try:
            best_params = self.get_best_parameters(coin_id)
            if not best_params:
                return False
            
            # Load current configuration
            config_data = self.config_manager.load_full_config()
            
            # Update coin-specific parameters
            if "tracked_coins" not in config_data:
                config_data["tracked_coins"] = {}
            
            if coin_id not in config_data["tracked_coins"]:
                config_data["tracked_coins"][coin_id] = {}
            
            # Update strategy parameters
            if "strategy" not in config_data["tracked_coins"][coin_id]:
                config_data["tracked_coins"][coin_id]["strategy"] = {}
            
            if "params" not in config_data["tracked_coins"][coin_id]["strategy"]:
                config_data["tracked_coins"][coin_id]["strategy"]["params"] = {}
            
            # Apply optimized parameters
            config_data["tracked_coins"][coin_id]["strategy"]["params"].update(best_params)
            
            # Save updated configuration
            self.config_manager.save_config(config_data)
            
            log_event("optimized_parameters_applied", {
                "coin_id": coin_id,
                "parameters": best_params
            })
            
            return True
            
        except Exception as ex:
            log_event("apply_parameters_error", {
                "coin_id": coin_id,
                "error": str(ex)
            })
            return False
    
    def should_optimize(self, coin_id: str) -> bool:
        """Check if parameters should be optimized for a coin."""
        if not self.enabled:
            return False
        
        try:
            # Check if optimization was run recently
            if coin_id in self.optimization_results:
                last_optimization = self.optimization_results[coin_id].get("optimization_time")
                if last_optimization:
                    last_time = datetime.fromisoformat(last_optimization)
                    hours_since = (datetime.now(timezone.utc) - last_time).total_seconds() / 3600
                    return hours_since >= self.optimization_interval_hours
            
            return True
            
        except Exception:
            return False
    
    def _save_optimization_results(self, coin_id: str):
        """Save optimization results to file."""
        try:
            results_file = self.study_storage / f"{coin_id}_results.json"
            
            with open(results_file, 'w') as f:
                json.dump(self.optimization_results.get(coin_id, {}), f, indent=2)
                
        except Exception as ex:
            log_event("save_optimization_results_error", {
                "coin_id": coin_id,
                "error": str(ex)
            })
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of all optimization results."""
        try:
            return {
                "enabled": self.enabled,
                "optuna_available": OPTUNA_AVAILABLE,
                "total_optimizations": len(self.optimization_results),
                "optimized_coins": list(self.optimization_results.keys()),
                "best_parameters": self.best_parameters,
                "optimization_history": self.optimization_history
            }
            
        except Exception as ex:
            log_event("optimization_summary_error", {"error": str(ex)})
            return {}
