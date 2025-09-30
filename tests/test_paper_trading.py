"""
Unit Tests for Paper Trading System

Comprehensive test suite covering all paper trading components.
"""

import asyncio
import pytest
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Import paper trading components
from paper_trader.broker import PaperBroker, AccountBalance, Position, AccountInfo
from paper_trader.execution import (
    ExecutionSimulator, SlippageConfig, FeeConfig, LatencyConfig,
    SlippageType, FeeType, FixedSlippageModel, SquareRootSlippageModel
)
from paper_trader.portfolio import PaperPortfolio, Trade, AccountSnapshot
from paper_trader.market_data import MarketDataAdapter, MarketTick, MarketDataConfig, DataMode, DataSource
from paper_trader.persistence import PaperTradingPersistence
from paper_trader.metrics import PerformanceMetrics, ReportGenerator
from paper_trader.config import PaperTradingConfig
from paper_trader.safety import SafetyChecker, enforce_paper_mode

# Import order models
from src.order_manager.models import OrderRequest, OrderType, TimeInForce


class TestPaperBroker:
    """Test PaperBroker functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.broker = PaperBroker(
            initial_cash=10000.0,
            base_currency="USDT",
            supported_symbols=["BTC/USDT", "ETH/USDT"]
        )
    
    def test_initialization(self):
        """Test broker initialization."""
        assert self.broker.name == "PaperBroker"
        assert self.broker.is_connected
        assert self.broker.is_paper_trading
        assert self.broker.portfolio.cash == 10000.0
    
    def test_connect_disconnect(self):
        """Test connection methods."""
        assert self.broker.connect()
        assert self.broker.is_connected
        
        assert self.broker.disconnect()
        assert not self.broker.is_connected
    
    def test_place_buy_order(self):
        """Test placing buy orders."""
        order_request = OrderRequest(
            symbol="BTC/USDT",
            side="buy",
            order_type=OrderType.MARKET,
            quantity=0.1
        )
        
        result = self.broker.place_order(order_request)
        
        assert result.success
        assert result.order_id in self.broker.orders
        assert result.state is not None
    
    def test_place_sell_order_insufficient_position(self):
        """Test placing sell order without position."""
        order_request = OrderRequest(
            symbol="BTC/USDT",
            side="sell",
            order_type=OrderType.MARKET,
            quantity=0.1
        )
        
        result = self.broker.place_order(order_request)
        
        # Should fail due to insufficient position
        assert not result.success
    
    def test_get_account_info(self):
        """Test getting account information."""
        account_info = self.broker.get_account_info()
        
        assert isinstance(account_info, AccountInfo)
        assert account_info.total_equity == 10000.0
        assert len(account_info.balances) >= 1
    
    def test_get_balance(self):
        """Test getting balance for currency."""
        balance = self.broker.get_balance("USDT")
        
        assert isinstance(balance, AccountBalance)
        assert balance.currency == "USDT"
        assert balance.free == 10000.0
    
    def test_validate_order_request(self):
        """Test order request validation."""
        # Valid buy order
        valid_order = OrderRequest(
            symbol="BTC/USDT",
            side="buy",
            order_type=OrderType.MARKET,
            quantity=0.1
        )
        assert self.broker.validate_order_request(valid_order)
        
        # Invalid order (negative quantity)
        invalid_order = OrderRequest(
            symbol="BTC/USDT",
            side="buy",
            order_type=OrderType.MARKET,
            quantity=-0.1
        )
        assert not self.broker.validate_order_request(invalid_order)
        
        # Unsupported symbol
        unsupported_order = OrderRequest(
            symbol="UNSUPPORTED/USDT",
            side="buy",
            order_type=OrderType.MARKET,
            quantity=0.1
        )
        assert not self.broker.validate_order_request(unsupported_order)
    
    def test_update_market_data(self):
        """Test updating market data."""
        ticker = {
            "symbol": "BTC/USDT",
            "last": 50000.0,
            "bid": 49990.0,
            "ask": 50010.0,
            "volume": 1000.0
        }
        
        self.broker.update_market_data("BTC/USDT", ticker)
        
        assert "BTC/USDT" in self.broker.ticker_cache
        assert self.broker.ticker_cache["BTC/USDT"]["last"] == 50000.0


class TestExecutionSimulator:
    """Test ExecutionSimulator functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.slippage_config = SlippageConfig(
            slippage_type=SlippageType.FIXED,
            base_slippage_bps=10.0
        )
        self.fee_config = FeeConfig(
            fee_type=FeeType.PERCENTAGE,
            taker_fee_bps=10.0
        )
        self.latency_config = LatencyConfig(
            min_latency_ms=50.0,
            max_latency_ms=100.0,
            mean_latency_ms=75.0,
            std_latency_ms=10.0
        )
        
        self.simulator = ExecutionSimulator(
            self.slippage_config,
            self.fee_config,
            self.latency_config,
            random_seed=42
        )
    
    def test_initialization(self):
        """Test simulator initialization."""
        assert self.simulator.total_orders == 0
        assert self.simulator.total_fees == 0.0
        assert self.simulator.total_slippage == 0.0
    
    @pytest.mark.asyncio
    async def test_simulate_execution_buy(self):
        """Test buy order execution simulation."""
        order_request = OrderRequest(
            symbol="BTC/USDT",
            side="buy",
            order_type=OrderType.MARKET,
            quantity=0.1
        )
        
        execution_price, fee, slippage = await self.simulator.simulate_execution(
            order_request, 50000.0
        )
        
        assert execution_price > 50000.0  # Buy orders have positive slippage
        assert fee > 0
        assert slippage > 0
        assert self.simulator.total_orders == 1
    
    @pytest.mark.asyncio
    async def test_simulate_execution_sell(self):
        """Test sell order execution simulation."""
        order_request = OrderRequest(
            symbol="BTC/USDT",
            side="sell",
            order_type=OrderType.MARKET,
            quantity=0.1
        )
        
        execution_price, fee, slippage = await self.simulator.simulate_execution(
            order_request, 50000.0
        )
        
        assert execution_price < 50000.0  # Sell orders have negative slippage
        assert fee > 0
        assert slippage > 0
        assert self.simulator.total_orders == 1
    
    def test_get_statistics(self):
        """Test getting execution statistics."""
        stats = self.simulator.get_statistics()
        
        assert "total_orders" in stats
        assert "total_fees_usd" in stats
        assert "total_slippage_usd" in stats
        assert "avg_fee_per_order" in stats
        assert "avg_slippage_per_order" in stats


