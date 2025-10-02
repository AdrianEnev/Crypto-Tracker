#!/usr/bin/env python3
"""
DEPRECATED: LLM Integration Test Script

⚠️  WARNING: This script is DEPRECATED but preserved for safety.
    LLM integration is now part of the main system.

This script tests LLM integration in isolation.
The main system now has integrated LLM functionality with proper configuration.

PRESERVED FOR SAFETY: Contains LLM testing patterns that could be useful.
TODO: Integrate LLM testing features into main system testing, then remove this script.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.llm.client import LLMClient, LLMConfig, LLMProvider
from src.llm.market_analyzer import ComprehensiveMarketAnalyzer


async def test_llm_connection():
    """Test basic LLM connection"""
    print("🧪 Testing LLM Connection...")
    
    # Get API key from config file
    try:
        from src.llm.config_manager import LLMConfigManager
        from src.tracker.config_manager import ConfigManager
        
        # Load config
        config_manager = ConfigManager("config/config.yaml")
        llm_config_manager = LLMConfigManager(config_manager)
        
        if not llm_config_manager.is_enabled():
            print("❌ LLM integration disabled in configuration")
            return False
        
        api_key = llm_config_manager.get_api_key()
        if not api_key:
            print("❌ No API key found")
            print("   Please set OPENAI_API_KEY environment variable")
            print("   Example: export OPENAI_API_KEY='your-key-here'")
            print("   Or use: python scripts/setup_llm_env.py setup")
            return False
        
        print(f"✅ Found API key: {api_key[:20]}...")
        
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    try:
        # Create LLM client using config manager
        llm_config = llm_config_manager.create_llm_config()
        
        client = LLMClient(llm_config)
        
        # Test simple request
        response = await client.generate_response(
            "Respond with JSON: {\"status\": \"working\", \"test\": \"successful\"}"
        )
        
        print("✅ LLM connection successful!")
        print(f"   Provider: {llm_config.provider.value}")
        print(f"   Model: {llm_config.model}")
        print(f"   Response: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM connection failed: {e}")
        return False


async def test_market_analysis():
    """Test market analysis functionality"""
    print("\n🧪 Testing Market Analysis...")
    
    try:
        # Load config
        from src.llm.config_manager import LLMConfigManager
        from src.tracker.config_manager import ConfigManager
        
        config_manager = ConfigManager("config/config.yaml")
        llm_config_manager = LLMConfigManager(config_manager)
        
        if not llm_config_manager.is_enabled():
            print("❌ LLM integration disabled in configuration")
            return False
        
        # Create LLM client and analyzer
        llm_config = llm_config_manager.create_llm_config()
        
        client = LLMClient(llm_config)
        analyzer = ComprehensiveMarketAnalyzer(client)
        
        # Create mock market data
        mock_data = {
            "timestamp": "2024-01-01T00:00:00Z",
            "coin_id": "bitcoin",
            "symbol": "BTC",
            "current_price": 50000.0,
            "technical": {
                "trend": "bullish",
                "support_resistance": "Support: $48000, Resistance: $52000",
                "volume": "high",
                "momentum": "strong",
                "rsi": 65.0,
                "moving_averages": "EMA20: $49500, EMA50: $48500"
            },
            "social": {
                "twitter_sentiment": 0.7,
                "reddit_sentiment": 0.6,
                "community_activity": "high",
                "influencer_sentiment": 0.8,
                "momentum_score": 0.7
            },
            "news": {
                "headlines": "Bitcoin ETF approval expected",
                "sentiment": 0.8,
                "coverage_volume": "high"
            },
            "economic": {
                "fed_policy": "dovish",
                "inflation": "moderate",
                "indicators": "positive",
                "dollar_strength": "weak",
                "interest_rates": "stable"
            },
            "political": {
                "government_stability": 0.9,
                "events": "none",
                "geopolitical": "stable",
                "policy_announcements": "crypto-friendly"
            },
            "regulatory": {
                "news": "positive",
                "compliance": "improving",
                "legal": "favorable"
            },
            "market_structure": {
                "institutional_flows": "positive",
                "exchange_flows": "normal",
                "derivatives": "bullish",
                "onchain": "strong"
            },
            "volatility": {
                "current": "moderate",
                "trends": "decreasing",
                "risk_metrics": "low"
            }
        }
        
        # Test market analysis
        analysis_result = await analyzer.analyze_market(
            coin="BTC",
            market_data=mock_data,
            analysis_mode="normal"
        )
        
        print("✅ Market analysis successful!")
        print(f"   Analysis mode: {analysis_result.get('analysis_mode', 'unknown')}")
        print(f"   Coin: {analysis_result.get('coin', 'unknown')}")
        
        # Test crisis detection
        crisis_result = await analyzer.detect_crisis_events(mock_data)
        
        print("✅ Crisis detection successful!")
        print(f"   Crisis score: {crisis_result.get('crisis_score', 0):.2f}")
        print(f"   Crisis level: {crisis_result.get('crisis_level', 'none')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Market analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_crisis_detection():
    """Test crisis detection with high-risk scenario"""
    print("\n🧪 Testing Crisis Detection...")
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No API key available for crisis detection test")
        return False
    
    try:
        # Create LLM client and analyzer
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
            api_key=api_key,
            max_tokens=2000,
            temperature=0.1
        )
        
        client = LLMClient(llm_config)
        analyzer = ComprehensiveMarketAnalyzer(client)
        
        # Create crisis scenario data
        crisis_data = {
            "timestamp": "2024-01-01T00:00:00Z",
            "coin_id": "bitcoin",
            "symbol": "BTC",
            "current_price": 45000.0,
            "technical": {
                "trend": "bearish",
                "support_resistance": "Support: $40000, Resistance: $50000",
                "volume": "extreme",
                "momentum": "weak",
                "rsi": 25.0,
                "moving_averages": "EMA20: $47000, EMA50: $50000"
            },
            "social": {
                "twitter_sentiment": 0.2,
                "reddit_sentiment": 0.3,
                "community_activity": "panic",
                "influencer_sentiment": 0.1,
                "momentum_score": 0.2
            },
            "news": {
                "headlines": "Government shutdown, banking crisis, regulatory crackdown",
                "sentiment": 0.1,
                "coverage_volume": "extreme"
            },
            "economic": {
                "fed_policy": "emergency",
                "inflation": "high",
                "indicators": "negative",
                "dollar_strength": "strong",
                "interest_rates": "rising"
            },
            "political": {
                "government_stability": 0.1,
                "events": "government shutdown, political crisis",
                "geopolitical": "tense",
                "policy_announcements": "crypto ban proposed"
            },
            "regulatory": {
                "news": "major crackdown",
                "compliance": "strict",
                "legal": "hostile"
            },
            "market_structure": {
                "institutional_flows": "negative",
                "exchange_flows": "outflows",
                "derivatives": "bearish",
                "onchain": "weak"
            },
            "volatility": {
                "current": "extreme",
                "trends": "increasing",
                "risk_metrics": "critical"
            }
        }
        
        # Test crisis detection
        crisis_result = await analyzer.detect_crisis_events(crisis_data)
        
        print("✅ Crisis detection test successful!")
        print(f"   Crisis score: {crisis_result.get('crisis_score', 0):.2f}")
        print(f"   Crisis level: {crisis_result.get('crisis_level', 'none')}")
        print(f"   Crisis type: {crisis_result.get('crisis_type', 'none')}")
        print(f"   Recommended response: {crisis_result.get('recommended_response', 'normal')}")
        
        # Test escalated analysis
        if crisis_result.get("crisis_score", 0) > 0.7:
            escalated_analysis = await analyzer.analyze_market(
                coin="BTC",
                market_data=crisis_data,
                analysis_mode="crisis"
            )
            
            print("✅ Escalated analysis successful!")
            print(f"   Analysis mode: {escalated_analysis.get('analysis_mode', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Crisis detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("🚀 LLM Integration Test Suite")
    print("=" * 50)
    
    # Test 1: Basic connection
    connection_ok = await test_llm_connection()
    
    if not connection_ok:
        print("\n❌ Basic connection failed. Please check your API key.")
        return
    
    # Test 2: Market analysis
    analysis_ok = await test_market_analysis()
    
    # Test 3: Crisis detection
    crisis_ok = await test_crisis_detection()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   Basic Connection: {'✅ PASS' if connection_ok else '❌ FAIL'}")
    print(f"   Market Analysis: {'✅ PASS' if analysis_ok else '❌ FAIL'}")
    print(f"   Crisis Detection: {'✅ PASS' if crisis_ok else '❌ FAIL'}")
    
    if all([connection_ok, analysis_ok, crisis_ok]):
        print("\n🎉 All tests passed! LLM integration is ready to use.")
        print("\nNext steps:")
        print("1. Run paper trading: python scripts/paper_trading_24_7.py --config config/paper_24_7.yaml")
        print("2. Monitor costs in OpenAI dashboard")
        print("3. Adjust analysis intervals as needed")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
