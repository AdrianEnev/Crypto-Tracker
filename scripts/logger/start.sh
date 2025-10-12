#!/bin/bash
# Quick start script for Crypto Price Logger

echo "=========================================="
echo "Crypto Price Logger - Quick Start"
echo "=========================================="
echo ""

# Check if virtual environment exists
VENV_PATH="../../.venv/bin/python"

if [ ! -f "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at $VENV_PATH"
    echo "Please run from the correct directory or activate your venv"
    exit 1
fi

echo "✅ Virtual environment found"
echo ""

# Check if config exists
if [ ! -f "config/alert_config.yaml" ]; then
    echo "❌ Configuration file not found: config/alert_config.yaml"
    exit 1
fi

echo "✅ Configuration file found"
echo ""

# Check email recipient
EMAIL=$(grep "email_recipient:" config/alert_config.yaml | awk '{print $2}')

if [ "$EMAIL" = "your@email.com" ]; then
    echo "⚠️  WARNING: Email recipient not configured!"
    echo ""
    echo "Please edit config/alert_config.yaml and update:"
    echo "  email_recipient: your@email.com"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "=========================================="
echo "Starting Crypto Price Logger..."
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the logger
exec $VENV_PATH crypto_price_logger.py "$@"
