"""
On-Chain Metrics Integration
Integrates exchange flows, active addresses, and other on-chain data.
"""

import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
import requests
import json


class OnChainDataProvider:
    """
    Provides on-chain metrics data including exchange flows, active addresses, etc.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # API endpoints (placeholders - would use real APIs)
        self.glassnode_api = self.config.get("glassnode_api", "https://api.glassnode.com/v1/metrics")
        self.cryptoquant_api = self.config.get("cryptoquant_api", "https://api.cryptoquant.com/v1")
        self.messari_api = self.config.get("messari_api", "https://data.messari.io/api/v1")
        
        # Cache settings
        self.cache_ttl = self.config.get("cache_ttl", 3600)  # 1 hour
        self.cache = {}
        
        # Thresholds
        self.exchange_flow_threshold = self.config.get("exchange_flow_threshold", 1000)  # BTC
        self.active_addresses_threshold = self.config.get("active_addresses_threshold", 0.1)  # 10% change
        self.supply_on_exchanges_threshold = self.config.get("supply_on_exchanges_threshold", 0.05)  # 5% change
        
    def get_exchange_flows(self, symbol: str, period: str = "24h") -> Dict[str, Any]:
        """
        Get exchange inflow/outflow data.
        
        Returns:
            Dict with exchange flow data and metadata
        """
        try:
            # Check cache first
            cache_key = f"exchange_flows_{symbol}_{period}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            # Placeholder: would fetch real exchange flow data
            # For now, simulate exchange flow data
            flow_data = self._simulate_exchange_flows(symbol, period)
            
            result = {
                "symbol": symbol,
                "period": period,
                "inflow": flow_data["inflow"],
                "outflow": flow_data["outflow"],
                "net_flow": flow_data["net_flow"],
                "inflow_change_pct": flow_data["inflow_change_pct"],
                "outflow_change_pct": flow_data["outflow_change_pct"],
                "net_flow_change_pct": flow_data["net_flow_change_pct"],
                "timestamp": datetime.now(timezone.utc).timestamp(),
                "success": True
            }
            
            # Cache result
            self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            return {
                "symbol": symbol,
                "period": period,
                "inflow": 0.0,
                "outflow": 0.0,
                "net_flow": 0.0,
                "inflow_change_pct": 0.0,
                "outflow_change_pct": 0.0,
                "net_flow_change_pct": 0.0,
                "timestamp": 0,
                "error": str(e),
                "success": False
            }
    
    def get_active_addresses(self, symbol: str, period: str = "24h") -> Dict[str, Any]:
        """
        Get active addresses data.
        
        Returns:
            Dict with active addresses data and metadata
        """
        try:
            # Check cache first
            cache_key = f"active_addresses_{symbol}_{period}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            # Placeholder: would fetch real active addresses data
            # For now, simulate active addresses data
            addresses_data = self._simulate_active_addresses(symbol, period)
            
            result = {
                "symbol": symbol,
                "period": period,
                "active_addresses": addresses_data["active_addresses"],
                "new_addresses": addresses_data["new_addresses"],
                "active_addresses_change_pct": addresses_data["active_addresses_change_pct"],
                "new_addresses_change_pct": addresses_data["new_addresses_change_pct"],
                "timestamp": datetime.now(timezone.utc).timestamp(),
                "success": True
            }
            
            # Cache result
            self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            return {
                "symbol": symbol,
                "period": period,
                "active_addresses": 0,
                "new_addresses": 0,
                "active_addresses_change_pct": 0.0,
                "new_addresses_change_pct": 0.0,
                "timestamp": 0,
                "error": str(e),
                "success": False
            }
    
    def get_supply_on_exchanges(self, symbol: str) -> Dict[str, Any]:
        """
        Get supply on exchanges data.
        
        Returns:
            Dict with supply on exchanges data and metadata
        """
        try:
            # Check cache first
            cache_key = f"supply_on_exchanges_{symbol}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            # Placeholder: would fetch real supply on exchanges data
            # For now, simulate supply on exchanges data
            supply_data = self._simulate_supply_on_exchanges(symbol)
            
            result = {
                "symbol": symbol,
                "supply_on_exchanges": supply_data["supply_on_exchanges"],
                "supply_on_exchanges_pct": supply_data["supply_on_exchanges_pct"],
                "supply_change_pct": supply_data["supply_change_pct"],
                "timestamp": datetime.now(timezone.utc).timestamp(),
                "success": True
            }
            
            # Cache result
            self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            return {
                "symbol": symbol,
                "supply_on_exchanges": 0.0,
                "supply_on_exchanges_pct": 0.0,
                "supply_change_pct": 0.0,
                "timestamp": 0,
                "error": str(e),
                "success": False
            }
    
    def get_whale_movements(self, symbol: str, period: str = "24h") -> Dict[str, Any]:
        """
        Get whale movement data.
        
        Returns:
            Dict with whale movement data and metadata
        """
        try:
            # Check cache first
            cache_key = f"whale_movements_{symbol}_{period}"
            if self._is_cache_valid(cache_key):
                return self.cache[cache_key]
            
            # Placeholder: would fetch real whale movement data
            # For now, simulate whale movement data
            whale_data = self._simulate_whale_movements(symbol, period)
            
            result = {
                "symbol": symbol,
                "period": period,
                "large_transfers": whale_data["large_transfers"],
                "whale_accumulation": whale_data["whale_accumulation"],
                "whale_distribution": whale_data["whale_distribution"],
                "net_whale_flow": whale_data["net_whale_flow"],
                "timestamp": datetime.now(timezone.utc).timestamp(),
                "success": True
            }
            
            # Cache result
            self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            return {
                "symbol": symbol,
                "period": period,
                "large_transfers": 0,
                "whale_accumulation": 0.0,
                "whale_distribution": 0.0,
                "net_whale_flow": 0.0,
                "timestamp": 0,
                "error": str(e),
                "success": False
            }
    
    def _simulate_exchange_flows(self, symbol: str, period: str) -> Dict[str, float]:
        """Simulate exchange flow data (placeholder)."""
        import random
        
        # Simulate realistic exchange flows
        base_inflow = 1000 if symbol.lower() == "btc" else 100
        base_outflow = 950 if symbol.lower() == "btc" else 95
        
        inflow = base_inflow * random.uniform(0.8, 1.2)
        outflow = base_outflow * random.uniform(0.8, 1.2)
        net_flow = inflow - outflow
        
        return {
            "inflow": inflow,
            "outflow": outflow,
            "net_flow": net_flow,
            "inflow_change_pct": random.uniform(-20, 20),
            "outflow_change_pct": random.uniform(-20, 20),
            "net_flow_change_pct": random.uniform(-30, 30)
        }
    
    def _simulate_active_addresses(self, symbol: str, period: str) -> Dict[str, Any]:
        """Simulate active addresses data (placeholder)."""
        import random
        
        # Simulate realistic active addresses
        base_addresses = 1000000 if symbol.lower() == "btc" else 500000
        
        active_addresses = int(base_addresses * random.uniform(0.9, 1.1))
        new_addresses = int(active_addresses * random.uniform(0.1, 0.3))
        
        return {
            "active_addresses": active_addresses,
            "new_addresses": new_addresses,
            "active_addresses_change_pct": random.uniform(-15, 15),
            "new_addresses_change_pct": random.uniform(-25, 25)
        }
    
    def _simulate_supply_on_exchanges(self, symbol: str) -> Dict[str, float]:
        """Simulate supply on exchanges data (placeholder)."""
        import random
        
        # Simulate realistic supply on exchanges
        base_supply = 1000000 if symbol.lower() == "btc" else 10000000
        supply_on_exchanges = base_supply * random.uniform(0.1, 0.3)
        total_supply = base_supply * 10  # Assume 10x total supply
        
        return {
            "supply_on_exchanges": supply_on_exchanges,
            "supply_on_exchanges_pct": (supply_on_exchanges / total_supply) * 100,
            "supply_change_pct": random.uniform(-5, 5)
        }
    
    def _simulate_whale_movements(self, symbol: str, period: str) -> Dict[str, Any]:
        """Simulate whale movement data (placeholder)."""
        import random
        
        # Simulate realistic whale movements
        large_transfers = random.randint(10, 100)
        whale_accumulation = random.uniform(1000, 10000)
        whale_distribution = random.uniform(800, 9000)
        net_whale_flow = whale_accumulation - whale_distribution
        
        return {
            "large_transfers": large_transfers,
            "whale_accumulation": whale_accumulation,
            "whale_distribution": whale_distribution,
            "net_whale_flow": net_whale_flow
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.cache:
            return False
        
        cached_time = self.cache[cache_key].get("timestamp", 0)
        current_time = datetime.now(timezone.utc).timestamp()
        
        return (current_time - cached_time) < self.cache_ttl
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache a result with timestamp."""
        result["cached_at"] = datetime.now(timezone.utc).timestamp()
        self.cache[cache_key] = result


