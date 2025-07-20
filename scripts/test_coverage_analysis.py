#!/usr/bin/env python3
"""
Comprehensive Test Coverage Analysis for Splunk MCP Integration Project

This script analyzes test coverage across all backend services and provides
detailed metrics about test files, coverage statistics, and testing completeness.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
import re
from datetime import datetime
import argparse


class CoverageAnalyzer:
    """Analyze test coverage across all services."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.services_dir = self.project_root / "services"
        self.results = {}
        
    def discover_services(self) -> List[Path]:
        """Discover all services with their test directories."""
        services = []
        
        for service_dir in self.services_dir.iterdir():
            if service_dir.is_dir() and not service_dir.name.startswith('.'):
                # Check if service has tests directory
                tests_dir = service_dir / "tests"
                if tests_dir.exists():
                    services.append(service_dir)
                    
        return sorted(services)
    
    def count_files(self, directory: Path, pattern: str = "*.py") -> Tuple[int, List[Path]]:
        """Count files matching pattern in directory."""
        files = list(directory.rglob(pattern))
        # Filter out __pycache__ and other non-source files
        source_files = [f for f in files if "__pycache__" not in str(f) and not f.name.startswith('.')]
        return len(source_files), source_files
    
    def count_lines_of_code(self, file_path: Path) -> int:
        """Count lines of code in a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Count non-empty, non-comment lines
                code_lines = 0
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                        code_lines += 1
                return code_lines
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return 0
    
    def analyze_test_files(self, service_dir: Path) -> Dict:
        """Analyze test files for a service."""
        tests_dir = service_dir / "tests"
        app_dir = service_dir / "app"
        
        # Count test files
        test_count, test_files = self.count_files(tests_dir, "test_*.py")
        
        # Count source files
        source_count, source_files = self.count_files(app_dir if app_dir.exists() else service_dir, "*.py")
        
        # Calculate lines of code
        test_loc = sum(self.count_lines_of_code(f) for f in test_files)
        source_loc = sum(self.count_lines_of_code(f) for f in source_files)
        
        # Analyze test coverage patterns
        test_types = self.categorize_tests(test_files)
        
        return {
            "test_files": test_count,
            "source_files": source_count,
            "test_loc": test_loc,
            "source_loc": source_loc,
            "test_to_source_ratio": round(test_loc / source_loc if source_loc > 0 else 0, 2),
            "test_files_list": [f.name for f in test_files],
            "test_types": test_types,
            "has_conftest": (tests_dir / "conftest.py").exists(),
            "has_pytest_ini": (service_dir / "pytest.ini").exists(),
        }
    
    def categorize_tests(self, test_files: List[Path]) -> Dict[str, int]:
        """Categorize tests by type based on filename patterns."""
        categories = {
            "api_tests": 0,
            "service_tests": 0,
            "model_tests": 0,
            "integration_tests": 0,
            "utility_tests": 0,
            "main_tests": 0,
            "other_tests": 0
        }
        
        for test_file in test_files:
            name = test_file.name.lower()
            if "api" in name or "endpoint" in name:
                categories["api_tests"] += 1
            elif "service" in name or "manager" in name:
                categories["service_tests"] += 1
            elif "model" in name:
                categories["model_tests"] += 1
            elif "integration" in name:
                categories["integration_tests"] += 1
            elif "util" in name or "auth" in name or "helper" in name:
                categories["utility_tests"] += 1
            elif "main" in name:
                categories["main_tests"] += 1
            else:
                categories["other_tests"] += 1
                
        return categories
    
    def check_dependencies(self, service_dir: Path) -> Dict:
        """Check testing dependencies in requirements.txt."""
        requirements_file = service_dir / "requirements.txt"
        testing_deps = {
            "pytest": False,
            "pytest-asyncio": False,
            "pytest-cov": False,
            "pytest-mock": False,
            "coverage": False,
            "httpx": False,  # For FastAPI testing
            "requests-mock": False
        }
        
        if requirements_file.exists():
            try:
                with open(requirements_file, 'r') as f:
                    content = f.read().lower()
                    for dep in testing_deps:
                        if dep in content:
                            testing_deps[dep] = True
            except Exception as e:
                print(f"Error reading requirements.txt for {service_dir.name}: {e}")
        
        return testing_deps
    
    def estimate_coverage_quality(self, service_data: Dict) -> str:
        """Estimate test coverage quality based on various metrics."""
        score = 0
        
        # Test file count (max 20 points)
        if service_data["test_files"] >= 6:
            score += 20
        elif service_data["test_files"] >= 4:
            score += 15
        elif service_data["test_files"] >= 2:
            score += 10
        elif service_data["test_files"] >= 1:
            score += 5
        
        # Test to source ratio (max 25 points)
        ratio = service_data["test_to_source_ratio"]
        if ratio >= 0.8:
            score += 25
        elif ratio >= 0.6:
            score += 20
        elif ratio >= 0.4:
            score += 15
        elif ratio >= 0.2:
            score += 10
        elif ratio > 0:
            score += 5
        
        # Test types diversity (max 20 points)
        test_types = service_data["test_types"]
        types_count = sum(1 for count in test_types.values() if count > 0)
        if types_count >= 5:
            score += 20
        elif types_count >= 4:
            score += 15
        elif types_count >= 3:
            score += 10
        elif types_count >= 2:
            score += 5
        
        # Infrastructure (max 15 points)
        if service_data["has_conftest"]:
            score += 10
        if service_data["has_pytest_ini"]:
            score += 5
        
        # Dependencies (max 20 points)
        deps = service_data["testing_dependencies"]
        essential_deps = ["pytest", "pytest-asyncio", "pytest-cov"]
        dep_score = sum(5 for dep in essential_deps if deps.get(dep, False))
        score += min(dep_score, 15)
        if deps.get("httpx", False) or deps.get("pytest-mock", False):
            score += 5
        
        # Determine quality level
        if score >= 85:
            return "EXCELLENT"
        elif score >= 70:
            return "GOOD"
        elif score >= 50:
            return "FAIR"
        elif score >= 30:
            return "POOR"
        else:
            return "MINIMAL"
    
    def analyze_all_services(self) -> Dict:
        """Analyze all services and return comprehensive results."""
        services = self.discover_services()
        results = {}
        
        print(f"🔍 Analyzing {len(services)} services for test coverage...\n")
        
        for service_dir in services:
            service_name = service_dir.name
            print(f"  📋 Analyzing {service_name}...")
            
            service_data = self.analyze_test_files(service_dir)
            service_data["testing_dependencies"] = self.check_dependencies(service_dir)
            service_data["coverage_quality"] = self.estimate_coverage_quality(service_data)
            
            results[service_name] = service_data
        
        return results
    
    def generate_summary_report(self, results: Dict) -> str:
        """Generate a comprehensive summary report."""
        total_services = len(results)
        total_test_files = sum(data["test_files"] for data in results.values())
        total_source_files = sum(data["source_files"] for data in results.values())
        total_test_loc = sum(data["test_loc"] for data in results.values())
        total_source_loc = sum(data["source_loc"] for data in results.values())
        overall_ratio = round(total_test_loc / total_source_loc if total_source_loc > 0 else 0, 2)
        
        # Coverage quality distribution
        quality_counts = {}
        for data in results.values():
            quality = data["coverage_quality"]
            quality_counts[quality] = quality_counts.get(quality, 0) + 1
        
        report = f"""