class TestSlippageModels:
    """Test slippage model implementations."""
    
    def test_fixed_slippage_model(self):
        """Test fixed slippage model."""
        model = FixedSlippageModel(10.0)  # 10 bps
        
        slippage = model.calculate_slippage(1000.0, 50000.0, "buy")
        
        assert slippage == 0.001  # 10 bps = 0.1%
    
    def test_square_root_slippage_model(self):
        """Test square root slippage model."""
        config = SlippageConfig(
            slippage_type=SlippageType.SQUARE_ROOT,
            base_slippage_bps=5.0,
            order_size_threshold=10000.0
        )
        model = SquareRootSlippageModel(config)
        
        # Small order
        small_slippage = model.calculate_slippage(1000.0, 50000.0, "buy")
        
        # Large order
        large_slippage = model.calculate_slippage(50000.0, 50000.0, "buy")
        
        assert large_slippage > small_slippage  # Larger orders have more slippage


class TestPaperPortfolio:
    """Test PaperPortfolio functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.portfolio = PaperPortfolio(initial_cash=10000.0)
    
    def test_initialization(self):
        """Test portfolio initialization."""
        assert self.portfolio.cash == 10000.0
        assert self.portfolio.initial_cash == 10000.0
        assert self.portfolio.realized_pnl == 0.0
        assert self.portfolio.unrealized_pnl == 0.0
        assert len(self.portfolio.positions) == 0
        assert len(self.portfolio.trades) == 0
    
    def test_execute_buy_trade(self):
        """Test executing buy trades."""
        success = self.portfolio.execute_trade(
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,
            price=50000.0,
            fee=5.0,
            order_id="test_order_1"
        )
        
        assert success
        assert len(self.portfolio.trades) == 1
        assert len(self.portfolio.positions) == 1
        assert self.portfolio.cash < 10000.0  # Cash reduced
        
        # Check position
        position = self.portfolio.positions["BTC/USDT"]
        assert position.size == 0.1
        assert position.entry_price == 50000.0
    
    def test_execute_sell_trade(self):
        """Test executing sell trades."""
        # First buy
        self.portfolio.execute_trade(
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,
            price=50000.0,
            fee=5.0,
            order_id="test_order_1"
        )
        
        # Then sell
        success = self.portfolio.execute_trade(
            symbol="BTC/USDT",
            side="sell",
            quantity=0.05,  # Partial sell
            price=51000.0,
            fee=2.5,
            order_id="test_order_2"
        )
        
        assert success
        assert len(self.portfolio.trades) == 2
        
        # Check remaining position
        position = self.portfolio.positions["BTC/USDT"]
        assert position.size == 0.05  # Half sold
    
    def test_insufficient_funds(self):
        """Test trade with insufficient funds."""
        success = self.portfolio.execute_trade(
            symbol="BTC/USDT",
            side="buy",
            quantity=1.0,  # Very large order
            price=50000.0,
            fee=500.0,
            order_id="test_order_1"
        )
        
        assert not success
        assert len(self.portfolio.trades) == 0
    
    def test_get_performance_metrics(self):
        """Test getting performance metrics."""
        # Execute some trades
        self.portfolio.execute_trade(
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,
            price=50000.0,
            fee=5.0,
            order_id="test_order_1"
        )
        
        self.portfolio.execute_trade(
            symbol="BTC/USDT",
            side="sell",
            quantity=0.1,
            price=51000.0,
            fee=5.1,
            order_id="test_order_2"
        )
        
        metrics = self.portfolio.get_performance_metrics()
        
        assert metrics["total_trades"] == 2
        assert metrics["total_fees"] == 10.1
        assert "win_rate" in metrics
        assert "total_pnl" in metrics


class TestMarketDataAdapter:
    """Test MarketDataAdapter functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = MarketDataConfig(
            mode=DataMode.REPLAY,
            source=DataSource.LOCAL_FILE,
            symbols=["BTC/USDT"],
            data_directory="./test_data"
        )
        self.adapter = MarketDataAdapter(self.config)
    
    def test_initialization(self):
        """Test adapter initialization."""
        assert self.adapter.config.mode == DataMode.REPLAY
        assert self.adapter.config.source == DataSource.LOCAL_FILE
        assert not self.adapter.is_streaming
    
    def test_add_remove_callbacks(self):
        """Test callback management."""
        callback = Mock()
        
        self.adapter.add_data_callback(callback)
        assert callback in self.adapter.data_callbacks
        
        self.adapter.remove_data_callback(callback)
        assert callback not in self.adapter.data_callbacks


