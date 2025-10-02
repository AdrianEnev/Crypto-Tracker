# Scripts Directory Organization

This directory contains scripts organized by functionality and usage frequency.

## 📁 Main Scripts Directory (`scripts/`)

### **Core Functionality Scripts** (Used regularly)
These scripts provide essential functionality for the trading system:

- **`llm_config_generator.py`** - AI-powered market analysis and configuration generator
- **`crypto_discovery_scanner.py`** - Social media-based crypto discovery scanner
- **`quick_crypto_scanner.py`** - Fast crypto market scanner
- **`fast_backtest.py`** - Fast backtesting engine
- **`security_manager.py`** - Security and API key management
- **`configure_allocation.py`** - Portfolio allocation configuration

## 📁 Test Scripts Directory (`scripts/test/`)

### **Test and Development Scripts** (Used occasionally)
These scripts are for testing, development, and debugging:

- **`test_llm_config_generator.py`** - Test script for LLM configuration generator
- **`paper_trading_24_7.py`** - 24/7 paper trading system (deprecated)
- **`paper_trading_24_7.sh`** - Shell script for 24/7 paper trading (deprecated)
- **`tune.py`** - Simple parameter optimization (deprecated)
- **`setup_llm_env.py`** - Basic LLM environment setup (deprecated)
- **`reporting.py`** - Basic report generation (deprecated)
- **`cache_manager.py`** - Cache management and monitoring (deprecated)
- **`ultra_fast_backtest.py`** - Ultra-fast backtesting (deprecated)
- **`test_llm_integration.py`** - LLM integration testing (deprecated)
- **`test_openai_official.py`** - OpenAI client testing (deprecated)
- **`test_cache_performance.py`** - Cache performance testing (deprecated)
- **`quick_test_24_7.py`** - Quick 24/7 system testing (deprecated)
- **`simple_test_strategy.py`** - Simple strategy testing (deprecated)

## 🎯 **Usage Guidelines**

### **Daily Use Scripts** (Main Directory)
- **Configuration Generation**: `python scripts/llm_config_generator.py`
- **Crypto Discovery**: `python scripts/crypto_discovery_scanner.py`
- **Backtesting**: `python scripts/fast_backtest.py`

### **Testing Scripts** (Test Directory)
- **Test LLM Generator**: `python scripts/test/test_llm_config_generator.py`
- **Other Tests**: Use as needed for development and debugging

## ⚠️ **Deprecated Scripts**

Several scripts are marked as deprecated but preserved for safety:
- `paper_trading_24_7.py` - Use `auto_trade.mode: paper` in config instead
- `tune.py` - Use `scripts/llm_config_generator.py` or main system's `ParameterOptimizer` instead
- `setup_llm_env.py` - Use `.env` files or `scripts/security_manager.py` instead
- `reporting.py` - Use main system's `EnhancedReporter` and `PerformanceMetricsTracker` instead
- `cache_manager.py` - Use main system's built-in caching mechanisms instead
- `ultra_fast_backtest.py` - Use `src/backtest/engine.py` or `src/backtest/simulation/simulator.py` instead
- `test_llm_integration.py` - LLM integration now in main system
- `test_openai_official.py` - OpenAI integration now in main system
- `test_cache_performance.py` - Cache monitoring now in main system
- `quick_test_24_7.py` - Use main system paper trading instead
- `simple_test_strategy.py` - Use main backtest system instead

## 🔧 **Adding New Scripts**

### **Core Functionality Scripts**
- Place in main `scripts/` directory
- Should provide essential functionality
- Used regularly by users
- Examples: scanners, generators, optimizers

### **Test Scripts**
- Place in `scripts/test/` directory
- Used for testing, development, debugging
- Not used in daily operations
- Examples: unit tests, integration tests, performance tests

## 📚 **Documentation**

- **Main Scripts**: Documented in individual script files
- **Test Scripts**: Documented with deprecation warnings
- **Usage Examples**: Provided in script docstrings
- **Integration**: Main scripts integrate with core system

---

**Organization completed: Core functionality scripts in main directory, test scripts moved to test subdirectory.**
