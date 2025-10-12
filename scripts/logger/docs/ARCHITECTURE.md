# System Architecture - Trading Automation

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    CRYPTO PRICE LOGGER                          │
│                  (Main Orchestrator)                            │
│                                                                 │
└────────┬─────────────────────┬─────────────────────┬───────────┘
         │                     │                     │
         │                     │                     │
    ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
    │  Price  │          │  Email  │          │ Trading │
    │ Monitor │          │ Alerts  │          │ System  │
    └────┬────┘          └────┬────┘          └────┬────┘
         │                     │                     │
         │              ┌──────▼──────┐             │
    ┌────▼────┐        │  Amazon SES  │        ┌────▼────────┐
    │ CCXT    │        │   (Email)    │        │  Strategy   │
    │Exchange │        └──────────────┘        │  Manager    │
    └────┬────┘                                 └────┬────────┘
         │                                           │
         │                                      ┌────▼────────┐
    ┌────▼─────────┐                          │   Trading   │
    │   Binance    │◄─────────────────────────│  Executor   │
    │   REST API   │                          └─────────────┘
    └──────────────┘
```

---

## 📊 Component Interaction Flow

### 1. Price Monitoring Loop

```
Every 30.5 seconds:
  
  ┌─────────────────────┐
  │ Fetch Current Price │
  └──────────┬──────────┘
             │
       ┌─────▼──────┐
       │  Compare   │
       │   with     │
       │  Target    │
       └─────┬──────┘
             │
        ┌────▼─────┐
        │ Condition│
        │   Met?   │
        └────┬─────┘
             │
    ┌────────┴────────┐
    │                 │
   YES               NO
    │                 │
    ▼                 ▼
┌───────┐      ┌──────────┐
│Trigger│      │ Continue │
│ Alert │      │Monitoring│
└───┬───┘      └──────────┘
    │
    ├──► Send Email
    │
    ├──► Execute Strategy (if enabled)
    │
    └──► Log to Markdown
```

### 2. Trading Execution Flow

```
Alert Triggered:
  
  ┌──────────────────┐
  │ Alert Triggered  │
  └────────┬─────────┘
           │
    ┌──────▼────────┐
    │ Find Linked   │
    │   Strategy    │
    └──────┬────────┘
           │
    ┌──────▼────────┐
    │ Safety Checks │
    │   - Position  │
    │   - Risk      │
    │   - Limits    │
    └──────┬────────┘
           │
      ┌────▼─────┐
      │ Calculate│
      │ Position │
      │   Size   │
      └────┬─────┘
           │
    ┌──────▼────────┐
    │ Place Limit   │
    │ BUY Order     │
    └──────┬────────┘
           │
    ┌──────▼────────┐
    │ Set Stop-Loss │
    │ Take-Profit   │
    └──────┬────────┘
           │
    ┌──────▼────────┐
    │ Track Position│
    │  in Memory &  │
    │     JSON      │
    └──────┬────────┘
           │
    ┌──────▼────────┐
    │ Monitor Price │
    │  Updates for  │
    │   SL/TP Hit   │
    └───────────────┘
```

### 3. Position Management Flow

```
Every Price Update:
  
  ┌──────────────────┐
  │  New Price Data  │
  └────────┬─────────┘
           │
    ┌──────▼────────┐
    │ For Each Open │
    │   Position:   │
    └──────┬────────┘
           │
    ┌──────▼────────┐
    │ Check if SL   │
    │    Hit?       │
    └──────┬────────┘
           │
      ┌────┴─────┐
      │          │
     YES        NO
      │          │
      │    ┌─────▼────────┐
      │    │ Check if TP  │
      │    │    Hit?      │
      │    └─────┬────────┘
      │          │
      │     ┌────┴─────┐
      │     │          │
      │    YES        NO
      │     │          │
      │     │    ┌─────▼────────┐
      │     │    │ Update       │
      │     │    │ Trailing Stop│
      │     │    └──────────────┘
      │     │
      ▼     ▼
  ┌────────────┐
  │Close       │
  │Position    │
  └─────┬──────┘
        │
  ┌─────▼──────┐
  │ Calculate  │
  │    PnL     │
  └─────┬──────┘
        │
  ┌─────▼──────┐
  │   Log to   │
  │ trades.md  │
  └────────────┘
