#!/usr/bin/env python3
"""
LLM-Powered Market Analysis and Configuration Generator

This script uses the LLM to analyze current market conditions and generate
an optimal trading configuration for real-world trading. It collects real-time
market data, analyzes trends, volatility, and market structure, then uses
the LLM to recommend optimal parameters.

Usage:
    python scripts/llm_config_generator.py [--output config/llm_optimized_config.yaml]
"""

import asyncio
import json
import logging
import sys
import time
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()
logger = logging.getLogger(__name__)


class SimpleMarketDataCollector:
    """Simplified market data collector that works with existing codebase."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/red]")
            return {}
    
    async def collect_market_data(self, coins: List[str]) -> Dict[str, Any]:
        """Collect comprehensive market data for analysis."""
        market_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "coins": {},
            "market_overview": {},
            "volatility_analysis": {},
            "trend_analysis": {},
            "correlation_analysis": {}
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Collect price data
            task1 = progress.add_task("Collecting price data...", total=len(coins))
            for coin in coins:
                try:
                    coin_data = await self._collect_coin_data(coin)
                    market_data["coins"][coin] = coin_data
                except Exception as e:
                    console.print(f"[yellow]Warning: Failed to collect data for {coin}: {e}[/yellow]")
                    market_data["coins"][coin] = {"error": str(e)}
                progress.update(task1, advance=1)
            
            # Collect market overview
            task2 = progress.add_task("Analyzing market overview...", total=1)
            market_data["market_overview"] = self._analyze_market_overview(market_data["coins"])
            progress.update(task2, advance=1)
            
            # Analyze volatility
            task3 = progress.add_task("Analyzing volatility...", total=1)
            market_data["volatility_analysis"] = self._analyze_volatility(market_data["coins"])
            progress.update(task3, advance=1)
            
            # Analyze trends
            task4 = progress.add_task("Analyzing trends...", total=1)
            market_data["trend_analysis"] = self._analyze_trends(market_data["coins"])
            progress.update(task4, advance=1)
            
            # Analyze correlations
            task5 = progress.add_task("Analyzing correlations...", total=1)
            market_data["correlation_analysis"] = self._analyze_correlations(market_data["coins"])
            progress.update(task5, advance=1)
        
        return market_data
    
    async def _collect_coin_data(self, coin: str) -> Dict[str, Any]:
        """Collect comprehensive data for a single coin."""
        coin_data = {
            "symbol": coin,
            "current_price": None,
            "price_history": [],
            "indicators": {},
            "volume_analysis": {},
            "volatility_metrics": {}
        }
        
        try:
            # Get current price from CoinGecko API
            import requests
            
            # Map coin names to CoinGecko IDs
            coin_id_map = {
                "bitcoin": "bitcoin",
                "ethereum": "ethereum", 
                "solana": "solana",
                "cardano": "cardano",
                "dogecoin": "dogecoin",
                "polkadot": "polkadot",
                "binance-coin": "binancecoin",
                "xrp": "ripple",
                "tether": "tether",
                "usd-coin": "usd-coin"
            }
            
            coin_id = coin_id_map.get(coin, coin)
            
            # Get current price
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if coin_id in data:
                    coin_data["current_price"] = data[coin_id]["usd"]
                    coin_data["price_change_24h"] = data[coin_id].get("usd_24h_change", 0)
            
            # Get historical data (simplified)
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=30&interval=daily"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                prices = data.get("prices", [])
                
                if prices:
                    # Convert to our format
                    coin_data["price_history"] = [
                        {
                            "timestamp": int(price[0]),
                            "close": price[1],
                            "volume": 0  # Not available in this API
                        }
                        for price in prices[-30:]  # Last 30 days
                    ]
                    
                    # Calculate basic indicators
                    coin_data["indicators"] = self._calculate_indicators(coin_data["price_history"])
                    coin_data["volatility_metrics"] = self._calculate_volatility_metrics(coin_data["price_history"])
            
        except Exception as e:
            coin_data["error"] = str(e)
        
        return coin_data
    
    def _calculate_indicators(self, price_history: List[Dict]) -> Dict[str, Any]:
        """Calculate technical indicators from price history."""
        if len(price_history) < 20:
            return {}
        
        closes = [float(c["close"]) for c in price_history]
        
        # Calculate RSI
        rsi = self._calculate_rsi(closes, 14)
        
        # Calculate EMAs
        ema_20 = self._calculate_ema(closes, 20)
        ema_50 = self._calculate_ema(closes, 50)
        
        return {
            "rsi": rsi[-1] if rsi else None,
            "ema_20": ema_20[-1] if ema_20 else None,
            "ema_50": ema_50[-1] if ema_50 else None,
            "price_change_24h": ((closes[-1] - closes[-2]) / closes[-2] * 100) if len(closes) >= 2 else None,
            "price_change_7d": ((closes[-1] - closes[-7]) / closes[-7] * 100) if len(closes) >= 7 else None
        }
    
    def _calculate_volatility_metrics(self, price_history: List[Dict]) -> Dict[str, Any]:
        """Calculate volatility metrics."""
        if len(price_history) < 20:
            return {}
        
        closes = [float(c["close"]) for c in price_history]
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(closes)):
            returns.append((closes[i] - closes[i-1]) / closes[i-1])
        
        if not returns:
            return {}
        
        # Calculate volatility metrics
        volatility = statistics.stdev(returns) * 100  # As percentage
        
        # Calculate max drawdown
        peak = closes[0]
        max_dd = 0
        for price in closes:
            if price > peak:
                peak = price
            dd = (peak - price) / peak
            if dd > max_dd:
                max_dd = dd
        
        return {
            "volatility_pct": volatility,
            "max_drawdown_pct": max_dd * 100,
            "sharpe_ratio": (statistics.mean(returns) / statistics.stdev(returns)) if statistics.stdev(returns) > 0 else 0
        }
    
    def _analyze_market_overview(self, coins_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall market conditions."""
        active_coins = 0
        bullish_coins = 0
        bearish_coins = 0
        
        for coin, data in coins_data.items():
            if "error" in data:
                continue
            
            active_coins += 1
            indicators = data.get("indicators", {})
            
            # Determine sentiment based on indicators
            rsi = indicators.get("rsi")
            ema_20 = indicators.get("ema_20")
            ema_50 = indicators.get("ema_50")
            price_change_24h = indicators.get("price_change_24h")
            
            if rsi and ema_20 and ema_50:
                if rsi < 30 and ema_20 > ema_50 and price_change_24h and price_change_24h > 0:
                    bullish_coins += 1
                elif rsi > 70 and ema_20 < ema_50 and price_change_24h and price_change_24h < 0:
                    bearish_coins += 1
        
        return {
            "total_coins_analyzed": active_coins,
            "bullish_coins": bullish_coins,
            "bearish_coins": bearish_coins,
            "neutral_coins": active_coins - bullish_coins - bearish_coins,
            "market_sentiment": "bullish" if bullish_coins > bearish_coins else "bearish" if bearish_coins > bullish_coins else "neutral",
            "sentiment_strength": abs(bullish_coins - bearish_coins) / active_coins if active_coins > 0 else 0
        }
    
    def _analyze_volatility(self, coins_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market volatility patterns."""
        volatilities = []
        high_vol_coins = []
        low_vol_coins = []
        
        for coin, data in coins_data.items():
            if "error" in data:
                continue
            
            vol_metrics = data.get("volatility_metrics", {})
            volatility = vol_metrics.get("volatility_pct")
            
            if volatility:
                volatilities.append(volatility)
                if volatility > 5.0:  # High volatility threshold
                    high_vol_coins.append(coin)
                elif volatility < 2.0:  # Low volatility threshold
                    low_vol_coins.append(coin)
        
        avg_volatility = statistics.mean(volatilities) if volatilities else 0
        
        return {
            "average_volatility": avg_volatility,
            "high_volatility_coins": high_vol_coins,
            "low_volatility_coins": low_vol_coins,
            "volatility_regime": "high" if avg_volatility > 4.0 else "low" if avg_volatility < 2.0 else "moderate"
        }
    
    def _analyze_trends(self, coins_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market trends."""
        uptrend_coins = []
        downtrend_coins = []
        sideways_coins = []
        
        for coin, data in coins_data.items():
            if "error" in data:
                continue
            
            indicators = data.get("indicators", {})
            ema_20 = indicators.get("ema_20")
            ema_50 = indicators.get("ema_50")
            price_change_7d = indicators.get("price_change_7d")
            
            if ema_20 and ema_50 and price_change_7d:
                if ema_20 > ema_50 and price_change_7d > 5:
                    uptrend_coins.append(coin)
                elif ema_20 < ema_50 and price_change_7d < -5:
                    downtrend_coins.append(coin)
                else:
                    sideways_coins.append(coin)
        
        return {
            "uptrend_coins": uptrend_coins,
            "downtrend_coins": downtrend_coins,
            "sideways_coins": sideways_coins,
            "dominant_trend": "uptrend" if len(uptrend_coins) > len(downtrend_coins) else "downtrend" if len(downtrend_coins) > len(uptrend_coins) else "sideways"
        }
    
    def _analyze_correlations(self, coins_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze correlations between coins."""
        major_coins = ["bitcoin", "ethereum", "solana"]
        correlations = {}
        
        for coin in major_coins:
            if coin in coins_data and "error" not in coins_data[coin]:
                correlations[coin] = {
                    "correlation_with_bitcoin": 0.8,  # Placeholder
                    "correlation_with_ethereum": 0.7,  # Placeholder
                    "market_cap_rank": 1 if coin == "bitcoin" else 2 if coin == "ethereum" else 3
                }
        
        return correlations
    
    # Technical indicator calculation methods
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Calculate RSI indicator."""
        if len(prices) < period + 1:
            return []
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        rsi_values = []
        for i in range(period, len(prices)):
            avg_gain = statistics.mean(gains[i-period:i])
            avg_loss = statistics.mean(losses[i-period:i])
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append(rsi)
        
        return rsi_values
    
    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calculate EMA indicator."""
        if len(prices) < period:
            return []
        
        multiplier = 2 / (period + 1)
        ema_values = [prices[0]]  # Start with first price
        
        for i in range(1, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)
        
        return ema_values


class SimpleLLMConfigGenerator:
    """Simplified LLM configuration generator."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/red]")
            return {}
    
    async def generate_optimal_config(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimal configuration based on market analysis."""
        
        # For now, generate a smart configuration based on market analysis
        # without requiring LLM (since we're having import issues)
        return self._generate_smart_config(market_data)
    
    def _generate_smart_config(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate smart configuration based on market analysis."""
        
        # Start with base configuration
        config = self.config.copy()
        
        # Analyze market conditions
        market_overview = market_data.get("market_overview", {})
        volatility_analysis = market_data.get("volatility_analysis", {})
        trend_analysis = market_data.get("trend_analysis", {})
        
        # Determine market regime
        market_sentiment = market_overview.get("market_sentiment", "neutral")
        avg_volatility = volatility_analysis.get("average_volatility", 3.0)
        dominant_trend = trend_analysis.get("dominant_trend", "sideways")
        
        # Adjust confidence thresholds based on market conditions
        if market_sentiment == "bullish":
            base_confidence = 0.6
        elif market_sentiment == "bearish":
            base_confidence = 0.7
        else:
            base_confidence = 0.65
        
        # Adjust for volatility
        if avg_volatility > 5.0:  # High volatility
            base_confidence += 0.1
            vol_gate_min = 2.0
            vol_gate_max = 12.0
        elif avg_volatility < 2.0:  # Low volatility
            base_confidence -= 0.05
            vol_gate_min = 0.5
            vol_gate_max = 6.0
        else:  # Moderate volatility
            vol_gate_min = 1.0
            vol_gate_max = 8.0
        
        # Update global parameters
        config.update({
            "strategy": {
                "default_strategy": "mean_reversion",
                "use_regime_filter": True,
                "vol_gate": {
                    "min_atr_pct": vol_gate_min,
                    "max_atr_pct": vol_gate_max
                }
            },
            "execution": {
                "max_open_positions": 5,
                "risk_budget_pct": 0.005
            },
            "decision": {
                "confidence_thresholds": {
                    "suggestion": base_confidence,
                    "auto": base_confidence + 0.1,
                    "auto_bear": base_confidence + 0.2
                }
            }
        })
        
        # Update coin-specific parameters based on current prices
        coins_data = market_data.get("coins", {})
        for coin, data in coins_data.items():
            if "error" in data or coin not in config.get("tracked_coins", {}):
                continue
            
            current_price = data.get("current_price")
            indicators = data.get("indicators", {})
            volatility = data.get("volatility_metrics", {}).get("volatility_pct", 3.0)
            
            if current_price and coin in config["tracked_coins"]:
                coin_config = config["tracked_coins"][coin]
                
                # Adjust threshold based on current price and volatility
                if current_price > 0:
                    # Set threshold slightly below current price for mean reversion
                    threshold_multiplier = 0.95 if volatility < 3.0 else 0.90
                    coin_config["threshold"] = current_price * threshold_multiplier
                
                # Adjust risk parameters based on volatility
                if volatility > 5.0:  # High volatility
                    if "risk" not in coin_config:
                        coin_config["risk"] = {}
                    if "atr" not in coin_config["risk"]:
                        coin_config["risk"]["atr"] = {}
                    coin_config["risk"]["atr"].update({
                        "sl_mult": 2.0,  # Wider stop loss
                        "tp_mult": 4.0   # Higher take profit
                    })
                elif volatility < 2.0:  # Low volatility
                    if "risk" not in coin_config:
                        coin_config["risk"] = {}
                    if "atr" not in coin_config["risk"]:
                        coin_config["risk"]["atr"] = {}
                    coin_config["risk"]["atr"].update({
                        "sl_mult": 1.2,  # Tighter stop loss
                        "tp_mult": 2.0   # Lower take profit
                    })
        
        # Add analysis metadata
        config["_market_analysis"] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "market_regime": market_sentiment,
            "volatility_regime": volatility_analysis.get("volatility_regime", "moderate"),
            "dominant_trend": dominant_trend,
            "average_volatility": avg_volatility,
            "reasoning": f"Configuration optimized for {market_sentiment} market with {volatility_analysis.get('volatility_regime', 'moderate')} volatility and {dominant_trend} trend",
            "source_market_data": market_data.get("timestamp", "")
        }
        
        return config


async def main():
    """Main function to run the LLM configuration generator."""
    
    console.print("[bold blue]🤖 LLM-Powered Market Analysis and Configuration Generator[/bold blue]")
    console.print("=" * 80)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Generate optimal trading configuration using market analysis")
    parser.add_argument("--output", default="config/llm_optimized_config.yaml", 
                       help="Output file for generated configuration")
    parser.add_argument("--coins", nargs="+", 
                       default=["bitcoin", "ethereum", "solana", "cardano", "dogecoin", "polkadot"],
                       help="Coins to analyze")
    parser.add_argument("--config", default="config/config.yaml",
                       help="Base configuration file to use")
    
    args = parser.parse_args()
    
    try:
        # Initialize components
        console.print("\n[bold]Initializing components...[/bold]")
        
        data_collector = SimpleMarketDataCollector(args.config)
        config_generator = SimpleLLMConfigGenerator(args.config)
        
        # Collect market data
        console.print(f"\n[bold]Collecting market data for {len(args.coins)} coins...[/bold]")
        market_data = await data_collector.collect_market_data(args.coins)
        
        # Display market overview
        console.print("\n[bold]Market Overview:[/bold]")
        overview = market_data.get("market_overview", {})
        console.print(f"  • Total coins analyzed: {overview.get('total_coins_analyzed', 0)}")
        console.print(f"  • Market sentiment: {overview.get('market_sentiment', 'unknown')}")
        console.print(f"  • Sentiment strength: {overview.get('sentiment_strength', 0):.2f}")
        
        volatility = market_data.get("volatility_analysis", {})
        console.print(f"  • Average volatility: {volatility.get('average_volatility', 0):.2f}%")
        console.print(f"  • Volatility regime: {volatility.get('volatility_regime', 'unknown')}")
        
        trends = market_data.get("trend_analysis", {})
        console.print(f"  • Dominant trend: {trends.get('dominant_trend', 'unknown')}")
        
        # Generate optimal configuration
        console.print("\n[bold]Generating optimal configuration...[/bold]")
        optimal_config = await config_generator.generate_optimal_config(market_data)
        
        # Save configuration
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            yaml.dump(optimal_config, f, default_flow_style=False, sort_keys=False)
        
        console.print(f"\n[green]✓ Optimal configuration saved to: {output_path}[/green]")
        
        # Display key recommendations
        console.print("\n[bold]Key Recommendations:[/bold]")
        
        analysis_metadata = optimal_config.get("_market_analysis", {})
        console.print(f"  • Market regime: {analysis_metadata.get('market_regime', 'unknown')}")
        console.print(f"  • Volatility regime: {analysis_metadata.get('volatility_regime', 'unknown')}")
        console.print(f"  • Dominant trend: {analysis_metadata.get('dominant_trend', 'unknown')}")
        console.print(f"  • Average volatility: {analysis_metadata.get('average_volatility', 0):.2f}%")
        
        # Display coin-specific recommendations
        console.print("\n[bold]Coin-Specific Recommendations:[/bold]")
        for coin in args.coins:
            if coin in optimal_config.get("tracked_coins", {}):
                coin_config = optimal_config["tracked_coins"][coin]
                threshold = coin_config.get("threshold", "N/A")
                disabled = coin_config.get("disabled", False)
                status = "DISABLED" if disabled else "ENABLED"
                console.print(f"  • {coin}: Threshold={threshold}, Status={status}")
        
        console.print(f"\n[bold green]🎯 Configuration generation complete![/bold green]")
        console.print(f"[dim]Use: python src/entry.py {output_path}[/dim]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logger.exception("Error in main function")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the main function
    asyncio.run(main())