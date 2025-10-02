"""
Intelligence System Integration

Integrates the new 4-tier intelligence system with the existing tracker.
This module provides a bridge between the old decision system and the new one.
"""

import asyncio
import logging
from typing import Optional

from ..intelligence import IntelligenceOrchestrator
from ..intelligence.models import TradingDecision
from ..data_feeds import SocialMediaAggregator, OrderbookAnalyzer


class IntelligenceIntegration:
    """
    Integrates intelligence orchestrator with tracker
    
    Provides:
    - Initialization of intelligence system
    - Bridge between sync and async
    - Fallback to old system if needed
    """
    
    def __init__(self, tracker, config=None):
        self.logger = logging.getLogger(__name__)
        self.tracker = tracker
        self.config = config or {}
        self.orchestrator: Optional[IntelligenceOrchestrator] = None
        self.enabled = False
        
        # Try to initialize
        self._initialize()
    
    def _initialize(self):
        """Initialize the intelligence system"""
        try:
            config_data = self.tracker.config_manager.load_full_config()
            intelligence_config = config_data.get('intelligence', {})
            
            if not intelligence_config.get('enabled', False):
                self.logger.info("Intelligence system disabled in config")
                return
            
            # Initialize data feeds
            data_feeds = self._init_data_feeds(intelligence_config)
            
            # Get LLM client
            llm_client = getattr(self.tracker, 'llm_client', None)
            if not llm_client:
                self.logger.warning("LLM client not available, intelligence system limited")
            
            # Initialize orchestrator
            self.orchestrator = IntelligenceOrchestrator(
                config=intelligence_config,
                llm_client=llm_client,
                data_feeds=data_feeds,
                ml_models=None,  # TODO: Add ML models
                strategies=None,  # TODO: Add strategies
                portfolio_manager=self.tracker.portfolio_manager
            )
            
            # Register alert callback
            self.orchestrator.register_alert_callback(self._handle_alert)
            
            self.enabled = True
            self.logger.info("Intelligence system initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize intelligence system: {e}")
            self.enabled = False
    
    def _init_data_feeds(self, config: dict):
        """Initialize data feeds"""
        class DataFeeds:
            pass
        
        data_feeds = DataFeeds()
        
        # Social media (enhanced with LLM)
        try:
            social_config = config.get('tier2_market', {}).get('social_media', {})
            if social_config.get('twitter', {}).get('enabled') or \
               social_config.get('reddit', {}).get('enabled'):
                
                # Use enhanced aggregator if LLM is available
                if hasattr(self, 'llm_client') and self.llm_client:
                    from ...data_feeds.social.enhanced_aggregator import EnhancedSocialMediaAggregator
                    data_feeds.social = EnhancedSocialMediaAggregator(social_config, self.llm_client)
                    self.logger.info("Enhanced social media feeds with LLM initialized")
                else:
                    data_feeds.social = SocialMediaAggregator(social_config)
                    self.logger.info("Standard social media feeds initialized")
        except Exception as e:
            self.logger.warning(f"Social media initialization failed: {e}")
        
        # Orderbook
        try:
            orderbook_config = config.get('tier2_market', {}).get('orderbook', {})
            if orderbook_config.get('enabled', True):
                # Get exchange client from tracker
                exchange_client = getattr(self.tracker, 'exchange_client', None)
                if not exchange_client and hasattr(self.tracker, 'execution_manager'):
                    # Try to get from execution manager
                    execution_manager = self.tracker.execution_manager
                    
                    # Check live executor first
                    if hasattr(execution_manager, 'live_executor') and execution_manager.live_executor:
                        exchange_client = getattr(execution_manager.live_executor, 'ex', None)
                    
                    # Check paper executor as fallback
                    if not exchange_client and hasattr(execution_manager, 'paper_executor') and execution_manager.paper_executor:
                        exchange_client = getattr(execution_manager.paper_executor, 'ex', None)
                
                if exchange_client:
                    data_feeds.orderbook = OrderbookAnalyzer(
                        exchange_client,
                        orderbook_config
                    )
                    self.logger.info("Orderbook analyzer initialized")
                else:
                    # Create a minimal exchange client for orderbook analysis in paper mode
                    try:
                        import ccxt
                        exchange_client = ccxt.binance({
                            'enableRateLimit': True,
                            'sandbox': False,  # Use public API for orderbook data
                        })
                        data_feeds.orderbook = OrderbookAnalyzer(
                            exchange_client,
                            orderbook_config
                        )
                        self.logger.info("Orderbook analyzer initialized with public exchange client")
                    except Exception as e:
                        self.logger.warning(f"Failed to create exchange client: {e}")
                        self.logger.warning("Exchange client not available for orderbook analysis")
        except Exception as e:
            self.logger.warning(f"Orderbook initialization failed: {e}")
        
        # On-chain data feeds (free APIs + LLM)
        try:
            onchain_config = config.get('tier2_market', {}).get('onchain', {})
            if onchain_config.get('enabled', False):
                from src.data_feeds.onchain import FreeOnChainAnalyzer, LLMOnChainAnalyzer
                
                if onchain_config.get('use_llm_analysis', True):
                    data_feeds.onchain = LLMOnChainAnalyzer(onchain_config)
                    self.logger.info("LLM-powered on-chain analyzer initialized")
                else:
                    data_feeds.onchain = FreeOnChainAnalyzer(onchain_config)
                    self.logger.info("Free on-chain analyzer initialized")
        except Exception as e:
            self.logger.warning(f"On-chain analyzer initialization failed: {e}")
        
        return data_feeds
    
    def make_decision_sync(self, coin_id: str, current_price: float) -> TradingDecision:
        """
        Synchronous wrapper for decision making
        
        Args:
            coin_id: Coin identifier
            current_price: Current price
            
        Returns:
            TradingDecision
        """
        if not self.enabled or not self.orchestrator:
            # Fallback to old system
            return self._fallback_decision(coin_id)
        
        try:
            # Run async decision in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                decision = loop.run_until_complete(
                    asyncio.wait_for(
                        self.orchestrator.make_decision(coin_id, current_price),
                        timeout=30.0
                    )
                )
                return decision
            finally:
                loop.close()
                
        except asyncio.TimeoutError:
            self.logger.warning(f"Intelligence decision timeout for {coin_id}")
            return self._fallback_decision(coin_id)
        except Exception as e:
            self.logger.error(f"Intelligence decision failed for {coin_id}: {e}")
            return self._fallback_decision(coin_id)
    
    async def make_decision_async(
        self,
        coin_id: str,
        current_price: float
    ) -> TradingDecision:
        """
        Async decision making
        
        Args:
            coin_id: Coin identifier
            current_price: Current price
            
        Returns:
            TradingDecision
        """
        if not self.enabled or not self.orchestrator:
            return self._fallback_decision(coin_id)
        
        try:
            decision = await asyncio.wait_for(
                self.orchestrator.make_decision(coin_id, current_price),
                timeout=30.0
            )
            return decision
        except asyncio.TimeoutError:
            self.logger.warning(f"Intelligence decision timeout for {coin_id}")
            return self._fallback_decision(coin_id)
        except Exception as e:
            self.logger.error(f"Intelligence decision failed for {coin_id}: {e}")
            return self._fallback_decision(coin_id)
    
    def _fallback_decision(self, coin_id: str) -> TradingDecision:
        """
        Fallback to old decision system
        
        Args:
            coin_id: Coin identifier
            
        Returns:
            TradingDecision (converted from old Decision)
        """
        try:
            from ..decision import make_decision
            old_decision = make_decision(self.tracker, coin_id)
            
            # Convert old Decision to new TradingDecision
            return TradingDecision(
                action=old_decision.action_recommended,
                confidence=old_decision.confidence,
                reason=f"Fallback: {old_decision.reason}",
                signal=old_decision.signal,
                tier_reached=0,
                metadata={'fallback': True}
            )
        except Exception as e:
            self.logger.error(f"Fallback decision failed: {e}")
            return TradingDecision.hold_default()
    
    def _handle_alert(self, service: str, message: str, level: str):
        """Handle alerts from intelligence system"""
        try:
            if level == "CRITICAL":
                self.tracker.notifier.alert(
                    f"Intelligence Alert: {service}",
                    message,
                    style="red"
                )
            elif level == "WARNING":
                self.tracker.notifier.alert(
                    f"Intelligence Warning: {service}",
                    message,
                    style="yellow"
                )
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
    
    def get_statistics(self) -> dict:
        """Get intelligence system statistics"""
        if not self.enabled or not self.orchestrator:
            return {'enabled': False}
        
        try:
            return {
                'enabled': True,
                **self.orchestrator.get_statistics()
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {'enabled': True, 'error': str(e)}
