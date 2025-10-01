"""
LLM Integration Module

Provides language model integration for enhanced market analysis,
crisis detection, and political/economic event analysis.
"""

from .client import LLMClient, LLMConfig
from .market_analyzer import ComprehensiveMarketAnalyzer
from .crisis_detector import CrisisDetectionLLM
from .political_analyzer import PoliticalEventAnalyzer

__all__ = [
    "LLMClient",
    "LLMConfig", 
    "ComprehensiveMarketAnalyzer",
    "CrisisDetectionLLM",
    "PoliticalEventAnalyzer"
]
