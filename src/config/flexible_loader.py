"""
Flexible Configuration Loader
Applies risk profiles and makes allocation percentages configurable.
"""

import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class FlexibleConfigLoader:
    """
    Loads and applies flexible configuration with risk profiles.
    """
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        self._apply_risk_profile()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            raise Exception(f"Failed to load config: {str(e)}")
    
    def _apply_risk_profile(self):
        """Apply risk profile settings to configuration."""
        try:
            risk_profile = self.config.get("risk_profile", "moderate")
            risk_presets = self.config.get("risk_presets", {})
            
            if risk_profile in risk_presets:
                preset = risk_presets[risk_profile]
                
                # Apply portfolio allocation
                portfolio_allocation = self.config.get("portfolio_allocation", {})
                portfolio_allocation.update({
                    "bitcoin_allocation_pct": preset.get("bitcoin_allocation_pct", 60.0),
                    "ethereum_allocation_pct": preset.get("ethereum_allocation_pct", 30.0),
                    "altcoins_allocation_pct": preset.get("altcoins_allocation_pct", 10.0)
                })
                self.config["portfolio_allocation"] = portfolio_allocation
                
                # Apply advanced strategies settings
                advanced_strategies = self.config.get("advanced_strategies", {})
                advanced_strategies.update({
                    "bitcoin_multi_bucket": {"enabled": preset.get("use_advanced_strategies", True)},
                    "ethereum_staking_trading": {"enabled": preset.get("use_advanced_strategies", True)},
                    "derivatives_integration": {"enabled": preset.get("use_derivatives_signals", True)},
                    "onchain_metrics": {"enabled": preset.get("use_onchain_signals", True)}
                })
                self.config["advanced_strategies"] = advanced_strategies
                
                # Apply risk management settings
                risk_management = self.config.get("risk_management", {})
                risk_management.update({
                    "position_sizing": {
                        "risk_per_trade_pct": preset.get("risk_per_trade_pct", 1.0),
                        "max_position_size_pct": preset.get("max_position_size_pct", 10.0)
                    }
                })
                self.config["risk_management"] = risk_management
                
        except Exception as e:
            print(f"Warning: Failed to apply risk profile: {str(e)}")
    
    def get_portfolio_allocation(self) -> Dict[str, float]:
        """Get portfolio allocation percentages."""
        portfolio_allocation = self.config.get("portfolio_allocation", {})
        return {
            "bitcoin_allocation_pct": portfolio_allocation.get("bitcoin_allocation_pct", 60.0),
            "ethereum_allocation_pct": portfolio_allocation.get("ethereum_allocation_pct", 30.0),
            "altcoins_allocation_pct": portfolio_allocation.get("altcoins_allocation_pct", 10.0)
        }
    
    def get_rebalancing_settings(self) -> Dict[str, Any]:
        """Get rebalancing settings."""
        portfolio_allocation = self.config.get("portfolio_allocation", {})
        rebalancing = portfolio_allocation.get("rebalancing", {})
        return {
            "enabled": rebalancing.get("enabled", True),
            "threshold_pct": rebalancing.get("threshold_pct", 10.0),
            "min_interval_days": rebalancing.get("min_interval_days", 30),
            "max_rebalance_pct": rebalancing.get("max_rebalance_pct", 5.0)
        }
    
    def is_advanced_strategy_enabled(self, strategy_name: str) -> bool:
        """Check if an advanced strategy is enabled."""
        advanced_strategies = self.config.get("advanced_strategies", {})
        strategy_config = advanced_strategies.get(strategy_name, {})
        return strategy_config.get("enabled", True)
    
    def is_derivatives_enabled(self) -> bool:
        """Check if derivatives integration is enabled."""
        advanced_strategies = self.config.get("advanced_strategies", {})
        derivatives = advanced_strategies.get("derivatives_integration", {})
        return derivatives.get("enabled", True)
    
    def is_onchain_enabled(self) -> bool:
        """Check if on-chain metrics are enabled."""
        advanced_strategies = self.config.get("advanced_strategies", {})
        onchain = advanced_strategies.get("onchain_metrics", {})
        return onchain.get("enabled", True)
    
    def get_coin_strategy(self, coin_id: str) -> str:
        """Get strategy name for a specific coin."""
        tracked_coins = self.config.get("tracked_coins", {})
        coin_config = tracked_coins.get(coin_id, {})
        strategy_config = coin_config.get("strategy", {})
        return strategy_config.get("name", "momentum")
    
    def should_use_advanced_strategy(self, coin_id: str) -> bool:
        """Check if coin should use advanced strategy."""
        strategy_name = self.get_coin_strategy(coin_id)
        
        if strategy_name == "bitcoin_multi_bucket":
            return self.is_advanced_strategy_enabled("bitcoin_multi_bucket")
        elif strategy_name == "ethereum_staking_trading":
            return self.is_advanced_strategy_enabled("ethereum_staking_trading")
        else:
            return False  # Simple strategies
    
    def get_risk_management_settings(self) -> Dict[str, Any]:
        """Get risk management settings."""
        return self.config.get("risk_management", {})
    
    def get_config(self) -> Dict[str, Any]:
        """Get the full configuration."""
        return self.config
    
    def create_simple_config(self, risk_profile: str = "conservative") -> Dict[str, Any]:
        """Create a simple configuration for users who want basic trading."""
        simple_config = {
            "risk_profile": risk_profile,
            "portfolio_allocation": {
                "bitcoin_allocation_pct": 70.0 if risk_profile == "conservative" else 50.0,
                "ethereum_allocation_pct": 25.0 if risk_profile == "conservative" else 35.0,
                "altcoins_allocation_pct": 5.0 if risk_profile == "conservative" else 15.0,
                "rebalancing": {
                    "enabled": True,
                    "threshold_pct": 15.0,
                    "min_interval_days": 30
                }
            },
            "advanced_strategies": {
                "bitcoin_multi_bucket": {"enabled": False},
                "ethereum_staking_trading": {"enabled": False},
                "derivatives_integration": {"enabled": False},
                "onchain_metrics": {"enabled": False},
                "volatility_regime_classification": {"enabled": False}
            },
            "tracked_coins": {
                "bitcoin": {
                    "strategy": {"name": "momentum"},
                    "risk": {"atr": {"period": 14, "sl_mult": 2.0, "tp_mult": 3.0}}
                },
                "ethereum": {
                    "strategy": {"name": "momentum"},
                    "risk": {"atr": {"period": 14, "sl_mult": 2.0, "tp_mult": 3.0}}
                }
            },
            "risk_management": {
                "max_daily_loss_pct": 3.0 if risk_profile == "conservative" else 5.0,
                "max_drawdown_pct": 10.0 if risk_profile == "conservative" else 15.0,
                "position_sizing": {
                    "method": "fixed",
                    "risk_per_trade_pct": 0.5 if risk_profile == "conservative" else 1.0,
                    "max_position_size_pct": 5.0 if risk_profile == "conservative" else 10.0
                }
            }
        }
        return simple_config


