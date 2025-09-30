"""
Bitcoin Core Allocation System
Implements core HODL allocation with rebalancing triggers.
"""

import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
import numpy as np


class BitcoinCoreAllocation:
    """
    Manages Bitcoin core HODL allocation with automatic rebalancing.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Core allocation parameters
        self.target_allocation_pct = self.config.get("core_allocation_pct", 60.0)  # 60% of crypto allocation
        self.rebalance_threshold = self.config.get("core_rebalance_threshold", 10.0)  # ±10% threshold
        self.min_rebalance_interval = self.config.get("min_rebalance_interval", 30)  # 30 days
        
        # Portfolio parameters
        self.total_crypto_allocation = self.config.get("total_crypto_allocation", 100000.0)
        self.bitcoin_price = self.config.get("bitcoin_price", 100000.0)
        
        # State tracking
        self.current_bitcoin_value = 0.0
        self.current_allocation_pct = 0.0
        self.last_rebalance_date = None
        self.rebalance_count = 0
        
        # Rebalancing history
        self.rebalance_history = []
        
    def calculate_current_allocation(self, bitcoin_quantity: float, bitcoin_price: float) -> Dict[str, Any]:
        """
        Calculate current Bitcoin allocation percentage.
        
        Args:
            bitcoin_quantity: Current Bitcoin holdings
            bitcoin_price: Current Bitcoin price
        
        Returns:
            Dict with allocation data
        """
        try:
            # Update current values
            self.bitcoin_price = bitcoin_price
            self.current_bitcoin_value = bitcoin_quantity * bitcoin_price
            
            # Calculate current allocation percentage
            if self.total_crypto_allocation > 0:
                self.current_allocation_pct = (self.current_bitcoin_value / self.total_crypto_allocation) * 100.0
            else:
                self.current_allocation_pct = 0.0
            
            # Calculate target values
            target_bitcoin_value = self.total_crypto_allocation * (self.target_allocation_pct / 100.0)
            target_bitcoin_quantity = target_bitcoin_value / bitcoin_price
            
            # Calculate deviation
            allocation_deviation = self.current_allocation_pct - self.target_allocation_pct
            
            return {
                "current_allocation_pct": self.current_allocation_pct,
                "target_allocation_pct": self.target_allocation_pct,
                "allocation_deviation": allocation_deviation,
                "current_bitcoin_value": self.current_bitcoin_value,
                "target_bitcoin_value": target_bitcoin_value,
                "current_bitcoin_quantity": bitcoin_quantity,
                "target_bitcoin_quantity": target_bitcoin_quantity,
                "bitcoin_price": bitcoin_price,
                "success": True
            }
            
        except Exception as e:
            return {
                "current_allocation_pct": 0.0,
                "target_allocation_pct": self.target_allocation_pct,
                "allocation_deviation": 0.0,
                "current_bitcoin_value": 0.0,
                "target_bitcoin_value": 0.0,
                "current_bitcoin_quantity": 0.0,
                "target_bitcoin_quantity": 0.0,
                "bitcoin_price": bitcoin_price,
                "error": str(e),
                "success": False
            }
    
    def check_rebalance_trigger(self, bitcoin_quantity: float, bitcoin_price: float) -> Dict[str, Any]:
        """
        Check if rebalancing is triggered.
        
        Args:
            bitcoin_quantity: Current Bitcoin holdings
            bitcoin_price: Current Bitcoin price
        
        Returns:
            Dict with rebalance decision
        """
        try:
            # Calculate current allocation
            allocation_data = self.calculate_current_allocation(bitcoin_quantity, bitcoin_price)
            
            if not allocation_data["success"]:
                return {"rebalance_needed": False, "reason": "allocation_calculation_failed"}
            
            allocation_deviation = allocation_data["allocation_deviation"]
            
            # Check if deviation exceeds threshold
            if abs(allocation_deviation) > self.rebalance_threshold:
                # Check minimum rebalance interval
                if self._can_rebalance():
                    return {
                        "rebalance_needed": True,
                        "reason": f"allocation_deviation_{allocation_deviation:.1f}%",
                        "allocation_data": allocation_data
                    }
                else:
                    return {
                        "rebalance_needed": False,
                        "reason": "min_rebalance_interval_not_met"
                    }
            else:
                return {
                    "rebalance_needed": False,
                    "reason": "allocation_within_threshold"
                }
            
        except Exception as e:
            return {
                "rebalance_needed": False,
                "reason": f"error: {str(e)}"
            }
    
    def calculate_rebalance_action(self, bitcoin_quantity: float, bitcoin_price: float) -> Dict[str, Any]:
        """
        Calculate rebalancing action.
        
        Args:
            bitcoin_quantity: Current Bitcoin holdings
            bitcoin_price: Current Bitcoin price
        
        Returns:
            Dict with rebalancing action
        """
        try:
            # Check if rebalancing is needed
            rebalance_check = self.check_rebalance_trigger(bitcoin_quantity, bitcoin_price)
            
            if not rebalance_check["rebalance_needed"]:
                return {
                    "action": "none",
                    "reason": rebalance_check["reason"],
                    "success": True
                }
            
            allocation_data = rebalance_check["allocation_data"]
            allocation_deviation = allocation_data["allocation_deviation"]
            
            # Calculate rebalancing action
            if allocation_deviation > 0:
                # Over-allocated to Bitcoin - sell Bitcoin
                action = "sell"
                quantity_to_adjust = allocation_data["current_bitcoin_quantity"] - allocation_data["target_bitcoin_quantity"]
                value_to_adjust = quantity_to_adjust * bitcoin_price
                
            else:
                # Under-allocated to Bitcoin - buy Bitcoin
                action = "buy"
                quantity_to_adjust = allocation_data["target_bitcoin_quantity"] - allocation_data["current_bitcoin_quantity"]
                value_to_adjust = quantity_to_adjust * bitcoin_price
            
            # Record rebalancing action
            self._record_rebalance(action, quantity_to_adjust, value_to_adjust, bitcoin_price)
            
            return {
                "action": action,
                "quantity_to_adjust": quantity_to_adjust,
                "value_to_adjust": value_to_adjust,
                "allocation_deviation": allocation_deviation,
                "reason": f"rebalance_to_target_{self.target_allocation_pct}%",
                "success": True
            }
            
        except Exception as e:
            return {
                "action": "none",
                "quantity_to_adjust": 0.0,
                "value_to_adjust": 0.0,
                "allocation_deviation": 0.0,
                "error": str(e),
                "success": False
            }
    
    def _can_rebalance(self) -> bool:
        """Check if enough time has passed since last rebalancing."""
        try:
            if self.last_rebalance_date is None:
                return True
            
            current_date = datetime.now(timezone.utc)
            days_since_rebalance = (current_date - self.last_rebalance_date).days
            
            return days_since_rebalance >= self.min_rebalance_interval
            
        except Exception:
            return False
    
    def _record_rebalance(self, action: str, quantity: float, value: float, price: float):
        """Record rebalancing action in history."""
        try:
            rebalance_record = {
                "timestamp": datetime.now(timezone.utc),
                "action": action,
                "quantity": quantity,
                "value": value,
                "price": price,
                "allocation_before": self.current_allocation_pct,
                "allocation_after": self.target_allocation_pct
            }
            
            self.rebalance_history.append(rebalance_record)
            self.last_rebalance_date = datetime.now(timezone.utc)
            self.rebalance_count += 1
            
            # Keep only recent history
            if len(self.rebalance_history) > 100:
                self.rebalance_history = self.rebalance_history[-100:]
                
        except Exception:
            pass
    
    def get_rebalance_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent rebalancing history."""
        try:
            return self.rebalance_history[-limit:] if self.rebalance_history else []
        except Exception:
            return []
    
    def get_allocation_status(self, bitcoin_quantity: float, bitcoin_price: float) -> Dict[str, Any]:
        """Get comprehensive allocation status."""
        try:
            allocation_data = self.calculate_current_allocation(bitcoin_quantity, bitcoin_price)
            rebalance_check = self.check_rebalance_trigger(bitcoin_quantity, bitcoin_price)
            
            return {
                "current_allocation_pct": allocation_data["current_allocation_pct"],
                "target_allocation_pct": allocation_data["target_allocation_pct"],
                "allocation_deviation": allocation_data["allocation_deviation"],
                "rebalance_needed": rebalance_check["rebalance_needed"],
                "rebalance_reason": rebalance_check["reason"],
                "can_rebalance": self._can_rebalance(),
                "days_since_last_rebalance": self._get_days_since_last_rebalance(),
                "rebalance_count": self.rebalance_count,
                "success": True
            }
            
        except Exception as e:
            return {
                "current_allocation_pct": 0.0,
                "target_allocation_pct": self.target_allocation_pct,
                "allocation_deviation": 0.0,
                "rebalance_needed": False,
                "rebalance_reason": "error",
                "can_rebalance": False,
                "days_since_last_rebalance": 0,
                "rebalance_count": 0,
                "error": str(e),
                "success": False
            }
    
    def _get_days_since_last_rebalance(self) -> int:
        """Get days since last rebalancing."""
        try:
            if self.last_rebalance_date is None:
                return 0
            
            current_date = datetime.now(timezone.utc)
            return (current_date - self.last_rebalance_date).days
            
        except Exception:
            return 0
    
    def update_total_crypto_allocation(self, new_allocation: float):
        """Update total crypto allocation value."""
        self.total_crypto_allocation = new_allocation
    
    def update_target_allocation(self, new_target_pct: float):
        """Update target allocation percentage."""
        self.target_allocation_pct = new_target_pct


