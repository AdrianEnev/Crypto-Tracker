# 🎨 Configurable Display Modes

The Crypto Tracker now supports multiple display modes with extensive customization options. You can configure exactly what information is shown and how it's displayed.

## 📋 Available Display Modes

### 1. **Minimal Mode** (`config_minimal.yaml`)
- **Purpose**: Clean, essential information only
- **Features**:
  - Compact table layout
  - No indicators, market structure, or detailed analysis
  - No portfolio/risk summaries
  - Fast refresh intervals
  - Minimal logging (warnings/errors only)

### 2. **Standard Mode** (`config.yaml`) - Default
- **Purpose**: Balanced view with key metrics
- **Features**:
  - Standard table layout
  - Basic indicators (RSI, EMA)
  - Volatility gates and regime filters
  - Portfolio and risk summaries
  - Moderate refresh intervals

### 3. **Detailed Mode** (`config_detailed.yaml`)
- **Purpose**: Comprehensive analysis and indicators
- **Features**:
  - Full table layout with all columns
  - Market structure analysis (HH/HL)
  - Multi-timeframe confirmation
  - Adaptive baseline calculations
  - Strategy details and reasoning
  - Timestamps in output

### 4. **Verbose Mode** (`config_verbose.yaml`)
- **Purpose**: Everything including OCO details
- **Features**:
  - All detailed mode features
  - Stop-loss/take-profit placement details
  - Debug-level logging
  - Frequent refresh intervals
  - Maximum reason length (200 chars)

## ⚙️ Configuration Options

### Display Mode Settings
```yaml
ui:
  display_mode: 'standard'  # 'minimal', 'standard', 'detailed', 'verbose'
```

### Content Visibility
```yaml
ui:
  show_indicators: true          # Show RSI, EMA values
  show_market_structure: false   # Show HH/HL analysis
  show_mtf_confirmation: false   # Show multi-timeframe confirmation
  show_adaptive_baseline: false  # Show adaptive threshold calculations
  show_oco_details: false        # Show stop-loss/take-profit placement
  show_vol_gate_status: true     # Show volatility gate status
  show_regime_filter: true       # Show regime filter status
```

### Decision Display Options
```yaml
ui:
  decision_display:
    show_confidence: true        # Show confidence levels
    show_reasoning: true         # Show decision reasoning
    show_strategy_details: false # Show detailed strategy analysis
    max_reason_length: 100       # Max characters for reason display
```

### Table Display Options
```yaml
ui:
  table_display:
    enabled: true                # Enable table display (false = line-by-line format)
    show_portfolio_summary: true # Show portfolio summary
    show_risk_summary: true      # Show risk management info
    show_execution_status: true  # Show execution system status
    compact_mode: false          # Use compact table layout
    show_pnl_details: true       # Show P&L information
    table_format: 'standard'     # 'standard' or 'per_coin' - display format
```

### Output and Logging
```yaml
ui:
  output:
    log_level: 'info'            # 'debug', 'info', 'warning', 'error'
    show_timestamps: false       # Show timestamps in console output
    color_output: true           # Use colored output
    progress_bars: true          # Show progress bars for long operations
```

### Refresh Intervals
```yaml
ui:
  refresh:
    status_table_interval: 60    # Seconds between status table updates
    decision_display_interval: 5 # Seconds between decision updates
    portfolio_summary_interval: 300 # Seconds between portfolio summaries
```

## 🚀 How to Use

### Option 1: Use Pre-configured Files
```bash
# Copy the desired config file over the main config
cp config/config_minimal.yaml config/config.yaml

# Run the tracker
python3 -m src.entry
```

### Option 2: Modify Main Config
Edit `config/config.yaml` and change the `display_mode` setting:
```yaml
ui:
  display_mode: 'detailed'  # Change this line
```

### Option 3: Mix and Match
Create your own custom configuration by copying one of the preset configs and modifying individual settings.

## 🎯 Display Mode Presets

The system automatically applies preset configurations based on the `display_mode` setting:

- **minimal**: Hides most information, compact layout, fast updates
- **standard**: Balanced information, standard layout, moderate updates
- **detailed**: Shows comprehensive analysis, full layout, frequent updates
- **verbose**: Shows everything, full layout, very frequent updates

## 📊 Display Format Options

The system supports different display formats controlled by the `table_display.enabled` option:

### **Table Display** (`table_display.enabled: true`)
When enabled, data is displayed in structured table format with two sub-options:

#### **Standard Table Format** (`table_format: 'standard'`)
- **Purpose**: Traditional table view with all cryptocurrencies in rows
- **Features**:
  - All coins displayed in a single table
  - Easy to compare metrics across coins
  - Compact horizontal layout
  - Good for overview and comparison

#### **Per-Coin Table Format** (`table_format: 'per_coin'`)
- **Purpose**: Individual table for each cryptocurrency
- **Features**:
  - Separate table for each coin
  - Detailed metrics in vertical layout
  - Percentage change from threshold
  - Better readability for individual analysis
  - More space for detailed information

### **Line-by-Line Display** (`table_display.enabled: false`)
When disabled, data is displayed in the original line-by-line format:
- **Purpose**: Simple, sequential display of decisions
- **Features**:
  - Each coin's decision on a separate line
  - Color-coded actions (Buy=green, Sell=red, Hold=yellow)
  - Signal and confidence information inline
  - Reason displayed below each decision
  - No status tables shown
  - Original behavior from before refactoring

## 🔧 Demo Scripts

Run the demo scripts to see different display options in action:

### Display Modes Demo
```bash
python3 demo_display_modes.py
```
This will show you examples of each display mode (minimal, standard, detailed, verbose) with sample data.

### Table Formats Demo
```bash
python3 demo_table_formats.py
```
This will show you examples of both table formats (standard vs per-coin) with sample data.

## 📊 What Changed from Original

### Before (Original tracker.py):
- Fixed, verbose display with extensive details
- All information shown regardless of need
- No customization options
- Hardcoded display logic

### After (Configurable DisplayManager):
- **4 display modes** with different detail levels
- **Granular control** over what information is shown
- **Configurable refresh intervals** for performance
- **Color-coded headers** indicating current mode
- **Structured reasoning display** for detailed/verbose modes
- **Compact vs. full table layouts**
- **Preset configurations** for easy switching

## 🎨 Visual Indicators

Each display mode has its own color scheme:
- **Minimal**: Dim colors
- **Standard**: Blue colors
- **Detailed**: Cyan colors  
- **Verbose**: Bright blue colors

The current mode is always shown in the table headers: `Crypto Tracker Status [STANDARD]`

## 🔄 Backward Compatibility

The refactored system maintains full backward compatibility. If no UI configuration is provided, it defaults to 'standard' mode with sensible defaults.

## 🚀 Performance Benefits

- **Reduced CPU usage** in minimal mode (fewer updates, less processing)
- **Configurable refresh intervals** prevent unnecessary updates
- **Selective information display** reduces console output
- **Compact layouts** for better readability on smaller screens

This configurable display system gives you complete control over the user interface while maintaining the same powerful trading functionality underneath.
