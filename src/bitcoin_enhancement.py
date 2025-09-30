"""
Bitcoin-specific decision enhancement.
Adds fundamental analysis and macro awareness to Bitcoin trading decisions.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
import pandas as pd


def enhance_bitcoin_decision(
    coin_id: str,
    current_price: float,
    threshold: float,
    rsi: Optional[float],
    confidence: float,
    tracker
) -> tuple[float, str]:
    """
    Enhance Bitcoin trading decisions with fundamental analysis.
    
    Returns:
        tuple: (enhanced_confidence, reason)
    """
    
    if coin_id.lower() != "bitcoin":
        return confidence, "not_bitcoin"
    
    try:
        enhanced_confidence = confidence
        reasons = []
        
        # 1. Bitcoin-specific threshold adjustment
        # Bitcoin tends to break through psychological levels
        if current_price > threshold * 0.95:  # Within 5% of threshold
            enhanced_confidence += 0.15
            reasons.append("near_breakout_level")
        
        # 2. Macro trend analysis
        # Check if we're in a Bitcoin bull market phase
        if _is_bitcoin_bull_market(current_price, tracker):
            enhanced_confidence += 0.2
            reasons.append("bull_market_phase")
        
        # 3. Institutional adoption signals
        # Higher prices often indicate institutional buying
        if current_price > 100000:  # Above $100k
            enhanced_confidence += 0.1
            reasons.append("institutional_level")
        
        # 4. RSI interpretation for Bitcoin
        # Bitcoin can stay "overbought" for extended periods
        if rsi is not None:
            if 50 < rsi < 70:  # Bitcoin's "sweet spot"
                enhanced_confidence += 0.15
                reasons.append("optimal_rsi_range")
            elif rsi > 70:  # Bitcoin can stay overbought
                enhanced_confidence += 0.05  # Small boost instead of penalty
                reasons.append("bitcoin_overbought_ok")
        
        # 5. Time-based factors
        current_hour = datetime.now(timezone.utc).hour
        if 14 <= current_hour <= 22:  # US trading hours
            enhanced_confidence += 0.05
            reasons.append("us_trading_hours")
        
        # 6. Volatility analysis
        volatility_score = _get_bitcoin_volatility_score(tracker, coin_id)
        if volatility_score > 0.6:  # High volatility = opportunity
            enhanced_confidence += 0.1
            reasons.append("high_volatility_opportunity")
        
        # Cap confidence at 0.95
        enhanced_confidence = min(0.95, enhanced_confidence)
        
        reason = ", ".join(reasons) if reasons else "bitcoin_fundamental_analysis"
        
        return enhanced_confidence, reason
        
    except Exception as e:
        return confidence, f"bitcoin_enhancement_error: {str(e)}"


def _is_bitcoin_bull_market(current_price: float, tracker) -> bool:
    """
    Determine if Bitcoin is in a bull market phase.
    """
    try:
        # Get historical data for Bitcoin
        bitcoin_history = tracker.history.get("bitcoin", {})
        candles = bitcoin_history.get("candles", [])
        
        if len(candles) < 50:
            return False
        
        # Calculate 50-day moving average
        recent_closes = [c.c for c in candles[-50:]]
        ma_50 = sum(recent_closes) / len(recent_closes)
        
        # Calculate 200-day moving average (if available)
        if len(candles) >= 200:
            long_closes = [c.c for c in candles[-200:]]
            ma_200 = sum(long_closes) / len(long_closes)
            
            # Bull market: price > MA50 > MA200
            return current_price > ma_50 > ma_200
        
        # Fallback: just check if price > MA50
        return current_price > ma_50
        
    except Exception:
        return False


def _get_bitcoin_volatility_score(tracker, coin_id: str) -> float:
    """
    Calculate Bitcoin volatility score (0-1).
    Higher volatility = more trading opportunities.
    """
    try:
        bitcoin_history = tracker.history.get(coin_id, {})
        candles = bitcoin_history.get("candles", [])
        
        if len(candles) < 20:
            return 0.5
        
        # Calculate recent volatility
        recent_closes = [c.c for c in candles[-20:]]
        volatility = 0
        
        for i in range(1, len(recent_closes)):
            daily_return = abs((recent_closes[i] - recent_closes[i-1]) / recent_closes[i-1])
            volatility += daily_return
        
        volatility /= len(recent_closes) - 1
        
        # Convert to 0-1 score
        # Bitcoin typically has 2-5% daily volatility
        if volatility > 0.05:  # >5% daily volatility
            return 0.9
        elif volatility > 0.03:  # 3-5% daily volatility
            return 0.7
        elif volatility > 0.02:  # 2-3% daily volatility
            return 0.5
        else:  # <2% daily volatility
            return 0.3
            
    except Exception:
        return 0.5


def apply_bitcoin_enhancement_to_decision(tracker, coin_id: str, decision) -> Any:
    """
    Apply Bitcoin-specific enhancements to a trading decision.
    """
    try:
        if coin_id.lower() != "bitcoin":
            return decision
        
        # Get current price from tracker
        current_price = None
        try:
            prices = tracker.price_manager.get_aggregated_prices({"bitcoin": "btc"})
            if prices and "bitcoin" in prices:
                price_data = prices["bitcoin"]
                if isinstance(price_data, dict):
                    current_price = price_data.get("price")
        except Exception:
            pass
        
        if current_price is None:
            return decision
        
        # Get Bitcoin config
        config_data = tracker.config_manager.load_full_config()
        bitcoin_config = config_data.get("tracked_coins", {}).get("bitcoin", {})
        threshold = float(bitcoin_config.get("threshold", 100000))
        
        # Get RSI from history
        bitcoin_history = tracker.history.get("bitcoin", {})
        last_data = bitcoin_history.get("last", {})
        rsi = last_data.get("rsi")
        
        # Enhance the decision
        enhanced_confidence, reason = enhance_bitcoin_decision(
            coin_id, current_price, threshold, rsi, decision.confidence, tracker
        )
        
        # Update decision
        decision.confidence = enhanced_confidence
        decision.reason = f"{decision.reason} | {reason}"
        
        return decision
        
    except Exception as e:
        # Return original decision if enhancement fails
        return decision
