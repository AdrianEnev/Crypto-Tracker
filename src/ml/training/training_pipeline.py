"""
ML Training Pipeline

Orchestrates the training of regime classification and signal enhancement models
using historical data from multiple sources.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import pandas as pd
import numpy as np

from .regime_classifier import RegimeClassifierTrainer, RegimeData, RegimeModel
from .signal_enhancer import SignalEnhancerTrainer, SignalData, SignalModel
from ..hooks import ModelLoader
from ...data_feeds import SocialMediaAggregator
from ...data_feeds.onchain import FreeOnChainAnalyzer


class TrainingPipeline:
    """
    Orchestrates ML model training pipeline.
    
    Features:
    - Automated data collection from multiple sources
    - Model training for regime classification and signal enhancement
    - Model validation and performance evaluation
    - Model deployment and versioning
    - Training job scheduling and monitoring
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        
        # Initialize trainers
        self.regime_trainer = RegimeClassifierTrainer(config.get('regime_classifier', {}))
        self.signal_trainer = SignalEnhancerTrainer(config.get('signal_enhancer', {}))
        
        # Data sources
        self.social_aggregator = None
        self.onchain_analyzer = None
        
        # Training configuration
        self.training_coins = config.get('training_coins', ['bitcoin', 'ethereum'])
        self.timeframes = config.get('timeframes', ['1d', '4h'])
        self.model_types = config.get('model_types', ['random_forest', 'gradient_boosting'])
        
        # Data collection parameters
        self.lookback_days = config.get('lookback_days', 365)
        self.min_data_points = config.get('min_data_points', 100)
        
        # Model storage
        self.models_dir = Path(config.get('models_dir', 'models'))
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Training results
        self.training_results = {}
    
    async def initialize_data_sources(self):
        """Initialize data sources for training."""
        try:
            # Initialize social media aggregator
            social_config = self.config.get('social_media', {})
            if social_config.get('enabled', False):
                self.social_aggregator = SocialMediaAggregator(social_config)
                self.logger.info("Social media aggregator initialized")
            
            # Initialize on-chain analyzer
            onchain_config = self.config.get('onchain', {})
            if onchain_config.get('enabled', False):
                self.onchain_analyzer = FreeOnChainAnalyzer(onchain_config)
                self.logger.info("On-chain analyzer initialized")
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize some data sources: {e}")
    
    async def collect_training_data(
        self, 
        coin_id: str, 
        timeframe: str
    ) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """
        Collect training data from multiple sources.
        
        Args:
            coin_id: Cryptocurrency identifier
            timeframe: Timeframe for data collection
            
        Returns:
            Tuple of (price_data, social_data, onchain_data)
        """
        try:
            # Collect price data (this would need to be implemented based on your data sources)
            price_data = await self._collect_price_data(coin_id, timeframe)
            
            # Collect social data
            social_data = None
            if self.social_aggregator:
                social_data = await self._collect_social_data(coin_id, timeframe)
            
            # Collect on-chain data
            onchain_data = None
            if self.onchain_analyzer:
                onchain_data = await self._collect_onchain_data(coin_id, timeframe)
            
            return price_data, social_data, onchain_data
            
        except Exception as e:
            self.logger.error(f"Failed to collect training data for {coin_id}: {e}")
            raise
    
    async def _collect_price_data(self, coin_id: str, timeframe: str) -> pd.DataFrame:
        """Collect price data for training."""
        # This is a placeholder - you would implement this based on your data sources
        # For now, generate synthetic data for demonstration
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=self.lookback_days)
        
        # Generate synthetic OHLCV data
        dates = pd.date_range(start=start_date, end=end_date, freq='D' if timeframe == '1d' else '4H')
        n_points = len(dates)
        
        # Generate realistic price data
        np.random.seed(42)  # For reproducibility
        returns = np.random.normal(0.001, 0.02, n_points)  # 0.1% daily return, 2% volatility
        prices = 100 * np.exp(np.cumsum(returns))  # Starting price of 100
        
        # Generate OHLCV data
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # Generate realistic OHLC from close price
            volatility = 0.01  # 1% intraday volatility
            high = price * (1 + np.random.uniform(0, volatility))
            low = price * (1 - np.random.uniform(0, volatility))
            open_price = price * (1 + np.random.uniform(-volatility/2, volatility/2))
            volume = np.random.uniform(1000, 10000)
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        self.logger.info(f"Generated {len(df)} price data points for {coin_id} {timeframe}")
        return df
    
    async def _collect_social_data(self, coin_id: str, timeframe: str) -> pd.DataFrame:
        """Collect social sentiment data for training."""
        try:
            # This would collect historical social data
            # For now, generate synthetic data
            
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=self.lookback_days)
            
            dates = pd.date_range(start=start_date, end=end_date, freq='D' if timeframe == '1d' else '4H')
            n_points = len(dates)
            
            # Generate synthetic social sentiment data
            np.random.seed(42)
            sentiment_scores = np.random.normal(0, 0.3, n_points)  # Centered around 0, std 0.3
            sentiment_scores = np.clip(sentiment_scores, -1, 1)  # Clip to [-1, 1]
            
            volumes = np.random.uniform(50, 500, n_points)
            confidences = np.random.uniform(0.3, 0.9, n_points)
            
            data = []
            for date, score, volume, confidence in zip(dates, sentiment_scores, volumes, confidences):
                data.append({
                    'timestamp': date,
                    'sentiment_score': score,
                    'volume': volume,
                    'confidence': confidence
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            
            self.logger.info(f"Generated {len(df)} social data points for {coin_id} {timeframe}")
            return df
            
        except Exception as e:
            self.logger.warning(f"Failed to collect social data: {e}")
            return None
    
    async def _collect_onchain_data(self, coin_id: str, timeframe: str) -> pd.DataFrame:
        """Collect on-chain data for training."""
        try:
            # This would collect historical on-chain data
            # For now, generate synthetic data
            
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=self.lookback_days)
            
            dates = pd.date_range(start=start_date, end=end_date, freq='D' if timeframe == '1d' else '4H')
            n_points = len(dates)
            
            # Generate synthetic on-chain data
            np.random.seed(42)
            exchange_flow = np.random.normal(0, 0.2, n_points)
            whale_activity = np.random.normal(0, 0.3, n_points)
            miner_pressure = np.random.normal(0.5, 0.2, n_points)
            confidence = np.random.uniform(0.4, 0.8, n_points)
            
            data = []
            for date, flow, whale, pressure, conf in zip(dates, exchange_flow, whale_activity, miner_pressure, confidence):
                data.append({
                    'timestamp': date,
                    'exchange_flow_score': flow,
                    'whale_activity_score': whale,
                    'miner_pressure_score': pressure,
                    'confidence': conf
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            
            self.logger.info(f"Generated {len(df)} on-chain data points for {coin_id} {timeframe}")
            return df
            
        except Exception as e:
            self.logger.warning(f"Failed to collect on-chain data: {e}")
            return None
    
    async def train_regime_classifier(
        self, 
        coin_id: str, 
        timeframe: str
    ) -> Optional[RegimeModel]:
        """Train regime classification model for a specific coin and timeframe."""
        try:
            self.logger.info(f"Training regime classifier for {coin_id} {timeframe}")
            
            # Collect training data
            price_data, social_data, onchain_data = await self.collect_training_data(coin_id, timeframe)
            
            if len(price_data) < self.min_data_points:
                self.logger.warning(f"Insufficient data for {coin_id} {timeframe}: {len(price_data)} points")
                return None
            
            # Prepare training data
            regime_data = self.regime_trainer.prepare_training_data(price_data, coin_id, timeframe)
            
            # Train models for each type
            best_model = None
            best_accuracy = 0
            
            for model_type in self.model_types:
                try:
                    model = self.regime_trainer.train_model(regime_data, model_type)
                    
                    if model.accuracy > best_accuracy:
                        best_accuracy = model.accuracy
                        best_model = model
                    
                    # Save model
                    model_path = self.regime_trainer.save_model(model)
                    self.logger.info(f"Regime classifier saved: {model_path}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to train {model_type} regime classifier: {e}")
                    continue
            
            if best_model:
                self.training_results[f'regime_{coin_id}_{timeframe}'] = {
                    'model': best_model,
                    'accuracy': best_accuracy,
                    'training_date': datetime.now(timezone.utc)
                }
            
            return best_model
            
        except Exception as e:
            self.logger.error(f"Failed to train regime classifier for {coin_id} {timeframe}: {e}")
            return None
    
    async def train_signal_enhancer(
        self, 
        coin_id: str, 
        timeframe: str
    ) -> Optional[SignalModel]:
        """Train signal enhancement model for a specific coin and timeframe."""
        try:
            self.logger.info(f"Training signal enhancer for {coin_id} {timeframe}")
            
            # Collect training data
            price_data, social_data, onchain_data = await self.collect_training_data(coin_id, timeframe)
            
            if len(price_data) < self.min_data_points:
                self.logger.warning(f"Insufficient data for {coin_id} {timeframe}: {len(price_data)} points")
                return None
            
            # Prepare training data
            signal_data = self.signal_trainer.prepare_training_data(
                price_data, social_data, onchain_data, coin_id, timeframe
            )
            
            # Train models for each type
            best_model = None
            best_r2 = -float('inf')
            
            for model_type in self.model_types:
                try:
                    model = self.signal_trainer.train_model(signal_data, model_type)
                    
                    if model.r2_score > best_r2:
                        best_r2 = model.r2_score
                        best_model = model
                    
                    # Save model
                    model_path = self.signal_trainer.save_model(model)
                    self.logger.info(f"Signal enhancer saved: {model_path}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to train {model_type} signal enhancer: {e}")
                    continue
            
            if best_model:
                self.training_results[f'signal_{coin_id}_{timeframe}'] = {
                    'model': best_model,
                    'r2_score': best_r2,
                    'training_date': datetime.now(timezone.utc)
                }
            
            return best_model
            
        except Exception as e:
            self.logger.error(f"Failed to train signal enhancer for {coin_id} {timeframe}: {e}")
            return None
    
    async def train_all_models(self) -> Dict[str, Any]:
        """Train all models for all coins and timeframes."""
        try:
            self.logger.info("Starting comprehensive model training")
            
            # Initialize data sources
            await self.initialize_data_sources()
            
            # Train models for each coin and timeframe combination
            for coin_id in self.training_coins:
                for timeframe in self.timeframes:
                    # Train regime classifier
                    regime_model = await self.train_regime_classifier(coin_id, timeframe)
                    
                    # Train signal enhancer
                    signal_model = await self.train_signal_enhancer(coin_id, timeframe)
                    
                    # Small delay between training jobs
                    await asyncio.sleep(1)
            
            # Generate training summary
            summary = self._generate_training_summary()
            
            self.logger.info("Model training completed")
            return summary
            
        except Exception as e:
            self.logger.error(f"Training pipeline failed: {e}")
            raise
    
    def _generate_training_summary(self) -> Dict[str, Any]:
        """Generate training summary report."""
        summary = {
            'training_date': datetime.now(timezone.utc).isoformat(),
            'total_models_trained': len(self.training_results),
            'regime_classifiers': {},
            'signal_enhancers': {},
            'overall_performance': {}
        }
        
        # Organize results by model type
        for key, result in self.training_results.items():
            if key.startswith('regime_'):
                coin_timeframe = key.replace('regime_', '')
                summary['regime_classifiers'][coin_timeframe] = {
                    'accuracy': result['accuracy'],
                    'training_date': result['training_date'].isoformat()
                }
            elif key.startswith('signal_'):
                coin_timeframe = key.replace('signal_', '')
                summary['signal_enhancers'][coin_timeframe] = {
                    'r2_score': result['r2_score'],
                    'training_date': result['training_date'].isoformat()
                }
        
        # Calculate overall performance
        if summary['regime_classifiers']:
            regime_accuracies = [r['accuracy'] for r in summary['regime_classifiers'].values()]
            summary['overall_performance']['avg_regime_accuracy'] = np.mean(regime_accuracies)
            summary['overall_performance']['best_regime_accuracy'] = np.max(regime_accuracies)
        
        if summary['signal_enhancers']:
            signal_r2_scores = [r['r2_score'] for r in summary['signal_enhancers'].values()]
            summary['overall_performance']['avg_signal_r2'] = np.mean(signal_r2_scores)
            summary['overall_performance']['best_signal_r2'] = np.max(signal_r2_scores)
        
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """Get training pipeline statistics."""
        return {
            'training_coins': self.training_coins,
            'timeframes': self.timeframes,
            'model_types': self.model_types,
            'lookback_days': self.lookback_days,
            'min_data_points': self.min_data_points,
            'models_trained': len(self.training_results),
            'regime_trainer_stats': self.regime_trainer.get_stats(),
            'signal_trainer_stats': self.signal_trainer.get_stats()
        }
