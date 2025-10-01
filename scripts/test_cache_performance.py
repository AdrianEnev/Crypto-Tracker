#!/usr/bin/env python3
"""
Cache Performance Test Script

Tests the smart caching system performance and validates its effectiveness
in reducing API calls and improving response times.
"""

import asyncio
import time
import random
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.social_media.smart_cache import get_global_cache, close_global_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CachePerformanceTester:
    """Test cache performance and effectiveness"""
    
    def __init__(self):
        self.cache = get_global_cache()
        self.test_results = []
    
    async def run_performance_tests(self) -> Dict[str, Any]:
        """Run comprehensive performance tests"""
        logger.info("🚀 Starting cache performance tests")
        
        tests = [
            ("basic_crud", self._test_basic_crud),
            ("concurrent_access", self._test_concurrent_access),
            ("cache_hit_rates", self._test_cache_hit_rates),
            ("memory_pressure", self._test_memory_pressure),
            ("ttl_expiration", self._test_ttl_expiration),
            ("cache_warming", self._test_cache_warming),
            ("multi_backend", self._test_multi_backend)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            logger.info(f"Running test: {test_name}")
            start_time = time.time()
            
            try:
                test_result = await test_func()
                duration = time.time() - start_time
                
                results[test_name] = {
                    "status": "passed",
                    "duration": duration,
                    "result": test_result
                }
                logger.info(f"✅ {test_name} completed in {duration:.2f}s")
                
            except Exception as e:
                duration = time.time() - start_time
                results[test_name] = {
                    "status": "failed",
                    "duration": duration,
                    "error": str(e)
                }
                logger.error(f"❌ {test_name} failed: {e}")
        
        return results
    
    async def _test_basic_crud(self) -> Dict[str, Any]:
        """Test basic cache operations"""
        test_data = {
            "test_string": "Hello, World!",
            "test_number": 42,
            "test_dict": {"key": "value", "nested": {"deep": True}},
            "test_list": [1, 2, 3, 4, 5]
        }
        
        results = {"operations": [], "success_count": 0}
        
        for key, value in test_data.items():
            # Test set
            set_start = time.time()
            success = await self.cache.set("test_source", "test_coin", key, value)
            set_time = time.time() - set_start
            
            # Test get
            get_start = time.time()
            retrieved = await self.cache.get("test_source", "test_coin", key)
            get_time = time.time() - get_start
            
            # Verify
            is_correct = retrieved == value
            if is_correct:
                results["success_count"] += 1
            
            results["operations"].append({
                "key": key,
                "set_time": set_time,
                "get_time": get_time,
                "correct": is_correct
            })
        
        results["success_rate"] = results["success_count"] / len(test_data)
        return results
    
    async def _test_concurrent_access(self) -> Dict[str, Any]:
        """Test concurrent cache access"""
        num_tasks = 50
        tasks = []
        
        async def concurrent_task(task_id: int):
            """Single concurrent task"""
            key = f"concurrent_{task_id}"
            value = f"data_{task_id}"
            
            # Set data
            await self.cache.set("test_source", "test_coin", key, value)
            
            # Get data multiple times
            for _ in range(5):
                retrieved = await self.cache.get("test_source", "test_coin", key)
                if retrieved != value:
                    return False
            
            return True
        
        # Create concurrent tasks
        for i in range(num_tasks):
            tasks.append(concurrent_task(i))
        
        # Run all tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Analyze results
        success_count = sum(1 for r in results if r is True)
        error_count = sum(1 for r in results if isinstance(r, Exception))
        
        return {
            "total_tasks": num_tasks,
            "successful_tasks": success_count,
            "failed_tasks": error_count,
            "duration": duration,
            "tasks_per_second": num_tasks / duration,
            "success_rate": success_count / num_tasks
        }
    
    async def _test_cache_hit_rates(self) -> Dict[str, Any]:
        """Test cache hit rates with different access patterns"""
        # Clear cache first
        await self.cache.clear_all()
        
        test_keys = [f"hit_test_{i}" for i in range(20)]
        test_values = [f"value_{i}" for i in range(20)]
        
        # Initial population
        for key, value in zip(test_keys, test_values):
            await self.cache.set("test_source", "test_coin", key, value)
        
        # Test different access patterns
        patterns = {
            "sequential": test_keys,
            "random": random.sample(test_keys, len(test_keys)),
            "repeated": test_keys[:5] * 4,  # Repeat first 5 keys 4 times
            "mixed": test_keys + random.sample(test_keys, 10)
        }
        
        results = {}
        
        for pattern_name, keys in patterns.items():
            # Reset cache stats
            await self.cache.clear_all()
            
            # Repopulate
            for key, value in zip(test_keys, test_values):
                await self.cache.set("test_source", "test_coin", key, value)
            
            # Access pattern
            start_time = time.time()
            for key in keys:
                await self.cache.get("test_source", "test_coin", key)
            duration = time.time() - start_time
            
            # Get stats
            stats = self.cache.get_stats()
            
            results[pattern_name] = {
                "access_count": len(keys),
                "unique_keys": len(set(keys)),
                "hit_rate": stats["hit_rate"],
                "duration": duration,
                "avg_response_time": stats["avg_response_time"]
            }
        
        return results
    
    async def _test_memory_pressure(self) -> Dict[str, Any]:
        """Test cache behavior under memory pressure"""
        # Fill cache with large data
        large_data_size = 1000  # 1000 entries
        large_data = []
        
        start_time = time.time()
        
        for i in range(large_data_size):
            # Create data of varying sizes
            data_size = random.randint(100, 1000)  # 100-1000 bytes
            data = "x" * data_size
            
            await self.cache.set("test_source", f"coin_{i}", "large_data", data)
            large_data.append(f"coin_{i}")
        
        fill_time = time.time() - start_time
        
        # Test access to random entries
        access_times = []
        for _ in range(100):
            coin_id = random.choice(large_data)
            start = time.time()
            await self.cache.get("test_source", coin_id, "large_data")
            access_times.append(time.time() - start)
        
        # Get final stats
        stats = self.cache.get_stats()
        
        return {
            "entries_created": large_data_size,
            "fill_time": fill_time,
            "avg_access_time": sum(access_times) / len(access_times),
            "max_access_time": max(access_times),
            "min_access_time": min(access_times),
            "memory_cache_size": stats["memory_size"],
            "disk_cache_size": stats["disk_size"],
            "hit_rate": stats["hit_rate"]
        }
    
    async def _test_ttl_expiration(self) -> Dict[str, Any]:
        """Test TTL expiration behavior"""
        # Set data with short TTL
        short_ttl = 1  # 1 second
        await self.cache.set("test_source", "test_coin", "short_ttl", "test_data", custom_ttl=short_ttl)
        
        # Verify immediate access
        immediate = await self.cache.get("test_source", "test_coin", "short_ttl")
        
        # Wait for expiration
        await asyncio.sleep(short_ttl + 0.1)
        
        # Verify expiration
        expired = await self.cache.get("test_source", "test_coin", "short_ttl")
        
        return {
            "immediate_access": immediate == "test_data",
            "expired_access": expired is None,
            "ttl_respected": immediate == "test_data" and expired is None
        }
    
    async def _test_cache_warming(self) -> Dict[str, Any]:
        """Test cache warming functionality"""
        # Mock fetch function
        async def mock_fetch(coin_id: str, data_type: str, params: Dict[str, Any] = None):
            await asyncio.sleep(0.01)  # Simulate API call
            return f"data_for_{coin_id}_{data_type}"
        
        # Test warming
        coins = ["bitcoin", "ethereum", "solana"]
        data_types = ["social_volume", "sentiment_score"]
        
        start_time = time.time()
        await self.cache.warm_cache("test_source", "bitcoin", data_types, mock_fetch)
        warm_time = time.time() - start_time
        
        # Verify warmed data
        verification_results = []
        for data_type in data_types:
            cached = await self.cache.get("test_source", "bitcoin", data_type)
            verification_results.append(cached is not None)
        
        return {
            "warm_time": warm_time,
            "data_types_warmed": len(data_types),
            "verification_success": all(verification_results),
            "warming_tasks_active": len(self.cache.warming_tasks)
        }
    
    async def _test_multi_backend(self) -> Dict[str, Any]:
        """Test multi-backend cache behavior"""
        test_key = "multi_backend_test"
        test_value = "test_data"
        
        # Set data
        await self.cache.set("test_source", "test_coin", test_key, test_value)
        
        # Test memory backend
        memory_result = await self.cache.memory_backend.get(test_key)
        
        # Test disk backend
        disk_result = await self.cache.disk_backend.get(test_key)
        
        # Test Redis backend (if available)
        redis_result = None
        if self.cache.redis_backend:
            try:
                redis_data = await self.cache.redis_backend.get(test_key)
                if redis_data:
                    import pickle
                    redis_entry = pickle.loads(redis_data)
                    redis_result = redis_entry.data
            except Exception as e:
                logger.warning(f"Redis test failed: {e}")
        
        return {
            "memory_backend": memory_result is not None,
            "disk_backend": disk_result is not None,
            "redis_backend": redis_result is not None,
            "redis_available": self.cache.redis_backend is not None,
            "all_backends_working": all([
                memory_result is not None,
                disk_result is not None,
                redis_result is not None if self.cache.redis_backend else True
            ])
        }
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive test report"""
        report = []
        report.append("📊 Cache Performance Test Report")
        report.append("=" * 50)
        report.append(f"Test Date: {datetime.now().isoformat()}")
        report.append("")
        
        # Overall summary
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r["status"] == "passed")
        failed_tests = total_tests - passed_tests
        
        report.append("📈 Overall Summary")
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Passed: {passed_tests}")
        report.append(f"Failed: {failed_tests}")
        report.append(f"Success Rate: {passed_tests/total_tests:.1%}")
        report.append("")
        
        # Individual test results
        report.append("🔍 Individual Test Results")
        report.append("-" * 30)
        
        for test_name, result in results.items():
            status_icon = "✅" if result["status"] == "passed" else "❌"
            report.append(f"{status_icon} {test_name}: {result['duration']:.2f}s")
            
            if result["status"] == "failed":
                report.append(f"   Error: {result['error']}")
            else:
                # Add key metrics for each test
                test_result = result["result"]
                if isinstance(test_result, dict):
                    if "success_rate" in test_result:
                        report.append(f"   Success Rate: {test_result['success_rate']:.1%}")
                    if "hit_rate" in test_result:
                        report.append(f"   Hit Rate: {test_result['hit_rate']:.1%}")
                    if "avg_response_time" in test_result:
                        report.append(f"   Avg Response Time: {test_result['avg_response_time']:.4f}s")
        
        report.append("")
        
        # Performance recommendations
        report.append("💡 Performance Recommendations")
        report.append("-" * 30)
        
        # Analyze results and provide recommendations
        avg_duration = sum(r["duration"] for r in results.values()) / len(results)
        if avg_duration > 1.0:
            report.append("• Consider optimizing cache operations - average test duration is high")
        
        # Check hit rates
        hit_rate_tests = [r for r in results.values() if "hit_rate" in str(r.get("result", {}))]
        if hit_rate_tests:
            avg_hit_rate = sum(r["result"].get("hit_rate", 0) for r in hit_rate_tests) / len(hit_rate_tests)
            if avg_hit_rate < 0.7:
                report.append("• Low hit rates detected - consider increasing cache TTL or implementing cache warming")
        
        # Check concurrent performance
        concurrent_result = results.get("concurrent_access", {})
        if concurrent_result.get("status") == "passed":
            tasks_per_second = concurrent_result["result"].get("tasks_per_second", 0)
            if tasks_per_second < 100:
                report.append("• Low concurrent throughput - consider optimizing cache backend")
        
        if not report[-1].startswith("•"):
            report.append("• All performance metrics are within acceptable ranges")
        
        return "\n".join(report)


async def main():
    """Main test execution"""
    parser = argparse.ArgumentParser(description="Cache Performance Tester")
    parser.add_argument("--output", help="Output file for test results")
    parser.add_argument("--report-only", action="store_true", help="Only generate report")
    
    args = parser.parse_args()
    
    tester = CachePerformanceTester()
    
    try:
        if not args.report_only:
            logger.info("Starting cache performance tests...")
            results = await tester.run_performance_tests()
            
            # Save results
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                logger.info(f"Test results saved to {args.output}")
            
            # Generate and print report
            report = tester.generate_report(results)
            print(report)
            
        else:
            # Load existing results and generate report
            if args.output and Path(args.output).exists():
                with open(args.output, 'r') as f:
                    results = json.load(f)
                report = tester.generate_report(results)
                print(report)
            else:
                logger.error("No existing results file found for report generation")
                sys.exit(1)
    
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)
    
    finally:
        await close_global_cache()


if __name__ == "__main__":
    asyncio.run(main())
