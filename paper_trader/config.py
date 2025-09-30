"""
Paper Trading Configuration

Configuration management for paper trading system including
default settings, validation, and environment-specific overrides.
"""

from __future__ import annotations

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .execution import SlippageConfig, FeeConfig, LatencyConfig, SlippageType, FeeType
from .market_data import MarketDataConfig, DataMode, DataSource


@dataclass
class PaperTradingConfig:
    """Complete configuration for paper trading system."""
    
    # Basic settings
    run_id: str = "default"
    mode: str = "replay"  # replay, live, hybrid
    initial_cash: float = 100000.0
    base_currency: str = "USDT"
    
    # Execution simulation
    slippage_config: SlippageConfig = field(default_factory=SlippageConfig)
    fee_config: FeeConfig = field(default_factory=FeeConfig)
    latency_config: LatencyConfig = field(default_factory=LatencyConfig)
    
    # Market data
    market_data_config: MarketDataConfig = field(default_factory=MarketDataConfig)
    
    # Portfolio settings
    max_positions: int = 10
    position_size_limit_pct: float = 0.1  # 10% of portfolio per position
    
    # Risk management
    max_drawdown_pct: float = 20.0
    stop_loss_pct: float = 0.02  # 2% stop loss
    take_profit_pct: float = 0.04  # 4% take profit
    
    # Reporting
    generate_reports: bool = True
    report_formats: List[str] = field(default_factory=lambda: ["json", "html"])
    save_trades: bool = True
    save_account_history: bool = True
    
    # Safety settings
    enforce_paper_mode: bool = True
    block_real_orders: bool = True
    
    @classmethod
    def from_file(cls, config_path: str) -> "PaperTradingConfig":
        """Load configuration from YAML file."""
        
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return cls.from_dict(config_data)
    
    @classmethod
    def from_dict(cls, config_data: Dict[str, Any]) -> "PaperTradingConfig":
        """Create configuration from dictionary."""
        
        # Extract basic settings
        config = cls(
            run_id=config_data.get("run_id", "default"),
            mode=config_data.get("mode", "replay"),
            initial_cash=config_data.get("initial_cash", 100000.0),
            base_currency=config_data.get("base_currency", "USDT"),
            max_positions=config_data.get("max_positions", 10),
            position_size_limit_pct=config_data.get("position_size_limit_pct", 0.1),
            max_drawdown_pct=config_data.get("max_drawdown_pct", 20.0),
            stop_loss_pct=config_data.get("stop_loss_pct", 0.02),
            take_profit_pct=config_data.get("take_profit_pct", 0.04),
            generate_reports=config_data.get("generate_reports", True),
            report_formats=config_data.get("report_formats", ["json", "html"]),
            save_trades=config_data.get("save_trades", True),
            save_account_history=config_data.get("save_account_history", True),
            enforce_paper_mode=config_data.get("enforce_paper_mode", True),
            block_real_orders=config_data.get("block_real_orders", True),
        )
        
        # Extract execution simulation settings
        execution_config = config_data.get("execution", {})
        if execution_config:
            config.slippage_config = cls._create_slippage_config(execution_config.get("slippage", {}))
            config.fee_config = cls._create_fee_config(execution_config.get("fees", {}))
            config.latency_config = cls._create_latency_config(execution_config.get("latency", {}))
        
        # Extract market data settings
        market_data_config = config_data.get("market_data", {})
        if market_data_config:
            config.market_data_config = cls._create_market_data_config(market_data_config)
        
        return config
    
    @staticmethod
    def _create_slippage_config(slippage_data: Dict[str, Any]) -> SlippageConfig:
        """Create slippage configuration from data."""
        
        slippage_type = SlippageType(slippage_data.get("type", "square_root"))
        
        return SlippageConfig(
            slippage_type=slippage_type,
            base_slippage_bps=slippage_data.get("base_slippage_bps", 5.0),
            max_slippage_bps=slippage_data.get("max_slippage_bps", 50.0),
            volatility_multiplier=slippage_data.get("volatility_multiplier", 1.0),
            order_size_threshold=slippage_data.get("order_size_threshold", 10000.0),
            orderbook_depth_levels=slippage_data.get("orderbook_depth_levels", 5),
            depth_impact_factor=slippage_data.get("depth_impact_factor", 0.1),
        )
    
    @staticmethod
    def _create_fee_config(fee_data: Dict[str, Any]) -> FeeConfig:
        """Create fee configuration from data."""
        
        fee_type = FeeType(fee_data.get("type", "percentage"))
        
        return FeeConfig(
            fee_type=fee_type,
            maker_fee_bps=fee_data.get("maker_fee_bps", 5.0),
            taker_fee_bps=fee_data.get("taker_fee_bps", 10.0),
            fixed_fee_usd=fee_data.get("fixed_fee_usd", 0.0),
            min_fee_usd=fee_data.get("min_fee_usd", 0.01),
            max_fee_usd=fee_data.get("max_fee_usd", 100.0),
            volume_tiers=fee_data.get("volume_tiers", [
                (0, 10.0),
                (1000000, 8.0),
                (10000000, 5.0),
            ]),
        )
    
    @staticmethod
    def _create_latency_config(latency_data: Dict[str, Any]) -> LatencyConfig:
        """Create latency configuration from data."""
        
        return LatencyConfig(
            min_latency_ms=latency_data.get("min_latency_ms", 50.0),
            max_latency_ms=latency_data.get("max_latency_ms", 500.0),
            mean_latency_ms=latency_data.get("mean_latency_ms", 200.0),
            std_latency_ms=latency_data.get("std_latency_ms", 100.0),
            network_jitter_ms=latency_data.get("network_jitter_ms", 20.0),
        )
    
    @staticmethod
    def _create_market_data_config(market_data: Dict[str, Any]) -> MarketDataConfig:
        """Create market data configuration from data."""
        
        mode = DataMode(market_data.get("mode", "replay"))
        source = DataSource(market_data.get("source", "local_file"))
        
        return MarketDataConfig(
            mode=mode,
            source=source,
            replay_speed=market_data.get("replay_speed", 1.0),
            start_time=market_data.get("start_time"),
            end_time=market_data.get("end_time"),
            exchange=market_data.get("exchange", "binance"),
            symbols=market_data.get("symbols", ["BTC/USDT", "ETH/USDT", "BNB/USDT"]),
            update_interval=market_data.get("update_interval", 1.0),
            data_directory=market_data.get("data_directory", "./data_cache"),
            file_format=market_data.get("file_format", "jsonl"),
            ws_url=market_data.get("ws_url"),
            ws_channels=market_data.get("ws_channels"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "initial_cash": self.initial_cash,
            "base_currency": self.base_currency,
            "max_positions": self.max_positions,
            "position_size_limit_pct": self.position_size_limit_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "generate_reports": self.generate_reports,
            "report_formats": self.report_formats,
            "save_trades": self.save_trades,
            "save_account_history": self.save_account_history,
            "enforce_paper_mode": self.enforce_paper_mode,
            "block_real_orders": self.block_real_orders,
            "execution": {
                "slippage": {
                    "type": self.slippage_config.slippage_type.value,
                    "base_slippage_bps": self.slippage_config.base_slippage_bps,
                    "max_slippage_bps": self.slippage_config.max_slippage_bps,
                    "volatility_multiplier": self.slippage_config.volatility_multiplier,
                    "order_size_threshold": self.slippage_config.order_size_threshold,
                    "orderbook_depth_levels": self.slippage_config.orderbook_depth_levels,
                    "depth_impact_factor": self.slippage_config.depth_impact_factor,
                },
                "fees": {
                    "type": self.fee_config.fee_type.value,
                    "maker_fee_bps": self.fee_config.maker_fee_bps,
                    "taker_fee_bps": self.fee_config.taker_fee_bps,
                    "fixed_fee_usd": self.fee_config.fixed_fee_usd,
                    "min_fee_usd": self.fee_config.min_fee_usd,
                    "max_fee_usd": self.fee_config.max_fee_usd,
                    "volume_tiers": [list(tier) for tier in self.fee_config.volume_tiers],
                },
                "latency": {
                    "min_latency_ms": self.latency_config.min_latency_ms,
                    "max_latency_ms": self.latency_config.max_latency_ms,
                    "mean_latency_ms": self.latency_config.mean_latency_ms,
                    "std_latency_ms": self.latency_config.std_latency_ms,
                    "network_jitter_ms": self.latency_config.network_jitter_ms,
                },
            },
            "market_data": {
                "mode": self.market_data_config.mode.value,
                "source": self.market_data_config.source.value,
                "replay_speed": self.market_data_config.replay_speed,
                "start_time": self.market_data_config.start_time.isoformat() if self.market_data_config.start_time else None,
                "end_time": self.market_data_config.end_time.isoformat() if self.market_data_config.end_time else None,
                "exchange": self.market_data_config.exchange,
                "symbols": self.market_data_config.symbols,
                "update_interval": self.market_data_config.update_interval,
                "data_directory": self.market_data_config.data_directory,
                "file_format": self.market_data_config.file_format,
                "ws_url": self.market_data_config.ws_url,
                "ws_channels": self.market_data_config.ws_channels,
            },
        }
    
    def save_to_file(self, config_path: str):
        """Save configuration to YAML file."""
        
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        
        errors = []
        
        # Validate basic settings
        if self.initial_cash <= 0:
            errors.append("Initial cash must be positive")
        
        if self.max_positions <= 0:
            errors.append("Max positions must be positive")
        
        if not 0 < self.position_size_limit_pct <= 1:
            errors.append("Position size limit must be between 0 and 1")
        
        if not 0 < self.max_drawdown_pct <= 100:
            errors.append("Max drawdown must be between 0 and 100")
        
        # Validate execution settings
        if self.slippage_config.base_slippage_bps < 0:
            errors.append("Base slippage must be non-negative")
        
        if self.slippage_config.max_slippage_bps < self.slippage_config.base_slippage_bps:
            errors.append("Max slippage must be >= base slippage")
        
        if self.fee_config.maker_fee_bps < 0:
            errors.append("Maker fee must be non-negative")
        
        if self.fee_config.taker_fee_bps < 0:
            errors.append("Taker fee must be non-negative")
        
        # Validate market data settings
        if self.market_data_config.replay_speed <= 0:
            errors.append("Replay speed must be positive")
        
        if not self.market_data_config.symbols:
            errors.append("At least one symbol must be specified")
        
        return errors
    
    @classmethod
    def create_default_config(cls, run_id: str = "default") -> "PaperTradingConfig":
        """Create default configuration."""
        
        return cls(
            run_id=run_id,
            mode="replay",
            initial_cash=100000.0,
            base_currency="USDT",
            slippage_config=SlippageConfig(),
            fee_config=FeeConfig(),
            latency_config=LatencyConfig(),
            market_data_config=MarketDataConfig(),
            max_positions=10,
            position_size_limit_pct=0.1,
            max_drawdown_pct=20.0,
            stop_loss_pct=0.02,
            take_profit_pct=0.04,
            generate_reports=True,
            report_formats=["json", "html"],
            save_trades=True,
            save_account_history=True,
            enforce_paper_mode=True,
            block_real_orders=True,
        )


def load_config_from_env() -> PaperTradingConfig:
    """Load configuration from environment variables."""
    
    config = PaperTradingConfig.create_default_config()
    
    # Override with environment variables
    if os.getenv("PAPER_RUN_ID"):
        config.run_id = os.getenv("PAPER_RUN_ID")
    
    if os.getenv("PAPER_MODE"):
        config.mode = os.getenv("PAPER_MODE")
    
    if os.getenv("PAPER_INITIAL_CASH"):
        config.initial_cash = float(os.getenv("PAPER_INITIAL_CASH"))
    
    if os.getenv("PAPER_BASE_CURRENCY"):
        config.base_currency = os.getenv("PAPER_BASE_CURRENCY")
    
    return config
