# API Reference

## 🌐 Overview

The trading system provides comprehensive REST APIs for trading operations, ML model management, risk monitoring, and system administration. All APIs follow RESTful conventions with JSON request/response formats.

## 🔐 Authentication

### API Keys
```http
GET /api/v1/account/balance
Authorization: Bearer <api_key>
```

### JWT Tokens
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "secure_password"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## 📊 Trading APIs

### Account Management

#### Get Account Balance
```http
GET /api/v1/account/balance
```

Response:
```json
{
  "total_balance": 10000.50,
  "available_balance": 8500.25,
  "margin_used": 1500.25,
  "currencies": [
    {
      "currency": "USDT",
      "balance": 5000.00,
      "available": 4500.00,
      "frozen": 500.00
    }
  ]
}
```

#### Get Trading History
```http
GET /api/v1/trades?symbol=BTC-USDT&limit=100&offset=0
```

Response:
```json
{
  "trades": [
    {
      "id": "trade_12345",
      "symbol": "BTC-USDT",
      "side": "buy",
      "amount": 0.1,
      "price": 45000.00,
      "fee": 4.50,
      "timestamp": "2024-01-15T10:30:00Z",
      "strategy": "momentum"
    }
  ],
  "total": 150,
  "limit": 100,
  "offset": 0
}
```

### Order Management

#### Place Order
```http
POST /api/v1/orders
Content-Type: application/json

{
  "symbol": "BTC-USDT",
  "side": "buy",
  "type": "market",
  "amount": 0.1,
  "strategy": "momentum",
  "stop_loss": 44000.00,
  "take_profit": 46000.00
}
```

Response:
```json
{
  "order_id": "order_67890",
  "symbol": "BTC-USDT",
  "side": "buy",
  "type": "market",
  "amount": 0.1,
  "price": 45000.00,
  "status": "filled",
  "timestamp": "2024-01-15T10:30:00Z",
  "strategy": "momentum"
}
```

#### Get Order Status
```http
GET /api/v1/orders/{order_id}
```

Response:
```json
{
  "order_id": "order_67890",
  "symbol": "BTC-USDT",
  "side": "buy",
  "type": "market",
  "amount": 0.1,
  "filled_amount": 0.1,
  "price": 45000.00,
  "average_price": 45000.00,
  "status": "filled",
  "timestamp": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:05Z"
}
```

#### Cancel Order
```http
DELETE /api/v1/orders/{order_id}
```

Response:
```json
{
  "order_id": "order_67890",
  "status": "cancelled",
  "cancelled_at": "2024-01-15T10:35:00Z"
}
```

### Portfolio Management

#### Get Portfolio
```http
GET /api/v1/portfolio
```

Response:
```json
{
  "total_value": 15000.75,
  "total_pnl": 2500.75,
  "daily_pnl": 125.50,
  "positions": [
    {
      "symbol": "BTC-USDT",
      "amount": 0.5,
      "average_price": 42000.00,
      "current_price": 45000.00,
      "unrealized_pnl": 1500.00,
      "percentage": 10.0
    }
  ],
  "allocation": {
    "BTC": 75.0,
    "ETH": 20.0,
    "USDT": 5.0
  }
}
```

#### Get Performance Metrics
```http
GET /api/v1/portfolio/performance?period=30d
```

Response:
```json
{
  "period": "30d",
  "total_return": 12.5,
  "sharpe_ratio": 1.85,
  "max_drawdown": -5.2,
  "win_rate": 68.5,
  "profit_factor": 1.95,
  "sortino_ratio": 2.1,
  "calmar_ratio": 2.4,
  "var_95": -2.1,
  "cvar_95": -3.2
}
```

## 🤖 ML Platform APIs

### Model Management

#### List Models
```http
GET /api/v1/ml/models
```

Response:
```json
{
  "models": [
    {
      "model_id": "model_123",
      "name": "momentum_strategy_optimizer",
      "version": "1.2.0",
      "type": "parameter_optimizer",
      "status": "active",
      "accuracy": 0.85,
      "created_at": "2024-01-10T10:00:00Z",
      "updated_at": "2024-01-15T09:30:00Z"
    }
  ],
  "total": 5
}
```

#### Get Model Details
```http
GET /api/v1/ml/models/{model_id}
```

Response:
```json
{
  "model_id": "model_123",
  "name": "momentum_strategy_optimizer",
  "version": "1.2.0",
  "type": "parameter_optimizer",
  "status": "active",
  "metadata": {
    "algorithm": "xgboost",
    "features": ["rsi", "macd", "bollinger_bands"],
    "training_data_size": 10000,
    "validation_accuracy": 0.85,
    "hyperparameters": {
      "n_estimators": 100,
      "max_depth": 6,
      "learning_rate": 0.1
    }
  },
  "performance_metrics": {
    "accuracy": 0.85,
    "precision": 0.82,
    "recall": 0.88,
    "f1_score": 0.85
  },
  "created_at": "2024-01-10T10:00:00Z",
  "updated_at": "2024-01-15T09:30:00Z"
}
```

