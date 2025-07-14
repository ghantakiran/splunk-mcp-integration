"""
Performance tests for the rate limiting system

Tests the performance characteristics of rate limiting under various load conditions,
concurrent access patterns, and stress scenarios.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple
from unittest.mock import Mock

import pytest

from app.core.rate_limiting import (
    RateLimitAlgorithm,
    RateLimitScope,
    RateLimitPolicy,
    RateLimitManager,
    FixedWindowRateLimiter,
    SlidingWindowRateLimiter,
    TokenBucketRateLimiter
)


class TestRateLimitingPerformance:
    """Performance tests for rate limiting algorithms"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_fixed_window_performance(self, redis_client):
        """Test fixed window algorithm performance under load"""
        limiter = FixedWindowRateLimiter(redis_client)
        
        async def make_request(request_id: int) -> Tuple[bool, float]:
            start_time = time.time()
            allowed, status = await limiter.check_limit(f"perf_test_{request_id % 10}", 100, 60)
            end_time = time.time()
            return allowed, end_time - start_time
        
        # Run concurrent requests
        start_time = time.time()
        tasks = [make_request(i) for i in range(1000)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze results
        allowed_count = sum(1 for allowed, _ in results if allowed)
        response_times = [rt for _, rt in results]
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        # Performance assertions
        assert total_time < 10.0, f"Total time {total_time}s too slow"
        assert avg_response_time < 0.01, f"Average response time {avg_response_time}s too slow"
        assert max_response_time < 0.1, f"Max response time {max_response_time}s too slow"
        assert allowed_count > 900, f"Too many requests denied: {1000 - allowed_count}"
        
        print(f"Fixed Window Performance:")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Requests/sec: {1000/total_time:.1f}")
        print(f"  Avg response time: {avg_response_time*1000:.2f}ms")
        print(f"  Max response time: {max_response_time*1000:.2f}ms")
        print(f"  Success rate: {allowed_count/10:.1f}%")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sliding_window_performance(self, redis_client):
        """Test sliding window algorithm performance under load"""
        limiter = SlidingWindowRateLimiter(redis_client)
        
        async def make_request(request_id: int) -> Tuple[bool, float]:
            start_time = time.time()
            allowed, status = await limiter.check_limit(f"sliding_perf_{request_id % 5}", 50, 60)
            end_time = time.time()
            return allowed, end_time - start_time
        
        # Run concurrent requests
        start_time = time.time()
        tasks = [make_request(i) for i in range(500)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze results
        allowed_count = sum(1 for allowed, _ in results if allowed)
        response_times = [rt for _, rt in results]
        avg_response_time = sum(response_times) / len(response_times)
        
        # Performance assertions (sliding window is more expensive)
        assert total_time < 15.0, f"Total time {total_time}s too slow"
        assert avg_response_time < 0.02, f"Average response time {avg_response_time}s too slow"
        assert allowed_count > 200, f"Too many requests denied: {500 - allowed_count}"
        
        print(f"Sliding Window Performance:")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Requests/sec: {500/total_time:.1f}")
        print(f"  Avg response time: {avg_response_time*1000:.2f}ms")
        print(f"  Success rate: {allowed_count/5:.1f}%")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_token_bucket_performance(self, redis_client):
        """Test token bucket algorithm performance under load"""
        limiter = TokenBucketRateLimiter(redis_client)
        
        async def make_request(request_id: int) -> Tuple[bool, float]:
            start_time = time.time()
            allowed, status = await limiter.check_limit(
                f"bucket_perf_{request_id % 3}", 100, 60, burst_limit=150, refill_rate=2.0
            )
            end_time = time.time()
            return allowed, end_time - start_time
        
        # Run concurrent requests
        start_time = time.time()
        tasks = [make_request(i) for i in range(300)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze results
        allowed_count = sum(1 for allowed, _ in results if allowed)
        response_times = [rt for _, rt in results]
        avg_response_time = sum(response_times) / len(response_times)
        
        # Performance assertions
        assert total_time < 10.0, f"Total time {total_time}s too slow"
        assert avg_response_time < 0.02, f"Average response time {avg_response_time}s too slow"
        assert allowed_count > 250, f"Too many requests denied: {300 - allowed_count}"
        
        print(f"Token Bucket Performance:")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Requests/sec: {300/total_time:.1f}")
        print(f"  Avg response time: {avg_response_time*1000:.2f}ms")
        print(f"  Success rate: {allowed_count/3:.1f}%")


class TestRateLimitManagerPerformance:
    """Performance tests for rate limit manager"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_manager_concurrent_requests(self, redis_client):
        """Test rate limit manager performance with concurrent requests"""
        manager = RateLimitManager(redis_client)
        
        # Add a custom policy for testing
        test_policy = RateLimitPolicy(
            name="performance_test",
            algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            scope=RateLimitScope.PER_IP,
            limit=1000,
            window_seconds=60,
            priority=1
        )
        manager.add_policy(test_policy)
        
        async def make_request(request_id: int) -> Tuple[bool, float, int]:
            request = Mock()
            request.client.host = f"192.168.1.{request_id % 256}"
            request.url.path = "/api/v1/test"
            request.method = "GET"
            
            start_time = time.time()
            allowed, statuses = await manager.check_rate_limits(request, user_id=f"user_{request_id % 100}")
            end_time = time.time()
            
            return allowed, end_time - start_time, len(statuses)
        
        # Run high concurrency test
        start_time = time.time()
        tasks = [make_request(i) for i in range(2000)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze results
        allowed_count = sum(1 for allowed, _, _ in results if allowed)
        response_times = [rt for _, rt, _ in results]
        status_counts = [sc for _, _, sc in results]
        
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        avg_status_count = sum(status_counts) / len(status_counts)
        
        # Performance assertions
        assert total_time < 20.0, f"Total time {total_time}s too slow"
        assert avg_response_time < 0.02, f"Average response time {avg_response_time}s too slow"
        assert max_response_time < 0.5, f"Max response time {max_response_time}s too slow"
        assert allowed_count > 1800, f"Too many requests denied: {2000 - allowed_count}"
        assert avg_status_count > 0, "No status objects returned"
        
        print(f"Manager Concurrent Requests Performance:")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Requests/sec: {2000/total_time:.1f}")
        print(f"  Avg response time: {avg_response_time*1000:.2f}ms")
        print(f"  Max response time: {max_response_time*1000:.2f}ms")
        print(f"  Success rate: {allowed_count/20:.1f}%")
        print(f"  Avg policies checked: {avg_status_count:.1f}")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_manager_multiple_policies(self, redis_client):
        """Test performance with multiple active policies"""
        manager = RateLimitManager(redis_client)
        
        # Add multiple test policies
        for i in range(10):
            policy = RateLimitPolicy(
                name=f"perf_policy_{i}",
                algorithm=RateLimitAlgorithm.FIXED_WINDOW,
                scope=RateLimitScope.PER_IP,
                limit=100 + i * 10,
                window_seconds=60,
                priority=i + 1
            )
            manager.add_policy(policy)
        
        async def make_request(request_id: int) -> Tuple[bool, float]:
            request = Mock()
            request.client.host = f"10.0.{request_id % 256}.{(request_id // 256) % 256}"
            request.url.path = "/api/v1/test"
            request.method = "GET"
            
            start_time = time.time()
            allowed, statuses = await manager.check_rate_limits(request)
            end_time = time.time()
            
            return allowed, end_time - start_time
        
        # Test with multiple policies
        start_time = time.time()
        tasks = [make_request(i) for i in range(1000)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze results
        allowed_count = sum(1 for allowed, _ in results if allowed)
        response_times = [rt for _, rt in results]
        avg_response_time = sum(response_times) / len(response_times)
        
        # Performance should still be good with multiple policies
        assert total_time < 15.0, f"Total time {total_time}s too slow with multiple policies"
        assert avg_response_time < 0.03, f"Average response time {avg_response_time}s too slow"
        assert allowed_count > 900, f"Too many requests denied with multiple policies"
        
        print(f"Multiple Policies Performance:")
        print(f"  Total policies: {len(manager.policies)}")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Requests/sec: {1000/total_time:.1f}")
        print(f"  Avg response time: {avg_response_time*1000:.2f}ms")
        print(f"  Success rate: {allowed_count/10:.1f}%")


class TestRateLimitingMemoryUsage:
    """Test memory usage characteristics of rate limiting"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_redis_memory_usage(self, redis_client):
        """Test Redis memory usage patterns"""
        limiter = FixedWindowRateLimiter(redis_client)
        
        # Get initial memory usage
        info = await redis_client.info("memory")
        initial_memory = info.get("used_memory", 0)
        
        # Generate many unique keys
        for i in range(10000):
            await limiter.check_limit(f"memory_test_key_{i}", 100, 60)
        
        # Check memory usage after operations
        info = await redis_client.info("memory")
        final_memory = info.get("used_memory", 0)
        memory_increase = final_memory - initial_memory
        
        # Memory usage should be reasonable
        assert memory_increase < 10 * 1024 * 1024, f"Memory usage too high: {memory_increase} bytes"
        
        print(f"Redis Memory Usage:")
        print(f"  Initial memory: {initial_memory:,} bytes")
        print(f"  Final memory: {final_memory:,} bytes")
        print(f"  Increase: {memory_increase:,} bytes")
        print(f"  Per key: {memory_increase/10000:.1f} bytes")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sliding_window_memory_efficiency(self, redis_client):
        """Test sliding window memory usage with many requests"""
        limiter = SlidingWindowRateLimiter(redis_client)
        
        # Simulate requests over time for sliding window
        for batch in range(50):
            tasks = []
            for i in range(20):
                task = limiter.check_limit(f"sliding_memory_{i % 5}", 100, 3600)
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            # Small delay to spread requests over time
            await asyncio.sleep(0.01)
        
        # Check memory usage
        info = await redis_client.info("memory")
        memory_usage = info.get("used_memory", 0)
        
        # Memory should be reasonable for sliding window
        assert memory_usage < 5 * 1024 * 1024, f"Sliding window memory too high: {memory_usage} bytes"
        
        print(f"Sliding Window Memory Usage: {memory_usage:,} bytes")


class TestRateLimitingScalability:
    """Test scalability characteristics"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_high_concurrency_scaling(self, redis_client):
        """Test scaling with very high concurrency"""
        manager = RateLimitManager(redis_client)
        
        # Test with increasing concurrency levels
        concurrency_levels = [100, 500, 1000, 2000]
        results = {}
        
        for concurrency in concurrency_levels:
            async def make_request(request_id: int) -> bool:
                request = Mock()
                request.client.host = f"172.16.{request_id % 256}.{(request_id // 256) % 256}"
                request.url.path = "/api/v1/test"
                request.method = "GET"
                
                allowed, _ = await manager.check_rate_limits(request)
                return allowed
            
            start_time = time.time()
            tasks = [make_request(i) for i in range(concurrency)]
            concurrent_results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            duration = end_time - start_time
            throughput = concurrency / duration
            success_rate = sum(concurrent_results) / len(concurrent_results)
            
            results[concurrency] = {
                "duration": duration,
                "throughput": throughput,
                "success_rate": success_rate
            }
            
            # Basic performance requirements
            assert duration < 30.0, f"Duration too long for {concurrency} requests: {duration}s"
            assert success_rate > 0.8, f"Success rate too low: {success_rate}"
            
            print(f"Concurrency {concurrency}:")
            print(f"  Duration: {duration:.3f}s")
            print(f"  Throughput: {throughput:.1f} req/s")
            print(f"  Success rate: {success_rate:.1%}")
        
        # Check that performance doesn't degrade too much with increased load
        base_throughput = results[100]["throughput"]
        high_throughput = results[2000]["throughput"]
        degradation = (base_throughput - high_throughput) / base_throughput
        
        assert degradation < 0.5, f"Performance degradation too high: {degradation:.1%}"
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_burst_traffic_handling(self, redis_client):
        """Test handling of burst traffic patterns"""
        limiter = TokenBucketRateLimiter(redis_client)
        
        # Simulate burst traffic pattern
        burst_sizes = [10, 50, 100, 200]
        
        for burst_size in burst_sizes:
            # Send burst of requests
            start_time = time.time()
            tasks = []
            for i in range(burst_size):
                task = limiter.check_limit(
                    f"burst_test_{burst_size}", 
                    100, 60, 
                    burst_limit=150, 
                    refill_rate=2.0
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            burst_duration = time.time() - start_time
            
            allowed_count = sum(1 for allowed, _ in results if allowed)
            success_rate = allowed_count / burst_size
            
            # Token bucket should handle reasonable bursts well
            if burst_size <= 150:  # Within burst limit
                assert success_rate > 0.9, f"Poor burst handling for size {burst_size}: {success_rate}"
            
            print(f"Burst size {burst_size}:")
            print(f"  Duration: {burst_duration:.3f}s")
            print(f"  Success rate: {success_rate:.1%}")
            print(f"  Allowed: {allowed_count}/{burst_size}")
            
            # Wait for some token refill
            await asyncio.sleep(1.0)


class TestRateLimitingStress:
    """Stress tests for rate limiting system"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sustained_load(self, redis_client):
        """Test sustained load over time"""
        manager = RateLimitManager(redis_client)
        
        # Run sustained load for 30 seconds
        duration = 30
        requests_per_second = 100
        total_requests = 0
        total_allowed = 0
        start_time = time.time()
        
        while time.time() - start_time < duration:
            batch_start = time.time()
            
            # Send batch of requests
            async def make_request(i: int) -> bool:
                request = Mock()
                request.client.host = f"10.1.{i % 256}.{(i // 256) % 256}"
                request.url.path = "/api/v1/test"
                request.method = "GET"
                
                allowed, _ = await manager.check_rate_limits(request)
                return allowed
            
            batch_size = requests_per_second // 10  # 10 batches per second
            tasks = [make_request(total_requests + i) for i in range(batch_size)]
            batch_results = await asyncio.gather(*tasks)
            
            total_requests += batch_size
            total_allowed += sum(batch_results)
            
            # Maintain rate
            batch_duration = time.time() - batch_start
            target_batch_duration = 0.1  # 100ms per batch
            if batch_duration < target_batch_duration:
                await asyncio.sleep(target_batch_duration - batch_duration)
        
        actual_duration = time.time() - start_time
        actual_rate = total_requests / actual_duration
        success_rate = total_allowed / total_requests
        
        print(f"Sustained Load Test:")
        print(f"  Duration: {actual_duration:.1f}s")
        print(f"  Total requests: {total_requests}")
        print(f"  Actual rate: {actual_rate:.1f} req/s")
        print(f"  Success rate: {success_rate:.1%}")
        
        # Should maintain reasonable performance under sustained load
        assert actual_rate > 80, f"Rate too low: {actual_rate} req/s"
        assert success_rate > 0.85, f"Success rate too low: {success_rate}"
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_redis_connection_stress(self, redis_client):
        """Test Redis connection handling under stress"""
        limiter = FixedWindowRateLimiter(redis_client)
        
        # Test with many rapid connections
        async def stress_worker(worker_id: int) -> List[bool]:
            results = []
            for i in range(100):
                key = f"stress_worker_{worker_id}_{i}"
                allowed, _ = await limiter.check_limit(key, 50, 60)
                results.append(allowed)
            return results
        
        # Run multiple workers concurrently
        start_time = time.time()
        worker_tasks = [stress_worker(i) for i in range(20)]
        worker_results = await asyncio.gather(*worker_tasks)
        duration = time.time() - start_time
        
        # Flatten results
        all_results = [result for worker_result in worker_results for result in worker_result]
        success_rate = sum(all_results) / len(all_results)
        
        print(f"Redis Connection Stress:")
        print(f"  Duration: {duration:.3f}s")
        print(f"  Total operations: {len(all_results)}")
        print(f"  Operations/sec: {len(all_results)/duration:.1f}")
        print(f"  Success rate: {success_rate:.1%}")
        
        # Should handle stress well
        assert duration < 15.0, f"Stress test took too long: {duration}s"
        assert success_rate > 0.95, f"Too many failures under stress: {success_rate}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "performance"])