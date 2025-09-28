"""
Order Book Data Fetcher

Fetches Level 2 order book data from various exchanges using CCXT
and other data sources for historical replay and simulation.
"""

from __future__ import annotations
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime, timedelta
import asyncio
import time

import ccxt  # type: ignore

from .models import OrderBookSnapshot, OrderBookEvent, OrderBookEventType


class OrderBookFetcher:
    """Fetches order book data from exchanges."""
    
    def __init__(self, exchange_name: str, api_key: Optional[str] = None, secret: Optional[str] = None):
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.secret = secret
        
        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_name)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'sandbox': False,
        })
        
        # Load markets
        try:
            self.markets = self.exchange.load_markets()
        except Exception as e:
            print(f"Warning: Failed to load markets for {exchange_name}: {e}")
            self.markets = {}
    
    def fetch_order_book(self, symbol: str, limit: int = 100) -> Optional[OrderBookSnapshot]:
        """
        Fetch current order book snapshot.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            limit: Maximum number of levels to fetch
            
        Returns:
            OrderBookSnapshot or None if failed
        """
        try:
            # Fetch order book from exchange
            order_book = self.exchange.fetch_order_book(symbol, limit)
            
            # Convert to our format
            timestamp = datetime.now()
            
            # Process bids (price, quantity pairs)
            bids = []
            for price, quantity in order_book.get('bids', []):
                if price > 0 and quantity > 0:
                    bids.append((price, quantity))
            
            # Process asks (price, quantity pairs)
            asks = []
            for price, quantity in order_book.get('asks', []):
                if price > 0 and quantity > 0:
                    asks.append((price, quantity))
            
            # Get last trade info
            last_trade_price = order_book.get('last')
            last_trade_id = order_book.get('lastTradeId')
            
            return OrderBookSnapshot(
                symbol=symbol,
                timestamp=timestamp,
                bids=bids,
                asks=asks,
                last_trade_price=last_trade_price,
                last_trade_id=last_trade_id,
                sequence_number=order_book.get('sequence')
            )
            
        except Exception as e:
            print(f"Failed to fetch order book for {symbol}: {e}")
            return None
    
    def fetch_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """
        Fetch recent trades for a symbol.
        
        Args:
            symbol: Trading symbol
            limit: Maximum number of trades to fetch
            
        Returns:
            List of trade dictionaries
        """
        try:
            trades = self.exchange.fetch_trades(symbol, limit=limit)
            return trades
        except Exception as e:
            print(f"Failed to fetch trades for {symbol}: {e}")
            return []
    
    def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Fetch ticker data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Ticker data dictionary or None if failed
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            print(f"Failed to fetch ticker for {symbol}: {e}")
            return None
    
    def get_supported_symbols(self) -> List[str]:
        """Get list of supported trading symbols."""
        return list(self.markets.keys())
    
    def is_symbol_supported(self, symbol: str) -> bool:
        """Check if a symbol is supported."""
        return symbol in self.markets
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol information."""
        return self.markets.get(symbol)
    
    async def stream_order_book_updates(
        self, 
        symbol: str, 
        duration_seconds: int = 60
    ) -> AsyncGenerator[OrderBookEvent, None]:
        """
        Stream order book updates for a specified duration.
        
        Args:
            symbol: Trading symbol
            duration_seconds: How long to stream (0 = indefinitely)
            
        Yields:
            OrderBookEvent objects
        """
        start_time = time.time()
        last_snapshot = None
        
        while True:
            try:
                # Check duration
                if duration_seconds > 0 and (time.time() - start_time) > duration_seconds:
                    break
                
                # Fetch current order book
                current_snapshot = self.fetch_order_book(symbol)
                if not current_snapshot:
                    await asyncio.sleep(1.0)
                    continue
                
                # Create update event
                if last_snapshot:
                    # Calculate differences
                    bids_update = self._calculate_bid_updates(last_snapshot.bids.levels, current_snapshot.bids.levels)
                    asks_update = self._calculate_ask_updates(last_snapshot.asks.levels, current_snapshot.asks.levels)
                    
                    if bids_update or asks_update:
                        event = OrderBookEvent(
                            symbol=symbol,
                            timestamp=current_snapshot.timestamp,
                            event_type=OrderBookEventType.UPDATE,
                            bids_update=bids_update,
                            asks_update=asks_update,
                            sequence_number=current_snapshot.sequence_number
                        )
                        yield event
                else:
                    # First snapshot
                    event = OrderBookEvent(
                        symbol=symbol,
                        timestamp=current_snapshot.timestamp,
                        event_type=OrderBookEventType.SNAPSHOT,
                        sequence_number=current_snapshot.sequence_number
                    )
                    yield event
                
                last_snapshot = current_snapshot
                await asyncio.sleep(0.1)  # 100ms update rate
                
            except Exception as e:
                print(f"Error in order book stream: {e}")
                await asyncio.sleep(1.0)
    
    def _calculate_bid_updates(
        self, 
        old_levels: List, 
        new_levels: List
    ) -> List[Tuple[float, float]]:
        """Calculate bid updates between two snapshots."""
        updates = []
        
        # Create dictionaries for easy lookup
        old_dict = {level.price: level.quantity for level in old_levels}
        new_dict = {level.price: level.quantity for level in new_levels}
        
        # Check for updates and new levels
        for price, quantity in new_dict.items():
            if price not in old_dict or old_dict[price] != quantity:
                updates.append((price, quantity))
        
        # Check for removed levels (quantity = 0)
        for price in old_dict:
            if price not in new_dict:
                updates.append((price, 0.0))
        
        return updates
    
    def _calculate_ask_updates(
        self, 
        old_levels: List, 
        new_levels: List
    ) -> List[Tuple[float, float]]:
        """Calculate ask updates between two snapshots."""
        # Same logic as bids
        return self._calculate_bid_updates(old_levels, new_levels)
    
    def fetch_historical_order_books(
        self, 
        symbol: str, 
        start_time: datetime, 
        end_time: datetime,
        interval_minutes: int = 1
    ) -> List[OrderBookSnapshot]:
        """
        Fetch historical order book snapshots.
        
        Note: Most exchanges don't provide historical order book data.
        This is a placeholder for future implementation or premium data feeds.
        """
        print(f"Warning: Historical order book data not available for {self.exchange_name}")
        print("This would require premium data feeds or exchange-specific APIs")
        return []
    
    def test_connection(self) -> bool:
        """Test connection to the exchange."""
        try:
            # Try to fetch a simple ticker
            symbols = self.get_supported_symbols()
            if symbols:
                ticker = self.fetch_ticker(symbols[0])
                return ticker is not None
            return False
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


class MultiExchangeOrderBookFetcher:
    """Fetches order book data from multiple exchanges."""
    
    def __init__(self, exchanges_config: Dict[str, Dict[str, str]]):
        """
        Initialize with multiple exchange configurations.
        
        Args:
            exchanges_config: Dict of {exchange_name: {api_key: str, secret: str}}
        """
        self.fetchers: Dict[str, OrderBookFetcher] = {}
        
        for exchange_name, config in exchanges_config.items():
            try:
                fetcher = OrderBookFetcher(
                    exchange_name=exchange_name,
                    api_key=config.get('api_key'),
                    secret=config.get('secret')
                )
                
                if fetcher.test_connection():
                    self.fetchers[exchange_name] = fetcher
                    print(f"✅ Connected to {exchange_name}")
                else:
                    print(f"❌ Failed to connect to {exchange_name}")
                    
            except Exception as e:
                print(f"❌ Error initializing {exchange_name}: {e}")
    
    def get_exchanges(self) -> List[str]:
        """Get list of connected exchanges."""
        return list(self.fetchers.keys())
    
    def fetch_order_book(self, symbol: str, exchange: Optional[str] = None) -> Optional[OrderBookSnapshot]:
        """
        Fetch order book from specified exchange or best available.
        
        Args:
            symbol: Trading symbol
            exchange: Specific exchange to use (optional)
            
        Returns:
            OrderBookSnapshot or None
        """
        if exchange:
            if exchange in self.fetchers:
                return self.fetchers[exchange].fetch_order_book(symbol)
            return None
        
        # Try all exchanges
        for exchange_name, fetcher in self.fetchers.items():
            if fetcher.is_symbol_supported(symbol):
                result = fetcher.fetch_order_book(symbol)
                if result:
                    return result
        
        return None
    
    def fetch_all_exchanges_order_books(self, symbol: str) -> Dict[str, Optional[OrderBookSnapshot]]:
        """Fetch order book from all exchanges for comparison."""
        results = {}
        
        for exchange_name, fetcher in self.fetchers.items():
            if fetcher.is_symbol_supported(symbol):
                results[exchange_name] = fetcher.fetch_order_book(symbol)
            else:
                results[exchange_name] = None
        
        return results
    
    def compare_spreads(self, symbol: str) -> Dict[str, Dict[str, float]]:
        """Compare spreads across all exchanges."""
        order_books = self.fetch_all_exchanges_order_books(symbol)
        spreads = {}
        
        for exchange, order_book in order_books.items():
            if order_book and order_book.is_valid():
                spreads[exchange] = {
                    "spread": order_book.spread or 0.0,
                    "spread_bps": order_book.spread_bps or 0.0,
                    "best_bid": order_book.best_bid or 0.0,
                    "best_ask": order_book.best_ask or 0.0,
                    "mid_price": order_book.mid_price or 0.0
                }
        
        return spreads
