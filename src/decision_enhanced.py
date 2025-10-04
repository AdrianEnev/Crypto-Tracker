from __future__ import annotations

from typing import Any, Dict, Optional
import asyncio
import logging

import pandas as pd
import yaml

from .models import Decision
from .strategies.factory import get_strategy

logger = logging.getLogger(__name__)


def _load_full_config(config_path: str) -> Dict[str, Any]:
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _build_df_from_history(tracker, coin_id: str) -> Optional[pd.DataFrame]:
    h = tracker.history.get(coin_id) or {}
    candles = h.get("candles") or []
    if not candles:
        return None
    df = pd.DataFrame(
        {
            "open": [c.o for c in candles],
            "high": [c.h for c in candles],
            "low": [c.l for c in candles],
            "close": [c.c for c in candles],
            "volume": [c.v for c in candles],
            "ts": [c.ts for c in candles],
        }
    )
    df.index = pd.to_datetime(df["ts"], unit="ms")
    return df


def compute_confidence(
    price: float,
    threshold: float,
    rsi: Optional[float],
    ma_short: Optional[float],
    ma_long: Optional[float],
) -> float:
    """
    Backwards-compatible confidence heuristic used by tests and backtests.
    Rough intuition:
    - Price below threshold -> bullish bias
    - RSI oversold (<30) -> stronger bullish bias
    - Trend filter (MA short > MA long) -> minor boost
    """
    try:
        conf = 0.5
        if price is not None and threshold is not None and float(price) < float(threshold):
            conf += 0.2
        if rsi is not None:
            r = float(rsi)
            if r < 30.0:
                conf += 0.2
            elif r > 70.0:
                conf -= 0.1
        if ma_short is not None and ma_long is not None:
            if float(ma_short) > float(ma_long):
                conf += 0.1
            else:
                conf -= 0.05
        return max(0.0, min(1.0, float(conf)))
    except Exception:
        return 0.0


def recommend_action(
    price: float,
    threshold: float,
    rsi: Optional[float],
    confidence: float,
    suggestion_threshold: float = 0.5,
) -> tuple[str, str, str]:
    """
    Backwards-compatible signal/action recommendation used by tests and backtests.
    Returns (signal, action, reason).
    """
    try:
        signal = "threshold_check"
        action = "Hold"
        reason_parts = []
        if price is not None and threshold is not None and float(price) < float(threshold):
            reason_parts.append("price<threshold")
            # Only allow Buy when RSI confirms oversold (<30) AND confidence gate passes
            if rsi is not None and float(rsi) < 30.0:
                signal = "threshold_rsi"
                reason_parts.append("RSI<30")
                if float(confidence) >= float(suggestion_threshold):
                    action = "Buy"
            else:
                # RSI not oversold -> Hold
                action = "Hold"
        else:
            # Over threshold or missing inputs → Hold
            action = "Hold"
        return signal, action, ", ".join(reason_parts) if reason_parts else ""
    except Exception:
        return "error", "Hold", "exception"


async def _get_social_media_signal(tracker, coin_id: str) -> Optional[Dict[str, Any]]:
    """Get social media signal for enhanced decision making."""
    try:
        if not hasattr(tracker, 'social_integration') or not tracker.social_integration:
            return None
            
        # Get social media signal
        social_signal = await tracker.social_integration.get_social_signal(coin_id)
        if social_signal:
            logger.info(f"Social media signal for {coin_id}: {social_signal}")
            return social_signal
        return None
    except Exception as e:
        logger.warning(f"Error getting social media signal for {coin_id}: {e}")
        return None


