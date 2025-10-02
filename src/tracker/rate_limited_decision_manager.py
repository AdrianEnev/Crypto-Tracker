"""
Rate-Limited Decision Manager

Manages trading decisions when external services are rate-limited or unavailable.
Implements proper backoff and fallback mechanisms.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..logger import log_event
from ..models import Decision


class ServiceStatus(Enum):
    """Status of external services."""
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class ServiceHealth:
    """Health status of an external service."""
    status: ServiceStatus
    backoff_until_ts: float = 0.0
    backoff_seconds: int = 0
    failure_count: int = 0
    last_error: Optional[str] = None


class RateLimitedDecisionManager:
    """
    Manages trading decisions when external services are rate-limited.
    
    Features:
    - Tracks status of all external services (LLM, social media, price feeds)
    - Implements 120s backoff for rate-limited services
    - Halts trading when critical services are unavailable
    - Provides user alerts for service status changes
    - Falls back to basic technical analysis when needed
    """
    
    def __init__(self, tracker):
        self.logger = logging.getLogger(__name__)
        self.tracker = tracker
        
        # Service health tracking
        self.services = {
            'llm': ServiceHealth(ServiceStatus.AVAILABLE),
            'social_media': ServiceHealth(ServiceStatus.AVAILABLE),
            'price_feeds': ServiceHealth(ServiceStatus.AVAILABLE),
            'crisis_detection': ServiceHealth(ServiceStatus.AVAILABLE),
            # Individual price feed services
            'coinmarketcap': ServiceHealth(ServiceStatus.AVAILABLE),
            'coingecko': ServiceHealth(ServiceStatus.AVAILABLE),
            'ccxt': ServiceHealth(ServiceStatus.AVAILABLE),
            'websocket': ServiceHealth(ServiceStatus.AVAILABLE)
        }
        
        # Configuration
        self.backoff_base_seconds = 120  # 2 minutes
        self.max_backoff_seconds = 600   # 10 minutes
        self.max_failures = 5
        self.trading_halt_threshold = 2  # Halt if 2+ critical services down
        
        # Critical services that can halt trading
        self.critical_services = {'llm', 'price_feeds', 'crisis_detection', 'coinmarketcap', 'coingecko'}
        
        # State
        self.trading_halted = False
        self.last_alert_time = 0.0
        self.alert_cooldown = 300  # 5 minutes between alerts
        
    def update_service_status(
        self, 
        service_name: str, 
        status, 
        error_msg: Optional[str] = None,
        backoff_seconds: int = 0
    ):
        """Update the status of a service."""
        if service_name not in self.services:
            self.logger.warning(f"Unknown service: {service_name}")
            return
        
        service = self.services[service_name]
        old_status = service.status
        
        # Handle both ServiceStatus enum and string values
        if isinstance(status, str):
            try:
                status = ServiceStatus(status)
            except ValueError:
                self.logger.warning(f"Invalid status: {status}")
                return
        
        service.status = status
        service.last_error = error_msg
        
        if backoff_seconds > 0:
            service.backoff_seconds = backoff_seconds
            service.backoff_until_ts = time.time() + backoff_seconds
        
        # Log status change
        if old_status != status:
            self.logger.info(f"Service {service_name} status changed: {old_status.value} -> {status.value}")
            log_event("service_status_change", {
                "service": service_name,
                "old_status": old_status.value,
                "new_status": status.value,
                "error": error_msg,
                "backoff_seconds": backoff_seconds
            })
            
            # Send user alert for critical changes
            self._send_service_alert(service_name, status, error_msg)
        
        # Check if trading should be halted
        self._update_trading_status()
    
    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is currently available."""
        if service_name not in self.services:
            return False
        
        service = self.services[service_name]
        
        if service.status == ServiceStatus.DISABLED:
            return False
        
        if service.status == ServiceStatus.RATE_LIMITED:
            return time.time() >= service.backoff_until_ts
        
        return service.status == ServiceStatus.AVAILABLE
    
    def get_service_backoff_remaining(self, service_name: str) -> int:
        """Get remaining backoff time for a service in seconds."""
        if service_name not in self.services:
            return 0
        
        service = self.services[service_name]
        if service.backoff_until_ts <= 0:
            return 0
        
        return max(0, int(service.backoff_until_ts - time.time()))
    
    def should_halt_trading(self) -> bool:
        """
        Determine if trading should be halted due to service issues.
        
        Returns:
            True if trading should be halted
        """
        if self.trading_halted:
            return True
        
        # Count unavailable critical services
        unavailable_critical = 0
        for service_name in self.critical_services:
            if not self.is_service_available(service_name):
                unavailable_critical += 1
        
        return unavailable_critical >= self.trading_halt_threshold
    
    def get_available_services(self) -> List[str]:
        """Get list of currently available services."""
        return [
            service_name for service_name in self.services.keys()
            if self.is_service_available(service_name)
        ]
    
    def get_unavailable_services(self) -> List[Tuple[str, str, int]]:
        """
        Get list of unavailable services with their status and backoff time.
        
        Returns:
            List of tuples (service_name, status, backoff_remaining)
        """
        unavailable = []
        for service_name, service in self.services.items():
            if not self.is_service_available(service_name):
                backoff_remaining = self.get_service_backoff_remaining(service_name)
                unavailable.append((service_name, service.status.value, backoff_remaining))
        
        return unavailable
    
    def make_safe_decision(self, coin_id: str, current_price: float) -> Decision:
        """
        Make a safe trading decision when external services are unavailable.
        
        This falls back to basic technical analysis without LLM or social media.
        """
        try:
            # Use basic technical analysis only
            from ..decision import make_decision
            
            # Temporarily disable enhanced features
            enhanced_features_backup = getattr(self.tracker, 'enhanced_features_backup', {})
            if hasattr(self.tracker, 'config_manager'):
                config_data = self.tracker.config_manager.load_full_config()
                enhanced_features = config_data.get('enhanced_features', {})
                
                # Backup current settings
                enhanced_features_backup = {
                    'social_media': enhanced_features.get('social_media', {}).get('enabled', False),
                    'llm': enhanced_features.get('llm', {}).get('enabled', False)
                }
                
                # Temporarily disable enhanced features
                enhanced_features.setdefault('social_media', {})['enabled'] = False
                enhanced_features.setdefault('llm', {})['enabled'] = False
            
            # Make basic decision
            decision = make_decision(self.tracker, coin_id)
            
            # Add safety context to reason
            decision.reason = f"SAFE_MODE: {decision.reason}"
            decision.confidence = min(decision.confidence, 0.5)  # Cap confidence in safe mode
            
            # Restore enhanced features settings
            if enhanced_features_backup:
                enhanced_features.get('social_media', {})['enabled'] = enhanced_features_backup['social_media']
                enhanced_features.get('llm', {})['enabled'] = enhanced_features_backup['llm']
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Safe decision making failed for {coin_id}: {e}")
            # Return conservative hold decision
            return Decision(
                signal="safe_mode_error",
                confidence=0.0,
                action_recommended="Hold",
                reason=f"Safe mode error: {str(e)}"
            )
    
    def _update_trading_status(self):
        """Update trading halt status based on service availability."""
        should_halt = self.should_halt_trading()
        
        if should_halt and not self.trading_halted:
            self.trading_halted = True
            self.logger.warning("TRADING HALTED: Critical services unavailable")
            log_event("trading_halted", {
                "reason": "critical_services_unavailable",
                "unavailable_services": self.get_unavailable_services()
            })
            
            # Send alert to user
            unavailable = self.get_unavailable_services()
            services_text = ", ".join([f"{name} ({status})" for name, status, _ in unavailable])
            self._send_trading_alert(
                "Trading Halted",
                f"Critical services unavailable: {services_text}",
                "red"
            )
            
        elif not should_halt and self.trading_halted:
            self.trading_halted = False
            self.logger.info("Trading resumed: Critical services recovered")
            log_event("trading_resumed", {
                "reason": "critical_services_recovered"
            })
            
            # Send recovery alert
            self._send_trading_alert(
                "Trading Resumed",
                "Critical services have recovered",
                "green"
            )
    
    def _send_service_alert(self, service_name: str, status: ServiceStatus, error_msg: Optional[str]):
        """Send alert about service status change."""
        try:
            if not hasattr(self.tracker, 'notifier'):
                return
            
            current_time = time.time()
            if current_time - self.last_alert_time < self.alert_cooldown:
                return  # Rate limit alerts
            
            self.last_alert_time = current_time
            
            if status == ServiceStatus.RATE_LIMITED:
                backoff_remaining = self.get_service_backoff_remaining(service_name)
                message = f"{service_name} rate-limited. Backing off for {backoff_remaining}s"
                style = "yellow"
            elif status == ServiceStatus.DISABLED:
                message = f"{service_name} disabled due to repeated failures"
                style = "red"
            elif status == ServiceStatus.AVAILABLE:
                message = f"{service_name} service recovered"
                style = "green"
            else:
                message = f"{service_name} error: {error_msg}"
                style = "red"
            
            self.tracker.notifier.alert(
                f"Service Alert: {service_name}",
                message,
                style=style
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send service alert: {e}")
    
    def _send_trading_alert(self, title: str, message: str, style: str):
        """Send trading status alert."""
        try:
            if not hasattr(self.tracker, 'notifier'):
                return
            
            self.tracker.notifier.alert(title, message, style=style)
            
        except Exception as e:
            self.logger.error(f"Failed to send trading alert: {e}")
    
    def update_price_feed_status(self, aggregator):
        """Update status of price feed services based on aggregator state."""
        try:
            if not hasattr(aggregator, 'enabled_sources'):
                return
            
            # Check CoinMarketCap status
            if 'cmc' in aggregator.enabled_sources and hasattr(aggregator, 'cmc'):
                cmc_fetcher = aggregator.cmc
                if hasattr(cmc_fetcher, 'backoff_until_ts') and cmc_fetcher.backoff_until_ts > 0:
                    if time.time() < cmc_fetcher.backoff_until_ts:
                        remaining = int(cmc_fetcher.backoff_until_ts - time.time())
                        self.update_service_status('coinmarketcap', 'rate_limited', 
                                                 f'CoinMarketCap rate-limited for {remaining}s', remaining)
                    else:
                        self.update_service_status('coinmarketcap', 'available')
                else:
                    self.update_service_status('coinmarketcap', 'available')
            
            # Check CoinGecko status
            if 'coingecko' in aggregator.enabled_sources and hasattr(aggregator, 'cg'):
                cg_fetcher = aggregator.cg
                if hasattr(cg_fetcher, 'backoff_until_ts') and cg_fetcher.backoff_until_ts > 0:
                    if time.time() < cg_fetcher.backoff_until_ts:
                        remaining = int(cg_fetcher.backoff_until_ts - time.time())
                        self.update_service_status('coingecko', 'rate_limited', 
                                                 f'CoinGecko rate-limited for {remaining}s', remaining)
                    else:
                        self.update_service_status('coingecko', 'available')
                else:
                    self.update_service_status('coingecko', 'available')
            
            # Check CCXT status
            if 'ccxt' in aggregator.enabled_sources and hasattr(aggregator, 'ccxt') and aggregator.ccxt:
                # CCXT doesn't have built-in rate limiting like CMC/CG, so we'll mark as available
                # unless there are specific failure indicators
                self.update_service_status('ccxt', 'available')
            
            # Check WebSocket status
            if 'websocket' in aggregator.enabled_sources and hasattr(aggregator, 'websocket') and aggregator.websocket:
                # WebSocket status would need to be tracked separately
                self.update_service_status('websocket', 'available')
                
        except Exception as e:
            self.logger.warning(f"Failed to update price feed status: {e}")
    
    def handle_price_feed_failure(self, feed_name: str, error_message: str, backoff_seconds: int = 0):
        """Handle price feed failure and update service status."""
        try:
            # Map feed names to service names
            feed_mapping = {
                'cmc': 'coinmarketcap',
                'coingecko': 'coingecko',
                'ccxt': 'ccxt',
                'websocket': 'websocket'
            }
            
            service_name = feed_mapping.get(feed_name.lower(), feed_name.lower())
            
            if backoff_seconds > 0:
                self.update_service_status(service_name, 'rate_limited', error_message, backoff_seconds)
            else:
                self.update_service_status(service_name, 'error', error_message)
                
        except Exception as e:
            self.logger.warning(f"Failed to handle price feed failure for {feed_name}: {e}")
    
    def get_status_summary(self) -> Dict:
        """Get comprehensive status summary."""
        available_services = self.get_available_services()
        unavailable_services = self.get_unavailable_services()
        
        # Separate price feeds from other services for display
        price_feeds = [name for name in available_services if name in ['coinmarketcap', 'coingecko', 'ccxt', 'websocket']]
        other_services = [name for name in available_services if name not in ['coinmarketcap', 'coingecko', 'ccxt', 'websocket']]
        
        unavailable_price_feeds = [(name, status, backoff) for name, status, backoff in unavailable_services 
                                 if name in ['coinmarketcap', 'coingecko', 'ccxt', 'websocket']]
        unavailable_other = [(name, status, backoff) for name, status, backoff in unavailable_services 
                           if name not in ['coinmarketcap', 'coingecko', 'ccxt', 'websocket']]
        
        return {
            'trading_halted': self.trading_halted,
            'available_services': available_services,
            'available_price_feeds': price_feeds,
            'available_other_services': other_services,
            'unavailable_services': [
                {
                    'name': name,
                    'status': status,
                    'backoff_remaining': backoff
                }
                for name, status, backoff in unavailable_services
            ],
            'unavailable_price_feeds': [
                {
                    'name': name,
                    'status': status,
                    'backoff_remaining': backoff
                }
                for name, status, backoff in unavailable_price_feeds
            ],
            'unavailable_other_services': [
                {
                    'name': name,
                    'status': status,
                    'backoff_remaining': backoff
                }
                for name, status, backoff in unavailable_other
            ],
            'critical_services_down': len([
                name for name, _, _ in unavailable_services
                if name in self.critical_services
            ])
        }
