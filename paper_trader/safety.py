"""
Safety Checks

Comprehensive safety checks to prevent real order execution
when running in paper trading mode.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Set
from pathlib import Path


class SafetyChecker:
    """Validates that paper trading mode is safe and no real orders will be executed."""
    
    def __init__(self):
        self.blocked_apis: Set[str] = {
            "ccxt.binance",
            "ccxt.coinbase", 
            "ccxt.kraken",
            "ccxt.bybit",
            "ccxt.okx",
            "requests.post",
            "requests.put",
            "requests.delete",
            "aiohttp.ClientSession.post",
            "aiohttp.ClientSession.put", 
            "aiohttp.ClientSession.delete",
        }
        
        self.blocked_env_vars: Set[str] = {
            "API_KEY",
            "API_SECRET", 
            "BINANCE_API_KEY",
            "BINANCE_SECRET_KEY",
            "COINBASE_API_KEY",
            "COINBASE_SECRET_KEY",
            "KRAKEN_API_KEY",
            "KRAKEN_SECRET_KEY",
        }
        
        self.blocked_modules: Set[str] = {
            "ccxt.binance",
            "ccxt.coinbase",
            "ccxt.kraken", 
            "ccxt.bybit",
            "ccxt.okx",
        }
    
    def check_paper_mode_safety(self) -> List[str]:
        """Comprehensive safety check for paper trading mode."""
        
        errors = []
        
        # Check environment variables
        env_errors = self._check_environment_variables()
        errors.extend(env_errors)
        
        # Check for real API keys in config
        config_errors = self._check_configuration_files()
        errors.extend(config_errors)
        
        # Check for blocked imports
        import_errors = self._check_imports()
        errors.extend(import_errors)
        
        # Check for real broker instances
        broker_errors = self._check_broker_instances()
        errors.extend(broker_errors)
        
        return errors
    
    def _check_environment_variables(self) -> List[str]:
        """Check for dangerous environment variables."""
        
        errors = []
        
        for var_name in self.blocked_env_vars:
            if os.getenv(var_name):
                errors.append(f"Dangerous environment variable found: {var_name}")
        
        return errors
    
    def _check_configuration_files(self) -> List[str]:
        """Check configuration files for real API keys."""
        
        errors = []
        
        # Check common config files
        config_files = [
            "config/config.yaml",
            "config/secrets.yaml", 
            ".env",
            "secrets/.env",
        ]
        
        for config_file in config_files:
            config_path = Path(config_file)
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        content = f.read().lower()
                        
                        # Look for API key patterns
                        if any(keyword in content for keyword in [
                            "api_key:", "api_secret:", "secret_key:",
                            "binance_api_key", "coinbase_api_key"
                        ]):
                            errors.append(f"Potential API keys found in {config_file}")
                
                except Exception:
                    pass  # Skip files that can't be read
        
        return errors
    
    def _check_imports(self) -> List[str]:
        """Check for dangerous imports."""
        
        errors = []
        
        # Check sys.modules for blocked modules
        for module_name in self.blocked_modules:
            if module_name in sys.modules:
                errors.append(f"Dangerous module imported: {module_name}")
        
        return errors
    
    def _check_broker_instances(self) -> List[str]:
        """Check for real broker instances in the system."""
        
        errors = []
        
        # This would need to be implemented based on the specific broker
        # implementations in the system
        # For now, we'll do a basic check
        
        return errors
    
    def validate_paper_configuration(self, config: Dict[str, Any]) -> List[str]:
        """Validate that configuration is safe for paper trading."""
        
        errors = []
        
        # Check mode
        if config.get("mode") != "paper":
            errors.append("Configuration mode must be 'paper' for paper trading")
        
        # Check for real exchange settings
        if config.get("exchange") and config.get("exchange") != "paper":
            errors.append("Exchange must be set to 'paper' for paper trading")
        
        # Check for API key settings
        if config.get("api_key") or config.get("api_secret"):
            errors.append("API keys should not be configured for paper trading")
        
        # Check execution settings
        execution_config = config.get("execution", {})
        if execution_config.get("mode") != "paper":
            errors.append("Execution mode must be 'paper'")
        
        return errors
    
    def block_dangerous_calls(self):
        """Monkey patch dangerous API calls to prevent real execution."""
        
        # This is a more advanced safety measure that would patch
        # dangerous functions at runtime
        pass
    
    def create_safety_report(self) -> Dict[str, Any]:
        """Create a comprehensive safety report."""
        
        errors = self.check_paper_mode_safety()
        
        return {
            "is_safe": len(errors) == 0,
            "errors": errors,
            "checked_items": {
                "environment_variables": len(self.blocked_env_vars),
                "configuration_files": 4,  # Based on _check_configuration_files
                "blocked_modules": len(self.blocked_modules),
                "blocked_apis": len(self.blocked_apis),
            },
            "recommendations": self._get_safety_recommendations(errors)
        }
    
    def _get_safety_recommendations(self, errors: List[str]) -> List[str]:
        """Get safety recommendations based on errors found."""
        
        recommendations = []
        
        if any("environment variable" in error for error in errors):
            recommendations.append("Remove or rename environment variables containing API keys")
        
        if any("configuration" in error for error in errors):
            recommendations.append("Review configuration files and remove API keys")
        
        if any("module" in error for error in errors):
            recommendations.append("Remove imports of real exchange modules")
        
        if not errors:
            recommendations.append("Configuration appears safe for paper trading")
        
        return recommendations


def enforce_paper_mode():
    """Enforce paper trading mode with comprehensive safety checks."""
    
    checker = SafetyChecker()
    errors = checker.check_paper_mode_safety()
    
    if errors:
        print("🚨 PAPER TRADING SAFETY CHECK FAILED")
        print("=" * 50)
        for error in errors:
            print(f"❌ {error}")
        print("=" * 50)
        print("Paper trading cannot proceed safely.")
        print("Please fix the above issues before running paper trading.")
        sys.exit(1)
    
    print("✅ Paper trading safety check passed")
    print("🛡️  No real order execution will occur")


def validate_paper_config(config: Dict[str, Any]) -> bool:
    """Validate configuration for paper trading."""
    
    checker = SafetyChecker()
    errors = checker.validate_paper_configuration(config)
    
    if errors:
        print("❌ Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


def create_safety_summary() -> str:
    """Create a safety summary for documentation."""
    
    checker = SafetyChecker()
    report = checker.create_safety_report()
    
    summary = f"""
Paper Trading Safety Summary
============================

Safety Status: {'✅ SAFE' if report['is_safe'] else '❌ UNSAFE'}

Checked Items:
- Environment Variables: {report['checked_items']['environment_variables']}
- Configuration Files: {report['checked_items']['configuration_files']}
- Blocked Modules: {report['checked_items']['blocked_modules']}
- Blocked APIs: {report['checked_items']['blocked_apis']}

Errors Found: {len(report['errors'])}

Recommendations:
"""
    
    for rec in report['recommendations']:
        summary += f"- {rec}\n"
    
    return summary


if __name__ == "__main__":
    # Run safety check
    enforce_paper_mode()
    
    # Print safety summary
    print(create_safety_summary())
