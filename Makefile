# Crypto Tracker Development Makefile

.PHONY: help install test lint format security backtest deploy clean

# Default target
help:
	@echo "Crypto Tracker Development Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup:"
	@echo "  install     Install dependencies"
	@echo "  install-dev Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint        Run linting checks"
	@echo "  format      Format code with black and isort"
	@echo "  type-check  Run type checking with mypy"
	@echo "  security    Run security scans"
	@echo ""
	@echo "Testing:"
	@echo "  test        Run all tests"
	@echo "  test-unit   Run unit tests only"
	@echo "  test-integration Run integration tests"
	@echo "  test-coverage Run tests with coverage"
	@echo ""
	@echo "Backtesting:"
	@echo "  backtest    Run backtests"
	@echo "  backtest-optimize Run optimization backtests"
	@echo ""
	@echo "Deployment:"
	@echo "  deploy-staging Deploy to staging"
	@echo "  deploy-prod Deploy to production"
	@echo ""
	@echo "Utilities:"
	@echo "  clean       Clean temporary files"
	@echo "  docs        Generate documentation"

# Setup
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -e .

# Code Quality
lint:
	@echo "Running linting checks..."
	flake8 src/ tests/ scripts/ --max-line-length=100 --ignore=E203,W503
	@echo "✅ Linting completed"

format:
	@echo "Formatting code..."
	black src/ tests/ scripts/
	isort src/ tests/ scripts/
	@echo "✅ Code formatting completed"

type-check:
	@echo "Running type checking..."
	mypy src/ --ignore-missing-imports --no-strict-optional
	@echo "✅ Type checking completed"

security:
	@echo "Running security scans..."
	bandit -r src/ -f txt
	safety check
	@echo "✅ Security scans completed"

# Testing
test:
	@echo "Running all tests..."
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html
	@echo "✅ All tests completed"

test-unit:
	@echo "Running unit tests..."
	pytest tests/ -m "unit" -v
	@echo "✅ Unit tests completed"

test-integration:
	@echo "Running integration tests..."
	pytest tests/ -m "integration" -v
	@echo "✅ Integration tests completed"

test-coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=src --cov-report=html --cov-report=xml --cov-fail-under=80
	@echo "✅ Coverage report generated in htmlcov/"

# Backtesting
backtest:
	@echo "Running backtests..."
	python demos/demo_enhanced_backtest.py
	@echo "✅ Backtests completed"

backtest-optimize:
	@echo "Running optimization backtests..."
	python src/backtest/optimizer.py
	@echo "✅ Optimization backtests completed"

# Security Management
security-validate:
	@echo "Validating security configuration..."
	python scripts/security_manager.py validate binance --api-key test_key --secret test_secret
	@echo "✅ Security validation completed"

security-list:
	@echo "Listing stored secrets..."
	python scripts/security_manager.py list
	@echo "✅ Secrets list completed"

# Deployment
deploy-staging:
	@echo "Deploying to staging..."
	@echo "⚠️  This would deploy to staging environment"
	@echo "✅ Staging deployment completed"

deploy-prod:
	@echo "Deploying to production..."
	@echo "⚠️  This would deploy to production environment"
	@echo "✅ Production deployment completed"

# Utilities
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	@echo "✅ Cleanup completed"

docs:
	@echo "Generating documentation..."
	@echo "📚 Documentation would be generated here"
	@echo "✅ Documentation generation completed"

# CI/CD Simulation
ci-local:
	@echo "Running local CI/CD pipeline..."
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) security
	$(MAKE) test-coverage
	@echo "✅ Local CI/CD pipeline completed"

# Quick development workflow
dev-setup: install-dev
	@echo "Setting up development environment..."
	cp .env.example .env
	@echo "📝 Please edit .env file with your configuration"
	@echo "✅ Development setup completed"

dev-test: format lint test
	@echo "✅ Development test cycle completed"

# Production readiness check
prod-check:
	@echo "Running production readiness checks..."
	$(MAKE) security
	$(MAKE) test-coverage
	@echo "🔒 Checking security configuration..."
	python -c "
	import yaml
	with open('config/config.yaml', 'r') as f:
	    config = yaml.safe_load(f)
	assert config['security']['api_key_safety']['enabled'], 'Security must be enabled'
	assert config['secrets']['backend'] != 'environment', 'Must use secure secrets backend'
	print('✅ Security configuration validated')
	"
	@echo "✅ Production readiness check completed"