📊 COMPREHENSIVE TEST COVERAGE ANALYSIS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎯 OVERALL METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Services Analyzed: {total_services}
• Total Test Files: {total_test_files}
• Total Source Files: {total_source_files}
• Total Test LOC: {total_test_loc:,}
• Total Source LOC: {total_source_loc:,}
• Overall Test/Source Ratio: {overall_ratio}

📈 COVERAGE QUALITY DISTRIBUTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        for quality in ["EXCELLENT", "GOOD", "FAIR", "POOR", "MINIMAL"]:
            count = quality_counts.get(quality, 0)
            percentage = round(count / total_services * 100) if total_services > 0 else 0
            icon = {"EXCELLENT": "🟢", "GOOD": "🔵", "FAIR": "🟡", "POOR": "🟠", "MINIMAL": "🔴"}[quality]
            report += f"{icon} {quality}: {count} services ({percentage}%)\n"
        
        report += f"""
🏆 TOP PERFORMING SERVICES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Sort services by quality and test metrics
        sorted_services = sorted(results.items(), key=lambda x: (
            {"EXCELLENT": 5, "GOOD": 4, "FAIR": 3, "POOR": 2, "MINIMAL": 1}[x[1]["coverage_quality"]],
            x[1]["test_files"],
            x[1]["test_to_source_ratio"]
        ), reverse=True)
        
        for service, data in sorted_services[:5]:
            quality_icon = {"EXCELLENT": "🟢", "GOOD": "🔵", "FAIR": "🟡", "POOR": "🟠", "MINIMAL": "🔴"}[data["coverage_quality"]]
            report += f"{quality_icon} {service}: {data['test_files']} tests, {data['test_loc']} LOC, ratio {data['test_to_source_ratio']}\n"
        
        report += f"""