async def _get_llm_analysis(tracker, coin_id: str, current_price: float) -> Optional[Dict[str, Any]]:
    """Get comprehensive LLM analysis for enhanced decision making."""
    try:
        if not hasattr(tracker, 'market_analyzer') or not tracker.market_analyzer:
            return None

        # Check if LLM client is disabled due to failures or rate limiting
        if hasattr(tracker.market_analyzer, 'llm_client'):
            llm_client = tracker.market_analyzer.llm_client
            
            # Check if API key is configured
            if not llm_client.config.api_key:
                logger.debug(f"LLM API key not configured, skipping analysis for {coin_id}")
                return None
            
            if llm_client.is_disabled():
                logger.debug(f"LLM client is disabled, skipping analysis for {coin_id}")
                return None
            
            # Check if LLM is in backoff period
            if hasattr(llm_client, 'backoff_until_ts') and llm_client.backoff_until_ts > 0:
                import time
                if time.time() < llm_client.backoff_until_ts:
                    remaining = int(llm_client.backoff_until_ts - time.time())
                    logger.debug(f"LLM is rate-limited, skipping analysis for {coin_id} (backoff: {remaining}s)")
                    return None

        # Get coin config for symbol
        coin_config = tracker.config.tracked_coins.get(coin_id)
        if not coin_config:
            return None

        symbol = coin_config.symbol.upper()

        # Prepare comprehensive market data for LLM analysis
        market_data = await _prepare_comprehensive_market_data(tracker, coin_id, symbol, current_price)
        
        if not market_data:
            return None
        
        # Perform LLM analysis with comprehensive data
        analysis_result = await tracker.market_analyzer.analyze_market(
            coin=symbol,
            market_data=market_data,
            analysis_mode="comprehensive"
        )
        
        if analysis_result:
            logger.info(f"LLM analysis for {coin_id}: {analysis_result.get('sentiment', 'neutral')}")
            return analysis_result
        return None
    except Exception as e:
        logger.warning(f"Error getting LLM analysis for {coin_id}: {e}")
        return None

async def _prepare_comprehensive_market_data(tracker, coin_id: str, symbol: str, current_price: float) -> Optional[Dict[str, Any]]:
    """Prepare comprehensive market data for LLM analysis."""
    try:
        from datetime import datetime, timezone
        
        # Get historical data
        history_data = tracker.price_manager.history.get(coin_id, {})
        candles = history_data.get("candles", [])
        indicators = history_data.get("last", {})
        
        # Prepare technical data
        technical_data = {
            "trend": _determine_trend(indicators),
            "support_resistance": _calculate_support_resistance(candles, current_price),
            "volume": _analyze_volume(candles),
            "momentum": _analyze_momentum(indicators),
            "rsi": indicators.get("rsi", 50.0),
            "moving_averages": _format_moving_averages(indicators, current_price),
            "volatility": _analyze_volatility(candles)
        }
        
        # Prepare social data (mock for now, would integrate with real social media)
        social_data = {
            "twitter_sentiment": 0.5,  # Would be real data
            "reddit_sentiment": 0.5,   # Would be real data
            "community_activity": "normal",
            "influencer_sentiment": 0.5,
            "momentum_score": 0.5
        }
        
        # Prepare market structure data
        market_structure_data = {
            "institutional_flows": "normal",
            "exchange_flows": "normal", 
            "derivatives": "stable",
            "onchain": "normal"
        }
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "coin_id": coin_id,
            "symbol": symbol,
            "current_price": current_price,
            "technical": technical_data,
            "social": social_data,
            "market_structure": market_structure_data,
            "historical_candles": candles[-50:] if candles else [],  # Last 50 candles
            "indicators": indicators
        }
        
    except Exception as e:
        logger.error(f"Error preparing market data for LLM: {e}")
        return None

def _determine_trend(indicators: Dict[str, Any]) -> str:
    """Determine market trend from indicators."""
    try:
        ema_fast = indicators.get("ema_fast")
        ema_slow = indicators.get("ema_slow")
        
        if ema_fast and ema_slow:
            if ema_fast > ema_slow * 1.02:
                return "bullish"
            elif ema_fast < ema_slow * 0.98:
                return "bearish"
        return "neutral"
    except Exception:
        return "neutral"

