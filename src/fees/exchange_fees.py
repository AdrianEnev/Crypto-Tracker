"""
Exchange-Specific Fee Configurations

Contains fee structures for major cryptocurrency exchanges including
volume tiers, maker/taker rates, and asset-specific fees.
"""

from typing import Dict, List, Optional

from .models import AssetSpecificFee, ExchangeFeeStructure, FeeTier


class ExchangeFeeRegistry:
    """Registry of exchange fee structures."""

    def __init__(self):
        self._exchanges: Dict[str, ExchangeFeeStructure] = {}
        self._register_default_exchanges()

    def register_exchange(self, exchange: ExchangeFeeStructure) -> None:
        """Register an exchange fee structure."""
        self._exchanges[exchange.exchange_name.lower()] = exchange

    def get_exchange(self, exchange_name: str) -> Optional[ExchangeFeeStructure]:
        """Get fee structure for an exchange."""
        return self._exchanges.get(exchange_name.lower())

    def list_exchanges(self) -> List[str]:
        """List all registered exchanges."""
        return list(self._exchanges.keys())

    def _register_default_exchanges(self) -> None:
        """Register default exchange fee structures."""
        self._register_binance()
        self._register_coinbase()
        self._register_bybit()
        self._register_kraken()
        self._register_okx()

    def _register_binance(self) -> None:
        """Register Binance fee structure."""
        binance_tiers = [
            FeeTier(
                volume_usd=0,
                maker_bps=2.0,
                taker_bps=4.0,
                withdrawal_fee_usd=0.0,
                description="VIP 0",
            ),
            FeeTier(volume_usd=50000, maker_bps=1.8, taker_bps=3.6, description="VIP 1"),
            FeeTier(volume_usd=250000, maker_bps=1.5, taker_bps=3.0, description="VIP 2"),
            FeeTier(volume_usd=1000000, maker_bps=1.2, taker_bps=2.4, description="VIP 3"),
            FeeTier(volume_usd=5000000, maker_bps=1.0, taker_bps=2.0, description="VIP 4"),
            FeeTier(volume_usd=20000000, maker_bps=0.8, taker_bps=1.6, description="VIP 5"),
            FeeTier(volume_usd=100000000, maker_bps=0.6, taker_bps=1.2, description="VIP 6"),
            FeeTier(volume_usd=500000000, maker_bps=0.4, taker_bps=0.8, description="VIP 7"),
            FeeTier(volume_usd=2000000000, maker_bps=0.2, taker_bps=0.4, description="VIP 8"),
            FeeTier(volume_usd=5000000000, maker_bps=0.1, taker_bps=0.2, description="VIP 9"),
        ]

        binance = ExchangeFeeStructure(
            exchange_name="binance",
            default_maker_bps=2.0,
            default_taker_bps=4.0,
            default_withdrawal_fee_usd=0.0,
            volume_tiers=binance_tiers,
            supported_assets=[
                "BTC",
                "ETH",
                "BNB",
                "ADA",
                "DOT",
                "LINK",
                "LTC",
                "BCH",
                "XLM",
                "XRP",
                "EOS",
                "TRX",
                "XMR",
                "DASH",
                "NEO",
                "IOTA",
            ],
        )

        self.register_exchange(binance)

    def _register_coinbase(self) -> None:
        """Register Coinbase Pro fee structure."""
        coinbase_tiers = [
            FeeTier(volume_usd=0, maker_bps=5.0, taker_bps=5.0, description="Standard"),
            FeeTier(volume_usd=10000, maker_bps=3.5, taker_bps=3.5, description="Tier 1"),
            FeeTier(volume_usd=50000, maker_bps=2.5, taker_bps=2.5, description="Tier 2"),
            FeeTier(volume_usd=100000, maker_bps=1.5, taker_bps=1.5, description="Tier 3"),
            FeeTier(volume_usd=1000000, maker_bps=1.0, taker_bps=1.0, description="Tier 4"),
            FeeTier(volume_usd=10000000, maker_bps=0.5, taker_bps=0.5, description="Tier 5"),
            FeeTier(volume_usd=50000000, maker_bps=0.25, taker_bps=0.25, description="Tier 6"),
            FeeTier(volume_usd=100000000, maker_bps=0.1, taker_bps=0.1, description="Tier 7"),
        ]

        coinbase = ExchangeFeeStructure(
            exchange_name="coinbase",
            default_maker_bps=5.0,
            default_taker_bps=5.0,
            default_withdrawal_fee_usd=0.0,
            volume_tiers=coinbase_tiers,
            supported_assets=[
                "BTC",
                "ETH",
                "LTC",
                "BCH",
                "XRP",
                "ETC",
                "ZRX",
                "BAT",
                "REP",
                "ZEC",
                "DASH",
                "XLM",
                "ADA",
                "EOS",
                "XTZ",
            ],
        )

        self.register_exchange(coinbase)

    def _register_bybit(self) -> None:
        """Register Bybit fee structure."""
        bybit_tiers = [
            FeeTier(volume_usd=0, maker_bps=1.0, taker_bps=6.0, description="Standard"),
            FeeTier(volume_usd=100000, maker_bps=0.8, taker_bps=5.5, description="VIP 1"),
            FeeTier(volume_usd=500000, maker_bps=0.6, taker_bps=5.0, description="VIP 2"),
            FeeTier(volume_usd=1000000, maker_bps=0.4, taker_bps=4.5, description="VIP 3"),
            FeeTier(volume_usd=5000000, maker_bps=0.2, taker_bps=4.0, description="VIP 4"),
            FeeTier(volume_usd=20000000, maker_bps=0.0, taker_bps=3.5, description="VIP 5"),
            FeeTier(volume_usd=50000000, maker_bps=0.0, taker_bps=3.0, description="VIP 6"),
            FeeTier(volume_usd=100000000, maker_bps=0.0, taker_bps=2.5, description="VIP 7"),
        ]

        bybit = ExchangeFeeStructure(
            exchange_name="bybit",
            default_maker_bps=1.0,
            default_taker_bps=6.0,
            default_withdrawal_fee_usd=0.0,
            volume_tiers=bybit_tiers,
            supported_assets=[
                "BTC",
                "ETH",
                "SOL",
                "XRP",
                "ADA",
                "AVAX",
                "DOT",
                "LINK",
                "MATIC",
                "UNI",
                "LTC",
                "BCH",
                "ATOM",
                "NEAR",
                "FTM",
            ],
        )

        self.register_exchange(bybit)

    def _register_kraken(self) -> None:
        """Register Kraken fee structure."""
        kraken_tiers = [
            FeeTier(volume_usd=0, maker_bps=1.6, taker_bps=2.6, description="Standard"),
            FeeTier(volume_usd=50000, maker_bps=1.4, taker_bps=2.4, description="Tier 1"),
            FeeTier(volume_usd=100000, maker_bps=1.2, taker_bps=2.2, description="Tier 2"),
            FeeTier(volume_usd=250000, maker_bps=1.0, taker_bps=2.0, description="Tier 3"),
            FeeTier(volume_usd=500000, maker_bps=0.8, taker_bps=1.8, description="Tier 4"),
            FeeTier(volume_usd=1000000, maker_bps=0.6, taker_bps=1.6, description="Tier 5"),
            FeeTier(volume_usd=2500000, maker_bps=0.4, taker_bps=1.4, description="Tier 6"),
            FeeTier(volume_usd=5000000, maker_bps=0.2, taker_bps=1.2, description="Tier 7"),
            FeeTier(volume_usd=10000000, maker_bps=0.0, taker_bps=1.0, description="Tier 8"),
        ]

        kraken = ExchangeFeeStructure(
            exchange_name="kraken",
            default_maker_bps=1.6,
            default_taker_bps=2.6,
            default_withdrawal_fee_usd=0.0,
            volume_tiers=kraken_tiers,
            supported_assets=[
                "BTC",
                "ETH",
                "LTC",
                "BCH",
                "XRP",
                "ETC",
                "ZEC",
                "DASH",
                "XMR",
                "REP",
                "XLM",
                "ADA",
                "DOT",
                "LINK",
                "UNI",
            ],
        )

        self.register_exchange(kraken)

    def _register_okx(self) -> None:
        """Register OKX fee structure."""
        okx_tiers = [
            FeeTier(volume_usd=0, maker_bps=2.0, taker_bps=5.0, description="Regular"),
            FeeTier(volume_usd=10000, maker_bps=1.8, taker_bps=4.5, description="VIP 1"),
            FeeTier(volume_usd=50000, maker_bps=1.5, taker_bps=4.0, description="VIP 2"),
            FeeTier(volume_usd=100000, maker_bps=1.2, taker_bps=3.5, description="VIP 3"),
            FeeTier(volume_usd=500000, maker_bps=1.0, taker_bps=3.0, description="VIP 4"),
            FeeTier(volume_usd=2000000, maker_bps=0.8, taker_bps=2.5, description="VIP 5"),
            FeeTier(volume_usd=10000000, maker_bps=0.6, taker_bps=2.0, description="VIP 6"),
            FeeTier(volume_usd=50000000, maker_bps=0.4, taker_bps=1.5, description="VIP 7"),
            FeeTier(volume_usd=100000000, maker_bps=0.2, taker_bps=1.0, description="VIP 8"),
        ]

        okx = ExchangeFeeStructure(
            exchange_name="okx",
            default_maker_bps=2.0,
            default_taker_bps=5.0,
            default_withdrawal_fee_usd=0.0,
            volume_tiers=okx_tiers,
            supported_assets=[
                "BTC",
                "ETH",
                "BNB",
                "ADA",
                "DOT",
                "LINK",
                "LTC",
                "BCH",
                "XLM",
                "XRP",
                "EOS",
                "TRX",
                "ATOM",
                "NEAR",
                "SOL",
            ],
        )

        self.register_exchange(okx)


# Global registry instance
_registry = ExchangeFeeRegistry()


def get_exchange_fees(exchange_name: str) -> Optional[ExchangeFeeStructure]:
    """Get fee structure for an exchange."""
    return _registry.get_exchange(exchange_name)


def register_exchange_fees(exchange: ExchangeFeeStructure) -> None:
    """Register a custom exchange fee structure."""
    _registry.register_exchange(exchange)


def list_supported_exchanges() -> List[str]:
    """List all supported exchanges."""
    return _registry.list_exchanges()


def get_default_fee_tiers() -> Dict[str, List[FeeTier]]:
    """Get default fee tiers for all exchanges."""
    return {
        exchange_name: _registry.get_exchange(exchange_name).volume_tiers
        for exchange_name in _registry.list_exchanges()
    }
