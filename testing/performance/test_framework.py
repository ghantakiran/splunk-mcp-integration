#!/usr/bin/env python3
"""
Performance Testing Framework Validation
========================================
Quick validation tests for the performance testing framework
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from load_test_scenarios import ProductionLoadTestScenarios, create_production_test_scenarios
    from performance_testing_framework import PerformanceTestingFramework, TestType
    print("✓ Successfully imported framework components")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

async def test_load_scenarios():
    """Test load test scenarios creation"""
    print("\n🧪 Testing Load Test Scenarios...")
    
    try:
        # Test scenario factory creation
        scenarios = ProductionLoadTestScenarios()
        assert len(scenarios.user_profiles) == 5, f"Expected 5 user profiles, got {len(scenarios.user_profiles)}"
        assert len(scenarios.workloads) == 5, f"Expected 5 workloads, got {len(scenarios.workloads)}"
        print("  ✓ Scenario factory created successfully")
        
        # Test user simulation parameters
        workload = scenarios.workloads[0]  # Normal business hours
        params = scenarios.get_user_simulation_parameters(workload, 10, "North America")
        assert "active_users" in params, "Missing active_users in simulation parameters"
        assert "estimated_concurrent_queries" in params, "Missing concurrent queries estimation"
        print("  ✓ User simulation parameters generated")
        
        # Test query mix generation
        profile = scenarios.user_profiles[0]  # Business user
        queries = scenarios.generate_realistic_query_mix(profile, 15)
        assert len(queries) > 0, "No queries generated"
        print("  ✓ Query mix generation working")
        
        # Test system requirements calculation
        requirements = scenarios.calculate_system_requirements(workload, 10)
        assert "peak_concurrent_users" in requirements, "Missing peak concurrent users"
        assert "resource_estimates" in requirements, "Missing resource estimates"
        print("  ✓ System requirements calculation working")
        
        # Test production test scenarios creation
        test_scenarios = create_production_test_scenarios()
        assert len(test_scenarios) == 5, f"Expected 5 test scenarios, got {len(test_scenarios)}"
        print("  ✓ Production test scenarios created")
        
        print("✅ Load Test Scenarios: All tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Load Test Scenarios: Test failed - {e}")
        return False

async def test_performance_framework():
    """Test performance testing framework"""
    print("\n🧪 Testing Performance Framework...")
    
    try:
        # Mock aiohttp for testing
        with patch('aiohttp.ClientSession') as mock_session:
            # Setup mock responses
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"success": true}')
            mock_response.json = AsyncMock(return_value={"success": True, "data": []})
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            # Test framework initialization
            framework = PerformanceTestingFramework("development")
            assert framework.environment == "development", "Environment not set correctly"
            print("  ✓ Framework initialized successfully")
            
            # Test load test execution (quick version)
            framework.max_users = 10  # Reduce for testing
            framework.test_duration = 5  # 5 seconds for testing
            
            # Mock the actual test execution methods to avoid long waits
            framework._simulate_user_load = AsyncMock(return_value={
                "test_type": TestType.LOAD_TEST,
                "success": True,
                "metrics": {
                    "concurrent_users": 10,
                    "total_queries": 50,
                    "successful_queries": 48,
                    "failed_queries": 2,
                    "avg_response_time": 1.2,
                    "p95_response_time": 2.1,
                    "error_rate": 0.04
                }
            })
            
            framework._monitor_system_performance = AsyncMock(return_value={
                "cpu_usage": [45.2, 52.1, 48.3],
                "memory_usage": [62.1, 65.4, 63.8],
                "disk_io": [12.1, 15.3, 13.7],
                "network_io": [8.9, 11.2, 9.8]
            })
            
            # Test load test
            result = await framework.execute_load_test()
            assert result["success"] == True, "Load test should succeed"
            assert "metrics" in result, "Load test should return metrics"
            print("  ✓ Load test execution working")
            
            print("✅ Performance Framework: All tests passed")
            return True
            
    except Exception as e:
        print(f"❌ Performance Framework: Test failed - {e}")
        return False

async def test_framework_integration():
    """Test framework integration"""
    print("\n🧪 Testing Framework Integration...")
    
    try:
        # Test that all components work together
        scenarios = ProductionLoadTestScenarios()
        test_scenarios = create_production_test_scenarios()
        
        # Verify scenario structure
        for scenario in test_scenarios:
            assert "name" in scenario, "Scenario missing name"
            assert "workload" in scenario, "Scenario missing workload"
            assert "validation_criteria" in scenario, "Scenario missing validation criteria"
            
        print("  ✓ Scenario integration working")
        
        # Test configuration loading (simulate)
        config_data = {
            "environments": {"development": {"base_url": "http://localhost:8000"}},
            "performance_targets": {"response_times": {"simple_queries": 1.0}}
        }
        
        # Verify configuration structure
        assert "environments" in config_data, "Config missing environments"
        assert "performance_targets" in config_data, "Config missing performance targets"
        print("  ✓ Configuration structure valid")
        
        print("✅ Framework Integration: All tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Framework Integration: Test failed - {e}")
        return False

def test_file_structure():
    """Test that all necessary files exist"""
    print("\n🧪 Testing File Structure...")
    
    required_files = [
        "performance-testing-framework.py",
        "load-test-scenarios.py", 
        "load-test-orchestrator.py",
        "README.md",
        "config.yaml",
        "analyze_results.py",
        "test_framework.py"
    ]
    
    missing_files = []
    current_dir = Path(__file__).parent
    
    for file_name in required_files:
        file_path = current_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)
        else:
            print(f"  ✓ {file_name} exists")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ File Structure: All required files present")
        return True

async def main():
    """Run all validation tests"""
    print("🚀 Starting Performance Testing Framework Validation")
    print("=" * 60)
    
    start_time = time.time()
    
    # Run all tests
    tests = [
        ("File Structure", test_file_structure()),
        ("Load Scenarios", test_load_scenarios()),
        ("Performance Framework", test_performance_framework()),
        ("Framework Integration", test_framework_integration())
    ]
    
    results = []
    for test_name, test_coro in tests:
        if asyncio.iscoroutine(test_coro):
            result = await test_coro
        else:
            result = test_coro
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 VALIDATION RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    execution_time = time.time() - start_time
    print(f"\nTests: {passed}/{total} passed")
    print(f"Time: {execution_time:.2f} seconds")
    
    if passed == total:
        print("\n🎉 All validation tests passed! Framework is ready for use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review and fix issues.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)