def create_config_for_risk_profile(risk_profile: str) -> str:
    """
    Create a configuration file for a specific risk profile.
    
    Args:
        risk_profile: "conservative", "moderate", or "aggressive"
    
    Returns:
        Path to the created configuration file
    """
    loader = FlexibleConfigLoader("config/paper_24_7_optimized.yaml")
    simple_config = loader.create_simple_config(risk_profile)
    
    config_filename = f"config/paper_24_7_{risk_profile}.yaml"
    
    with open(config_filename, 'w') as file:
        yaml.dump(simple_config, file, default_flow_style=False, indent=2)
    
    return config_filename


def get_allocation_summary(config_path: str) -> str:
    """
    Get a human-readable summary of the allocation configuration.
    
    Args:
        config_path: Path to configuration file
    
    Returns:
        String summary of allocation settings
    """
    try:
        loader = FlexibleConfigLoader(config_path)
        allocation = loader.get_portfolio_allocation()
        rebalancing = loader.get_rebalancing_settings()
        
        summary = f"""
📊 PORTFOLIO ALLOCATION SUMMARY
===============================

🎯 Asset Allocation:
   • Bitcoin: {allocation['bitcoin_allocation_pct']:.1f}% of crypto portfolio
   • Ethereum: {allocation['ethereum_allocation_pct']:.1f}% of crypto portfolio  
   • Altcoins: {allocation['altcoins_allocation_pct']:.1f}% of crypto portfolio

🔄 Rebalancing:
   • Enabled: {'Yes' if rebalancing['enabled'] else 'No'}
   • Threshold: ±{rebalancing['threshold_pct']:.1f}% deviation
   • Min Interval: {rebalancing['min_interval_days']} days

🚀 Advanced Features:
   • Bitcoin Multi-Bucket: {'Enabled' if loader.is_advanced_strategy_enabled('bitcoin_multi_bucket') else 'Disabled'}
   • Ethereum Staking: {'Enabled' if loader.is_advanced_strategy_enabled('ethereum_staking_trading') else 'Disabled'}
   • Derivatives Signals: {'Enabled' if loader.is_derivatives_enabled() else 'Disabled'}
   • On-Chain Metrics: {'Enabled' if loader.is_onchain_enabled() else 'Disabled'}

💡 Example with $100,000 portfolio:
   • Bitcoin: ${allocation['bitcoin_allocation_pct'] * 1000:.0f}
   • Ethereum: ${allocation['ethereum_allocation_pct'] * 1000:.0f}
   • Altcoins: ${allocation['altcoins_allocation_pct'] * 1000:.0f}
        """
        
        return summary
        
    except Exception as e:
        return f"Error generating allocation summary: {str(e)}"