class BitcoinDipLadder:
    """
    Implements Bitcoin dip ladder accumulation system.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Dip ladder parameters
        self.dip_levels = self.config.get("dip_levels", [5.0, 10.0, 20.0, 35.0, 50.0])  # % drawdowns
        self.dip_weights = self.config.get("dip_weights", [0.4, 0.3, 0.2, 0.1, 0.0])     # Allocation weights
        self.exchange_flow_filter = self.config.get("exchange_flow_filter", True)
        
        # State tracking
        self.local_peaks = []
        self.dip_triggers = []
        self.accumulation_history = []
        
        # Exchange flow data
        self.exchange_flow_data = {}
        
    def calculate_dip_signal(self, data: pd.DataFrame, current_price: float) -> Dict[str, Any]:
        """
        Calculate dip ladder signal.
        
        Args:
            data: Price data
            current_price: Current Bitcoin price
        
        Returns:
            Dict with dip signal
        """
        try:
            # Calculate local peak
            peak_price = self._calculate_local_peak(data)
            
            # Calculate drawdown
            drawdown = self._calculate_drawdown(current_price, peak_price)
            
            # Check if drawdown matches any ladder level
            for i, level in enumerate(self.dip_levels):
                if abs(drawdown - level) < 1.0:  # Within 1% of ladder level
                    weight = self.dip_weights[i]
                    if weight > 0:
                        # Check exchange flow filter
                        if self.exchange_flow_filter:
                            flow_ok = self._check_exchange_flow_filter()
                        else:
                            flow_ok = True
                        
                        if flow_ok:
                            # Calculate allocation amount
                            allocation_amount = self._calculate_allocation_amount(weight, current_price)
                            
                            return {
                                "signal": 1,  # Buy signal
                                "confidence": weight,
                                "drawdown": drawdown,
                                "dip_level": level,
                                "allocation_amount": allocation_amount,
                                "reason": f"dip_ladder_{level}%",
                                "success": True
                            }
            
            return {
                "signal": 0,
                "confidence": 0.0,
                "drawdown": drawdown,
                "dip_level": 0.0,
                "allocation_amount": 0.0,
                "reason": "no_dip_trigger",
                "success": True
            }
            
        except Exception as e:
            return {
                "signal": 0,
                "confidence": 0.0,
                "drawdown": 0.0,
                "dip_level": 0.0,
                "allocation_amount": 0.0,
                "error": str(e),
                "success": False
            }
    
    def _calculate_local_peak(self, data: pd.DataFrame, window: int = 20) -> float:
        """Calculate local peak price."""
        try:
            closes = data["close"].tolist()
            if len(closes) < window:
                return closes[-1] if closes else 0.0
            
            recent_closes = closes[-window:]
            return max(recent_closes)
        except Exception:
            return 0.0
    
    def _calculate_drawdown(self, current_price: float, peak_price: float) -> float:
        """Calculate drawdown percentage."""
        try:
            if peak_price <= 0:
                return 0.0
            return ((peak_price - current_price) / peak_price) * 100.0
        except Exception:
            return 0.0
    
    def _check_exchange_flow_filter(self) -> bool:
        """Check exchange flow filter (placeholder)."""
        try:
            # Placeholder: would check actual exchange flow data
            # For now, assume flow is OK
            return True
        except Exception:
            return False
    
    def _calculate_allocation_amount(self, weight: float, current_price: float) -> float:
        """Calculate allocation amount based on weight."""
        try:
            # Placeholder: would use actual portfolio value
            base_allocation = 10000.0  # $10,000 base allocation
            return base_allocation * weight
        except Exception:
            return 0.0