class OnChainSignalGenerator:
    """
    Generates trading signals based on on-chain metrics.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Signal thresholds
        self.exchange_flow_threshold = self.config.get("exchange_flow_threshold", 1000)
        self.active_addresses_threshold = self.config.get("active_addresses_threshold", 0.1)
        self.supply_on_exchanges_threshold = self.config.get("supply_on_exchanges_threshold", 0.05)
        
        # Data provider
        self.data_provider = OnChainDataProvider(config)
        
    def generate_exchange_flow_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Generate signal based on exchange flows.
        
        Returns:
            Dict with signal and metadata
        """
        try:
            flow_data = self.data_provider.get_exchange_flows(symbol)
            if not flow_data["success"]:
                return {"signal": 0, "confidence": 0.0, "reason": "data_error"}
            
            net_flow = flow_data["net_flow"]
            net_flow_change_pct = flow_data["net_flow_change_pct"]
            
            # Generate signal based on exchange flows
            if net_flow < -self.exchange_flow_threshold:
                # Large net outflow - bullish signal
                signal = 1
                confidence = min(1.0, abs(net_flow) / (self.exchange_flow_threshold * 2))
                reason = f"large_outflow_{net_flow:.0f}"
            elif net_flow > self.exchange_flow_threshold:
                # Large net inflow - bearish signal
                signal = -1
                confidence = min(1.0, abs(net_flow) / (self.exchange_flow_threshold * 2))
                reason = f"large_inflow_{net_flow:.0f}"
            else:
                # Neutral flow
                signal = 0
                confidence = 0.0
                reason = "neutral_flow"
            
            return {
                "signal": signal,
                "confidence": confidence,
                "reason": reason,
                "net_flow": net_flow,
                "net_flow_change_pct": net_flow_change_pct,
                "success": True
            }
            
        except Exception as e:
            return {
                "signal": 0,
                "confidence": 0.0,
                "reason": f"error: {str(e)}",
                "success": False
            }
    
    def generate_active_addresses_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Generate signal based on active addresses.
        
        Returns:
            Dict with signal and metadata
        """
        try:
            addresses_data = self.data_provider.get_active_addresses(symbol)
            if not addresses_data["success"]:
                return {"signal": 0, "confidence": 0.0, "reason": "data_error"}
            
            active_addresses_change_pct = addresses_data["active_addresses_change_pct"]
            new_addresses_change_pct = addresses_data["new_addresses_change_pct"]
            
            # Generate signal based on active addresses
            if active_addresses_change_pct > self.active_addresses_threshold * 100:
                # Significant increase in active addresses - bullish
                signal = 1
                confidence = min(1.0, active_addresses_change_pct / 20)
                reason = f"active_addresses_up_{active_addresses_change_pct:.1f}%"
            elif active_addresses_change_pct < -self.active_addresses_threshold * 100:
                # Significant decrease in active addresses - bearish
                signal = -1
                confidence = min(1.0, abs(active_addresses_change_pct) / 20)
                reason = f"active_addresses_down_{active_addresses_change_pct:.1f}%"
            else:
                # Neutral change
                signal = 0
                confidence = 0.0
                reason = "neutral_addresses"
            
            return {
                "signal": signal,
                "confidence": confidence,
                "reason": reason,
                "active_addresses_change_pct": active_addresses_change_pct,
                "new_addresses_change_pct": new_addresses_change_pct,
                "success": True
            }
            
        except Exception as e:
            return {
                "signal": 0,
                "confidence": 0.0,
                "reason": f"error: {str(e)}",
                "success": False
            }
    
    def generate_supply_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Generate signal based on supply on exchanges.
        
        Returns:
            Dict with signal and metadata
        """
        try:
            supply_data = self.data_provider.get_supply_on_exchanges(symbol)
            if not supply_data["success"]:
                return {"signal": 0, "confidence": 0.0, "reason": "data_error"}
            
            supply_change_pct = supply_data["supply_change_pct"]
            supply_on_exchanges_pct = supply_data["supply_on_exchanges_pct"]
            
            # Generate signal based on supply on exchanges
            if supply_change_pct < -self.supply_on_exchanges_threshold * 100:
                # Decrease in supply on exchanges - bullish
                signal = 1
                confidence = min(1.0, abs(supply_change_pct) / 10)
                reason = f"supply_decrease_{supply_change_pct:.1f}%"
            elif supply_change_pct > self.supply_on_exchanges_threshold * 100:
                # Increase in supply on exchanges - bearish
                signal = -1
                confidence = min(1.0, supply_change_pct / 10)
                reason = f"supply_increase_{supply_change_pct:.1f}%"
            else:
                # Neutral change
                signal = 0
                confidence = 0.0
                reason = "neutral_supply"
            
            return {
                "signal": signal,
                "confidence": confidence,
                "reason": reason,
                "supply_change_pct": supply_change_pct,
                "supply_on_exchanges_pct": supply_on_exchanges_pct,
                "success": True
            }
            
        except Exception as e:
            return {
                "signal": 0,
                "confidence": 0.0,
                "reason": f"error: {str(e)}",
                "success": False
            }
    
    def generate_whale_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Generate signal based on whale movements.
        
        Returns:
            Dict with signal and metadata
        """
        try:
            whale_data = self.data_provider.get_whale_movements(symbol)
            if not whale_data["success"]:
                return {"signal": 0, "confidence": 0.0, "reason": "data_error"}
            
            net_whale_flow = whale_data["net_whale_flow"]
            large_transfers = whale_data["large_transfers"]
            
            # Generate signal based on whale movements
            if net_whale_flow > 1000:  # Significant whale accumulation
                signal = 1
                confidence = min(1.0, net_whale_flow / 5000)
                reason = f"whale_accumulation_{net_whale_flow:.0f}"
            elif net_whale_flow < -1000:  # Significant whale distribution
                signal = -1
                confidence = min(1.0, abs(net_whale_flow) / 5000)
                reason = f"whale_distribution_{net_whale_flow:.0f}"
            else:
                # Neutral whale activity
                signal = 0
                confidence = 0.0
                reason = "neutral_whale_activity"
            
            return {
                "signal": signal,
                "confidence": confidence,
                "reason": reason,
                "net_whale_flow": net_whale_flow,
                "large_transfers": large_transfers,
                "success": True
            }
            
        except Exception as e:
            return {
                "signal": 0,
                "confidence": 0.0,
                "reason": f"error: {str(e)}",
                "success": False
            }
    
    def generate_combined_signal(self, symbol: str) -> Dict[str, Any]:
        """
        Generate combined signal from all on-chain metrics.
        
        Returns:
            Dict with combined signal and metadata
        """
        try:
            # Get individual signals
            flow_signal = self.generate_exchange_flow_signal(symbol)
            addresses_signal = self.generate_active_addresses_signal(symbol)
            supply_signal = self.generate_supply_signal(symbol)
            whale_signal = self.generate_whale_signal(symbol)
            
            # Combine signals with weights
            weights = {
                "flow": 0.3,
                "addresses": 0.25,
                "supply": 0.25,
                "whale": 0.2
            }
            
            # Calculate weighted signal
            weighted_signal = 0.0
            total_confidence = 0.0
            
            if flow_signal["success"]:
                weighted_signal += flow_signal["signal"] * flow_signal["confidence"] * weights["flow"]
                total_confidence += flow_signal["confidence"] * weights["flow"]
            
            if addresses_signal["success"]:
                weighted_signal += addresses_signal["signal"] * addresses_signal["confidence"] * weights["addresses"]
                total_confidence += addresses_signal["confidence"] * weights["addresses"]
            
            if supply_signal["success"]:
                weighted_signal += supply_signal["signal"] * supply_signal["confidence"] * weights["supply"]
                total_confidence += supply_signal["confidence"] * weights["supply"]
            
            if whale_signal["success"]:
                weighted_signal += whale_signal["signal"] * whale_signal["confidence"] * weights["whale"]
                total_confidence += whale_signal["confidence"] * weights["whale"]
            
            # Determine final signal
            if weighted_signal > 0.3:
                final_signal = 1
            elif weighted_signal < -0.3:
                final_signal = -1
            else:
                final_signal = 0
            
            return {
                "signal": final_signal,
                "confidence": total_confidence,
                "weighted_signal": weighted_signal,
                "flow_signal": flow_signal,
                "addresses_signal": addresses_signal,
                "supply_signal": supply_signal,
                "whale_signal": whale_signal,
                "success": True
            }
            
        except Exception as e:
            return {
                "signal": 0,
                "confidence": 0.0,
                "reason": f"error: {str(e)}",
                "success": False
            }