def _calculate_support_resistance(candles: list, current_price: float) -> str:
    """Calculate support and resistance levels."""
    try:
        if not candles:
            return f"Support: ${current_price * 0.95:.2f}, Resistance: ${current_price * 1.05:.2f}"
        
        # Simple calculation based on recent highs/lows
        recent_candles = candles[-20:] if len(candles) >= 20 else candles
        highs = [c.h for c in recent_candles]
        lows = [c.l for c in recent_candles]
        
        resistance = max(highs) if highs else current_price * 1.05
        support = min(lows) if lows else current_price * 0.95
        
        return f"Support: ${support:.2f}, Resistance: ${resistance:.2f}"
    except Exception:
        return f"Support: ${current_price * 0.95:.2f}, Resistance: ${current_price * 1.05:.2f}"

def _analyze_volume(candles: list) -> str:
    """Analyze volume patterns."""
    try:
        if not candles:
            return "normal"
        
        recent_candles = candles[-10:] if len(candles) >= 10 else candles
        volumes = [c.v for c in recent_candles]
        avg_volume = sum(volumes) / len(volumes)
        
        if avg_volume > 1.5:
            return "high"
        elif avg_volume < 0.5:
            return "low"
        return "normal"
    except Exception:
        return "normal"

def _analyze_momentum(indicators: Dict[str, Any]) -> str:
    """Analyze momentum from RSI."""
    try:
        rsi = indicators.get("rsi")
        if rsi:
            if rsi > 70:
                return "strong_bearish"
            elif rsi > 60:
                return "weak_bearish"
            elif rsi < 30:
                return "strong_bullish"
            elif rsi < 40:
                return "weak_bullish"
        return "neutral"
    except Exception:
        return "neutral"

def _format_moving_averages(indicators: Dict[str, Any], current_price: float) -> str:
    """Format moving averages for display."""
    try:
        ema_fast = indicators.get("ema_fast", current_price * 0.98)
        ema_slow = indicators.get("ema_slow", current_price * 1.02)
        return f"EMA20: ${ema_fast:.2f}, EMA50: ${ema_slow:.2f}"
    except Exception:
        return f"EMA20: ${current_price * 0.98:.2f}, EMA50: ${current_price * 1.02:.2f}"

def _analyze_volatility(candles: list) -> str:
    """Analyze current volatility."""
    try:
        if not candles or len(candles) < 5:
            return "normal"
        
        recent_candles = candles[-5:]
        price_changes = []
        
        for i in range(1, len(recent_candles)):
            change = abs(recent_candles[i].c - recent_candles[i-1].c) / recent_candles[i-1].c
            price_changes.append(change)
        
        avg_change = sum(price_changes) / len(price_changes)
        
        if avg_change > 0.05:  # 5%
            return "high"
        elif avg_change < 0.01:  # 1%
            return "low"
        return "normal"
    except Exception:
        return "normal"


def _enhance_decision_with_social_signal(base_decision: Decision, social_signal: Dict[str, Any]) -> Decision:
    """Enhance decision with social media signal."""
    try:
        if not social_signal:
            return base_decision
            
        # Extract social sentiment
        sentiment = social_signal.get('sentiment', 'neutral')
        confidence_boost = social_signal.get('confidence_boost', 0.0)
        
        # Adjust confidence based on social sentiment
        enhanced_confidence = base_decision.confidence
        
        if sentiment == 'bullish' and base_decision.action_recommended == 'Buy':
            enhanced_confidence += confidence_boost
        elif sentiment == 'bearish' and base_decision.action_recommended == 'Sell':
            enhanced_confidence += confidence_boost
        elif sentiment == 'bearish' and base_decision.action_recommended == 'Buy':
            enhanced_confidence -= confidence_boost * 0.5
        elif sentiment == 'bullish' and base_decision.action_recommended == 'Sell':
            enhanced_confidence -= confidence_boost * 0.5
            
        # Clamp confidence to valid range
        enhanced_confidence = max(0.0, min(1.0, enhanced_confidence))
        
        # Update reason to include social context
        enhanced_reason = f"{base_decision.reason}, social={sentiment}"
        
        return Decision(
            signal=f"{base_decision.signal}_social",
            confidence=enhanced_confidence,
            action_recommended=base_decision.action_recommended,
            reason=enhanced_reason
        )
    except Exception as e:
        logger.warning(f"Error enhancing decision with social signal: {e}")
        return base_decision