```

---

## 🗂️ Data Flow Diagram

```
Configuration Files          Runtime Data             Output Logs
─────────────────          ──────────────           ──────────────

alert_config.yaml    ──┐
                       │
trading_config.yaml ──┼──► Crypto Price  ──► trades.md
                       │       Logger        
.env (API keys)     ──┘                   ──► progress.md
                              │
                              │           ──► alerts_history.md
                              │
                              ▼           ──► errors.md
                       
                       Trading Executor
                              │
                              ▼
                       
                     Position Tracker
                              │
                              ▼
                       
                  trading_positions.json
                              │
                              ▼
                       
                       Binance API
                              │
                              ▼
                       
                        LIVE MARKET
```

---

## 🧩 Module Dependencies

```
crypto_price_logger.py
├── email_notifier.py
├── rate_limiter.py
├── trading_executor.py (optional)
│   └── binance.client (python-binance)
└── strategy_manager.py (optional)
    └── trading_executor.py

Configuration Dependencies:
├── config/alert_config.yaml (required)
├── config/trading_config.yaml (if trading enabled)
└── .env (required for trading)
```

---

## 📋 State Management

### In-Memory State

```python
crypto_price_logger.py:
  - alert_cooldowns: Dict[alert_id → datetime]
  - stats: Dict[checks, alerts, errors, start_time]
  - running: bool

trading_executor.py:
  - positions: Dict[position_id → position_data]
  - open_orders: Dict[order_id → order_data]
  - stats: Dict[trades, pnl, win_rate]

strategy_manager.py:
  - strategy_states: Dict[strategy_id → state]
  - last_execution_times: Dict[strategy_id → datetime]
```

### Persistent State

```
Files:
  - trading_positions.json (positions)
  - markdown_logs/trades.md (history)
  - markdown_logs/progress.md (activity)
  - markdown_logs/alerts_history.md (alerts)
  - markdown_logs/errors.md (errors)
```

---

## 🔄 Execution Contexts

### Main Loop (Every 30.5s)

```
1. Fetch prices for all enabled alerts
2. Check alert conditions
3. Send emails if conditions met
4. Trigger trading strategies (if enabled)
5. Update open positions
6. Check stop-loss / take-profit
7. Update trailing stops
8. Log heartbeat (every 5 min)
9. Sleep until next cycle
```

### Trading Context (On Alert Trigger)

```
1. Receive alert trigger
2. Find linked strategies
3. For each strategy:
   a. Validate safety checks
   b. Calculate position size
   c. Place limit order
   d. Set stop-loss
   e. Set take-profit
   f. Track position
   g. Log trade
```

### Position Update Context (On Price Change)

```
1. Receive new price
2. For each open position:
   a. Check stop-loss hit
   b. Check take-profit hit
   c. Update trailing stop
   d. Close if condition met
   e. Calculate PnL
   f. Log exit
```

---

## 🛡️ Safety Layers

```
Layer 1: Configuration Safety
  - Trading disabled by default
  - Paper trading enabled by default
  - All strategies require explicit enable

Layer 2: Pre-Trade Checks
  - Max position size validation
  - Max open positions check
  - Daily/weekly loss limits
  - Risk percentage validation

Layer 3: Order Execution
  - Limit orders (not market)
  - Stop-loss required
  - Take-profit recommended
  - Position size calculation

Layer 4: Runtime Monitoring
  - Continuous position tracking
  - Automatic stop-loss execution
  - Trailing stop updates
  - PnL calculation

Layer 5: Circuit Breaker
  - Portfolio drawdown monitoring
  - Automatic trading halt
  - Cooldown period enforcement
  - Manual override option
