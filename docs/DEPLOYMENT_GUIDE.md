# Deployment Guide

## 🚀 Overview

This guide covers the deployment of the advanced cryptocurrency trading system in various environments, from development to production. The system supports both traditional deployment and containerized deployment with comprehensive monitoring and scaling capabilities.

## 📋 Prerequisites

### System Requirements

**Minimum Requirements**:
- **CPU**: 4 cores, 2.4 GHz
- **RAM**: 8 GB
- **Storage**: 50 GB SSD
- **Network**: Stable internet connection (low latency preferred)

**Recommended for Production**:
- **CPU**: 8+ cores, 3.0 GHz
- **RAM**: 32+ GB
- **Storage**: 500+ GB NVMe SSD
- **Network**: Dedicated low-latency connection

### Software Dependencies

**Core Requirements**:
- Python 3.8+
- PostgreSQL 12+
- Redis 6+
- Node.js 16+ (for web dashboards)

**Python Packages**:
```bash
pip install -r requirements.txt
```

**System Packages** (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install -y postgresql redis-server nginx certbot python3-dev
```

## 🏗️ Deployment Architectures

### 1. Single Server Deployment

**Use Case**: Development, testing, small-scale production

**Architecture**:
```
┌─────────────────────────────────┐
│           Single Server         │
│                                 │
│  ┌─────────┐  ┌─────────────┐   │
│  │ Trading │  │    ML       │   │
│  │ Engine  │  │ Platform    │   │
│  └─────────┘  └─────────────┘   │
│                                 │
│  ┌─────────┐  ┌─────────────┐   │
│  │PostgreSQL│  │   Redis     │   │
│  └─────────┘  └─────────────┘   │
└─────────────────────────────────┘
```

**Deployment Steps**:
```bash
# 1. Clone repository
git clone <repository-url>
cd tracker

# 2. Setup virtual environment
python -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure database
sudo -u postgres createdb trading_db
sudo -u postgres createuser trading_user

# 5. Configure application
cp config/config.yaml.example config/config.yaml
# Edit configuration files

# 6. Initialize database
python scripts/init_database.py

# 7. Start services
python src/entry.py --mode production
```

### 2. Multi-Tier Deployment

**Use Case**: Medium-scale production with separation of concerns

**Architecture**:
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Web       │  │ Application │  │    Data     │
│   Tier      │  │    Tier     │  │    Tier     │
│             │  │             │  │             │
│ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │
│ │ Nginx   │ │  │ │Trading  │ │  │ │PostgreSQL│ │
│ │Dashboard│ │  │ │Engine   │ │  │ │         │ │
│ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │
│             │  │ ┌─────────┐ │  │ ┌─────────┐ │
│             │  │ │   ML    │ │  │ │  Redis  │ │
│             │  │ │Platform │ │  │ │         │ │
│             │  │ └─────────┘ │  │ └─────────┘ │
└─────────────┘  └─────────────┘  └─────────────┘
```

**Deployment Configuration**:

**Web Tier (Nginx)**:
```nginx
# /etc/nginx/sites-available/trading-system
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api/ {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Application Tier**:
```bash
# Start trading engine
python src/entry.py --host 0.0.0.0 --port 8001

# Start ML platform
python -m src.ml.deployment.model_server --host 0.0.0.0 --port 8002

# Start monitoring dashboard
python -m src.ml.observability.dashboard --host 0.0.0.0 --port 8000
```

### 3. Containerized Deployment

**Use Case**: Scalable production deployment with orchestration

**Docker Compose Configuration**:
```yaml
# docker-compose.yml
version: '3.8'

services:
  trading-engine:
    build: .
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/trading_db
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs

  ml-platform:
    build: .
    ports:
      - "8002:8002"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/trading_db
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ./models:/app/models

  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=trading_db
      - POSTGRES_USER=trading_user
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - trading-engine
      - ml-platform

volumes:
  postgres_data:
  redis_data:
```

**Dockerfile**:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 trading && chown -R trading:trading /app
USER trading

# Expose ports
EXPOSE 8000 8001 8002

# Default command
CMD ["python", "src/entry.py"]
```

### 4. Kubernetes Deployment

**Use Case**: Large-scale production with auto-scaling

**Kubernetes Manifests**:

**Namespace**:
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: trading-system
```

**ConfigMap**:
```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: trading-config
  namespace: trading-system
data:
  config.yaml: |
    # Trading configuration
    trading:
      mode: production
      risk_limit: 0.02
    ml:
      model_path: /models
      batch_size: 32
```

**Deployment**:
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trading-engine
  namespace: trading-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: trading-engine
  template:
    metadata:
      labels:
        app: trading-engine
    spec:
      containers:
      - name: trading-engine
        image: trading-system:latest
        ports:
        - containerPort: 8001
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: trading-secrets
              key: database-url
        volumeMounts:
        - name: config
          mountPath: /app/config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
      volumes:
      - name: config
        configMap:
          name: trading-config
```

**Service**:
```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: trading-service
  namespace: trading-system
spec:
  selector:
    app: trading-engine
  ports:
  - port: 80
    targetPort: 8001
  type: LoadBalancer
```

**Horizontal Pod Autoscaler**:
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: trading-hpa
  namespace: trading-system
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: trading-engine
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## 🔧 Configuration Management

### Environment-Specific Configuration

**Development**:
```yaml
# config/config_dev.yaml
trading:
  mode: paper
  risk_limit: 0.01
database:
  host: localhost
  port: 5432
  name: trading_dev
logging:
  level: DEBUG
  file: logs/dev.log
```

**Staging**:
```yaml
# config/config_staging.yaml
trading:
  mode: paper
  risk_limit: 0.015
database:
  host: staging-db.company.com
  port: 5432
  name: trading_staging
logging:
  level: INFO
  file: logs/staging.log
```

**Production**:
```yaml
# config/config_prod.yaml
trading:
  mode: live
  risk_limit: 0.02
database:
  host: prod-db.company.com
  port: 5432
  name: trading_prod
logging:
  level: WARNING
  file: logs/prod.log
```

### Environment Variables

```bash
# Database configuration
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
export REDIS_URL="redis://host:6379"

# Trading configuration
export TRADING_MODE="production"
export RISK_LIMIT="0.02"

# ML configuration
export ML_MODEL_PATH="/models"
export ML_BATCH_SIZE="32"

# Monitoring configuration
export MONITORING_ENABLED="true"
export ALERT_WEBHOOK_URL="https://hooks.slack.com/..."
```

## 📊 Monitoring & Observability

### Health Checks

**Application Health Check**:
```python
# health_check.py
from flask import Flask, jsonify
import psycopg2
import redis

app = Flask(__name__)

@app.route('/health')
def health_check():
    status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    # Database check
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        status['checks']['database'] = 'healthy'
    except Exception as e:
        status['checks']['database'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'
    
    # Redis check
    try:
        r = redis.from_url(REDIS_URL)
        r.ping()
        status['checks']['redis'] = 'healthy'
    except Exception as e:
        status['checks']['redis'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'
    
    return jsonify(status)
```

**Kubernetes Health Checks**:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Metrics Collection

**Prometheus Configuration**:
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'trading-system'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: /metrics
    scrape_interval: 5s
```

**Grafana Dashboard**:
```json
{
  "dashboard": {
    "title": "Trading System Dashboard",
    "panels": [
      {
        "title": "Trading Performance",
        "type": "graph",
        "targets": [
          {
            "expr": "trading_pnl_total",
            "legendFormat": "PnL"
          }
        ]
      },
      {
        "title": "System Health",
        "type": "singlestat",
        "targets": [
          {
            "expr": "up",
            "legendFormat": "Status"
          }
        ]
      }
    ]
  }
}
```

## 🔒 Security Configuration

### SSL/TLS Setup

**Nginx SSL Configuration**:
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Firewall Configuration

**UFW Rules**:
```bash
# Allow SSH
sudo ufw allow 22

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow application ports
sudo ufw allow 8000
sudo ufw allow 8001
sudo ufw allow 8002

# Allow database (internal only)
sudo ufw allow from 10.0.0.0/8 to any port 5432
sudo ufw allow from 172.16.0.0/12 to any port 5432
sudo ufw allow from 192.168.0.0/16 to any port 5432

# Enable firewall
sudo ufw enable
```

## 🚀 Deployment Scripts

### Automated Deployment

**Deploy Script**:
```bash
#!/bin/bash
# deploy.sh

set -e

ENVIRONMENT=${1:-production}
VERSION=${2:-latest}

echo "Deploying trading system to $ENVIRONMENT environment..."

# Pull latest code
git pull origin main

# Build Docker image
docker build -t trading-system:$VERSION .

# Deploy using Docker Compose
docker-compose -f docker-compose.$ENVIRONMENT.yml up -d

# Wait for health check
echo "Waiting for services to be healthy..."
sleep 30

# Run health checks
python scripts/health_check.py

echo "Deployment completed successfully!"
```

**Rollback Script**:
```bash
#!/bin/bash
# rollback.sh

PREVIOUS_VERSION=${1:-previous}

echo "Rolling back to version $PREVIOUS_VERSION..."

# Stop current services
docker-compose down

# Start previous version
docker-compose -f docker-compose.production.yml up -d

echo "Rollback completed!"
```

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] Code review completed
- [ ] Tests passing
- [ ] Security scan completed
- [ ] Configuration validated
- [ ] Database migrations prepared
- [ ] Backup strategy in place

### Deployment
- [ ] Environment variables configured
- [ ] Database initialized
- [ ] Services started
- [ ] Health checks passing
- [ ] Monitoring configured
- [ ] SSL certificates installed

### Post-Deployment
- [ ] Smoke tests executed
- [ ] Performance monitoring active
- [ ] Logs being collected
- [ ] Alerts configured
- [ ] Documentation updated
- [ ] Team notified

## 🆘 Troubleshooting

### Common Issues

**Database Connection Issues**:
```bash
# Check database connectivity
psql -h hostname -U username -d database_name -c "SELECT 1;"

# Check connection pool
python -c "import psycopg2; print(psycopg2.connect('your_connection_string'))"
```

**Memory Issues**:
```bash
# Check memory usage
free -h
top -p $(pgrep -f "python.*trading")

# Increase swap if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**Performance Issues**:
```bash
# Check CPU usage
htop

# Check disk I/O
iostat -x 1

# Check network latency
ping -c 10 your-exchange.com
```

### Log Analysis

**Application Logs**:
```bash
# View recent logs
tail -f logs/trading.log

# Search for errors
grep -i error logs/trading.log

# Monitor real-time
journalctl -u trading-system -f
```

**Database Logs**:
```bash
# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-13-main.log

# Redis logs
sudo tail -f /var/log/redis/redis-server.log
```

---

This deployment guide provides comprehensive instructions for deploying the trading system in various environments, from simple single-server setups to complex Kubernetes clusters. Choose the deployment method that best fits your requirements and scale.