def _enhance_decision_with_llm_analysis(base_decision: Decision, llm_analysis: Dict[str, Any]) -> Decision:
    """Enhance decision with LLM analysis."""
    try:
        if not llm_analysis:
            return base_decision
            
        # Extract LLM insights
        sentiment = llm_analysis.get('sentiment', 'neutral')
        confidence_score = llm_analysis.get('confidence_score', 0.5)
        recommendation = llm_analysis.get('recommendation', 'hold')
        
        # Adjust confidence based on LLM analysis
        enhanced_confidence = base_decision.confidence
        
        # If LLM recommendation aligns with technical signal, boost confidence
        if recommendation.lower() == base_decision.action_recommended.lower():
            enhanced_confidence += confidence_score * 0.2
        elif recommendation.lower() != 'hold' and recommendation.lower() != base_decision.action_recommended.lower():
            # Conflicting signals - reduce confidence
            enhanced_confidence -= confidence_score * 0.3
            
        # Clamp confidence to valid range
        enhanced_confidence = max(0.0, min(1.0, enhanced_confidence))
        
        # Update reason to include LLM context
        enhanced_reason = f"{base_decision.reason}, llm={sentiment}"
        
        return Decision(
            signal=f"{base_decision.signal}_llm",
            confidence=enhanced_confidence,
            action_recommended=base_decision.action_recommended,
            reason=enhanced_reason
        )
    except Exception as e:
        logger.warning(f"Error enhancing decision with LLM analysis: {e}")
        return base_decision


def make_decision(tracker, coin_id: str) -> Decision:
    """
    Orchestrate strategy evaluation for a coin and return a Decision.
    Applies regime and volatility gates from config.
    """
    cfg_all = _load_full_config(tracker.config_path)
    per_coin_cfg = (cfg_all.get("tracked_coins") or {}).get(coin_id) or {}
    strat_cfg = per_coin_cfg.get("strategy") or {}
    strat_name = str(
        strat_cfg.get("name")
        or (cfg_all.get("strategy") or {}).get("default_strategy")
        or "mean_reversion"
    )
    strat_params: Dict[str, Any] = strat_cfg.get("params") or {}

    df = _build_df_from_history(tracker, coin_id)
    if df is None or df.empty:
        return Decision(
            signal="no_data",
            confidence=0.0,
            action_recommended="Hold",
            reason="No candles in history",
        )

    # Instantiate and run strategy
    try:
        strategy = get_strategy(strat_name, strat_params)
    except Exception as ex:
        return Decision(
            signal="strategy_error", confidence=0.0, action_recommended="Hold", reason=f"{ex}"
        )

    try:
        signals = strategy.generate_signals(df)
        last_sig = (
            int(signals["signal"].iloc[-1])
            if "signal" in signals.columns and not signals.empty
            else 0
        )
    except Exception as ex:
        return Decision(
            signal="strategy_eval_error", confidence=0.0, action_recommended="Hold", reason=str(ex)
        )

    # Regime filter (EMA fast vs slow) if enabled & available in tracker.history
    regime_ok = True
    use_regime = bool((cfg_all.get("strategy") or {}).get("use_regime_filter", False))
    if use_regime:
        last = (tracker.history.get(coin_id) or {}).get("last") or {}
        ef = last.get("ema_fast")
        es = last.get("ema_slow")
        if ef is None or es is None:
            # If no EMA context, fail safe to neutral
            regime_ok = False
        else:
            if last_sig > 0:
                regime_ok = float(ef) > float(es)
            elif last_sig < 0:
                regime_ok = float(ef) < float(es)

    # Volatility gate using ATR%
    vol_ok = True
    vg = (cfg_all.get("strategy") or {}).get("vol_gate") or {}
    if vg:
        min_atr_pct = vg.get("min_atr_pct")
        max_atr_pct = vg.get("max_atr_pct")
        last = (tracker.history.get(coin_id) or {}).get("last") or {}
        atr_val = last.get("atr")
        close = last.get("close")
        if atr_val is None or close is None or float(close) <= 0:
            vol_ok = False
        else:
            atr_pct = (float(atr_val) / float(close)) * 100.0
            if min_atr_pct is not None and atr_pct < float(min_atr_pct):
                vol_ok = False
            if max_atr_pct is not None and atr_pct > float(max_atr_pct):
                vol_ok = False

    # Decide action
    action = "Hold"
    reason_parts = [f"strat={strat_name}"]
    if last_sig > 0:
        action = "Buy"
        reason_parts.append("signal=buy")
    elif last_sig < 0:
        action = "Sell"
        reason_parts.append("signal=sell")
    else:
        reason_parts.append("signal=flat")

    if not regime_ok:
        action = "Hold"
        reason_parts.append("regime_blocked")
    if not vol_ok:
        action = "Hold"
        reason_parts.append("vol_gate_blocked")

    # Confidence heuristic: base 0.8 if both gates pass and we have a non-zero signal; else low
    confidence = (
        0.8 if (last_sig != 0 and regime_ok and vol_ok) else (0.3 if last_sig != 0 else 0.0)
    )

    base_decision = Decision(
        signal=f"{strat_name}_signal",
        confidence=confidence,
        action_recommended=action,
        reason=",".join(reason_parts),
    )
    
    # Enhanced decision making with social media and LLM
    try:
        # Check if enhanced features are enabled
        enhanced_features = cfg_all.get("enhanced_features", {})
        social_enabled = enhanced_features.get("social_media", {}).get("enabled", False)
        llm_enabled = enhanced_features.get("llm", {}).get("enabled", False)
        
        # For now, use synchronous approach (can be made async later)
        enhanced_decision = base_decision
        
        # TODO: Integrate async social media and LLM analysis
        # This requires making the decision engine async or using a different approach
        # For now, we'll return the base decision
        
        return enhanced_decision
        
    except Exception as e:
        logger.warning(f"Error in enhanced decision making: {e}")
        return base_decision