class TestPersistence:
    """Test PaperTradingPersistence functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.persistence = PaperTradingPersistence(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_create_run(self):
        """Test creating a new run."""
        run_id = "test_run_1"
        config = {"mode": "paper", "initial_cash": 10000.0}
        
        success = self.persistence.create_run(run_id, config, 10000.0)
        
        assert success
        
        # Verify run exists
        summary = self.persistence.get_run_summary(run_id)
        assert summary is not None
        assert summary["id"] == run_id
    
    def test_save_trade(self):
        """Test saving trades."""
        run_id = "test_run_1"
        self.persistence.create_run(run_id, {}, 10000.0)
        
        trade = Trade(
            id="trade_1",
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,
            price=50000.0,
            fee=5.0,
            timestamp=datetime.now(timezone.utc),
            order_id="order_1"
        )
        
        success = self.persistence.save_trade(trade, run_id)
        assert success
        
        # Verify trade was saved
        trades = self.persistence.get_trades(run_id)
        assert len(trades) == 1
        assert trades[0].id == "trade_1"
    
    def test_export_to_csv(self):
        """Test CSV export functionality."""
        run_id = "test_run_1"
        self.persistence.create_run(run_id, {}, 10000.0)
        
        # Add some test data
        trade = Trade(
            id="trade_1",
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,
            price=50000.0,
            fee=5.0,
            timestamp=datetime.now(timezone.utc),
            order_id="order_1"
        )
        self.persistence.save_trade(trade, run_id)
        
        # Export to CSV
        exported_files = self.persistence.export_to_csv(run_id)
        
        assert "trades" in exported_files
        assert Path(exported_files["trades"]).exists()


class TestPerformanceMetrics:
    """Test PerformanceMetrics functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.trades = [
            Trade(
                id="trade_1",
                symbol="BTC/USDT",
                side="buy",
                quantity=0.1,
                price=50000.0,
                fee=5.0,
                timestamp=datetime.now(timezone.utc),
                order_id="order_1"
            ),
            Trade(
                id="trade_2",
                symbol="BTC/USDT",
                side="sell",
                quantity=0.1,
                price=51000.0,
                fee=5.1,
                timestamp=datetime.now(timezone.utc),
                order_id="order_2"
            )
        ]
        
        self.account_history = [
            AccountSnapshot(
                timestamp=datetime.now(timezone.utc),
                cash=10000.0,
                total_equity=10000.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                positions=[]
            ),
            AccountSnapshot(
                timestamp=datetime.now(timezone.utc),
                cash=9890.0,
                total_equity=10090.0,
                unrealized_pnl=0.0,
                realized_pnl=100.0,
                positions=[]
            )
        ]
        
        self.metrics = PerformanceMetrics(self.trades, self.account_history, 10000.0)
    
    def test_initialization(self):
        """Test metrics initialization."""
        assert self.metrics.total_trades == 2
        assert self.metrics.total_fees == 10.1
        assert self.metrics.win_rate >= 0
        assert self.metrics.max_drawdown >= 0
    
    def test_get_summary(self):
        """Test getting performance summary."""
        summary = self.metrics.get_summary()
        
        assert "total_trades" in summary
        assert "win_rate" in summary
        assert "total_return" in summary
        assert "max_drawdown" in summary
        assert "sharpe_ratio" in summary


