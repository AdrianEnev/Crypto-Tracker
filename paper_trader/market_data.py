"""
Market Data Adapter

Provides market data for paper trading in both replay and live modes.
Supports historical data replay and real-time market data streaming.
"""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Callable
import pandas as pd
import ccxt

from .broker import BrokerError


class DataMode(Enum):
    """Market data modes."""
    
    REPLAY = "replay"  # Historical data replay
    LIVE = "live"      # Real-time data streaming
    HYBRID = "hybrid"  # Start with replay, switch to live


class DataSource(Enum):
    """Data sources."""
    
    LOCAL_FILE = "local_file"  # Local JSON/CSV files
    CCXT_REST = "ccxt_rest"    # CCXT REST API
    CCXT_WS = "ccxt_ws"        # CCXT WebSocket
    CUSTOM = "custom"          # Custom data provider


@dataclass
class MarketDataConfig:
    """Configuration for market data adapter."""
    
    mode: DataMode = DataMode.REPLAY
    source: DataSource = DataSource.LOCAL_FILE
    
    # Replay settings
    replay_speed: float = 1.0  # Speed multiplier (1.0 = real time)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Live settings
    exchange: str = "binance"
    symbols: List[str] = None
    update_interval: float = 1.0  # Seconds between updates
    
    # Data file settings
    data_directory: str = "./data_cache"
    file_format: str = "jsonl"  # jsonl, csv, parquet
    
    # WebSocket settings
    ws_url: Optional[str] = None
    ws_channels: List[str] = None
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]


