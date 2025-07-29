#!/usr/bin/env python3
"""
Database Performance Testing for Splunk MCP Platform
===================================================
Comprehensive database performance testing and optimization analysis
"""

import asyncio
import asyncpg
import aioredis
import time
import statistics
import logging
import json
import argparse
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import concurrent.futures
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class DatabaseTestConfiguration:
    """Database test configuration"""
    postgres_url: str = "postgresql://user:pass@localhost:5432/splunk_mcp"
    redis_url: str = "redis://localhost:6379"
    concurrent_connections: int = 20
    test_duration: int = 60
    query_iterations: int = 100
    
@dataclass 
class DatabaseMetrics:
    """Database performance metrics"""
    connection_time: float = 0.0
    query_times: List[float] = None
    connection_pool_size: int = 0
    active_connections: int = 0
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    throughput: float = 0.0
    
    def __post_init__(self):
        if self.query_times is None:
            self.query_times = []

class DatabasePerformanceTester:
    """Database performance testing suite"""
    
    def __init__(self, config: DatabaseTestConfiguration):
        self.config = config
        self.postgres_pool = None
        self.redis_client = None
        
    async def setup_connections(self):
        """Setup database connection pools"""
        try:
            # PostgreSQL connection pool
            self.postgres_pool = await asyncpg.create_pool(
                self.config.postgres_url,
                min_size=5,
                max_size=self.config.concurrent_connections,
                command_timeout=30,
                server_settings={
                    'jit': 'off'  # Disable JIT for consistent performance
                }
            )
            logger.info("PostgreSQL connection pool created")
            
            # Redis connection
            self.redis_client = aioredis.from_url(self.config.redis_url)
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
        except Exception as e:
            logger.error(f"Failed to setup database connections: {e}")
            raise
            
    async def cleanup_connections(self):
        """Cleanup database connections"""
        if self.postgres_pool:
            await self.postgres_pool.close()
        if self.redis_client:
            await self.redis_client.close()
            
    async def test_postgres_connection_performance(self) -> Dict:
        """Test PostgreSQL connection performance"""
        logger.info("Testing PostgreSQL connection performance...")
        
        connection_times = []
        
        # Test direct connections (not from pool)
        for _ in range(10):
            start_time = time.time()
            conn = await asyncpg.connect(self.config.postgres_url)
            connection_time = time.time() - start_time
            connection_times.append(connection_time)
            await conn.close()
            
        # Test pool connections
        pool_connection_times = []
        for _ in range(20):
            start_time = time.time()
            async with self.postgres_pool.acquire() as conn:
                connection_time = time.time() - start_time
                pool_connection_times.append(connection_time)
                
        return {
            "direct_connection": {
                "avg_time": statistics.mean(connection_times),
                "min_time": min(connection_times),
                "max_time": max(connection_times),
                "samples": len(connection_times)
            },
            "pool_connection": {
                "avg_time": statistics.mean(pool_connection_times),
                "min_time": min(pool_connection_times),
                "max_time": max(pool_connection_times),
                "samples": len(pool_connection_times)
            }
        }
        
    async def test_postgres_query_performance(self) -> Dict:
        """Test PostgreSQL query performance"""
        logger.info("Testing PostgreSQL query performance...")
        
        # Define test queries
        queries = {
            "simple_select": "SELECT 1",
            "table_count": "SELECT COUNT(*) FROM information_schema.tables",
            "system_info": """
                SELECT 
                    version() as postgres_version,
                    current_database() as database_name,
                    current_timestamp as current_time
            """,
            "complex_join": """
                SELECT t.table_name, c.column_name, c.data_type 
                FROM information_schema.tables t 
                JOIN information_schema.columns c ON t.table_name = c.table_name 
                WHERE t.table_schema = 'public' 
                LIMIT 100
            """,
        }
        
        # Add application-specific queries if tables exist
        app_queries = await self._get_application_queries()
        queries.update(app_queries)
        
        query_results = {}
        
        for query_name, query_sql in queries.items():
            query_times = []
            successful_queries = 0
            
            # Run each query multiple times
            for _ in range(self.config.query_iterations):
                try:
                    start_time = time.time()
                    async with self.postgres_pool.acquire() as conn:
                        result = await conn.fetch(query_sql)
                    query_time = time.time() - start_time
                    
                    query_times.append(query_time)
                    successful_queries += 1
                    
                except Exception as e:
                    logger.debug(f"Query {query_name} failed: {e}")
                    
            if query_times:
                query_results[query_name] = {
                    "avg_time": statistics.mean(query_times),
                    "median_time": statistics.median(query_times),
                    "min_time": min(query_times),
                    "max_time": max(query_times),
                    "p95_time": statistics.quantiles(query_times, n=20)[18] if len(query_times) >= 20 else max(query_times),
                    "success_rate": successful_queries / self.config.query_iterations * 100,
                    "total_attempts": self.config.query_iterations,
                    "query_sql": query_sql[:100] + "..." if len(query_sql) > 100 else query_sql
                }
            else:
                query_results[query_name] = {
                    "error": "All queries failed",
                    "success_rate": 0,
                    "query_sql": query_sql[:100] + "..." if len(query_sql) > 100 else query_sql
                }
                
        return query_results
        
    async def _get_application_queries(self) -> Dict[str, str]:
        """Get application-specific queries if tables exist"""
        app_queries = {}
        
        try:
            async with self.postgres_pool.acquire() as conn:
                # Check if application tables exist
                tables = await conn.fetch("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('users', 'queries', 'sessions', 'dashboards', 'alerts')
                """)
                
                existing_tables = [row['table_name'] for row in tables]
                
                # Add queries for existing tables
                if 'users' in existing_tables:
                    app_queries['user_count'] = "SELECT COUNT(*) FROM users"
                    app_queries['recent_users'] = """
                        SELECT id, username, created_at 
                        FROM users 
                        WHERE created_at > NOW() - INTERVAL '7 days'
                        ORDER BY created_at DESC 
                        LIMIT 10
                    """
                    
                if 'queries' in existing_tables:
                    app_queries['query_count'] = "SELECT COUNT(*) FROM queries"
                    app_queries['recent_queries'] = """
                        SELECT id, query_text, created_at, execution_time
                        FROM queries 
                        WHERE created_at > NOW() - INTERVAL '24 hours'
                        ORDER BY created_at DESC 
                        LIMIT 20
                    """
                    
                if 'sessions' in existing_tables:
                    app_queries['active_sessions'] = """
                        SELECT COUNT(*) 
                        FROM sessions 
                        WHERE expires_at > NOW()
                    """
                    
        except Exception as e:
            logger.debug(f"Error checking application tables: {e}")
            
        return app_queries
        
    async def test_postgres_concurrent_load(self) -> Dict:
        """Test PostgreSQL under concurrent load"""
        logger.info(f"Testing PostgreSQL concurrent load with {self.config.concurrent_connections} connections...")
        
        async def execute_concurrent_queries():
            """Execute queries concurrently"""
            query_times = []
            successful_queries = 0
            
            # Run queries for specified duration
            end_time = time.time() + self.config.test_duration
            
            while time.time() < end_time:
                try:
                    start_time = time.time()
                    async with self.postgres_pool.acquire() as conn:
                        # Mix of different query types
                        queries = [
                            "SELECT 1",
                            "SELECT COUNT(*) FROM information_schema.tables",
                            "SELECT pg_sleep(0.01)",  # Small delay to simulate processing
                        ]
                        
                        for query in queries:
                            await conn.fetch(query)
                            
                    query_time = time.time() - start_time
                    query_times.append(query_time)
                    successful_queries += 1
                    
                except Exception as e:
                    logger.debug(f"Concurrent query failed: {e}")
                    
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)
                
            return query_times, successful_queries
            
        # Run concurrent tasks
        tasks = [execute_concurrent_queries() for _ in range(self.config.concurrent_connections)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        all_query_times = []
        total_successful = 0
        
        for result in results:
            if isinstance(result, tuple):
                query_times, successful = result
                all_query_times.extend(query_times)
                total_successful += successful
                
        if all_query_times:
            throughput = len(all_query_times) / self.config.test_duration
            
            return {
                "concurrent_connections": self.config.concurrent_connections,
                "test_duration": self.config.test_duration,
                "total_queries": len(all_query_times),
                "successful_queries": total_successful,
                "queries_per_second": throughput,
                "avg_response_time": statistics.mean(all_query_times),
                "median_response_time": statistics.median(all_query_times),
                "p95_response_time": statistics.quantiles(all_query_times, n=20)[18] if len(all_query_times) >= 20 else max(all_query_times),
                "min_response_time": min(all_query_times),
                "max_response_time": max(all_query_times)
            }
        else:
            return {"error": "No successful queries completed"}
            
    async def test_redis_performance(self) -> Dict:
        """Test Redis performance"""
        logger.info("Testing Redis performance...")
        
        # Basic operations test
        basic_ops = {}
        
        # SET operations
        set_times = []
        for i in range(1000):
            start_time = time.time()
            await self.redis_client.set(f"test_key_{i}", f"test_value_{i}")
            set_time = time.time() - start_time
            set_times.append(set_time)
            
        basic_ops['set_operations'] = {
            "total_operations": len(set_times),
            "avg_time": statistics.mean(set_times),
            "min_time": min(set_times),
            "max_time": max(set_times),
            "operations_per_second": len(set_times) / sum(set_times)
        }
        
        # GET operations
        get_times = []
        for i in range(1000):
            start_time = time.time()
            value = await self.redis_client.get(f"test_key_{i}")
            get_time = time.time() - start_time
            get_times.append(get_time)
            
        basic_ops['get_operations'] = {
            "total_operations": len(get_times),
            "avg_time": statistics.mean(get_times),
            "min_time": min(get_times),
            "max_time": max(get_times),
            "operations_per_second": len(get_times) / sum(get_times)
        }
        
        # Complex operations test
        complex_ops = {}
        
        # List operations
        list_times = []
        list_key = "test_list"
        
        # LPUSH operations
        start_time = time.time()
        for i in range(100):
            await self.redis_client.lpush(list_key, f"item_{i}")
        lpush_time = time.time() - start_time
        
        # LRANGE operations
        start_time = time.time()
        items = await self.redis_client.lrange(list_key, 0, -1)
        lrange_time = time.time() - start_time
        
        complex_ops['list_operations'] = {
            "lpush_time": lpush_time,
            "lpush_ops_per_second": 100 / lpush_time,
            "lrange_time": lrange_time,
            "items_retrieved": len(items)
        }
        
        # Hash operations
        hash_key = "test_hash"
        hash_times = []
        
        for i in range(100):
            start_time = time.time()
            await self.redis_client.hset(hash_key, f"field_{i}", f"value_{i}")
            hash_time = time.time() - start_time
            hash_times.append(hash_time)
            
        complex_ops['hash_operations'] = {
            "avg_hset_time": statistics.mean(hash_times),
            "total_hash_operations": len(hash_times)
        }
        
        # Cleanup test data
        await self.redis_client.flushdb()
        
        return {
            "basic_operations": basic_ops,
            "complex_operations": complex_ops,
            "redis_info": await self._get_redis_info()
        }
        
    async def _get_redis_info(self) -> Dict:
        """Get Redis server information"""
        try:
            info = await self.redis_client.info()
            return {
                "redis_version": info.get('redis_version', 'unknown'),
                "used_memory": info.get('used_memory_human', 'unknown'),
                "connected_clients": info.get('connected_clients', 0),
                "total_commands_processed": info.get('total_commands_processed', 0),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0)
            }
        except Exception as e:
            logger.debug(f"Error getting Redis info: {e}")
            return {"error": str(e)}
            
    async def test_database_integration(self) -> Dict:
        """Test integration between PostgreSQL and Redis"""
        logger.info("Testing database integration performance...")
        
        integration_times = []
        successful_operations = 0
        
        for i in range(50):
            try:
                start_time = time.time()
                
                # Simulate application workflow:
                # 1. Query PostgreSQL
                async with self.postgres_pool.acquire() as conn:
                    result = await conn.fetch("SELECT 1 as test_value")
                    
                # 2. Cache result in Redis
                cache_key = f"integration_test_{i}"
                await self.redis_client.set(cache_key, json.dumps([dict(r) for r in result]))
                
                # 3. Retrieve from cache
                cached_data = await self.redis_client.get(cache_key)
                
                # 4. Verify data integrity
                if cached_data:
                    parsed_data = json.loads(cached_data)
                    if parsed_data[0]['test_value'] == 1:
                        successful_operations += 1
                        
                integration_time = time.time() - start_time
                integration_times.append(integration_time)
                
            except Exception as e:
                logger.debug(f"Integration test {i} failed: {e}")
                
        if integration_times:
            return {
                "total_operations": len(integration_times),
                "successful_operations": successful_operations,
                "success_rate": successful_operations / len(integration_times) * 100,
                "avg_integration_time": statistics.mean(integration_times),
                "min_integration_time": min(integration_times),
                "max_integration_time": max(integration_times)
            }
        else:
            return {"error": "No successful integration tests completed"}
            
    async def analyze_database_performance(self) -> Dict:
        """Analyze overall database performance"""
        logger.info("Analyzing database performance...")
        
        try:
            # Get system metrics
            system_metrics = {
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            }
            
            # Get PostgreSQL specific metrics
            postgres_metrics = {}
            try:
                async with self.postgres_pool.acquire() as conn:
                    # Database size
                    size_result = await conn.fetch("""
                        SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
                    """)
                    postgres_metrics['database_size'] = size_result[0]['db_size']
                    
                    # Active connections
                    conn_result = await conn.fetch("""
                        SELECT count(*) as active_connections 
                        FROM pg_stat_activity 
                        WHERE state = 'active'
                    """)
                    postgres_metrics['active_connections'] = conn_result[0]['active_connections']
                    
                    # Long running queries
                    long_queries = await conn.fetch("""
                        SELECT count(*) as long_queries 
                        FROM pg_stat_activity 
                        WHERE state = 'active' 
                        AND query_start < now() - interval '1 minute'
                    """)
                    postgres_metrics['long_running_queries'] = long_queries[0]['long_queries']
                    
            except Exception as e:
                postgres_metrics['error'] = str(e)
                
            return {
                "system_metrics": system_metrics,
                "postgres_metrics": postgres_metrics,
                "pool_status": {
                    "pool_size": self.postgres_pool.get_size(),
                    "pool_min_size": self.postgres_pool.get_min_size(),
                    "pool_max_size": self.postgres_pool.get_max_size()
                }
            }
            
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}
            
    async def run_comprehensive_database_tests(self) -> Dict:
        """Run complete database performance test suite"""
        logger.info("Starting comprehensive database performance tests...")
        
        start_time = datetime.now()
        
        # Setup connections
        await self.setup_connections()
        
        try:
            results = {
                "test_configuration": asdict(self.config),
                "test_start_time": start_time.isoformat(),
            }
            
            # PostgreSQL tests
            logger.info("Running PostgreSQL performance tests...")
            results["postgres_connection_performance"] = await self.test_postgres_connection_performance()
            results["postgres_query_performance"] = await self.test_postgres_query_performance()
            results["postgres_concurrent_load"] = await self.test_postgres_concurrent_load()
            
            # Redis tests
            logger.info("Running Redis performance tests...")
            results["redis_performance"] = await self.test_redis_performance()
            
            # Integration tests
            logger.info("Running database integration tests...")
            results["database_integration"] = await self.test_database_integration()
            
            # Performance analysis
            logger.info("Analyzing performance metrics...")
            results["performance_analysis"] = await self.analyze_database_performance()
            
            end_time = datetime.now()
            results["test_end_time"] = end_time.isoformat()
            results["total_test_duration"] = (end_time - start_time).total_seconds()
            
            return results
            
        finally:
            await self.cleanup_connections()
            
    def generate_database_report(self, results: Dict, output_file: str = None) -> str:
        """Generate database performance report"""
        if not output_file:
            output_file = f"database-performance-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Database performance report saved to: {output_file}")
        return output_file
        
    def print_database_summary(self, results: Dict):
        """Print database performance summary"""
        print("\n" + "="*60)
        print("DATABASE PERFORMANCE TEST SUMMARY")
        print("="*60)
        
        # Test configuration
        config = results.get("test_configuration", {})
        print(f"Test Duration: {results.get('total_test_duration', 0):.1f} seconds")
        print(f"Concurrent Connections: {config.get('concurrent_connections', 0)}")
        
        # PostgreSQL results
        postgres_load = results.get("postgres_concurrent_load", {})
        if postgres_load and "queries_per_second" in postgres_load:
            print(f"\nPostgreSQL Performance:")
            print(f"  Queries per Second: {postgres_load['queries_per_second']:.1f}")
            print(f"  Average Response: {postgres_load['avg_response_time']:.3f}s")
            print(f"  P95 Response: {postgres_load['p95_response_time']:.3f}s")
            
        # Redis results
        redis_results = results.get("redis_performance", {})
        basic_ops = redis_results.get("basic_operations", {})
        if basic_ops:
            get_ops = basic_ops.get("get_operations", {})
            set_ops = basic_ops.get("set_operations", {})
            print(f"\nRedis Performance:")
            if get_ops:
                print(f"  GET ops/sec: {get_ops.get('operations_per_second', 0):.0f}")
            if set_ops:
                print(f"  SET ops/sec: {set_ops.get('operations_per_second', 0):.0f}")
                
        # Integration results
        integration = results.get("database_integration", {})
        if integration and "success_rate" in integration:
            print(f"\nDatabase Integration:")
            print(f"  Success Rate: {integration['success_rate']:.1f}%")
            print(f"  Avg Integration Time: {integration['avg_integration_time']:.3f}s")
            
        # System metrics
        analysis = results.get("performance_analysis", {})
        system_metrics = analysis.get("system_metrics", {})
        if system_metrics:
            print(f"\nSystem Resource Usage:")
            print(f"  CPU: {system_metrics.get('cpu_usage', 0):.1f}%")
            print(f"  Memory: {system_metrics.get('memory_usage', 0):.1f}%")
            print(f"  Disk: {system_metrics.get('disk_usage', 0):.1f}%")
            
        print("="*60)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Database Performance Testing Suite')
    parser.add_argument('--postgres-url', default='postgresql://user:pass@localhost:5432/splunk_mcp',
                       help='PostgreSQL connection URL')
    parser.add_argument('--redis-url', default='redis://localhost:6379',
                       help='Redis connection URL')
    parser.add_argument('--connections', type=int, default=20,
                       help='Number of concurrent connections')
    parser.add_argument('--duration', type=int, default=60,
                       help='Test duration in seconds')
    parser.add_argument('--iterations', type=int, default=100,
                       help='Query iterations for single query tests')
    parser.add_argument('--output', help='Output report file')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Create configuration
    config = DatabaseTestConfiguration(
        postgres_url=args.postgres_url,
        redis_url=args.redis_url,
        concurrent_connections=args.connections,
        test_duration=args.duration,
        query_iterations=args.iterations
    )
    
    # Run database performance tests
    async def run_tests():
        tester = DatabasePerformanceTester(config)
        
        try:
            results = await tester.run_comprehensive_database_tests()
            
            # Generate report
            report_file = tester.generate_database_report(results, args.output)
            
            # Print summary
            tester.print_database_summary(results)
            
            # Determine exit code based on performance
            postgres_load = results.get("postgres_concurrent_load", {})
            qps = postgres_load.get("queries_per_second", 0)
            
            if qps > 100:  # Good performance
                sys.exit(0)
            elif qps > 50:  # Acceptable performance
                sys.exit(1)
            else:  # Poor performance
                sys.exit(2)
                
        except KeyboardInterrupt:
            logger.info("Database performance test interrupted by user")
            sys.exit(130)
        except Exception as e:
            logger.error(f"Database performance test failed: {e}")
            sys.exit(1)
    
    # Run the test suite
    asyncio.run(run_tests())

if __name__ == '__main__':
    main()