#!/usr/bin/env python3
"""
Quick test script - validates all components in under 30 seconds.

This script performs fast validation of:
1. Configuration file
2. Email system (connection only, no send)
3. Exchange connection
4. Rate limiter
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_config():
    """Test configuration loading."""
    print("1️⃣  Testing configuration...", end=" ")
    try:
        import yaml
        config_path = Path(__file__).parent / "config" / "alert_config.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        required = ['global', 'exchange', 'alerts', 'logging']
        missing = [s for s in required if s not in config]
        
        if missing:
            print(f"❌ Missing sections: {missing}")
            return False
        
        # Check email recipient
        recipient = config['global'].get('email_recipient', '')
        if recipient == 'your@email.com':
            print("⚠️  Warning: Update email_recipient in config!")
            return True
        
        print("✅")
        return True
    except Exception as e:
        print(f"❌ {e}")
        return False


def test_email_connection():
    """Test email system (connection only)."""
    print("2️⃣  Testing email connection...", end=" ")
    try:
        from email_notifier import EmailNotifier
        
        notifier = EmailNotifier()
        
        # Quick connection test
        if notifier.test_connection():
            print("✅")
            return True
        else:
            print("❌")
            return False
    except Exception as e:
        print(f"❌ {e}")
        return False


def test_exchange():
    """Test exchange connection."""
    print("3️⃣  Testing exchange connection...", end=" ")
    try:
        import ccxt
        
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'timeout': 10000,
        })
        
        # Quick market load
        exchange.load_markets()
        
        print("✅")
        return True
    except Exception as e:
        print(f"❌ {e}")
        return False


def test_price_fetch():
    """Test single price fetch."""
    print("4️⃣  Testing price fetch...", end=" ")
    try:
        import ccxt
        from rate_limiter import get_global_rate_limiter
        
        exchange = ccxt.binance({'enableRateLimit': True, 'timeout': 10000})
        rate_limiter = get_global_rate_limiter()
        
        # Fetch single price
        rate_limiter.acquire('binance', tokens=1, blocking=True)
        ticker = exchange.fetch_ticker('BTC/USDT')
        price = ticker.get('last')
        
        if price:
            print(f"✅ (BTC: ${price:,.2f})")
            return True
        else:
            print("❌ No price data")
            return False
    except Exception as e:
        print(f"❌ {e}")
        return False


def test_markdown_logs():
    """Test markdown log directory."""
    print("5️⃣  Testing markdown logs...", end=" ")
    try:
        markdown_dir = Path(__file__).parent / "markdown_logs"
        
        if not markdown_dir.exists():
            markdown_dir.mkdir(exist_ok=True)
        
        # Check log files exist
        required_files = ['progress.md', 'todo.md', 'alerts_history.md', 'errors.md']
        for file in required_files:
            file_path = markdown_dir / file
            if not file_path.exists():
                print(f"❌ Missing {file}")
                return False
        
        print("✅")
        return True
    except Exception as e:
        print(f"❌ {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Crypto Price Logger - Quick Test")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Configuration", test_config()))
    results.append(("Email Connection", test_email_connection()))
    results.append(("Exchange Connection", test_exchange()))
    results.append(("Price Fetch", test_price_fetch()))
    results.append(("Markdown Logs", test_markdown_logs()))
    
    # Summary
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:20s} {status}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print()
        print("🎉 All tests passed! System is ready to run.")
        print()
        print("Next steps:")
        print("  1. Update email_recipient in config/alert_config.yaml")
        print("  2. Run: python crypto_price_logger.py --dry-run")
        print("  3. Run: python crypto_price_logger.py")
        return 0
    else:
        print()
        print("⚠️  Some tests failed. Please fix the issues above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
