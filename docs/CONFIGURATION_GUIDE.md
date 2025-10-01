# 🎯 **Flexible Configuration Guide**

## 📊 **Portfolio Allocation Customization**

The system now supports **fully configurable portfolio allocation**! You can customize how your portfolio is distributed across different assets based on your risk tolerance and investment strategy.

### **🔧 How to Customize Allocation**

#### **1. Edit the Configuration File**

Open `config/paper_24_7_optimized.yaml` and modify the `portfolio_allocation` section:

```yaml
portfolio_allocation:
  # Bitcoin allocation as percentage of total crypto portfolio
  bitcoin_allocation_pct: 60.0  # Change this value (0-100)
  
  # Ethereum allocation as percentage of total crypto portfolio  
  ethereum_allocation_pct: 30.0  # Change this value (0-100)
  
  # Other altcoins allocation as percentage of total crypto portfolio
  altcoins_allocation_pct: 10.0  # Change this value (0-100)
```

#### **2. Choose Your Risk Profile**

Set your risk profile in the configuration:

```yaml
risk_profile: "conservative"  # Options: conservative, moderate, aggressive, custom
```

**Risk Profile Presets:**

| Profile | Bitcoin | Ethereum | Altcoins | Advanced Features |
|---------|---------|----------|----------|-------------------|
| **Conservative** | 75% | 20% | 5% | Disabled |
| **Moderate** | 60% | 30% | 10% | Enabled |
| **Aggressive** | 40% | 40% | 20% | Enabled |

#### **3. Enable/Disable Advanced Strategies**

You can choose which advanced features to use:

```yaml
advanced_strategies:
  bitcoin_multi_bucket:
    enabled: true  # Set to false for simple momentum strategy
  ethereum_staking_trading:
    enabled: true  # Set to false for simple momentum strategy
  derivatives_integration:
    enabled: true  # Set to false to disable funding rates, basis, options
  onchain_metrics:
    enabled: true  # Set to false to disable exchange flows, active addresses
```

### **🎯 Allocation Examples**

#### **Example 1: Bitcoin Maximalist**
```yaml
portfolio_allocation:
  bitcoin_allocation_pct: 90.0
  ethereum_allocation_pct: 8.0
  altcoins_allocation_pct: 2.0
```

#### **Example 2: Balanced Portfolio**
```yaml
portfolio_allocation:
  bitcoin_allocation_pct: 50.0
  ethereum_allocation_pct: 30.0
  altcoins_allocation_pct: 20.0
```

#### **Example 3: Altcoin Heavy**
```yaml
portfolio_allocation:
  bitcoin_allocation_pct: 30.0
  ethereum_allocation_pct: 40.0
  altcoins_allocation_pct: 30.0
```

#### **Example 4: Ethereum Focused**
```yaml
portfolio_allocation:
  bitcoin_allocation_pct: 40.0
  ethereum_allocation_pct: 50.0
  altcoins_allocation_pct: 10.0
```

### **🔄 Rebalancing Configuration**

Control how often and aggressively the system rebalances:

```yaml
portfolio_allocation:
  rebalancing:
    enabled: true
    threshold_pct: 10.0      # Rebalance when allocation drifts ±10%
    min_interval_days: 30    # Minimum days between rebalancing
    max_rebalance_pct: 5.0   # Maximum % of portfolio to rebalance at once
```

**Rebalancing Examples:**

| Setting | Threshold | Min Interval | Max Rebalance | Behavior |
|---------|-----------|--------------|---------------|----------|
| **Conservative** | 15% | 45 days | 3% | Infrequent, small adjustments |
| **Moderate** | 10% | 30 days | 5% | Balanced rebalancing |
| **Aggressive** | 8% | 15 days | 8% | Frequent, larger adjustments |

### **🚀 Strategy Selection**

#### **For Bitcoin:**

**Simple Strategy (Conservative):**
```yaml
bitcoin:
  strategy:
    name: momentum  # Simple momentum strategy
```

**Advanced Strategy (Moderate/Aggressive):**
```yaml
bitcoin:
  strategy:
    name: bitcoin_multi_bucket  # Advanced multi-bucket strategy
```

#### **For Ethereum:**

**Simple Strategy (Conservative):**
```yaml
ethereum:
  strategy:
    name: momentum  # Simple momentum strategy
```

**Advanced Strategy (Moderate/Aggressive):**
```yaml
ethereum:
  strategy:
    name: ethereum_staking_trading  # Advanced staking + trading strategy
```

### **⚙️ Quick Configuration Files**

I've created pre-configured files for different risk profiles:

- **`config/paper_24_7_conservative.yaml`** - 75% Bitcoin, simple strategies
- **`config/paper_24_7_optimized.yaml`** - 60% Bitcoin, advanced strategies  
- **`config/paper_24_7_aggressive.yaml`** - 40% Bitcoin, all advanced features

### **💡 Configuration Tips**

#### **For Conservative Investors:**
- Set `bitcoin_allocation_pct: 70-80`
- Set `advanced_strategies` to `enabled: false`
- Use `risk_per_trade_pct: 0.5`
- Use `max_position_size_pct: 5.0`

#### **For Moderate Investors:**
- Set `bitcoin_allocation_pct: 50-60`
- Enable some advanced strategies
- Use `risk_per_trade_pct: 1.0`
- Use `max_position_size_pct: 10.0`

#### **For Aggressive Investors:**
- Set `bitcoin_allocation_pct: 30-40`
- Enable all advanced strategies
- Use `risk_per_trade_pct: 2.0`
- Use `max_position_size_pct: 15.0`

### **🔍 How to Check Your Current Allocation**

Use the configuration loader to see your current settings:

```python
from src.config.flexible_loader import FlexibleConfigLoader

loader = FlexibleConfigLoader("config/paper_24_7_optimized.yaml")
allocation = loader.get_portfolio_allocation()
print(f"Bitcoin: {allocation['bitcoin_allocation_pct']}%")
print(f"Ethereum: {allocation['ethereum_allocation_pct']}%")
print(f"Altcoins: {allocation['altcoins_allocation_pct']}%")
```

### **🎯 Key Benefits of This System**

1. **✅ Fully Configurable** - No hardcoded allocation percentages
2. **✅ Risk Profile Support** - Choose conservative, moderate, or aggressive
3. **✅ Advanced Features Optional** - Enable/disable sophisticated strategies
4. **✅ Flexible Rebalancing** - Control frequency and aggressiveness
5. **✅ Strategy Selection** - Choose simple or advanced strategies per coin
6. **✅ Future-Proof** - Easy to add new allocation options

This system gives you **complete control** over your portfolio allocation while keeping the sophisticated strategies as optional features for those who want them! 🎯
