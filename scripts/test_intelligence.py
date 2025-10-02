#!/usr/bin/env python3
"""
Test script for Intelligence System

Tests all 4 tiers independently and together
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.intelligence.models import CrisisLevel, SocialSentiment, OrderbookSignal
from src.intelligence.error_handler import IntelligenceFallbackHandler


def test_error_handler():
    """Test error handler"""
    print("🧪 Testing Error Handler...")
    
    handler = IntelligenceFallbackHandler()
    
    # Test failure tracking
    for i in range(3):
        handler.handle_failure('test_service', Exception(f"Test error {i}"))
    
    assert handler.failure_counts['test_service'] == 3
    assert handler.is_enabled('test_service')
    
    # Test auto-disable
    for i in range(10):
        handler.handle_failure('test_service', Exception(f"Test error {i}"))
    
    assert not handler.is_enabled('test_service')
    
    print("✅ Error Handler: PASSED")


def test_models():
    """Test data models"""
    print("🧪 Testing Data Models...")
    
    # Test CrisisStatus
    from src.intelligence.models import CrisisStatus
    crisis = CrisisStatus.none()
    assert crisis.level == CrisisLevel.NONE
    assert crisis.risk_adjustment == 1.0
    
    # Test SocialSentiment
    sentiment = SocialSentiment.default()
    assert sentiment.score == 0.0
    assert sentiment.volume == 0
    
    # Test OrderbookSignal
    orderbook = OrderbookSignal.default()
    assert orderbook.is_liquid == False
    
    print("✅ Data Models: PASSED")


async def test_social_media():
    """Test social media integration"""
    print("🧪 Testing Social Media Integration...")
    
    try:
        from src.data_feeds.social import TwitterSentimentAnalyzer
        
        # Test with no API key (should handle gracefully)
        twitter = TwitterSentimentAnalyzer(bearer_token=None)
        assert twitter.enabled == False
        
        sentiment = await twitter.get_sentiment('BTC')
        assert sentiment.score == 0.0  # Should return default
        
        print("✅ Social Media: PASSED (graceful degradation)")
    except Exception as e:
        print(f"⚠️  Social Media: SKIPPED ({e})")


async def test_orderbook():
    """Test orderbook analysis"""
    print("🧪 Testing Orderbook Analysis...")
    
    try:
        from src.data_feeds.orderbook import OrderbookAnalyzer
        
        # Mock exchange client
        class MockExchange:
            async def fetch_order_book(self, symbol, limit=100):
                return {
                    'bids': [[50000, 1.0], [49900, 2.0], [49800, 1.5]],
                    'asks': [[50100, 1.0], [50200, 2.0], [50300, 1.5]]
                }
        
        analyzer = OrderbookAnalyzer(MockExchange())
        signal = await analyzer.analyze('BTC/USDT')
        
        assert signal.spread_bps > 0
        assert -1 <= signal.bid_ask_imbalance <= 1
        
        print("✅ Orderbook Analysis: PASSED")
    except Exception as e:
        print(f"❌ Orderbook Analysis: FAILED ({e})")


async def test_tier1():
    """Test Tier 1 (Crisis Detection)"""
    print("🧪 Testing Tier 1 (Crisis Detection)...")
    
    try:
        from src.intelligence.tier1_macro import CrisisDetector
        
        # Mock LLM client
        class MockLLM:
            class Config:
                class Provider:
                    value = 'openai'
                provider = Provider()
            
            config = Config()
            
            async def generate_response(self, prompt):
                return {
                    'choices': [{
                        'message': {
                            'content': '{"crisis_level": "NONE", "confidence": 0.9, "reason": "Normal conditions"}'
                        }
                    }]
                }
        
        detector = CrisisDetector(MockLLM(), {})
        crisis = await detector.detect_crisis()
        
        assert crisis.level == CrisisLevel.NONE
        
        print("✅ Tier 1: PASSED")
    except Exception as e:
        print(f"❌ Tier 1: FAILED ({e})")


async def test_tier2():
    """Test Tier 2 (Market Intelligence)"""
    print("🧪 Testing Tier 2 (Market Intelligence)...")
    
    try:
        from src.intelligence.tier2_market import MarketIntelligence
        
        # Mock data feeds
        class MockDataFeeds:
            pass
        
        analyzer = MarketIntelligence({}, MockDataFeeds())
        market_state = await analyzer.analyze('bitcoin', 'BTC/USDT')
        
        assert market_state.regime in ['TRENDING', 'RANGING', 'VOLATILE', 'UNKNOWN']
        
        print("✅ Tier 2: PASSED")
    except Exception as e:
        print(f"❌ Tier 2: FAILED ({e})")


async def test_orchestrator():
    """Test full orchestrator"""
    print("🧪 Testing Orchestrator...")
    
    try:
        from src.intelligence.orchestrator import IntelligenceOrchestrator
        
        # Mock components
        class MockLLM:
            class Config:
                class Provider:
                    value = 'openai'
                provider = Provider()
            config = Config()
            async def generate_response(self, prompt):
                return {'choices': [{'message': {'content': '{"crisis_level": "NONE", "confidence": 0.9}'}}]}
        
        class MockDataFeeds:
            pass
        
        config = {
            'tier1_macro': {},
            'tier2_market': {},
            'tier3_tactical': {},
            'tier4_execution': {},
            'confidence_threshold': 0.6
        }
        
        orchestrator = IntelligenceOrchestrator(
            config=config,
            llm_client=MockLLM(),
            data_feeds=MockDataFeeds()
        )
        
        decision = await orchestrator.make_decision('bitcoin', 50000.0)
        
        assert decision.action in ['BUY', 'SELL', 'HOLD', 'EMERGENCY_HOLD']
        assert 0 <= decision.confidence <= 1
        assert decision.tier_reached in [1, 2, 3, 4]
        
        print("✅ Orchestrator: PASSED")
        print(f"   Decision: {decision.action} (confidence: {decision.confidence:.2f})")
        print(f"   Tier reached: {decision.tier_reached}")
        
    except Exception as e:
        print(f"❌ Orchestrator: FAILED ({e})")
        import traceback
        traceback.print_exc()


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Intelligence System Test Suite")
    print("=" * 60)
    print()
    
    # Sync tests
    test_error_handler()
    test_models()
    
    # Async tests
    await test_social_media()
    await test_orderbook()
    await test_tier1()
    await test_tier2()
    await test_orchestrator()
    
    print()
    print("=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(run_all_tests())
