#!/usr/bin/env python3
"""
Cache Management and Monitoring Script

Provides tools for monitoring cache performance, managing cache data,
and optimizing cache settings for the social media integration.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.social_media.smart_cache import get_global_cache, close_global_cache
from src.social_media.config import SocialMediaConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheManager:
    """Cache management and monitoring utilities"""
    
    def __init__(self):
        self.cache = get_global_cache()
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        stats = self.cache.get_stats()
        
        # Add additional metrics
        stats.update({
            "timestamp": datetime.now().isoformat(),
            "cache_backends": {
                "memory": await self.cache.memory_backend.size(),
                "disk": await self.cache.disk_backend.size(),
                "redis": "enabled" if self.cache.redis_backend else "disabled"
            }
        })
        
        return stats
    
    async def clear_cache(self, source: str = None, coin_id: str = None, 
                         data_type: str = None) -> int:
        """Clear cache entries matching criteria"""
        if source and coin_id and data_type:
            return await self.cache.invalidate(source, coin_id, data_type)
        else:
            await self.cache.clear_all()
            return -1  # Indicates full clear
    
    async def warm_cache(self, coins: List[str], data_types: List[str]):
        """Warm cache with common data"""
        logger.info(f"Warming cache for {len(coins)} coins and {len(data_types)} data types")
        
        # This would integrate with actual data sources
        # For now, we'll just log the intention
        for coin_id in coins:
            for data_type in data_types:
                logger.info(f"Would warm cache for {coin_id}:{data_type}")
    
    async def analyze_cache_performance(self) -> Dict[str, Any]:
        """Analyze cache performance and provide recommendations"""
        stats = await self.get_cache_stats()
        
        analysis = {
            "hit_rate_analysis": self._analyze_hit_rate(stats["hit_rate"]),
            "response_time_analysis": self._analyze_response_time(stats["avg_response_time"]),
            "size_analysis": self._analyze_cache_size(stats),
            "recommendations": []
        }
        
        # Generate recommendations
        if stats["hit_rate"] < 0.7:
            analysis["recommendations"].append(
                "Low hit rate detected. Consider increasing cache TTL or implementing cache warming."
            )
        
        if stats["avg_response_time"] > 0.1:
            analysis["recommendations"].append(
                "High response time detected. Consider optimizing cache backend or reducing cache size."
            )
        
        if stats["memory_size"] > 8000:  # 80% of default max
            analysis["recommendations"].append(
                "Memory cache near capacity. Consider increasing memory cache size or implementing LRU eviction."
            )
        
        return analysis
    
    def _analyze_hit_rate(self, hit_rate: float) -> Dict[str, Any]:
        """Analyze cache hit rate"""
        if hit_rate >= 0.9:
            return {"status": "excellent", "message": "Hit rate is excellent"}
        elif hit_rate >= 0.7:
            return {"status": "good", "message": "Hit rate is good"}
        elif hit_rate >= 0.5:
            return {"status": "fair", "message": "Hit rate is fair, room for improvement"}
        else:
            return {"status": "poor", "message": "Hit rate is poor, needs optimization"}
    
    def _analyze_response_time(self, avg_response_time: float) -> Dict[str, Any]:
        """Analyze average response time"""
        if avg_response_time <= 0.01:
            return {"status": "excellent", "message": "Response time is excellent"}
        elif avg_response_time <= 0.05:
            return {"status": "good", "message": "Response time is good"}
        elif avg_response_time <= 0.1:
            return {"status": "fair", "message": "Response time is fair"}
        else:
            return {"status": "poor", "message": "Response time is poor, needs optimization"}
    
    def _analyze_cache_size(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cache size utilization"""
        memory_size = stats["memory_size"]
        disk_size = stats["disk_size"]
        
        return {
            "memory_utilization": f"{memory_size} entries",
            "disk_utilization": f"{disk_size} entries",
            "status": "normal" if memory_size < 8000 else "high"
        }
    
    async def export_cache_data(self, output_file: str):
        """Export cache data for analysis"""
        stats = await self.get_cache_stats()
        analysis = await self.analyze_cache_performance()
        
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "analysis": analysis,
            "cache_config": {
                "memory_size": self.cache.memory_backend.max_size,
                "disk_cache_dir": str(self.cache.disk_backend.cache_dir),
                "disk_size_mb": self.cache.disk_backend.max_size_bytes // (1024 * 1024),
                "redis_enabled": self.cache.redis_backend is not None
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Cache data exported to {output_file}")
    
    async def optimize_cache_settings(self) -> Dict[str, Any]:
        """Suggest optimal cache settings based on usage patterns"""
        stats = await self.get_cache_stats()
        
        recommendations = {
            "memory_cache_size": self.cache.memory_backend.max_size,
            "disk_cache_size_mb": self.cache.disk_backend.max_size_bytes // (1024 * 1024),
            "suggested_changes": []
        }
        
        # Analyze and suggest changes
        if stats["hit_rate"] < 0.6:
            # Increase memory cache size
            new_size = min(self.cache.memory_backend.max_size * 2, 20000)
            recommendations["suggested_changes"].append({
                "setting": "memory_cache_size",
                "current": self.cache.memory_backend.max_size,
                "suggested": new_size,
                "reason": "Low hit rate, increase memory cache size"
            })
        
        if stats["avg_response_time"] > 0.05:
            # Enable Redis if not already enabled
            if not self.cache.redis_backend:
                recommendations["suggested_changes"].append({
                    "setting": "redis_cache",
                    "current": "disabled",
                    "suggested": "enabled",
                    "reason": "High response time, enable Redis for better performance"
                })
        
        return recommendations


async def main():
    """Main CLI interface for cache management"""
    parser = argparse.ArgumentParser(description="Cache Management and Monitoring")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show cache statistics")
    stats_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear cache")
    clear_parser.add_argument("--source", help="Clear specific source")
    clear_parser.add_argument("--coin", help="Clear specific coin")
    clear_parser.add_argument("--data-type", help="Clear specific data type")
    clear_parser.add_argument("--all", action="store_true", help="Clear all cache")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze cache performance")
    analyze_parser.add_argument("--output", help="Output file for analysis")
    
    # Warm command
    warm_parser = subparsers.add_parser("warm", help="Warm cache with common data")
    warm_parser.add_argument("--coins", nargs="+", default=["bitcoin", "ethereum"], 
                           help="Coins to warm cache for")
    warm_parser.add_argument("--data-types", nargs="+", 
                           default=["social_volume", "sentiment_score"], 
                           help="Data types to warm")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export cache data")
    export_parser.add_argument("output_file", help="Output file path")
    
    # Optimize command
    optimize_parser = subparsers.add_parser("optimize", help="Suggest cache optimizations")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cache_manager = CacheManager()
    
    try:
        if args.command == "stats":
            stats = await cache_manager.get_cache_stats()
            if args.json:
                print(json.dumps(stats, indent=2))
            else:
                print("📊 Cache Statistics")
                print("=" * 50)
                print(f"Hit Rate: {stats['hit_rate']:.2%}")
                print(f"Total Requests: {stats['total_requests']}")
                print(f"Cache Hits: {stats['hits']}")
                print(f"Cache Misses: {stats['misses']}")
                print(f"Avg Response Time: {stats['avg_response_time']:.4f}s")
                print(f"Memory Cache Size: {stats['memory_size']} entries")
                print(f"Disk Cache Size: {stats['disk_size']} entries")
                print(f"Warming Tasks: {stats['warming_tasks']}")
        
        elif args.command == "clear":
            if args.all:
                cleared = await cache_manager.clear_cache()
                print(f"✅ Cleared all cache entries")
            else:
                cleared = await cache_manager.clear_cache(args.source, args.coin, args.data_type)
                print(f"✅ Cleared {cleared} cache entries")
        
        elif args.command == "analyze":
            analysis = await cache_manager.analyze_cache_performance()
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(analysis, f, indent=2)
                print(f"📈 Analysis saved to {args.output}")
            else:
                print("📈 Cache Performance Analysis")
                print("=" * 50)
                print(f"Hit Rate: {analysis['hit_rate_analysis']['status']} - {analysis['hit_rate_analysis']['message']}")
                print(f"Response Time: {analysis['response_time_analysis']['status']} - {analysis['response_time_analysis']['message']}")
                print(f"Cache Size: {analysis['size_analysis']['status']}")
                if analysis['recommendations']:
                    print("\n💡 Recommendations:")
                    for rec in analysis['recommendations']:
                        print(f"  • {rec}")
        
        elif args.command == "warm":
            await cache_manager.warm_cache(args.coins, args.data_types)
            print(f"🔥 Cache warming initiated for {len(args.coins)} coins")
        
        elif args.command == "export":
            await cache_manager.export_cache_data(args.output_file)
            print(f"📁 Cache data exported to {args.output_file}")
        
        elif args.command == "optimize":
            recommendations = await cache_manager.optimize_cache_settings()
            print("⚙️ Cache Optimization Recommendations")
            print("=" * 50)
            print(f"Current Memory Cache Size: {recommendations['memory_cache_size']}")
            print(f"Current Disk Cache Size: {recommendations['disk_cache_size_mb']} MB")
            
            if recommendations['suggested_changes']:
                print("\n💡 Suggested Changes:")
                for change in recommendations['suggested_changes']:
                    print(f"  • {change['setting']}: {change['current']} → {change['suggested']}")
                    print(f"    Reason: {change['reason']}")
            else:
                print("\n✅ No optimization needed - cache settings are optimal")
    
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        sys.exit(1)
    
    finally:
        await close_global_cache()


if __name__ == "__main__":
    asyncio.run(main())
