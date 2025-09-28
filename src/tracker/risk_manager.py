"""
Risk management for the crypto tracker.
Handles risk controls, protection mechanisms, and safety checks.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from src.risk import (
    RiskParams,
    compute_stop_levels,
    compute_trailing_stop,
    ATRRiskParams,
    compute_stop_levels_atr,
    compute_trailing_stop_atr,
)
from src.logger import log_event


class RiskManager:
    """Manages risk controls and protection mechanisms."""
    
    def __init__(self, config_manager, portfolio_manager):
        self.config_manager = config_manager
        self.portfolio_manager = portfolio_manager
        
        # Risk parameters
        self.risk = RiskParams()
        self.atr_params: Optional[ATRRiskParams] = None
        self.atr_params_map: Dict[str, ATRRiskParams] = {}
        
        # Protection state
        self._protection: Dict[str, Any] = {}
        self._protection_state_path = Path(config_manager.config_path).parent.parent / 'logs' / 'protection_state.json'
        
        # Execution limits
        self.max_open_positions: int = 999999
        self.per_coin_cooldown_seconds: int = 0
        self.cooloff_max_entries_per_hour: Optional[int] = None
        self.cooloff_seconds: Optional[int] = None
        self._portfolio_cooloff_until: float = 0.0
        
        # Staggered entry controls
        self.stagger_max_per_cycle: int = 1
        self.stagger_spacing_seconds: int = 300
        self._stagger_used_in_cycle: int = 0
        self._stagger_queue: list[Dict[str, Any]] = []
        
        # Position sizing
        self.risk_budget_pct: float = 0.005
        self.max_size_usd: Optional[float] = None
        self.min_size_usd: Optional[float] = None
        
        # Volatility gating
        self.vol_gate_min_atr_pct: Optional[float] = None
        self.vol_gate_max_atr_pct: Optional[float] = None
        
        # Kill switch and safety
        self.safe_mode: bool = False
        self.kill_dd_intraday_pct: Optional[float] = None
        self.kill_max_errors_per_hour: Optional[int] = None
        self.kill_switch_active: bool = False
        
        # Backoff tracking
        self._live_exit_backoff: Dict[str, Dict[str, float]] = {}
        self._breakeven_armed: Dict[str, bool] = {}
        self._live_be_armed: Dict[str, bool] = {}
        self._live_last_trail: Dict[str, float] = {}
        
        self._load_risk_settings()
        self._load_protection_state()
    
    def _load_risk_settings(self):
        """Load risk management settings from configuration."""
        try:
            config_data = self.config_manager.load_full_config()
            risk_config = config_data.get('risk', {})
            execution_config = config_data.get('execution', {})
            
            # Basic risk parameters
            self.risk = RiskParams(
                stop_loss_pct=risk_config.get('stop_loss_pct', 0.03),
                take_profit_pct=risk_config.get('take_profit_pct', 0.06),
                trailing_stop_pct=risk_config.get('trailing_stop_pct', 0.04)
            )
            
            # ATR-based risk parameters
            atr_config = risk_config.get('atr', {})
            if atr_config:
                self.atr_params = ATRRiskParams(
                    period=atr_config.get('period', 14),
                    sl_mult=atr_config.get('sl_mult', 1.5),
                    tp_mult=atr_config.get('tp_mult', 3.0),
                    trail_mult=atr_config.get('trail_mult', 2.0)
                )
            
            # Per-coin ATR parameters
            for coin_id, coin_data in config_data.get('tracked_coins', {}).items():
                coin_risk = coin_data.get('risk', {})
                if coin_risk and 'atr' in coin_risk:
                    atr_cfg = coin_risk['atr']
                    self.atr_params_map[coin_id] = ATRRiskParams(
                        period=atr_cfg.get('period', 14),
                        sl_mult=atr_cfg.get('sl_mult', 1.5),
                        tp_mult=atr_cfg.get('tp_mult', 3.0),
                        trail_mult=atr_cfg.get('trail_mult', 2.0)
                    )
            
            # Execution limits
            self.max_open_positions = execution_config.get('max_open_positions', 999999)
            self.per_coin_cooldown_seconds = execution_config.get('per_coin_cooldown_seconds', 0)
            self.risk_budget_pct = execution_config.get('risk_budget_pct', 0.005)
            self.max_size_usd = execution_config.get('max_size_usd')
            self.min_size_usd = execution_config.get('min_size_usd')
            
            # Cooloff settings
            self.cooloff_max_entries_per_hour = execution_config.get('cooloff_max_entries_per_hour')
            self.cooloff_seconds = execution_config.get('cooloff_seconds')
            
            # Staggered entry settings
            self.stagger_max_per_cycle = execution_config.get('stagger_max_per_cycle', 1)
            self.stagger_spacing_seconds = execution_config.get('stagger_spacing_seconds', 300)
            
            # Volatility gating
            vol_gate = config_data.get('strategy', {}).get('vol_gate', {})
            self.vol_gate_min_atr_pct = vol_gate.get('min_atr_pct')
            self.vol_gate_max_atr_pct = vol_gate.get('max_atr_pct')
            
            # Kill switch settings
            self.kill_dd_intraday_pct = execution_config.get('kill_dd_intraday_pct')
            self.kill_max_errors_per_hour = execution_config.get('kill_max_errors_per_hour')
            
        except Exception as ex:
            log_event('risk_settings_load_error', {'error': str(ex)})
    
    def _load_protection_state(self):
        """Load protection state from disk."""
        try:
            if self._protection_state_path.exists():
                with self._protection_state_path.open('r') as f:
                    self._protection = json.load(f) or {}
        except Exception:
            self._protection = {}
    
    def _save_protection_state(self):
        """Save protection state to disk."""
        try:
            self._protection_state_path.parent.mkdir(parents=True, exist_ok=True)
            with self._protection_state_path.open('w') as f:
                json.dump(self._protection, f)
        except Exception:
            pass
    
    def can_enter_position(self, symbol: str, coin_id: str) -> tuple[bool, str]:
        """Check if we can enter a new position for the given symbol."""
        try:
            # Check max open positions
            current_positions = len(self.portfolio_manager.portfolio.positions)
            if current_positions >= self.max_open_positions:
                return False, "max_positions_exceeded"
            
            # Check if already in position
            if self.portfolio_manager.get_position(symbol) is not None:
                return False, "already_in_position"
            
            # Check cooldown
            if self.per_coin_cooldown_seconds > 0:
                last_entry = self._protection.get(f"{coin_id}_last_entry")
                if last_entry:
                    last_entry_time = datetime.fromisoformat(last_entry)
                    time_since = (datetime.now(timezone.utc) - last_entry_time).total_seconds()
                    if time_since < self.per_coin_cooldown_seconds:
                        return False, "cooldown_active"
            
            # Check portfolio cooloff
            if self.cooloff_max_entries_per_hour:
                now = datetime.now(timezone.utc).timestamp()
                if now < self._portfolio_cooloff_until:
                    return False, "portfolio_cooloff"
            
            # Check staggered entry limits
            if self._stagger_used_in_cycle >= self.stagger_max_per_cycle:
                return False, "stagger_limit"
            
            # Check exposure limits
            portfolio_summary = self.portfolio_manager.get_portfolio_summary({})
            if portfolio_summary['total_exposure'] >= (self.max_size_usd or float('inf')):
                return False, "exposure_limit"
            
            # Check safe mode
            if self.safe_mode or self.kill_switch_active:
                return False, "safe_mode_active"
            
            return True, "ok"
            
        except Exception as ex:
            log_event('risk_check_error', {'symbol': symbol, 'error': str(ex)})
            return False, "error"
    
    def compute_stop_levels_for_symbol(self, symbol: str, current_price: float, coin_id: str, atr_value: Optional[float] = None) -> tuple[Optional[float], Optional[float]]:
        """Compute stop loss and take profit levels for a symbol."""
        try:
            # Get ATR parameters for this coin
            coin_atr_params = self.atr_params_map.get(coin_id, self.atr_params)
            
            # Use ATR-based levels if available
            if coin_atr_params is not None and atr_value is not None and float(atr_value) > 0:
                sl, tp = compute_stop_levels_atr(float(current_price), float(atr_value), coin_atr_params)
                if sl is not None and tp is not None:
                    return sl, tp
            
            # Fallback to percentage-based levels
            return compute_stop_levels(float(current_price), self.risk)
            
        except Exception as ex:
            log_event('stop_levels_error', {'symbol': symbol, 'error': str(ex)})
            return None, None
    
    def compute_trailing_stop_for_symbol(self, symbol: str, peak_price: float) -> Optional[float]:
        """Compute trailing stop level for a symbol."""
        try:
            return compute_trailing_stop(float(peak_price), self.risk)
        except Exception as ex:
            log_event('trailing_stop_error', {'symbol': symbol, 'error': str(ex)})
            return None
    
    def record_position_entry(self, symbol: str, coin_id: str):
        """Record that a position was entered."""
        try:
            now = datetime.now(timezone.utc)
            self._protection[f"{coin_id}_last_entry"] = now.isoformat()
            
            # Update staggered entry tracking
            self._stagger_used_in_cycle += 1
            
            # Update portfolio cooloff if needed
            if self.cooloff_seconds:
                self._portfolio_cooloff_until = now.timestamp() + self.cooloff_seconds
            
            self._save_protection_state()
            
        except Exception as ex:
            log_event('position_entry_record_error', {'symbol': symbol, 'error': str(ex)})
    
    def reset_stagger_cycle(self):
        """Reset staggered entry cycle (called periodically)."""
        self._stagger_used_in_cycle = 0
    
    def check_volatility_gate(self, atr_pct: float) -> bool:
        """Check if volatility is within acceptable range."""
        if self.vol_gate_min_atr_pct is not None and atr_pct < self.vol_gate_min_atr_pct:
            return False
        if self.vol_gate_max_atr_pct is not None and atr_pct > self.vol_gate_max_atr_pct:
            return False
        return True
    
    def get_risk_factor(self) -> float:
        """Get current risk factor (reduced during drawdowns)."""
        return self.portfolio_manager.get_risk_factor()
    
    def is_safe_mode_active(self) -> bool:
        """Check if safe mode or kill switch is active."""
        return self.safe_mode or self.kill_switch_active
    
    def activate_kill_switch(self, reason: str):
        """Activate kill switch to halt trading."""
        self.kill_switch_active = True
        log_event('kill_switch_activated', {'reason': reason})
    
    def deactivate_kill_switch(self):
        """Deactivate kill switch."""
        self.kill_switch_active = False
        log_event('kill_switch_deactivated', {})
