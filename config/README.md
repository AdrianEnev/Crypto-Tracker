# Configuration Files

This folder contains the main configuration files for the enhanced crypto trading system.

## 📁 Main Configuration Files

### **Production Configuration**
- **`config.yaml`** - Main production configuration with all features
  - Complete trading system configuration
  - Enhanced features (social media, LLM, monitoring)
  - Performance metrics and reporting
  - Parameter optimization settings
  - Risk management and execution settings

### **Testing Configuration**
- **`config_testing.yaml`** - Enhanced testing configuration
  - Optimized for testing the enhanced main algorithm
  - All advanced features enabled
  - Paper trading mode for safety
  - Comprehensive monitoring and error recovery
  - Performance tracking and enhanced reporting

## 🚀 Quick Start

### **For Production Use:**
```bash
python src/entry.py config/config.yaml
```

### **For Testing Enhanced Features:**
```bash
python src/entry.py config/config_testing.yaml
```

## 🔧 Configuration Features

### **Enhanced Features (All Integrated)**
- ✅ **Social Media Integration** - Twitter, Reddit sentiment analysis
- ✅ **LLM Analysis** - GPT-4 market analysis and decision enhancement
- ✅ **24/7 Monitoring** - Heartbeat logging, error recovery, automatic restarts
- ✅ **Performance Metrics** - Real-time tracking, CSV export, analytics
- ✅ **Parameter Optimization** - Automated hyperparameter tuning with Optuna
- ✅ **Enhanced Reporting** - Advanced analytics, risk metrics, comprehensive reports

### **Core Trading Features**
- ✅ **Multi-Exchange Support** - Binance, Coinbase, etc.
- ✅ **Risk Management** - Exposure limits, stop losses, position sizing
- ✅ **Strategy Support** - Mean reversion, momentum, custom strategies
- ✅ **Paper Trading** - Safe testing without real money
- ✅ **Live Trading** - Production trading with real funds

## 📊 Configuration Structure

```yaml
# Enhanced Features
enhanced_features:
  social_media:
    enabled: true
    weight: 0.3
  llm:
    enabled: true
    weight: 0.2

# Monitoring & Error Recovery
monitoring:
  enabled: true
  heartbeat_interval_seconds: 300
  max_restarts: 10

# Performance Metrics
performance_metrics:
  enabled: true
  export_metrics: true

# Parameter Optimization
optimization:
  enabled: false  # Enable for automated tuning
  optimization_trials: 100

# Enhanced Reporting
reporting:
  enabled: true
  enhanced_reports: true
  csv_export: true
```

## 🧪 Test Configurations

Experimental and testing configurations are stored in the `test/` subfolder:
- Strategy testing configs
- Backtesting configurations
- Paper trading experiments
- Feature development configs
- Configuration examples

See `test/README.md` for details.

## ⚠️ Important Notes

- **Paper trading is enabled by default** in testing configs for safety
- **All enhanced features are configurable** through YAML
- **Graceful fallbacks** when enhanced features encounter issues
- **Comprehensive logging** for monitoring and debugging
- **Production config** includes all features with safe defaults

## 🔄 Migration from Old Configs

The enhanced main system now includes all advanced features that were previously scattered across multiple test configuration files. The main system is now the **single source of truth** for all trading capabilities.

**Old deprecated configs** have been moved to `test/` folder for reference only.
