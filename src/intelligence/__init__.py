"""
Intelligence System - Tiered Decision Making Architecture

This module implements a hierarchical intelligence system for trading decisions:
- Tier 1: Macro/Crisis Detection (LLM-based)
- Tier 2: Market Intelligence (ML + Alternative Data)
- Tier 3: Tactical Strategies (ML-Enhanced)
- Tier 4: Execution Intelligence (Optimization)
"""

from .orchestrator import IntelligenceOrchestrator
from .models import (
    TradingDecision,
    CrisisStatus,
    CrisisLevel,
    MarketState,
    TacticalSignal,
    ExecutionPlan
)

__all__ = [
    'IntelligenceOrchestrator',
    'TradingDecision',
    'CrisisStatus',
    'CrisisLevel',
    'MarketState',
    'TacticalSignal',
    'ExecutionPlan'
]
