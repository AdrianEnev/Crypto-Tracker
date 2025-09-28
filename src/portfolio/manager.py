"""
Portfolio manager that integrates portfolio optimization with the existing trading system.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .optimizer import PortfolioOptimizer


class PortfolioManager:
    """
    Advanced portfolio manager with optimization capabilities.
    
    Integrates with existing portfolio system while adding:
    - Multi-asset allocation optimization
    - Dynamic rebalancing
    - Risk management
    - Performance tracking
    """
    
    def __init__(
        self,
        config_manager,
        app_config: Any,
        optimization_config: Optional[Dict] = None
    ):
        self.config_manager = config_manager
        self.app_config = app_config
        
        # Portfolio optimizer
        self.optimizer = PortfolioOptimizer()
        
        # Optimization configuration
        self.optimization_config = optimization_config or {
            "method": "markowitz",
            "target_volatility": 0.15,
            "rebalance_frequency": "monthly",
            "transaction_costs": 0.001,
            "max_weight": 0.4,
            "min_weight": 0.05,
            "rebalance_threshold": 0.05
        }
        
        # Portfolio state
        self.current_weights = {}
        self.target_weights = {}
        self.last_rebalance = None
        self.optimization_history = []
        
        # Load existing portfolio state
        self._load_portfolio_state()
    
    def optimize_portfolio(
        self,
        assets: List[str],
        returns_data: pd.DataFrame,
        method: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Optimize portfolio allocation for given assets.
        
        Args:
            assets: List of asset symbols
            returns_data: Historical returns data
            method: Optimization method override
            
        Returns:
            Optimization results including weights and metrics
        """
        try:
            method = method or self.optimization_config["method"]
            
            # Run optimization
            optimized_weights = self.optimizer.optimize_allocation(
                assets=assets,
                returns_data=returns_data,
                target_volatility=self.optimization_config["target_volatility"],
                method=method,
                rebalance_frequency=self.optimization_config["rebalance_frequency"],
                transaction_costs=self.optimization_config["transaction_costs"],
                max_weight=self.optimization_config["max_weight"],
                min_weight=self.optimization_config["min_weight"]
            )
            
            # Calculate portfolio metrics
            metrics = self.optimizer.calculate_portfolio_metrics(
                optimized_weights, returns_data
            )
            
            # Calculate correlation matrix
            correlation_matrix = self.optimizer.calculate_correlation_matrix(returns_data)
            
            # Store results
            self.target_weights = optimized_weights
            
            # Record optimization
            optimization_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "method": method,
                "assets": assets,
                "weights": optimized_weights,
                "metrics": metrics,
                "config": self.optimization_config
            }
            self.optimization_history.append(optimization_record)
            
            return {
                "success": True,
                "weights": optimized_weights,
                "metrics": metrics,
                "correlation_matrix": correlation_matrix.to_dict(),
                "optimization_record": optimization_record
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "weights": self._get_equal_weights(assets),
                "metrics": {}
            }
    
    def check_rebalancing_needed(self) -> Dict[str, Any]:
        """Check if portfolio needs rebalancing."""
        if not self.current_weights or not self.target_weights:
            return {"needed": False, "reason": "No weights available"}
        
        # Get rebalancing suggestions
        rebalance_analysis = self.optimizer.suggest_rebalancing(
            current_weights=self.current_weights,
            target_weights=self.target_weights,
            transaction_costs=self.optimization_config["transaction_costs"],
            threshold=self.optimization_config["rebalance_threshold"]
        )
        
        return {
            "needed": rebalance_analysis["should_rebalance"],
            "trades": rebalance_analysis["trades"],
            "total_cost": rebalance_analysis["total_transaction_cost"],
            "total_trades": rebalance_analysis["total_trades"]
        }
    
    def execute_rebalancing(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """
        Execute portfolio rebalancing trades.
        
        Args:
            current_prices: Current prices for all assets
            
        Returns:
            Rebalancing execution results
        """
        try:
            rebalance_check = self.check_rebalancing_needed()
            
            if not rebalance_check["needed"]:
                return {
                    "success": True,
                    "executed": False,
                    "message": "No rebalancing needed"
                }
            
            trades = rebalance_check["trades"]
            executed_trades = []
            total_cost = 0
            
            for trade in trades:
                asset = trade["asset"]
                action = trade["action"]
                size = trade["size"]
                
                if asset in current_prices:
                    price = current_prices[asset]
                    
                    # Calculate trade size in units
                    if action == "BUY":
                        trade_value = size * 10000  # Assuming $10k portfolio
                        units = trade_value / price
                        executed_trades.append({
                            "asset": asset,
                            "action": action,
                            "units": units,
                            "price": price,
                            "value": trade_value,
                            "cost": trade["transaction_cost"]
                        })
                        total_cost += trade["transaction_cost"]
                    
                    elif action == "SELL":
                        trade_value = size * 10000
                        units = trade_value / price
                        executed_trades.append({
                            "asset": asset,
                            "action": action,
                            "units": units,
                            "price": price,
                            "value": trade_value,
                            "cost": trade["transaction_cost"]
                        })
                        total_cost += trade["transaction_cost"]
            
            # Update current weights to target weights
            self.current_weights = self.target_weights.copy()
            self.last_rebalance = datetime.now(timezone.utc)
            
            # Save state
            self._save_portfolio_state()
            
            return {
                "success": True,
                "executed": True,
                "trades": executed_trades,
                "total_cost": total_cost,
                "new_weights": self.current_weights
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "executed": False
            }
    
    def get_portfolio_summary(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        try:
            # Calculate current portfolio value
            total_value = 0
            asset_values = {}
            
            for asset, weight in self.current_weights.items():
                if asset in current_prices:
                    value = weight * 10000 * current_prices[asset]  # Assuming $10k portfolio
                    asset_values[asset] = value
                    total_value += value
            
            # Calculate allocation percentages
            allocation_pct = {}
            for asset, value in asset_values.items():
                allocation_pct[asset] = (value / total_value * 100) if total_value > 0 else 0
            
            return {
                "total_value": total_value,
                "asset_values": asset_values,
                "allocation_percentages": allocation_pct,
                "target_weights": self.target_weights,
                "current_weights": self.current_weights,
                "last_rebalance": self.last_rebalance.isoformat() if self.last_rebalance else None,
                "rebalancing_needed": self.check_rebalancing_needed()["needed"],
                "optimization_count": len(self.optimization_history)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def update_weights(self, weights: Dict[str, float]) -> None:
        """Update current portfolio weights."""
        self.current_weights = weights.copy()
        self._save_portfolio_state()
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """Get optimization history."""
        return self.optimization_history.copy()
    
    def set_optimization_config(self, config: Dict[str, Any]) -> None:
        """Update optimization configuration."""
        self.optimization_config.update(config)
        self._save_portfolio_state()
    
    def _get_equal_weights(self, assets: List[str]) -> Dict[str, float]:
        """Get equal weights for fallback."""
        weight = 1.0 / len(assets) if assets else 0
        return {asset: weight for asset in assets}
    
    def _load_portfolio_state(self) -> None:
        """Load portfolio state from disk."""
        try:
            config_path = Path(self.config_manager.config_path)
            state_path = config_path.parent.parent / "logs" / "portfolio_state.json"
            
            if state_path.exists():
                with open(state_path, 'r') as f:
                    state = json.load(f)
                
                self.current_weights = state.get("current_weights", {})
                self.target_weights = state.get("target_weights", {})
                self.optimization_history = state.get("optimization_history", [])
                
                last_rebalance_str = state.get("last_rebalance")
                if last_rebalance_str:
                    self.last_rebalance = datetime.fromisoformat(last_rebalance_str.replace('Z', '+00:00'))
                
        except Exception as e:
            print(f"Error loading portfolio state: {e}")
    
    def _save_portfolio_state(self) -> None:
        """Save portfolio state to disk."""
        try:
            config_path = Path(self.config_manager.config_path)
            state_path = config_path.parent.parent / "logs" / "portfolio_state.json"
            
            state = {
                "current_weights": self.current_weights,
                "target_weights": self.target_weights,
                "optimization_history": self.optimization_history[-50:],  # Keep last 50 records
                "last_rebalance": self.last_rebalance.isoformat() if self.last_rebalance else None,
                "optimization_config": self.optimization_config
            }
            
            with open(state_path, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            print(f"Error saving portfolio state: {e}")
    
    def get_risk_metrics(self, returns_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate comprehensive risk metrics for current portfolio."""
        if not self.current_weights:
            return {"error": "No portfolio weights available"}
        
        try:
            # Basic metrics
            metrics = self.optimizer.calculate_portfolio_metrics(
                self.current_weights, returns_data
            )
            
            # Correlation analysis
            correlation_matrix = self.optimizer.calculate_correlation_matrix(returns_data)
            
            # Risk decomposition
            risk_decomposition = self._calculate_risk_decomposition(
                self.current_weights, returns_data
            )
            
            return {
                "portfolio_metrics": metrics,
                "correlation_matrix": correlation_matrix.to_dict(),
                "risk_decomposition": risk_decomposition
            }
            
        except Exception as e:
            return {"error": f"Risk calculation failed: {str(e)}"}
    
    def _calculate_risk_decomposition(
        self, weights: Dict[str, float], returns_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Calculate risk contribution by asset."""
        try:
            # Calculate covariance matrix
            cov_matrix = returns_data.cov() * 252
            
            # Portfolio variance
            weight_vector = np.array([weights.get(asset, 0) for asset in returns_data.columns])
            portfolio_var = np.dot(weight_vector, np.dot(cov_matrix.values, weight_vector))
            portfolio_vol = np.sqrt(portfolio_var)
            
            # Risk contributions
            marginal_contrib = np.dot(cov_matrix.values, weight_vector)
            risk_contrib = weight_vector * marginal_contrib / portfolio_vol
            
            risk_decomposition = {}
            for i, asset in enumerate(returns_data.columns):
                if asset in weights:
                    risk_decomposition[asset] = {
                        "weight": weights[asset],
                        "risk_contribution": risk_contrib[i],
                        "risk_percentage": (risk_contrib[i] / portfolio_vol * 100) if portfolio_vol > 0 else 0
                    }
            
            return {
                "portfolio_volatility": portfolio_vol,
                "asset_contributions": risk_decomposition,
                "concentration_risk": max(risk_decomposition.values(), key=lambda x: x["risk_percentage"])["risk_percentage"]
            }
            
        except Exception as e:
            return {"error": f"Risk decomposition failed: {str(e)}"}
