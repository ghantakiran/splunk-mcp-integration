#!/usr/bin/env python3
"""
Performance Test Results Analyzer
=================================
Comprehensive analysis and reporting for Splunk MCP Integration performance test results
"""

import json
import statistics
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import matplotlib.pyplot as plt
import pandas as pd
from dataclasses import dataclass
import seaborn as sns

@dataclass
class PerformanceInsight:
    """Performance analysis insight"""
    category: str
    severity: str  # 'critical', 'warning', 'info', 'success'
    title: str
    description: str
    recommendation: str
    metrics: Dict[str, Any]

class PerformanceResultsAnalyzer:
    """Comprehensive performance results analyzer"""
    
    def __init__(self, results_file: str, config_file: str = None):
        self.results_file = Path(results_file)
        self.config_file = Path(config_file) if config_file else None
        self.results = self._load_results()
        self.config = self._load_config() if self.config_file else {}
        self.insights: List[PerformanceInsight] = []
        
    def _load_results(self) -> Dict[str, Any]:
        """Load performance test results"""
        try:
            with open(self.results_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load results file: {e}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration file"""
        try:
            import yaml
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
        except ImportError:
            print("Warning: PyYAML not installed, using default configuration")
            return {}
        except Exception as e:
            print(f"Warning: Failed to load config file: {e}")
            return {}
    
    def analyze_comprehensive(self) -> Dict[str, Any]:
        """Perform comprehensive performance analysis"""
        analysis = {
            "executive_summary": self._generate_executive_summary(),
            "performance_analysis": self._analyze_performance_metrics(),
            "system_analysis": self._analyze_system_metrics(),
            "scalability_analysis": self._analyze_scalability(),
            "reliability_analysis": self._analyze_reliability(),
            "recommendations": self._generate_recommendations(),
            "insights": [insight.__dict__ for insight in self.insights],
            "detailed_metrics": self._extract_detailed_metrics()
        }
        
        return analysis
    
    def _generate_executive_summary(self) -> Dict[str, Any]:
        """Generate executive summary"""
        overall_success = self.results.get("overall_success", False)
        test_results = self.results.get("test_results", [])
        
        passed_tests = sum(1 for test in test_results if test.get("success", False))
        total_tests = len(test_results)
        success_rate = (passed_tests / total_tests) if total_tests > 0 else 0
        
        # Extract key metrics
        concurrent_users_test = next(
            (test for test in test_results if "10K Concurrent" in test.get("test_name", "")), 
            {}
        )
        response_time_test = next(
            (test for test in test_results if "3 Second Response" in test.get("test_name", "")), 
            {}
        )
        
        max_concurrent_users = 0
        avg_response_time = 0
        
        if concurrent_users_test.get("metrics"):
            max_concurrent_users = concurrent_users_test["metrics"].get("total_users", 0)
            
        if response_time_test.get("metrics"):
            avg_response_time = response_time_test["metrics"].get("avg_response_time", 0)
        
        # Determine overall grade
        if success_rate >= 0.9 and overall_success:
            grade = "A"
            status = "Excellent"
        elif success_rate >= 0.8:
            grade = "B" 
            status = "Good"
        elif success_rate >= 0.7:
            grade = "C"
            status = "Satisfactory"
        elif success_rate >= 0.6:
            grade = "D"
            status = "Needs Improvement"
        else:
            grade = "F"
            status = "Critical Issues"
        
        summary = {
            "overall_grade": grade,
            "overall_status": status,
            "overall_success": overall_success,
            "test_success_rate": success_rate,
            "tests_passed": passed_tests,
            "total_tests": total_tests,
            "key_metrics": {
                "max_concurrent_users": max_concurrent_users,
                "avg_response_time": round(avg_response_time, 3),
                "target_concurrent_users": 10000,
                "target_response_time": 3.0
            },
            "critical_issues": self._identify_critical_issues(),
            "achievements": self._identify_achievements()
        }
        
        return summary
    
    def _analyze_performance_metrics(self) -> Dict[str, Any]:
        """Analyze performance metrics"""
        test_results = self.results.get("test_results", [])
        
        # Response time analysis
        response_time_analysis = self._analyze_response_times(test_results)
        
        # Throughput analysis
        throughput_analysis = self._analyze_throughput(test_results)
        
        # Concurrent user analysis
        user_capacity_analysis = self._analyze_user_capacity(test_results)
        
        # NLP performance analysis
        nlp_analysis = self._analyze_nlp_performance(test_results)
        
        return {
            "response_times": response_time_analysis,
            "throughput": throughput_analysis,
            "user_capacity": user_capacity_analysis,
            "nlp_performance": nlp_analysis
        }
    
    def _analyze_response_times(self, test_results: List[Dict]) -> Dict[str, Any]:
        """Analyze response time performance"""
        response_time_test = next(
            (test for test in test_results if "3 Second Response" in test.get("test_name", "")), 
            {}
        )
        
        if not response_time_test.get("metrics"):
            return {"status": "no_data", "analysis": "No response time data available"}
        
        metrics = response_time_test["metrics"]
        avg_time = metrics.get("avg_response_time", 0)
        p95_time = metrics.get("p95_response_time", 0)
        p99_time = metrics.get("p99_response_time", 0)
        max_time = metrics.get("max_response_time", 0)
        
        # Performance classification
        if avg_time <= 1.0:
            performance_class = "excellent"
        elif avg_time <= 2.0:
            performance_class = "good"
        elif avg_time <= 3.0:
            performance_class = "acceptable"
        elif avg_time <= 5.0:
            performance_class = "poor"
        else:
            performance_class = "critical"
        
        # Generate insights
        if avg_time > 3.0:
            self.insights.append(PerformanceInsight(
                category="performance",
                severity="critical" if avg_time > 5.0 else "warning",
                title="Response Time Target Not Met",
                description=f"Average response time ({avg_time:.2f}s) exceeds target (3.0s)",
                recommendation="Optimize database queries, implement caching, review system resources",
                metrics={"avg_response_time": avg_time, "target": 3.0}
            ))
        
        if p95_time > 5.0:
            self.insights.append(PerformanceInsight(
                category="performance",
                severity="warning",
                title="P95 Response Time High",
                description=f"95th percentile response time ({p95_time:.2f}s) indicates performance issues for some requests",
                recommendation="Investigate slow queries, optimize worst-case scenarios",
                metrics={"p95_response_time": p95_time}
            ))
        
        return {
            "performance_class": performance_class,
            "avg_response_time": avg_time,
            "p50_response_time": metrics.get("p50_response_time", 0),
            "p95_response_time": p95_time,
            "p99_response_time": p99_time,
            "max_response_time": max_time,
            "target_met": avg_time <= 3.0,
            "samples": metrics.get("samples", 0)
        }
    
    def _analyze_throughput(self, test_results: List[Dict]) -> Dict[str, Any]:
        """Analyze system throughput"""
        # Look for throughput data in various tests
        throughput_data = []
        
        for test in test_results:
            metrics = test.get("metrics", {})
            if "queries_per_second" in metrics:
                throughput_data.append(metrics["queries_per_second"])
            elif "estimated_concurrent_queries" in metrics:
                throughput_data.append(metrics["estimated_concurrent_queries"])
        
        if not throughput_data:
            return {"status": "no_data", "analysis": "No throughput data available"}
        
        max_throughput = max(throughput_data)
        avg_throughput = statistics.mean(throughput_data)
        
        # Compare against targets
        target_throughput = self.config.get("performance_targets", {}).get("throughput", {}).get("queries_per_second", 500)
        
        throughput_performance = "excellent" if max_throughput >= target_throughput else "needs_improvement"
        
        if max_throughput < target_throughput * 0.8:
            self.insights.append(PerformanceInsight(
                category="throughput",
                severity="warning",
                title="Throughput Below Target",
                description=f"Maximum throughput ({max_throughput:.1f} qps) below target ({target_throughput} qps)",
                recommendation="Optimize query processing, consider horizontal scaling",
                metrics={"max_throughput": max_throughput, "target": target_throughput}
            ))
        
        return {
            "performance_class": throughput_performance,
            "max_throughput": max_throughput,
            "avg_throughput": avg_throughput,
            "target_throughput": target_throughput,
            "target_met": max_throughput >= target_throughput
        }
    
    def _analyze_user_capacity(self, test_results: List[Dict]) -> Dict[str, Any]:
        """Analyze concurrent user capacity"""
        user_test = next(
            (test for test in test_results if "10K Concurrent" in test.get("test_name", "")), 
            {}
        )
        
        if not user_test.get("metrics"):
            return {"status": "no_data", "analysis": "No user capacity data available"}
        
        metrics = user_test["metrics"]
        total_users = metrics.get("total_users", 0)
        successful_users = metrics.get("successful_users", 0)
        success_rate = metrics.get("success_rate", 0)
        
        target_users = 10000
        capacity_performance = "excellent" if total_users >= target_users and success_rate >= 0.95 else "needs_improvement"
        
        if total_users < target_users:
            self.insights.append(PerformanceInsight(
                category="capacity",
                severity="critical",
                title="User Capacity Target Not Met",
                description=f"System handled {total_users} users, target is {target_users}",
                recommendation="Increase system resources, optimize architecture for scale",
                metrics={"actual_users": total_users, "target_users": target_users}
            ))
        
        if success_rate < 0.95:
            self.insights.append(PerformanceInsight(
                category="capacity",
                severity="warning",
                title="User Success Rate Low",
                description=f"User success rate ({success_rate:.1%}) indicates system stress",
                recommendation="Improve error handling, increase system stability",
                metrics={"success_rate": success_rate}
            ))
        
        return {
            "performance_class": capacity_performance,
            "total_users_tested": total_users,
            "successful_users": successful_users,
            "user_success_rate": success_rate,
            "target_users": target_users,
            "target_met": total_users >= target_users and success_rate >= 0.95
        }
    
    def _analyze_nlp_performance(self, test_results: List[Dict]) -> Dict[str, Any]:
        """Analyze NLP engine performance"""
        nlp_test = next(
            (test for test in test_results if "NLP Processing" in test.get("test_name", "")), 
            {}
        )
        
        if not nlp_test.get("metrics"):
            return {"status": "no_data", "analysis": "No NLP performance data available"}
        
        performance_by_complexity = nlp_test["metrics"].get("performance_by_complexity", {})
        
        # Define targets by complexity
        targets = {
            "simple_queries": 1.0,
            "moderate_queries": 2.0,
            "complex_queries": 5.0,
            "very_complex_queries": 10.0
        }
        
        analysis = {}
        overall_performance = "excellent"
        
        for complexity, target in targets.items():
            if complexity in performance_by_complexity:
                perf_data = performance_by_complexity[complexity]
                avg_time = perf_data.get("avg_time", 0)
                
                performance_class = "excellent" if avg_time <= target else "needs_improvement"
                if performance_class == "needs_improvement":
                    overall_performance = "needs_improvement"
                
                analysis[complexity] = {
                    "avg_time": avg_time,
                    "target": target,
                    "target_met": avg_time <= target,
                    "sample_count": perf_data.get("sample_count", 0)
                }
                
                if avg_time > target * 1.5:
                    self.insights.append(PerformanceInsight(
                        category="nlp",
                        severity="warning",
                        title=f"NLP Performance Issue - {complexity.replace('_', ' ').title()}",
                        description=f"Processing time ({avg_time:.2f}s) exceeds target ({target}s)",
                        recommendation="Optimize NLP models, consider query caching",
                        metrics={"complexity": complexity, "avg_time": avg_time, "target": target}
                    ))
        
        return {
            "overall_performance": overall_performance,
            "by_complexity": analysis,
            "total_requests": nlp_test["metrics"].get("total_nlp_requests", 0)
        }
    
    def _analyze_system_metrics(self) -> Dict[str, Any]:
        """Analyze system resource utilization"""
        test_results = self.results.get("test_results", [])
        
        # Extract system metrics from various tests
        cpu_data = []
        memory_data = []
        
        for test in test_results:
            metrics = test.get("metrics", {})
            system_metrics = metrics.get("system_metrics", {})
            
            if isinstance(system_metrics, dict):
                if "avg_cpu_usage" in system_metrics:
                    cpu_data.append(system_metrics["avg_cpu_usage"])
                if "avg_memory_usage" in system_metrics:
                    memory_data.append(system_metrics["avg_memory_usage"])
        
        cpu_analysis = self._analyze_resource_usage("CPU", cpu_data, 80.0)
        memory_analysis = self._analyze_resource_usage("Memory", memory_data, 85.0)
        
        return {
            "cpu_utilization": cpu_analysis,
            "memory_utilization": memory_analysis,
            "overall_resource_health": self._calculate_resource_health(cpu_analysis, memory_analysis)
        }
    
    def _analyze_resource_usage(self, resource_name: str, data: List[float], threshold: float) -> Dict[str, Any]:
        """Analyze resource usage patterns"""
        if not data:
            return {"status": "no_data", "analysis": f"No {resource_name} data available"}
        
        avg_usage = statistics.mean(data)
        max_usage = max(data)
        min_usage = min(data)
        
        # Determine status
        if max_usage >= threshold:
            status = "critical"
            severity = "critical"
        elif avg_usage >= threshold * 0.8:
            status = "warning"
            severity = "warning"
        else:
            status = "healthy"
            severity = "info"
        
        if max_usage >= threshold:
            self.insights.append(PerformanceInsight(
                category="resources",
                severity=severity,
                title=f"{resource_name} Usage High",
                description=f"Peak {resource_name.lower()} usage ({max_usage:.1f}%) exceeds threshold ({threshold}%)",
                recommendation=f"Monitor {resource_name.lower()} usage, consider scaling up resources",
                metrics={"resource": resource_name, "peak_usage": max_usage, "threshold": threshold}
            ))
        
        return {
            "status": status,
            "avg_usage": avg_usage,
            "peak_usage": max_usage,
            "min_usage": min_usage,
            "threshold": threshold,
            "threshold_exceeded": max_usage >= threshold
        }
    
    def _calculate_resource_health(self, cpu_analysis: Dict, memory_analysis: Dict) -> str:
        """Calculate overall resource health"""
        cpu_status = cpu_analysis.get("status", "unknown")
        memory_status = memory_analysis.get("status", "unknown")
        
        if cpu_status == "critical" or memory_status == "critical":
            return "critical"
        elif cpu_status == "warning" or memory_status == "warning":
            return "warning"
        else:
            return "healthy"
    
    def _analyze_scalability(self) -> Dict[str, Any]:
        """Analyze system scalability"""
        test_results = self.results.get("test_results", [])
        
        scaling_test = next(
            (test for test in test_results if "Auto-scaling" in test.get("test_name", "")), 
            {}
        )
        
        if not scaling_test.get("metrics"):
            return {"status": "no_data", "analysis": "No scalability data available"}
        
        scaling_analysis = scaling_test["metrics"].get("scaling_analysis", {})
        
        scale_up_detected = scaling_analysis.get("scale_up_detected", False)
        scale_down_detected = scaling_analysis.get("scale_down_detected", False)
        performance_maintained = scaling_analysis.get("performance_maintained", False)
        
        scalability_score = sum([scale_up_detected, scale_down_detected, performance_maintained]) / 3
        
        if scalability_score < 0.7:
            self.insights.append(PerformanceInsight(
                category="scalability",
                severity="warning",
                title="Scalability Issues Detected",
                description="Auto-scaling behavior not working as expected",
                recommendation="Review auto-scaling policies, check resource limits and triggers",
                metrics=scaling_analysis
            ))
        
        return {
            "scalability_score": scalability_score,
            "scale_up_working": scale_up_detected,
            "scale_down_working": scale_down_detected,
            "performance_maintained": performance_maintained,
            "overall_status": "good" if scalability_score >= 0.8 else "needs_improvement"
        }
    
    def _analyze_reliability(self) -> Dict[str, Any]:
        """Analyze system reliability"""
        test_results = self.results.get("test_results", [])
        
        # Look for stability test
        stability_test = next(
            (test for test in test_results if "System Stability" in test.get("test_name", "")), 
            {}
        )
        
        if not stability_test.get("metrics"):
            return {"status": "no_data", "analysis": "No reliability data available"}
        
        stability_analysis = stability_test["metrics"].get("stability_analysis", {})
        
        memory_leak = stability_analysis.get("memory_leak_detected", False)
        performance_degradation = stability_analysis.get("performance_degradation", False)
        error_rate = stability_analysis.get("overall_error_rate", 0)
        stability_score = stability_analysis.get("system_stability_score", 0)
        
        # Calculate reliability grade
        reliability_factors = [
            not memory_leak,
            not performance_degradation,
            error_rate < 0.05,
            stability_score >= 0.8
        ]
        
        reliability_score = sum(reliability_factors) / len(reliability_factors)
        
        if memory_leak:
            self.insights.append(PerformanceInsight(
                category="reliability",
                severity="critical",
                title="Memory Leak Detected",
                description="System shows signs of memory leaks during sustained load",
                recommendation="Investigate memory management, review object lifecycle",
                metrics={"memory_leak_detected": True}
            ))
        
        if performance_degradation:
            self.insights.append(PerformanceInsight(
                category="reliability",
                severity="warning",
                title="Performance Degradation Detected",
                description="System performance degrades over time under load",
                recommendation="Optimize long-running processes, review resource cleanup",
                metrics={"performance_degradation": True}
            ))
        
        return {
            "reliability_score": reliability_score,
            "memory_leak_detected": memory_leak,
            "performance_degradation": performance_degradation,
            "error_rate": error_rate,
            "stability_score": stability_score,
            "overall_status": "good" if reliability_score >= 0.8 else "critical"
        }
    
    def _identify_critical_issues(self) -> List[Dict[str, Any]]:
        """Identify critical issues from test results"""
        issues = []
        test_results = self.results.get("test_results", [])
        
        for test in test_results:
            if not test.get("success", True):
                issues.append({
                    "test_name": test.get("test_name", "Unknown Test"),
                    "errors": test.get("errors", [])[:3]  # First 3 errors
                })
        
        return issues
    
    def _identify_achievements(self) -> List[str]:
        """Identify successful achievements"""
        achievements = []
        requirements = self.results.get("system_requirements_validation", {})
        
        achievement_map = {
            "concurrent_users_10k": "Successfully handled 10,000+ concurrent users",
            "response_time_3s": "Achieved <3 second average response time",
            "system_stability": "Maintained system stability under sustained load",
            "nlp_performance": "NLP engine performed within targets",
            "real_time_performance": "Real-time features met performance targets",
            "database_performance": "Database performance met requirements",
            "auto_scaling": "Auto-scaling behavior working correctly"
        }
        
        for requirement, passed in requirements.items():
            if passed and requirement in achievement_map:
                achievements.append(achievement_map[requirement])
        
        return achievements
    
    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Group insights by category and severity
        critical_insights = [i for i in self.insights if i.severity == "critical"]
        warning_insights = [i for i in self.insights if i.severity == "warning"]
        
        # Critical recommendations (immediate action required)
        if critical_insights:
            recommendations.append({
                "priority": "critical",
                "category": "immediate_action",
                "title": "Critical Issues Requiring Immediate Attention",
                "actions": [insight.recommendation for insight in critical_insights[:5]]  # Top 5
            })
        
        # Performance optimization recommendations
        performance_insights = [i for i in self.insights if i.category == "performance"]
        if performance_insights:
            recommendations.append({
                "priority": "high",
                "category": "performance_optimization",
                "title": "Performance Optimization Opportunities",
                "actions": [
                    "Implement query result caching for frequently accessed data",
                    "Optimize database indexes for common query patterns",
                    "Consider implementing CDN for static assets",
                    "Review and optimize slow database queries"
                ]
            })
        
        # Scalability recommendations
        scalability_insights = [i for i in self.insights if i.category == "scalability"]
        if scalability_insights:
            recommendations.append({
                "priority": "medium",
                "category": "scalability_improvements",
                "title": "Scalability Enhancement Suggestions",
                "actions": [
                    "Review auto-scaling policies and triggers",
                    "Implement horizontal pod autoscaling",
                    "Consider implementing connection pooling",
                    "Optimize resource allocation and limits"
                ]
            })
        
        # Monitoring and observability
        recommendations.append({
            "priority": "medium",
            "category": "monitoring",
            "title": "Enhanced Monitoring and Observability", 
            "actions": [
                "Set up detailed performance monitoring dashboards",
                "Implement proactive alerting for key metrics",
                "Add distributed tracing for complex queries",
                "Create automated performance regression detection"
            ]
        })
        
        return recommendations
    
    def _extract_detailed_metrics(self) -> Dict[str, Any]:
        """Extract detailed metrics for further analysis"""
        return {
            "test_execution_summary": {
                "total_tests": len(self.results.get("test_results", [])),
                "passed_tests": sum(1 for test in self.results.get("test_results", []) if test.get("success")),
                "execution_time": self._calculate_execution_time(),
                "environment": self.results.get("environment", "unknown")
            },
            "raw_test_results": self.results.get("test_results", []),
            "system_requirements_validation": self.results.get("system_requirements_validation", {}),
            "configuration_used": self.config
        }
    
    def _calculate_execution_time(self) -> str:
        """Calculate total test execution time"""
        start_time_str = self.results.get("start_time", "")
        end_time_str = self.results.get("end_time", "")
        
        if not start_time_str or not end_time_str:
            return "unknown"
        
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            duration = end_time - start_time
            return str(duration)
        except Exception:
            return "unknown"
    
    def generate_html_report(self, output_file: str):
        """Generate comprehensive HTML report"""
        analysis = self.analyze_comprehensive()
        
        html_content = self._create_html_report(analysis)
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"HTML report generated: {output_file}")
    
    def _create_html_report(self, analysis: Dict[str, Any]) -> str:
        """Create HTML report content"""
        executive = analysis["executive_summary"]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Splunk MCP Performance Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; }}
                .grade {{ font-size: 48px; font-weight: bold; }}
                .grade.A {{ color: #28a745; }}
                .grade.B {{ color: #17a2b8; }}
                .grade.C {{ color: #ffc107; }}
                .grade.D {{ color: #fd7e14; }}
                .grade.F {{ color: #dc3545; }}
                .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #e9ecef; border-radius: 5px; }}
                .critical {{ color: #dc3545; }}
                .warning {{ color: #ffc107; }}
                .success {{ color: #28a745; }}
                .section {{ margin: 30px 0; }}
                .insight {{ margin: 10px 0; padding: 15px; border-left: 4px solid #ccc; }}
                .insight.critical {{ border-color: #dc3545; }}
                .insight.warning {{ border-color: #ffc107; }}
                .insight.success {{ border-color: #28a745; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Splunk MCP Performance Test Report</h1>
                <div class="grade {executive['overall_grade']}">{executive["overall_grade"]}</div>
                <p><strong>Status:</strong> {executive["overall_status"]}</p>
                <p><strong>Tests Passed:</strong> {executive["tests_passed"]}/{executive["total_tests"]} ({executive["test_success_rate"]:.1%})</p>
            </div>
            
            <div class="section">
                <h2>Key Metrics</h2>
                <div class="metric">
                    <strong>Max Concurrent Users:</strong><br>
                    {executive["key_metrics"]["max_concurrent_users"]:,} / {executive["key_metrics"]["target_concurrent_users"]:,}
                </div>
                <div class="metric">
                    <strong>Avg Response Time:</strong><br>
                    {executive["key_metrics"]["avg_response_time"]}s / {executive["key_metrics"]["target_response_time"]}s
                </div>
            </div>
        """
        
        # Add critical issues
        if executive["critical_issues"]:
            html += """
            <div class="section">
                <h2>Critical Issues</h2>
            """
            for issue in executive["critical_issues"]:
                html += f"""
                <div class="insight critical">
                    <strong>{issue["test_name"]}</strong>
                    <ul>
                """
                for error in issue.get("errors", []):
                    html += f"<li>{error}</li>"
                html += "</ul></div>"
            html += "</div>"
        
        # Add achievements
        if executive["achievements"]:
            html += """
            <div class="section">
                <h2>Achievements</h2>
                <ul>
            """
            for achievement in executive["achievements"]:
                html += f"<li class='success'>{achievement}</li>"
            html += "</ul></div>"
        
        # Add recommendations
        html += """
        <div class="section">
            <h2>Recommendations</h2>
        """
        for rec in analysis["recommendations"]:
            priority_class = "critical" if rec["priority"] == "critical" else "warning"
            html += f"""
            <div class="insight {priority_class}">
                <h3>{rec["title"]}</h3>
                <ul>
            """
            for action in rec["actions"]:
                html += f"<li>{action}</li>"
            html += "</ul></div>"
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return html

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Analyze performance test results")
    parser.add_argument("results_file", help="Path to performance test results JSON file")
    parser.add_argument("--config", help="Path to configuration YAML file")
    parser.add_argument("--output", "-o", default="console", choices=["console", "json", "html"], 
                       help="Output format")
    parser.add_argument("--export-path", help="Path to export analysis results")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    try:
        analyzer = PerformanceResultsAnalyzer(args.results_file, args.config)
        analysis = analyzer.analyze_comprehensive()
        
        if args.output == "console":
            print_console_summary(analysis)
        elif args.output == "json":
            if args.export_path:
                with open(args.export_path, 'w') as f:
                    json.dump(analysis, f, indent=2, default=str)
                print(f"Analysis exported to: {args.export_path}")
            else:
                print(json.dumps(analysis, indent=2, default=str))
        elif args.output == "html":
            export_path = args.export_path or "performance_report.html"
            analyzer.generate_html_report(export_path)
        
    except Exception as e:
        print(f"Error analyzing results: {e}")
        sys.exit(1)

def print_console_summary(analysis: Dict[str, Any]):
    """Print console summary of analysis"""
    executive = analysis["executive_summary"]
    
    print("\n" + "="*80)
    print("PERFORMANCE TEST ANALYSIS SUMMARY")
    print("="*80)
    
    # Overall grade and status
    grade_symbol = {"A": "🏆", "B": "✅", "C": "⚠️", "D": "❌", "F": "💥"}.get(executive["overall_grade"], "❓")
    print(f"\nOverall Grade: {grade_symbol} {executive['overall_grade']} - {executive['overall_status']}")
    print(f"Tests Passed: {executive['tests_passed']}/{executive['total_tests']} ({executive['test_success_rate']:.1%})")
    
    # Key metrics
    print("\nKey Performance Metrics:")
    print(f"  Concurrent Users: {executive['key_metrics']['max_concurrent_users']:,} / {executive['key_metrics']['target_concurrent_users']:,}")
    print(f"  Response Time: {executive['key_metrics']['avg_response_time']}s / {executive['key_metrics']['target_response_time']}s")
    
    # Critical issues
    if executive["critical_issues"]:
        print("\n🚨 Critical Issues:")
        for issue in executive["critical_issues"][:3]:  # Show top 3
            print(f"  • {issue['test_name']}")
            for error in issue.get("errors", [])[:2]:  # Show top 2 errors
                print(f"    - {error}")
    
    # Achievements
    if executive["achievements"]:
        print("\n🎯 Achievements:")
        for achievement in executive["achievements"][:5]:  # Show top 5
            print(f"  ✓ {achievement}")
    
    # Top recommendations
    if analysis["recommendations"]:
        print("\n💡 Top Recommendations:")
        for rec in analysis["recommendations"][:3]:  # Show top 3
            priority_symbol = {"critical": "🔥", "high": "⚡", "medium": "📋"}.get(rec["priority"], "📝")
            print(f"  {priority_symbol} {rec['title']}")
            for action in rec["actions"][:2]:  # Show top 2 actions
                print(f"    - {action}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()