#### Train Model
```http
POST /api/v1/ml/models/train
Content-Type: application/json

{
  "model_type": "parameter_optimizer",
  "strategy": "momentum",
  "features": ["technical", "sentiment"],
  "training_period": "90d",
  "hyperparameters": {
    "n_estimators": 150,
    "max_depth": 8,
    "learning_rate": 0.05
  }
}
```

Response:
```json
{
  "training_id": "training_456",
  "status": "started",
  "estimated_duration": "2h",
  "created_at": "2024-01-15T10:00:00Z"
}
```

#### Get Training Status
```http
GET /api/v1/ml/training/{training_id}
```

Response:
```json
{
  "training_id": "training_456",
  "status": "completed",
  "progress": 100,
  "model_id": "model_789",
  "metrics": {
    "accuracy": 0.87,
    "training_loss": 0.15,
    "validation_loss": 0.18
  },
  "started_at": "2024-01-15T10:00:00Z",
  "completed_at": "2024-01-15T12:30:00Z"
}
```

### Model Inference

#### Get Predictions
```http
POST /api/v1/ml/models/{model_id}/predict
Content-Type: application/json

{
  "data": {
    "rsi": 45.2,
    "macd": 0.15,
    "bollinger_position": 0.3,
    "volume_ratio": 1.2
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

Response:
```json
{
  "prediction": {
    "signal": "buy",
    "confidence": 0.85,
    "parameters": {
      "rsi_period": 14,
      "ema_fast": 12,
      "ema_slow": 26,
      "stop_loss": 0.03,
      "take_profit": 0.06
    }
  },
  "model_version": "1.2.0",
  "inference_time_ms": 25,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Feature Engineering

#### Get Features
```http
GET /api/v1/ml/features?symbol=BTC-USDT&period=24h&features=technical,sentiment
```

Response:
```json
{
  "symbol": "BTC-USDT",
  "period": "24h",
  "timestamp": "2024-01-15T10:30:00Z",
  "features": {
    "technical": {
      "rsi": 45.2,
      "macd": 0.15,
      "bollinger_upper": 46000,
      "bollinger_lower": 44000,
      "bollinger_position": 0.3,
      "volume_ratio": 1.2
    },
    "sentiment": {
      "social_sentiment": 0.65,
      "news_sentiment": 0.72,
      "fear_greed_index": 45,
      "whale_activity": 0.8
    },
    "onchain": {
      "hash_rate": 450.5,
      "active_addresses": 850000,
      "transaction_volume": 1250000000,
      "exchange_inflow": 15000000
    }
  }
}
```

## 🛡️ Risk Management APIs

### Risk Assessment

#### Get Risk Status
```http
GET /api/v1/risk/status
```

Response:
```json
{
  "overall_risk_score": 6.5,
  "risk_level": "medium",
  "categories": {
    "data_quality": {
      "score": 7.2,
      "level": "high",
      "issues": ["missing_data_percent: 15%"]
    },
    "model_performance": {
      "score": 4.8,
      "level": "medium",
      "issues": ["accuracy: 0.72"]
    },
    "financial": {
      "score": 5.5,
      "level": "medium",
      "issues": ["drawdown: 8%"]
    }
  },
  "active_risks": 3,
  "last_updated": "2024-01-15T10:30:00Z"
}
```

#### Get Risk Events
```http
GET /api/v1/risk/events?category=model_performance&limit=50
```

Response:
```json
{
  "events": [
    {
      "risk_id": "risk_789",
      "category": "model_performance",
      "level": "high",
      "title": "Model Performance Degradation",
      "description": "Model accuracy dropped to 0.72",
      "detected_at": "2024-01-15T09:00:00Z",
      "status": "active",
      "probability": 0.8,
      "impact_score": 7.0,
      "risk_score": 5.6
    }
  ],
  "total": 12,
  "limit": 50
}
```

### Compliance Monitoring

#### Get Compliance Status
```http
GET /api/v1/compliance/status
```

Response:
```json
{
  "frameworks": {
    "gdpr": {
      "compliance_score": 0.95,
      "level": "excellent",
      "violations": 0,
      "rules": 5
    },
    "ai_act": {
      "compliance_score": 0.80,
      "level": "good",
      "violations": 1,
      "rules": 4
    }
  },
  "total_violations": 1,
  "last_audit": "2024-01-01T00:00:00Z"
}
```

#### Get Compliance Violations
```http
GET /api/v1/compliance/violations?framework=ai_act&status=open
```

Response:
```json
{
  "violations": [
    {
      "violation_id": "violation_123",
      "framework": "ai_act",
      "rule_name": "AI Transparency",
      "severity": "medium",
      "description": "Missing model documentation",
      "detected_at": "2024-01-15T08:00:00Z",
      "status": "open",
      "assigned_to": "ml_team"
    }
  ],
  "total": 1
}
```

### Bias Detection

#### Get Bias Assessment
```http
GET /api/v1/bias/assessment?model_id=model_123
```

Response:
```json
{
  "model_id": "model_123",
  "assessment": "fair",
  "severity": "low",
  "metrics": {
    "demographic_parity": 0.85,
    "equalized_odds": 0.82,
    "equal_opportunity": 0.88,
    "disparate_impact": 0.90
  },
  "protected_attributes": ["gender", "region"],
  "recommendations": [
    "Continue monitoring fairness metrics",
    "Consider bias mitigation if metrics degrade"
  ],
  "last_assessed": "2024-01-15T10:00:00Z"
}
```

## 📊 Monitoring APIs

### System Health

#### Get System Status
```http
GET /api/v1/system/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "trading_engine": {
      "status": "healthy",
      "uptime": "7d 12h 30m",
      "response_time_ms": 25
    },
    "ml_platform": {
      "status": "healthy",
      "uptime": "7d 12h 30m",
      "response_time_ms": 45
    },
    "database": {
      "status": "healthy",
      "connections": 15,
      "response_time_ms": 5
    },
    "redis": {
      "status": "healthy",
      "memory_usage": "256MB",
      "response_time_ms": 2
    }
  }
}
```

#### Get Metrics
```http
GET /api/v1/metrics?metric=trading.pnl&period=24h&interval=1h
```

Response:
```json
{
  "metric": "trading.pnl",
  "period": "24h",
  "interval": "1h",
  "data": [
    {
      "timestamp": "2024-01-15T00:00:00Z",
      "value": 125.50
    },
    {
      "timestamp": "2024-01-15T01:00:00Z",
      "value": 98.75
    }
  ]
}
```

### Alerts

#### Get Active Alerts
```http
GET /api/v1/alerts?status=active&severity=high
```

Response:
```json
{
  "alerts": [
    {
      "alert_id": "alert_456",
      "title": "High Risk Detected",
      "description": "Risk score exceeded threshold",
      "severity": "high",
      "status": "active",
      "created_at": "2024-01-15T10:15:00Z",
      "acknowledged": false
    }
  ],
  "total": 3
}
```

#### Acknowledge Alert
```http
POST /api/v1/alerts/{alert_id}/acknowledge
Content-Type: application/json

{
  "acknowledged_by": "user@example.com",
  "notes": "Investigating the issue"
}
```

Response:
```json
{
  "alert_id": "alert_456",
  "status": "acknowledged",
  "acknowledged_at": "2024-01-15T10:45:00Z",
  "acknowledged_by": "user@example.com"
}
```

## ⚙️ Configuration APIs

### Strategy Configuration

#### Get Strategy Config
```http
GET /api/v1/strategies/{strategy_name}/config
```

Response:
```json
{
  "strategy_name": "momentum",
  "parameters": {
    "ema_fast": 12,
    "ema_slow": 26,
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "stop_loss": 0.03,
    "take_profit": 0.06
  },
  "risk_limits": {
    "max_position_size": 0.1,
    "max_daily_loss": 0.02,
    "max_drawdown": 0.05
  },
  "enabled": true,
  "updated_at": "2024-01-15T09:00:00Z"
}
```

#### Update Strategy Config
```http
PUT /api/v1/strategies/{strategy_name}/config
Content-Type: application/json

{
  "parameters": {
    "ema_fast": 10,
    "ema_slow": 21,
    "stop_loss": 0.025
  },
  "enabled": true
}
```

Response:
```json
{
  "strategy_name": "momentum",
  "status": "updated",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### System Configuration

#### Get System Config
```http
GET /api/v1/config
```

Response:
```json
{
  "trading": {
    "mode": "production",
    "risk_limit": 0.02,
    "max_positions": 10
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "pool_size": 20
  },
  "monitoring": {
    "enabled": true,
    "alert_webhook": "https://hooks.slack.com/...",
    "metrics_retention_days": 90
  }
}
```

## 🔍 Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Invalid parameter value",
    "details": {
      "parameter": "amount",
      "value": -0.1,
      "expected": "positive number"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_12345"
  }
}
```

### HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily unavailable

### Rate Limiting

- **Trading APIs**: 100 requests per minute
- **ML APIs**: 50 requests per minute
- **Monitoring APIs**: 200 requests per minute
- **Configuration APIs**: 20 requests per minute

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248600
```

## 📝 WebSocket APIs

### Real-time Price Feed
```javascript
const ws = new WebSocket('wss://api.trading-system.com/ws/prices');

ws.onopen = function() {
    ws.send(JSON.stringify({
        action: 'subscribe',
        symbols: ['BTC-USDT', 'ETH-USDT']
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Price update:', data);
};
```

Response:
```json
{
  "type": "price_update",
  "symbol": "BTC-USDT",
  "price": 45000.00,
  "volume": 125.5,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Real-time Alerts
```javascript
const ws = new WebSocket('wss://api.trading-system.com/ws/alerts');

ws.onmessage = function(event) {
    const alert = JSON.parse(event.data);
    console.log('Alert:', alert);
};
```

Response:
```json
{
  "type": "alert",
  "alert_id": "alert_789",
  "title": "Risk Threshold Exceeded",
  "severity": "high",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

This API reference provides comprehensive documentation for all available endpoints, request/response formats, authentication methods, and error handling. Use this guide to integrate with the trading system's APIs effectively.