class TestSafetyChecker:
    """Test SafetyChecker functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.checker = SafetyChecker()
    
    def test_check_environment_variables(self):
        """Test environment variable checking."""
        # This test would need to be run in a controlled environment
        # where we can set/unset environment variables
        errors = self.checker._check_environment_variables()
        assert isinstance(errors, list)
    
    def test_validate_paper_configuration(self):
        """Test paper configuration validation."""
        # Valid paper config
        valid_config = {
            "mode": "paper",
            "exchange": "paper",
            "execution": {"mode": "paper"}
        }
        
        errors = self.checker.validate_paper_configuration(valid_config)
        assert len(errors) == 0
        
        # Invalid config with API keys
        invalid_config = {
            "mode": "paper",
            "api_key": "test_key",
            "api_secret": "test_secret"
        }
        
        errors = self.checker.validate_paper_configuration(invalid_config)
        assert len(errors) > 0
    
    def test_create_safety_report(self):
        """Test creating safety report."""
        report = self.checker.create_safety_report()
        
        assert "is_safe" in report
        assert "errors" in report
        assert "checked_items" in report
        assert "recommendations" in report


class TestIntegration:
    """Integration tests for the complete paper trading system."""
    
    @pytest.mark.asyncio
    async def test_complete_paper_trading_flow(self):
        """Test complete paper trading flow."""
        
        # Initialize components
        broker = PaperBroker(initial_cash=10000.0)
        persistence = PaperTradingPersistence(tempfile.mkdtemp())
        
        # Create run
        run_id = "integration_test"
        persistence.create_run(run_id, {}, 10000.0)
        
        # Place orders
        buy_order = OrderRequest(
            symbol="BTC/USDT",
            side="buy",
            order_type=OrderType.MARKET,
            quantity=0.1
        )
        
        result = broker.place_order(buy_order)
        assert result.success
        
        # Wait for execution
        await asyncio.sleep(0.1)
        
        # Check portfolio state
        account_info = broker.get_account_info()
        assert account_info.total_equity > 0
        
        # Save data
        trades = broker.get_trade_history()
        for trade in trades:
            persistence.save_trade(trade, run_id)
        
        # Verify data was saved
        saved_trades = persistence.get_trades(run_id)
        assert len(saved_trades) > 0
        
        # Generate metrics
        account_history = persistence.get_account_history(run_id)
        metrics = PerformanceMetrics(trades, account_history, 10000.0)
        
        summary = metrics.get_summary()
        assert "total_trades" in summary


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
