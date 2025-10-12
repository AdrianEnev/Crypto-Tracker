#!/usr/bin/env python3
"""
Test script for price fetching functionality.

This script tests the CCXT exchange connection and price fetching.
"""

import sys
import ccxt
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from rate_limiter import get_global_rate_limiter


def test_exchange_connection(exchange_name: str = 'binance'):
    """Test exchange connection."""
    print(f"Testing {exchange_name} exchange connection...")
    
    try:
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({
            'enableRateLimit': True,
            'timeout': 30000,
        })
        
        # Load markets
        markets = exchange.load_markets()
        print(f"✅ Connected to {exchange_name}")
        print(f"   Available markets: {len(markets)}")
        
        return exchange
    except Exception as e:
        print(f"❌ Error connecting to {exchange_name}: {e}")
        return None


def test_price_fetch(exchange: ccxt.Exchange, symbols: list):
    """Test fetching prices for symbols."""
    print(f"\nTesting price fetching for {len(symbols)} symbols...")
    
    rate_limiter = get_global_rate_limiter()
    
    for symbol in symbols:
        try:
            # Apply rate limiting
            rate_limiter.acquire(exchange.id, tokens=1, blocking=True)
            
            # Fetch ticker
            ticker = exchange.fetch_ticker(symbol)
            price = ticker.get('last') or ticker.get('close')
            
            if price:
                print(f"✅ {symbol:15s} ${price:,.8f}")
            else:
                print(f"⚠️  {symbol:15s} No price data")
                
        except Exception as e:
            print(f"❌ {symbol:15s} Error: {e}")


def main():
    """Main test function."""
    print("=" * 60)
    print("Crypto Price Logger - Price Fetcher Test")
    print("=" * 60)
    
    # Test exchange connection
    exchange = test_exchange_connection('binance')
    
    if not exchange:
        print("\n⚠️  Exchange connection failed!")
        sys.exit(1)
    
    # Test symbols
    test_symbols = [
        'BTC/USDT',
        'ETH/USDT',
        'SOL/USDT',
        'ADA/USDT',
        'DOT/USDT',
    ]
    
    # Fetch prices
    test_price_fetch(exchange, test_symbols)
    
    # Test rate limiter status
    rate_limiter = get_global_rate_limiter()
    status = rate_limiter.get_status('binance')
    
    print(f"\n📊 Rate Limiter Status:")
    print(f"   Available tokens: {status['available']:.1f}/{status['max']}")
    print(f"   Usage: {100 - status['percentage']:.1f}%")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