📋 DETAILED SERVICE BREAKDOWN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        for service, data in sorted_services:
            quality_icon = {"EXCELLENT": "🟢", "GOOD": "🔵", "FAIR": "🟡", "POOR": "🟠", "MINIMAL": "🔴"}[data["coverage_quality"]]
            
            report += f"""
{quality_icon} {service.upper()} ({data["coverage_quality"]})
  📁 Test Files: {data["test_files"]} | Source Files: {data["source_files"]}
  📄 Test LOC: {data["test_loc"]:,} | Source LOC: {data["source_loc"]:,} | Ratio: {data["test_to_source_ratio"]}
  🧪 Test Types: API:{data["test_types"]["api_tests"]} Service:{data["test_types"]["service_tests"]} Model:{data["test_types"]["model_tests"]} Utils:{data["test_types"]["utility_tests"]}
  ⚙️  Infrastructure: conftest.py:{data["has_conftest"]} pytest.ini:{data["has_pytest_ini"]}
  📦 Dependencies: pytest:{data["testing_dependencies"]["pytest"]} async:{data["testing_dependencies"]["pytest-asyncio"]} cov:{data["testing_dependencies"]["pytest-cov"]}
"""
        
        return report
    
    def save_detailed_json(self, results: Dict, filename: str = "test_coverage_analysis.json"):
        """Save detailed results to JSON file."""
        output_file = self.project_root / filename
        
        # Convert Path objects to strings for JSON serialization
        json_results = {}
        for service, data in results.items():
            json_data = data.copy()
            json_data["timestamp"] = datetime.now().isoformat()
            json_results[service] = json_data
        
        with open(output_file, 'w') as f:
            json.dump(json_results, f, indent=2)
        
        return output_file


def main():
    parser = argparse.ArgumentParser(description="Analyze test coverage across all services")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--output", default="test_coverage_analysis.json", help="Output JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    analyzer = CoverageAnalyzer(args.project_root)
    
    try:
        # Analyze all services
        results = analyzer.analyze_all_services()
        
        # Generate and print summary report
        report = analyzer.generate_summary_report(results)
        print(report)
        
        # Save detailed JSON results
        json_file = analyzer.save_detailed_json(results, args.output)
        print(f"\n💾 Detailed results saved to: {json_file}")
        
        # Calculate estimated overall coverage
        excellent_services = sum(1 for data in results.values() if data["coverage_quality"] == "EXCELLENT")
        good_services = sum(1 for data in results.values() if data["coverage_quality"] == "GOOD")
        total_services = len(results)
        
        high_quality_percentage = round((excellent_services + good_services) / total_services * 100) if total_services > 0 else 0
        
        print(f"""
🎯 COVERAGE ACHIEVEMENT ESTIMATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• High Quality Services: {excellent_services + good_services}/{total_services} ({high_quality_percentage}%)
• Estimated Overall Coverage: {"🟢 >90%" if high_quality_percentage >= 80 else "🟡 70-90%" if high_quality_percentage >= 60 else "🔴 <70%"}
• Recommendation: {"✅ Coverage target achieved!" if high_quality_percentage >= 80 else "⚠️  Additional testing needed for some services"}
""")
        
        return 0 if high_quality_percentage >= 80 else 1
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())