async def make_enhanced_decision(tracker, coin_id: str, current_price: float) -> Decision:
    """
    Enhanced decision making with social media and LLM integration.
    This is the async version that can incorporate all enhanced features.
    """
    # Get base technical decision
    base_decision = make_decision(tracker, coin_id)
    
    cfg_all = _load_full_config(tracker.config_path)
    enhanced_features = cfg_all.get("enhanced_features", {})
    
    enhanced_decision = base_decision
    
    # Enhance with social media signals
    social_enabled = enhanced_features.get("social_media", {}).get("enabled", False)
    if social_enabled and hasattr(tracker, 'social_integration'):
        try:
            social_signal = await _get_social_media_signal(tracker, coin_id)
            if social_signal:
                enhanced_decision = _enhance_decision_with_social_signal(enhanced_decision, social_signal)
        except Exception as e:
            logger.warning(f"Error enhancing with social media: {e}")
    
    # Enhance with LLM analysis
    llm_enabled = enhanced_features.get("llm", {}).get("enabled", False)
    if llm_enabled and hasattr(tracker, 'market_analyzer'):
        # Check if LLM client is disabled or rate-limited before attempting analysis
        llm_available = True
        if hasattr(tracker.market_analyzer, 'llm_client'):
            llm_client = tracker.market_analyzer.llm_client
            
            # Check if API key is configured
            if not llm_client.config.api_key:
                logger.debug(f"LLM API key not configured, skipping LLM analysis for {coin_id}")
                llm_available = False
            elif llm_client.is_disabled():
                logger.debug(f"LLM client is disabled, skipping LLM analysis for {coin_id}")
                llm_available = False
            elif hasattr(llm_client, 'backoff_until_ts') and llm_client.backoff_until_ts > 0:
                import time
                if time.time() < llm_client.backoff_until_ts:
                    remaining = int(llm_client.backoff_until_ts - time.time())
                    logger.debug(f"LLM is rate-limited, skipping LLM analysis for {coin_id} (backoff: {remaining}s)")
                    llm_available = False
        
        if llm_available:
            try:
                llm_analysis = await _get_llm_analysis(tracker, coin_id, current_price)
                if llm_analysis and not llm_analysis.get("error"):
                    enhanced_decision = _enhance_decision_with_llm_analysis(enhanced_decision, llm_analysis)
                elif llm_analysis and llm_analysis.get("error"):
                    # LLM failed but returned error info - use fallback
                    logger.warning(f"LLM analysis failed for {coin_id}: {llm_analysis.get('error')}")
            except Exception as e:
                logger.warning(f"Error enhancing with LLM: {e}")
    
    return enhanced_decision


