"""
Test Enhanced Backtesting Features

Comprehensive tests for Phase 3 & 4 implementation including
fee models, slippage calculation, and order book simulation.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from fees import (
    FeeCalculator, FeeCalculationMode, OrderFeeContext,
    ExchangeFeeRegistry, get_exchange_fees
)
from slippage import (
    DepthBasedSlippage, VolumeBasedSlippage, MarketImpactCalculator,
    SlippageContext, SlippageType, MarketCondition
)
from orderbook import (
    OrderBookSnapshot, OrderBookSimulator, SimulatedOrder,
    SQLiteOrderBookStorage, OrderBookReplayEngine
)
from backtest.simulation.enhanced_simulator import EnhancedTradingSimulator


class TestFeeModels:
    """Test fee calculation models."""
    
    def test_fee_calculation_modes(self):
        """Test different fee calculation modes."""
        # Test zero fees
        calc_zero = FeeCalculator(FeeCalculationMode.ZERO)
        context = OrderFeeContext(
            order_value_usd=10000.0,
            order_quantity=0.2,
            order_price=50000.0,
            side="buy",
            order_type="market",
            exchange="binance"
        )
        
        fees = calc_zero.calculate_fees(context)
        assert fees.total_fees_usd == 0.0
        assert fees.calculation_mode == FeeCalculationMode.ZERO
        
        # Test simplified fees
        calc_simple = FeeCalculator(FeeCalculationMode.SIMPLIFIED)
        fees = calc_simple.calculate_fees(context)
        assert fees.total_fees_usd > 0.0
        assert fees.calculation_mode == FeeCalculationMode.SIMPLIFIED
        
        # Test realistic fees
        calc_realistic = FeeCalculator(FeeCalculationMode.REALISTIC)
        fees = calc_realistic.calculate_fees(context)
        assert fees.total_fees_usd > 0.0
        assert fees.calculation_mode == FeeCalculationMode.REALISTIC
    
    def test_exchange_fee_tiers(self):
        """Test exchange fee tier calculations."""
        exchange_fees = get_exchange_fees("binance")
        assert exchange_fees is not None
        assert exchange_fees.exchange_name == "binance"
        assert len(exchange_fees.volume_tiers) > 0
        
        # Test tier selection
        tier_low = exchange_fees.get_tier_for_volume(10000.0)
        tier_high = exchange_fees.get_tier_for_volume(1000000.0)
        
        assert tier_high.maker_bps <= tier_low.maker_bps
        assert tier_high.taker_bps <= tier_low.taker_bps
    
    def test_maker_taker_differentiation(self):
        """Test maker vs taker fee differentiation."""
        calc = FeeCalculator(FeeCalculationMode.REALISTIC)
        
        # Maker order (limit order)
        maker_context = OrderFeeContext(
            order_value_usd=10000.0,
            order_quantity=0.2,
            order_price=50000.0,
            side="buy",
            order_type="limit",
            is_maker=True,
            exchange="binance"
        )
        
        maker_fees = calc.calculate_fees(maker_context)
        
        # Taker order (market order)
        taker_context = OrderFeeContext(
            order_value_usd=10000.0,
            order_quantity=0.2,
            order_price=50000.0,
            side="buy",
            order_type="market",
            is_maker=False,
            exchange="binance"
        )
        
        taker_fees = calc.calculate_fees(taker_context)
        
        # Maker fees should be lower than taker fees
        assert maker_fees.trading_fee_usd < taker_fees.trading_fee_usd
        assert maker_fees.fee_type_used.value == "maker"
        assert taker_fees.fee_type_used.value == "taker"


class TestSlippageModels:
    """Test slippage calculation models."""
    
    def test_depth_based_slippage(self):
        """Test depth-based slippage calculation."""
        # Create sample order book
        bids = [(50000.0, 1.0), (49999.0, 2.0), (49998.0, 3.0)]
        asks = [(50001.0, 1.0), (50002.0, 2.0), (50003.0, 3.0)]
        
        snapshot = OrderBookSnapshot(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            bids=bids,
            asks=asks
        )
        
        # Test slippage calculation
        slippage_calc = DepthBasedSlippage()
        context = SlippageContext(
            symbol="BTC/USDT",
            side="buy",
            quantity=2.0,
            order_type="market",
            order_book=snapshot
        )
        
        result = slippage_calc.calculate_slippage(context)
        
        assert result.slippage_bps > 0.0
        assert result.effective_price > 50001.0  # Should be above best ask
        assert result.fill_quantity == 2.0
        assert result.depth_levels_used > 0
    
    def test_volume_based_slippage(self):
        """Test volume-based slippage calculation."""
        slippage_calc = VolumeBasedSlippage()
        context = SlippageContext(
            symbol="BTC/USDT",
            side="buy",
            quantity=1.0,
            order_type="market",
            current_price=50000.0,
            volume_24h=1000000.0,  # $1M daily volume
            volatility=0.02  # 2% volatility
        )
        
        result = slippage_calc.calculate_slippage(context)
        
        assert result.slippage_bps >= 0.0
        assert result.effective_price > 0.0
        assert result.market_condition in MarketCondition
    
    def test_market_impact_calculation(self):
        """Test market impact calculation."""
        impact_calc = MarketImpactCalculator()
        context = SlippageContext(
            symbol="BTC/USDT",
            side="buy",
            quantity=10.0,  # Large order
            order_type="market",
            current_price=50000.0,
            volume_24h=10000000.0,  # $10M daily volume
            volatility=0.03  # 3% volatility
        )
        
        result = impact_calc.calculate_market_impact(context)
        
        assert result.slippage_bps > 0.0
        assert result.market_impact_bps > 0.0
        assert result.market_condition in MarketCondition


class TestOrderBookSimulation:
    """Test order book simulation functionality."""
    
    def test_order_book_snapshot_validation(self):
        """Test order book snapshot validation."""
        # Valid order book
        valid_bids = [(50000.0, 1.0), (49999.0, 2.0)]
        valid_asks = [(50001.0, 1.0), (50002.0, 2.0)]
        
        valid_snapshot = OrderBookSnapshot(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            bids=valid_bids,
            asks=valid_asks
        )
        
        assert valid_snapshot.is_valid()
        assert valid_snapshot.best_bid == 50000.0
        assert valid_snapshot.best_ask == 50001.0
        assert valid_snapshot.spread == 1.0
        assert valid_snapshot.spread_bps == 2.0  # 1/50000 * 10000
        
        # Invalid order book (crossed)
        invalid_bids = [(50001.0, 1.0)]  # Bid above ask
        invalid_asks = [(50000.0, 1.0)]
        
        invalid_snapshot = OrderBookSnapshot(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            bids=invalid_bids,
            asks=invalid_asks
        )
        
        assert not invalid_snapshot.is_valid()
    
    def test_order_simulation(self):
        """Test order simulation against order book."""
        # Create simulator and order book
        simulator = OrderBookSimulator()
        
        bids = [(50000.0, 1.0), (49999.0, 2.0), (49998.0, 3.0)]
        asks = [(50001.0, 1.0), (50002.0, 2.0), (50003.0, 3.0)]
        
        snapshot = OrderBookSnapshot(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            bids=bids,
            asks=asks
        )
        
        simulator.set_order_book(snapshot)
        
        # Test market buy order
        order = SimulatedOrder(
            order_id="test_1",
            symbol="BTC/USDT",
            side="buy",
            order_type="market",
            quantity=2.0
        )
        
        fill = simulator.simulate_order(order)
        
        assert fill.filled_quantity > 0.0
        assert fill.average_price >= 50001.0  # Should be at or above best ask
        assert fill.slippage_bps >= 0.0
        assert fill.is_completely_filled or fill.is_partial_fill
        
        # Test limit buy order
        limit_order = SimulatedOrder(
            order_id="test_2",
            symbol="BTC/USDT",
            side="buy",
            order_type="limit",
            quantity=1.0,
            price=49999.0  # Below best ask
        )
        
        limit_fill = simulator.simulate_order(limit_order)
        
        # Limit order below market should not execute immediately
        assert limit_fill.filled_quantity == 0.0
        assert not limit_fill.is_completely_filled
    
    def test_order_book_storage(self):
        """Test order book data storage and retrieval."""
        # Create temporary storage
        storage = SQLiteOrderBookStorage(":memory:")  # In-memory database
        
        # Create test snapshot
        snapshot = OrderBookSnapshot(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            bids=[(50000.0, 1.0), (49999.0, 2.0)],
            asks=[(50001.0, 1.0), (50002.0, 2.0)],
            last_trade_price=50000.5,
            sequence_number=1
        )
        
        # Store snapshot
        assert storage.store_snapshot(snapshot)
        
        # Retrieve snapshot
        start_time = snapshot.timestamp - timedelta(minutes=1)
        end_time = snapshot.timestamp + timedelta(minutes=1)
        
        retrieved_snapshots = list(storage.get_snapshots("BTC/USDT", start_time, end_time))
        
        assert len(retrieved_snapshots) == 1
        assert retrieved_snapshots[0].symbol == snapshot.symbol
        assert retrieved_snapshots[0].best_bid == snapshot.best_bid
        assert retrieved_snapshots[0].best_ask == snapshot.best_ask
        
        storage.close()


class TestEnhancedSimulator:
    """Test enhanced trading simulator."""
    
    def test_enhanced_simulator_initialization(self):
        """Test enhanced simulator initialization."""
        simulator = EnhancedTradingSimulator(
            exchange="binance",
            fee_mode=FeeCalculationMode.REALISTIC,
            slippage_model=SlippageType.VOLUME_BASED,
            monthly_volume_usd=50000.0
        )
        
        assert simulator.exchange == "binance"
        assert simulator.monthly_volume_usd == 50000.0
        assert simulator.fee_calculator.calculation_mode == FeeCalculationMode.REALISTIC
        assert simulator.slippage_calculator.slippage_model == SlippageType.VOLUME_BASED
    
    def test_simulation_statistics(self):
        """Test simulation statistics tracking."""
        simulator = EnhancedTradingSimulator()
        
        # Get initial stats
        initial_stats = simulator.get_simulation_statistics()
        assert initial_stats["total_trades"] == 0
        assert initial_stats["total_volume_usd"] == 0.0
        
        # The simulator would need actual trade execution to update stats
        # This is tested in integration tests


class TestIntegration:
    """Integration tests for the complete system."""
    
    def test_fee_slippage_integration(self):
        """Test integration between fee and slippage models."""
        # Create calculators
        fee_calc = FeeCalculator(FeeCalculationMode.REALISTIC)
        slippage_calc = DepthBasedSlippage()
        
        # Create order book
        snapshot = OrderBookSnapshot(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            bids=[(50000.0, 1.0), (49999.0, 2.0)],
            asks=[(50001.0, 1.0), (50002.0, 2.0)]
        )
        
        # Calculate fees
        fee_context = OrderFeeContext(
            order_value_usd=10000.0,
            order_quantity=0.2,
            order_price=50000.0,
            side="buy",
            order_type="market",
            exchange="binance"
        )
        
        fees = fee_calc.calculate_fees(fee_context)
        
        # Calculate slippage
        slippage_context = SlippageContext(
            symbol="BTC/USDT",
            side="buy",
            quantity=0.2,
            order_type="market",
            order_book=snapshot
        )
        
        slippage = slippage_calc.calculate_slippage(slippage_context)
        
        # Both should return valid results
        assert fees.total_fees_usd >= 0.0
        assert slippage.slippage_bps >= 0.0
        assert slippage.effective_price > 0.0
    
    def test_order_book_replay_integration(self):
        """Test order book replay with simulation."""
        # Create storage and sample data
        storage = SQLiteOrderBookStorage(":memory:")
        
        # Create multiple snapshots
        base_time = datetime.now()
        snapshots = []
        
        for i in range(5):
            timestamp = base_time + timedelta(minutes=i)
            snapshot = OrderBookSnapshot(
                symbol="BTC/USDT",
                timestamp=timestamp,
                bids=[(50000.0 + i, 1.0), (49999.0 + i, 2.0)],
                asks=[(50001.0 + i, 1.0), (50002.0 + i, 2.0)]
            )
            snapshots.append(snapshot)
            storage.store_snapshot(snapshot)
        
        # Create replay engine
        replay_engine = OrderBookReplayEngine(storage, replay_speed=10.0)
        
        # Replay snapshots
        replayed_snapshots = list(replay_engine.replay_snapshots(
            "BTC/USDT",
            snapshots[0].timestamp,
            snapshots[-1].timestamp
        ))
        
        assert len(replayed_snapshots) == 5
        
        # Verify chronological order
        for i in range(1, len(replayed_snapshots)):
            assert replayed_snapshots[i].timestamp > replayed_snapshots[i-1].timestamp
        
        storage.close()


def test_performance_benchmarks():
    """Performance benchmarks for the enhanced backtesting system."""
    import time
    
    # Benchmark fee calculation
    fee_calc = FeeCalculator(FeeCalculationMode.REALISTIC)
    context = OrderFeeContext(
        order_value_usd=10000.0,
        order_quantity=0.2,
        order_price=50000.0,
        side="buy",
        order_type="market",
        exchange="binance"
    )
    
    start_time = time.time()
    for _ in range(1000):
        fee_calc.calculate_fees(context)
    fee_time = time.time() - start_time
    
    print(f"Fee calculation: {fee_time:.3f}s for 1000 calculations")
    assert fee_time < 1.0  # Should be fast
    
    # Benchmark slippage calculation
    slippage_calc = VolumeBasedSlippage()
    slippage_context = SlippageContext(
        symbol="BTC/USDT",
        side="buy",
        quantity=1.0,
        order_type="market",
        current_price=50000.0,
        volume_24h=1000000.0
    )
    
    start_time = time.time()
    for _ in range(1000):
        slippage_calc.calculate_slippage(slippage_context)
    slippage_time = time.time() - start_time
    
    print(f"Slippage calculation: {slippage_time:.3f}s for 1000 calculations")
    assert slippage_time < 1.0  # Should be fast


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