@dataclass
class MarketTick:
    """Single market data tick."""
    
    symbol: str
    timestamp: datetime
    price: float
    volume: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None
    
    def to_ticker(self) -> Dict[str, Any]:
        """Convert to ticker format."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "last": self.price,
            "bid": self.bid or self.price,
            "ask": self.ask or self.price,
            "high": self.high or self.price,
            "low": self.low or self.price,
            "open": self.open or self.price,
            "close": self.close or self.price,
            "volume": self.volume or 0.0,
        }


class MarketDataProvider(ABC):
    """Abstract base class for market data providers."""
    
    @abstractmethod
    async def get_data(self, symbol: str, start_time: Optional[datetime] = None, 
                      end_time: Optional[datetime] = None) -> List[MarketTick]:
        """Get market data for a symbol."""
        pass
    
    @abstractmethod
    async def stream_data(self, symbol: str) -> AsyncGenerator[MarketTick, None]:
        """Stream real-time market data for a symbol."""
        pass


class LocalFileProvider(MarketDataProvider):
    """Market data provider for local files."""
    
    def __init__(self, config: MarketDataConfig):
        self.config = config
        self.data_directory = Path(config.data_directory)
    
    async def get_data(self, symbol: str, start_time: Optional[datetime] = None, 
                      end_time: Optional[datetime] = None) -> List[MarketTick]:
        """Load data from local files."""
        
        # Find data file for symbol
        data_file = self._find_data_file(symbol)
        if not data_file or not data_file.exists():
            raise BrokerError(f"No data file found for symbol {symbol}", "LocalFileProvider")
        
        # Load data based on format
        if self.config.file_format == "jsonl":
            return await self._load_jsonl(data_file, symbol, start_time, end_time)
        elif self.config.file_format == "csv":
            return await self._load_csv(data_file, symbol, start_time, end_time)
        elif self.config.file_format == "parquet":
            return await self._load_parquet(data_file, symbol, start_time, end_time)
        else:
            raise BrokerError(f"Unsupported file format: {self.config.file_format}", "LocalFileProvider")
    
    async def stream_data(self, symbol: str) -> AsyncGenerator[MarketTick, None]:
        """Stream data from local files (replay mode)."""
        
        data = await self.get_data(symbol, self.config.start_time, self.config.end_time)
        
        for tick in data:
            yield tick
            
            # Simulate real-time delay
            if self.config.replay_speed > 0:
                await asyncio.sleep(1.0 / self.config.replay_speed)
    
    def _find_data_file(self, symbol: str) -> Optional[Path]:
        """Find data file for symbol."""
        
        # Try different naming patterns
        patterns = [
            f"binance_{symbol.replace('/', '-')}_*.{self.config.file_format}",
            f"{symbol.replace('/', '_').lower()}*.{self.config.file_format}",
            f"{symbol.replace('/', '-').lower()}*.{self.config.file_format}",
        ]
        
        for pattern in patterns:
            files = list(self.data_directory.glob(pattern))
            if files:
                return files[0]  # Return first match
        
        return None
    
    async def _load_jsonl(self, file_path: Path, symbol: str, 
                         start_time: Optional[datetime], end_time: Optional[datetime]) -> List[MarketTick]:
        """Load data from JSONL file."""
        
        ticks = []
        
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    
                    # Parse timestamp
                    if 'timestamp' in data:
                        timestamp = datetime.fromtimestamp(data['timestamp'], tz=timezone.utc)
                    elif 'time' in data:
                        timestamp = datetime.fromtimestamp(data['time'], tz=timezone.utc)
                    else:
                        continue
                    
                    # Filter by time range
                    if start_time and timestamp < start_time:
                        continue
                    if end_time and timestamp > end_time:
                        continue
                    
                    # Create tick
                    tick = MarketTick(
                        symbol=symbol,
                        timestamp=timestamp,
                        price=data.get('close', data.get('price', 0.0)),
                        volume=data.get('volume', 0.0),
                        high=data.get('high'),
                        low=data.get('low'),
                        open=data.get('open'),
                        close=data.get('close'),
                    )
                    
                    ticks.append(tick)
                
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        
        return sorted(ticks, key=lambda x: x.timestamp)
    
    async def _load_csv(self, file_path: Path, symbol: str, 
                       start_time: Optional[datetime], end_time: Optional[datetime]) -> List[MarketTick]:
        """Load data from CSV file."""
        
        df = pd.read_csv(file_path)
        
        # Convert timestamp column
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
        elif 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['time'], unit='s', utc=True)
        else:
            raise BrokerError("No timestamp column found in CSV", "LocalFileProvider")
        
        # Filter by time range
        if start_time:
            df = df[df['timestamp'] >= start_time]
        if end_time:
            df = df[df['timestamp'] <= end_time]
        
        # Convert to ticks
        ticks = []
        for _, row in df.iterrows():
            tick = MarketTick(
                symbol=symbol,
                timestamp=row['timestamp'],
                price=row.get('close', row.get('price', 0.0)),
                volume=row.get('volume', 0.0),
                high=row.get('high'),
                low=row.get('low'),
                open=row.get('open'),
                close=row.get('close'),
            )
            ticks.append(tick)
        
        return ticks
    
    async def _load_parquet(self, file_path: Path, symbol: str, 
                           start_time: Optional[datetime], end_time: Optional[datetime]) -> List[MarketTick]:
        """Load data from Parquet file."""
        
        df = pd.read_parquet(file_path)
        
        # Convert timestamp column
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
        elif 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['time'], unit='s', utc=True)
        else:
            raise BrokerError("No timestamp column found in Parquet", "LocalFileProvider")
        
        # Filter by time range
        if start_time:
            df = df[df['timestamp'] >= start_time]
        if end_time:
            df = df[df['timestamp'] <= end_time]
        
        # Convert to ticks
        ticks = []
        for _, row in df.iterrows():
            tick = MarketTick(
                symbol=symbol,
                timestamp=row['timestamp'],
                price=row.get('close', row.get('price', 0.0)),
                volume=row.get('volume', 0.0),
                high=row.get('high'),
                low=row.get('low'),
                open=row.get('open'),
                close=row.get('close'),
            )
            ticks.append(tick)
        
        return ticks


class CCXTProvider(MarketDataProvider):
    """Market data provider using CCXT."""
    
    def __init__(self, config: MarketDataConfig):
        self.config = config
        self.exchange = getattr(ccxt, config.exchange)()
    
    async def get_data(self, symbol: str, start_time: Optional[datetime] = None, 
                      end_time: Optional[datetime] = None) -> List[MarketTick]:
        """Get historical data from CCXT."""
        
        try:
            # Convert datetime to milliseconds
            since = None
            if start_time:
                since = int(start_time.timestamp() * 1000)
            
            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(symbol, '1m', since=since)
            
            ticks = []
            for candle in ohlcv:
                timestamp = datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc)
                
                # Filter by time range
                if end_time and timestamp > end_time:
                    break
                
                tick = MarketTick(
                    symbol=symbol,
                    timestamp=timestamp,
                    price=candle[4],  # close price
                    volume=candle[5],
                    high=candle[2],
                    low=candle[3],
                    open=candle[1],
                    close=candle[4],
                )
                ticks.append(tick)
            
            return ticks
        
        except Exception as e:
            raise BrokerError(f"Failed to fetch data from {self.config.exchange}: {e}", "CCXTProvider")
    
    async def stream_data(self, symbol: str) -> AsyncGenerator[MarketTick, None]:
        """Stream real-time data from CCXT (simulated with periodic fetches)."""
        
        while True:
            try:
                # Get current ticker
                ticker = self.exchange.fetch_ticker(symbol)
                
                tick = MarketTick(
                    symbol=symbol,
                    timestamp=datetime.now(timezone.utc),
                    price=ticker['last'],
                    volume=ticker.get('baseVolume', 0.0),
                    bid=ticker.get('bid'),
                    ask=ticker.get('ask'),
                    high=ticker.get('high'),
                    low=ticker.get('low'),
                    open=ticker.get('open'),
                    close=ticker['last'],
                )
                
                yield tick
                
                # Wait for next update
                await asyncio.sleep(self.config.update_interval)
            
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                await asyncio.sleep(5.0)  # Wait longer on error


class MarketDataAdapter:
    """Main market data adapter that coordinates data providers."""
    
    def __init__(self, config: MarketDataConfig):
        self.config = config
        self.provider = self._create_provider()
        self.data_callbacks: List[Callable[[MarketTick], None]] = []
        self.is_streaming = False
        self._streaming_tasks: List[asyncio.Task] = []
    
    def _create_provider(self) -> MarketDataProvider:
        """Create appropriate data provider."""
        
        if self.config.source == DataSource.LOCAL_FILE:
            return LocalFileProvider(self.config)
        elif self.config.source == DataSource.CCXT_REST:
            return CCXTProvider(self.config)
        else:
            raise BrokerError(f"Unsupported data source: {self.config.source}", "MarketDataAdapter")
    
    async def get_historical_data(self, symbol: str, start_time: Optional[datetime] = None, 
                                 end_time: Optional[datetime] = None) -> List[MarketTick]:
        """Get historical market data."""
        return await self.provider.get_data(symbol, start_time, end_time)
    
    async def start_streaming(self, symbols: Optional[List[str]] = None):
        """Start streaming market data."""
        
        if self.is_streaming:
            return
        
        symbols = symbols or self.config.symbols
        self.is_streaming = True
        
        # Start streaming tasks for each symbol
        for symbol in symbols:
            task = asyncio.create_task(self._stream_symbol(symbol))
            self._streaming_tasks.append(task)
    
    async def stop_streaming(self):
        """Stop streaming market data."""
        
        self.is_streaming = False
        
        # Cancel all streaming tasks
        for task in self._streaming_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._streaming_tasks, return_exceptions=True)
        self._streaming_tasks.clear()
    
    def add_data_callback(self, callback: Callable[[MarketTick], None]):
        """Add callback for market data updates."""
        self.data_callbacks.append(callback)
    
    def remove_data_callback(self, callback: Callable[[MarketTick], None]):
        """Remove data callback."""
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
    
    async def _stream_symbol(self, symbol: str):
        """Stream data for a single symbol."""
        
        try:
            async for tick in self.provider.stream_data(symbol):
                if not self.is_streaming:
                    break
                
                # Notify callbacks
                for callback in self.data_callbacks:
                    try:
                        callback(tick)
                    except Exception as e:
                        print(f"Error in data callback: {e}")
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error streaming data for {symbol}: {e}")
    
    async def replay_historical_data(self, symbols: Optional[List[str]] = None, 
                                   start_time: Optional[datetime] = None,
                                   end_time: Optional[datetime] = None):
        """Replay historical data at configured speed."""
        
        symbols = symbols or self.config.symbols
        
        for symbol in symbols:
            data = await self.get_historical_data(symbol, start_time, end_time)
            
            for tick in data:
                # Notify callbacks
                for callback in self.data_callbacks:
                    try:
                        callback(tick)
                    except Exception as e:
                        print(f"Error in data callback: {e}")
                
                # Simulate real-time delay
                if self.config.replay_speed > 0:
                    await asyncio.sleep(1.0 / self.config.replay_speed)