```

---

## 📊 Communication Patterns

### Alert System → Trading System

```
Event-driven:
  alert.trigger() → strategy_manager.handle_alert_trigger()
  
Flow:
  1. Alert condition met
  2. Email sent (existing functionality)
  3. Check if trading enabled
  4. Find linked strategies
  5. Execute strategy
```

### Price Monitor → Position Manager

```
Polling-based:
  Every price check → update_positions()
  
Flow:
  1. Fetch new price
  2. Update all positions with new price
  3. Check exit conditions
  4. Execute exits if needed
```

### Trading Executor → Binance API

```
Request-Response:
  executor.place_order() → binance.create_order()
  
Flow:
  1. Prepare order parameters
  2. Send to Binance API
  3. Receive order confirmation
  4. Track order status
  5. Handle fills
```

---

## 🔐 Security Architecture

```
Credential Management:
  .env file (gitignored)
    ↓
  load_dotenv()
    ↓
  TradingExecutor (in-memory only)
    ↓
  Binance Client
    ↓
  Encrypted HTTPS to Binance

Never logged, never stored in files
```

---

## 📈 Scalability Considerations

### Current Design

- **Single-threaded**: Simple, reliable, no race conditions
- **Synchronous**: Easy to debug and maintain
- **30.5s polling**: Balance between responsiveness and API limits
- **Local state**: Fast access, simple management

### If Scaling Needed (Future)

- **Multi-threading**: Parallel price fetching
- **WebSocket**: Real-time price updates
- **Database**: PostgreSQL for position history
- **Distributed**: Multiple instances with shared state
- **Event-driven**: Message queue (Redis/RabbitMQ)

Current design handles:
- ✅ 10+ alerts
- ✅ 5 open positions
- ✅ Multiple strategies
- ✅ 24/7 operation
- ✅ Sub-second response to conditions

---

## 🔧 Error Handling Strategy

```
Level 1: Try-Catch Blocks
  - Individual operations wrapped
  - Specific error messages
  - Continue operation

Level 2: Retry Logic
  - API calls retry with exponential backoff
  - Max 3 attempts
  - Log all attempts

Level 3: Graceful Degradation
  - Email fails → Log and continue
  - Trading fails → Log and continue
  - Price fetch fails → Skip cycle

Level 4: Error Logging
  - All errors to markdown_logs/errors.md
  - Timestamp and context
  - Stack trace for debugging

Level 5: System State
  - Positions always saved to JSON
  - Trade history always logged
  - No data loss on errors
```

---

## 🎯 Design Principles

1. **Safety First**: Multiple safety layers, paper trading default
2. **Transparency**: Everything logged, full audit trail
3. **Modularity**: Components can be used independently
4. **Configurability**: No code changes needed
5. **Reliability**: Graceful error handling, automatic recovery
6. **Simplicity**: Straightforward architecture, easy to understand
7. **Extensibility**: Easy to add new strategies/features
8. **Performance**: Efficient API usage, rate limiting

---

## 📚 Key Interfaces

### TradingExecutor API

```python
# Order placement
place_limit_order(symbol, side, quantity, price, stop_loss, take_profit)
place_stop_loss_order(symbol, side, quantity, stop_price)

# Position management
close_position(position_id, close_price, reason)
update_trailing_stop(position_id, current_price)
check_position_exits(symbol, current_price)

# Queries
get_current_price(symbol) → float
get_account_balance(asset) → float
get_open_positions() → List[Position]
```

### StrategyManager API

```python
# Event handlers
handle_alert_trigger(alert_id, symbol, current_price)
check_time_based_strategies()
check_breakout_strategies(symbol, current_price)

# Updates
update_positions(symbol, current_price)

# Queries
get_strategy_summary() → Dict
```

---

This architecture is designed for:
- ✅ Reliability (24/7 operation)
- ✅ Safety (multiple protection layers)
- ✅ Maintainability (clear structure)
- ✅ Extensibility (easy to add features)
- ✅ Transparency (comprehensive logging)

**Built for real-world trading automation! 📈**
