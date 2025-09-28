"""
Portfolio optimization system implementing Markowitz mean-variance optimization,
volatility targeting, Kelly criterion, and dynamic rebalancing.
"""

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class PortfolioOptimizer:
    """
    Advanced portfolio optimization with multiple allocation strategies.
    
    Features:
    - Markowitz mean-variance optimization
    - Volatility targeting
    - Kelly criterion position sizing
    - Dynamic rebalancing
    - Correlation analysis
    - Risk parity allocation
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
        self.optimization_cache = {}
    
    def optimize_allocation(
        self,
        assets: List[str],
        returns_data: pd.DataFrame,
        target_volatility: float = 0.15,
        method: str = "markowitz",
        rebalance_frequency: str = "monthly",
        transaction_costs: float = 0.001,
        max_weight: float = 0.4,
        min_weight: float = 0.0
    ) -> Dict[str, float]:
        """
        Optimize portfolio allocation using specified method.
        
        Args:
            assets: List of asset symbols
            returns_data: DataFrame with asset returns (columns = assets, index = dates)
            target_volatility: Target annualized volatility
            method: Optimization method ("markowitz", "risk_parity", "equal_weight", "kelly")
            rebalance_frequency: Rebalancing frequency
            transaction_costs: Transaction cost per trade
            max_weight: Maximum weight per asset
            min_weight: Minimum weight per asset
            
        Returns:
            Dictionary with optimized weights
        """
        if method == "markowitz":
            return self._markowitz_optimization(
                assets, returns_data, target_volatility, max_weight, min_weight
            )
        elif method == "risk_parity":
            return self._risk_parity_optimization(
                assets, returns_data, max_weight, min_weight
            )
        elif method == "equal_weight":
            return self._equal_weight_optimization(assets)
        elif method == "kelly":
            return self._kelly_optimization(
                assets, returns_data, max_weight, min_weight
            )
        else:
            raise ValueError(f"Unknown optimization method: {method}")
    
    def _markowitz_optimization(
        self,
        assets: List[str],
        returns_data: pd.DataFrame,
        target_volatility: float,
        max_weight: float,
        min_weight: float
    ) -> Dict[str, float]:
        """Markowitz mean-variance optimization."""
        try:
            # Calculate expected returns and covariance matrix
            expected_returns = returns_data.mean() * 252  # Annualized
            cov_matrix = returns_data.cov() * 252  # Annualized
            
            # Convert to numpy arrays
            mu = expected_returns.values
            S = cov_matrix.values
            
            # Portfolio optimization using quadratic programming
            n = len(assets)
            
            # Objective function: maximize Sharpe ratio
            # Minimize: w^T * S * w - lambda * mu^T * w
            # Subject to: sum(w) = 1, w >= min_weight, w <= max_weight
            
            # Use simplified optimization (can be enhanced with scipy.optimize)
            weights = self._quadratic_optimization(
                mu, S, target_volatility, max_weight, min_weight
            )
            
            return dict(zip(assets, weights))
            
        except Exception as e:
            print(f"Markowitz optimization failed: {e}")
            return self._equal_weight_optimization(assets)
    
    def _risk_parity_optimization(
        self,
        assets: List[str],
        returns_data: pd.DataFrame,
        max_weight: float,
        min_weight: float
    ) -> Dict[str, float]:
        """Risk parity optimization - equal risk contribution."""
        try:
            # Calculate covariance matrix
            cov_matrix = returns_data.cov() * 252
            
            # Initialize with equal weights
            n = len(assets)
            weights = np.ones(n) / n
            
            # Iterative optimization for risk parity
            for iteration in range(50):  # Max iterations
                # Calculate portfolio volatility
                portfolio_var = np.dot(weights, np.dot(cov_matrix.values, weights))
                portfolio_vol = np.sqrt(portfolio_var)
                
                # Calculate marginal risk contributions
                marginal_contrib = np.dot(cov_matrix.values, weights) / portfolio_vol
                
                # Calculate risk contributions
                risk_contrib = weights * marginal_contrib
                
                # Target risk contribution (equal for all assets)
                target_contrib = portfolio_vol / n
                
                # Update weights to achieve equal risk contribution
                new_weights = weights * (target_contrib / risk_contrib)
                
                # Apply constraints
                new_weights = np.clip(new_weights, min_weight, max_weight)
                new_weights = new_weights / np.sum(new_weights)  # Normalize
                
                # Check convergence
                if np.allclose(weights, new_weights, rtol=1e-4):
                    break
                
                weights = new_weights
            
            return dict(zip(assets, weights))
            
        except Exception as e:
            print(f"Risk parity optimization failed: {e}")
            return self._equal_weight_optimization(assets)
    
    def _kelly_optimization(
        self,
        assets: List[str],
        returns_data: pd.DataFrame,
        max_weight: float,
        min_weight: float
    ) -> Dict[str, float]:
        """Kelly criterion optimization."""
        try:
            weights = {}
            
            for asset in assets:
                if asset in returns_data.columns:
                    asset_returns = returns_data[asset].dropna()
                    
                    # Calculate Kelly fraction for this asset
                    kelly_fraction = self._calculate_kelly_fraction(asset_returns)
                    
                    # Apply constraints
                    kelly_fraction = max(min_weight, min(max_weight, kelly_fraction))
                    weights[asset] = kelly_fraction
            
            # Normalize weights to sum to 1
            total_weight = sum(weights.values())
            if total_weight > 0:
                weights = {k: v / total_weight for k, v in weights.items()}
            else:
                weights = self._equal_weight_optimization(assets)
            
            return weights
            
        except Exception as e:
            print(f"Kelly optimization failed: {e}")
            return self._equal_weight_optimization(assets)
    
    def _equal_weight_optimization(self, assets: List[str]) -> Dict[str, float]:
        """Equal weight allocation."""
        weight = 1.0 / len(assets)
        return {asset: weight for asset in assets}
    
    def _calculate_kelly_fraction(self, returns: pd.Series) -> float:
        """Calculate Kelly criterion fraction for an asset."""
        try:
            # Separate winning and losing returns
            wins = returns[returns > 0]
            losses = returns[returns < 0]
            
            if len(wins) == 0 or len(losses) == 0:
                return 0.0
            
            # Calculate win rate
            win_rate = len(wins) / len(returns)
            
            # Calculate average win and loss
            avg_win = wins.mean()
            avg_loss = abs(losses.mean())
            
            if avg_loss == 0:
                return 0.0
            
            # Kelly formula: f = (bp - q) / b
            # where b = avg_win/avg_loss, p = win_rate, q = 1 - win_rate
            b = avg_win / avg_loss
            p = win_rate
            q = 1 - win_rate
            
            kelly_fraction = (b * p - q) / b
            
            # Ensure non-negative
            return max(0.0, kelly_fraction)
            
        except Exception:
            return 0.0
    
    def _quadratic_optimization(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        target_volatility: float,
        max_weight: float,
        min_weight: float
    ) -> np.ndarray:
        """Simplified quadratic optimization for portfolio weights."""
        n = len(expected_returns)
        
        # Risk aversion parameter (lambda)
        # Higher lambda = more risk averse
        lambda_risk = 1.0
        
        # Objective: minimize w^T * S * w - lambda * mu^T * w
        # This is equivalent to maximizing Sharpe ratio for given risk aversion
        
        # Use iterative approach for simplicity
        # Start with equal weights
        weights = np.ones(n) / n
        
        for iteration in range(20):
            # Calculate gradient
            portfolio_var = np.dot(weights, np.dot(cov_matrix, weights))
            portfolio_vol = np.sqrt(portfolio_var)
            
            # Gradient of variance term
            grad_var = 2 * np.dot(cov_matrix, weights)
            
            # Gradient of expected return term
            grad_return = expected_returns
            
            # Total gradient
            gradient = grad_var - lambda_risk * grad_return
            
            # Simple gradient descent step
            step_size = 0.01
            new_weights = weights - step_size * gradient
            
            # Apply constraints
            new_weights = np.clip(new_weights, min_weight, max_weight)
            new_weights = new_weights / np.sum(new_weights)  # Normalize
            
            # Check convergence
            if np.allclose(weights, new_weights, rtol=1e-4):
                break
            
            weights = new_weights
        
        return weights
    
    def calculate_portfolio_metrics(
        self,
        weights: Dict[str, float],
        returns_data: pd.DataFrame
    ) -> Dict[str, float]:
        """Calculate portfolio performance metrics."""
        try:
            # Ensure all assets in weights exist in returns_data
            available_assets = [asset for asset in weights.keys() if asset in returns_data.columns]
            if not available_assets:
                return {"error": "No matching assets found"}
            
            # Filter data and weights
            filtered_returns = returns_data[available_assets]
            filtered_weights = {asset: weights[asset] for asset in available_assets}
            
            # Normalize weights
            total_weight = sum(filtered_weights.values())
            if total_weight > 0:
                normalized_weights = np.array([filtered_weights[asset] for asset in available_assets])
                normalized_weights = normalized_weights / total_weight
            else:
                return {"error": "Invalid weights"}
            
            # Calculate portfolio returns
            portfolio_returns = filtered_returns.dot(normalized_weights)
            
            # Calculate metrics
            expected_return = portfolio_returns.mean() * 252  # Annualized
            volatility = portfolio_returns.std() * np.sqrt(252)  # Annualized
            
            # Sharpe ratio
            sharpe_ratio = (expected_return - self.risk_free_rate) / volatility if volatility > 0 else 0
            
            # Maximum drawdown
            cumulative_returns = (1 + portfolio_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # Value at Risk (95%)
            var_95 = np.percentile(portfolio_returns, 5)
            
            return {
                "expected_return": expected_return,
                "volatility": volatility,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "var_95": var_95,
                "weights": dict(zip(available_assets, normalized_weights)),
                "num_assets": len(available_assets)
            }
            
        except Exception as e:
            return {"error": f"Calculation failed: {str(e)}"}
    
    def calculate_correlation_matrix(self, returns_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate and return correlation matrix."""
        return returns_data.corr()
    
    def suggest_rebalancing(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        transaction_costs: float = 0.001,
        threshold: float = 0.05
    ) -> Dict[str, any]:
        """Suggest rebalancing trades based on weight differences."""
        trades = []
        total_transaction_cost = 0
        
        # Calculate weight differences
        all_assets = set(current_weights.keys()) | set(target_weights.keys())
        
        for asset in all_assets:
            current_weight = current_weights.get(asset, 0.0)
            target_weight = target_weights.get(asset, 0.0)
            weight_diff = target_weight - current_weight
            
            if abs(weight_diff) > threshold:
                trade_type = "BUY" if weight_diff > 0 else "SELL"
                trade_size = abs(weight_diff)
                cost = trade_size * transaction_costs
                
                trades.append({
                    "asset": asset,
                    "action": trade_type,
                    "size": trade_size,
                    "transaction_cost": cost,
                    "current_weight": current_weight,
                    "target_weight": target_weight
                })
                
                total_transaction_cost += cost
        
        return {
            "trades": trades,
            "total_trades": len(trades),
            "total_transaction_cost": total_transaction_cost,
            "should_rebalance": len(trades) > 0
        }
    
    def volatility_targeting(
        self,
        weights: Dict[str, float],
        returns_data: pd.DataFrame,
        target_volatility: float = 0.15
    ) -> Dict[str, float]:
        """Adjust portfolio weights to target volatility."""
        try:
            # Calculate current portfolio volatility
            metrics = self.calculate_portfolio_metrics(weights, returns_data)
            current_vol = metrics.get("volatility", 0.15)
            
            if current_vol <= 0:
                return weights
            
            # Calculate volatility scaling factor
            scaling_factor = target_volatility / current_vol
            
            # Apply scaling (this is a simplified approach)
            # In practice, you might want to use leverage or cash allocation
            if scaling_factor < 1.0:
                # Reduce risk by scaling down weights
                scaled_weights = {asset: weight * scaling_factor for asset, weight in weights.items()}
                
                # Add cash allocation
                cash_weight = 1.0 - sum(scaled_weights.values())
                scaled_weights["CASH"] = cash_weight
                
                return scaled_weights
            else:
                # Current volatility is below target - could add leverage
                # For safety, just return original weights
                return weights
                
        except Exception as e:
            print(f"Volatility targeting failed: {e}")
            return weights