async def make_batched_enhanced_decisions(tracker, coins_data: Dict[str, Dict]) -> Dict[str, Decision]:
    """
    Make enhanced decisions for multiple coins using batched LLM analysis.
    
    Args:
        tracker: The CryptoTracker instance
        coins_data: Dict mapping coin_id -> {'current_price': float, 'market_data': dict}
        
    Returns:
        Dict mapping coin_id -> Decision
    """
    from ..llm.batched_analyzer import BatchedLLMAnalyzer
    
    cfg_all = _load_full_config(tracker.config_path)
    enhanced_features = cfg_all.get("enhanced_features", {})
    
    # Get base decisions for all coins
    base_decisions = {}
    for coin_id, coin_data in coins_data.items():
        base_decisions[coin_id] = make_decision(tracker, coin_id)
    
    # Check if LLM is available for batching
    llm_enabled = enhanced_features.get("llm", {}).get("enabled", False)
    if not llm_enabled or not hasattr(tracker, 'market_analyzer'):
        logger.debug("LLM not enabled or market analyzer not available")
        return base_decisions
    
    # Initialize batched analyzer if not exists
    if not hasattr(tracker, 'batched_llm_analyzer'):
        try:
            from ..llm.config_manager import LLMConfigManager
            llm_config_manager = LLMConfigManager(
                tracker.config_manager,
                tracker.config_manager.secrets_manager if hasattr(tracker.config_manager, 'secrets_manager') else None
            )
            tracker.batched_llm_analyzer = BatchedLLMAnalyzer(
                tracker.market_analyzer.llm_client,
                llm_config_manager
            )
        except Exception as e:
            logger.warning(f"Failed to initialize batched LLM analyzer: {e}")
            return base_decisions
    
    # Prepare market data for batch analysis
    batch_market_data = {}
    for coin_id, coin_data in coins_data.items():
        try:
            # Get comprehensive market data
            market_data = await _prepare_comprehensive_market_data(
                tracker, coin_id, coin_data.get('symbol', coin_id.upper()), 
                coin_data.get('current_price', 0.0)
            )
            if market_data:
                batch_market_data[coin_id] = market_data
        except Exception as e:
            logger.warning(f"Failed to prepare market data for {coin_id}: {e}")
    
    if not batch_market_data:
        logger.warning("No market data prepared for batch analysis")
        return base_decisions
    
    # Perform batched LLM analysis
    try:
        batch_result = await tracker.batched_llm_analyzer.analyze_coins_batch(
            batch_market_data, 
            analysis_type="comprehensive"
        )
        
        if batch_result.success and batch_result.coin_analyses:
            # Enhance decisions with LLM analysis
            enhanced_decisions = {}
            for coin_id, base_decision in base_decisions.items():
                if coin_id in batch_result.coin_analyses:
                    llm_analysis = batch_result.coin_analyses[coin_id]
                    enhanced_decision = _enhance_decision_with_llm_analysis(base_decision, llm_analysis)
                    enhanced_decisions[coin_id] = enhanced_decision
                else:
                    enhanced_decisions[coin_id] = base_decision
            return enhanced_decisions
        else:
            logger.warning(f"Batched LLM analysis failed: {batch_result.error}")
            return base_decisions
            
    except Exception as e:
        logger.error(f"Batched enhanced decision making failed: {e}")
        return base_decisions
