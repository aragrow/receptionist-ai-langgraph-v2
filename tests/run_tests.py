# ============================== run_tests.py ==============================
#!/usr/bin/env python3
"""
Master Test Controller for AI Receptionist App
Runs all test categories and reports results in a tabulated format.

# Run the master test controller
python run_tests.py
"""

import subprocess
import sys
import time
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
from tabulate import tabulate
import json
import re


@dataclass
class TestResult:
    """Test result data structure."""
    category: str
    file_path: str
    passed: int
    failed: int
    errors: int
    skipped: int
    warnings: int
    duration: float
    status: str
    details: str = ""


class TestController:
    """Master test controller for running and reporting test results."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.test_categories = {
            "Unit Tests - Models": "tests/test_unit_models.py",
            "Unit Tests - Utilities": "tests/test_utilities.py", 
            "Unit Tests - Services": "tests/test_services.py",
            "Node/Workflow Tests": "tests/test_nodes.py",
            "Integration Tests": "tests/test_integration.py",
            "Access Control Tests": "tests/test_access_control.py",
            "Performance Tests": "tests/test_performance.py",
            "Regression Tests": "tests/test_regression.py",
            "Workflow Tests": "tests/test_workflow.py"
        }
    
    def run_pytest_category(self, category: str, file_path: str) -> TestResult:
        """Run pytest for a specific test category."""
        print(f"🧪 Running {category}...")
        
        start_time = time.time()
        
        try:
            # Run pytest with JSON report
            cmd = [
                sys.executable, "-m", "pytest", 
                file_path,
                "--tb=short",
                "--json-report",
                "--json-report-file=temp_report.json",
                "-v"
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start_time
            
            # Parse JSON report if available
            report_data = self._parse_json_report()
            
            if result.returncode == 0:
                status = "✅ PASS"
            elif result.returncode == 1:
                status = "❌ FAIL" 
            else:
                status = "⚠️ ERROR"
            
            # Extract test counts from output
            passed, failed, errors, skipped, warnings = self._parse_pytest_output(result.stdout)
            
            return TestResult(
                category=category,
                file_path=file_path,
                passed=passed,
                failed=failed,
                errors=errors,
                skipped=skipped,
                warnings=warnings,
                duration=duration,
                status=status,
                details=result.stdout.split('\n')[-3] if result.stdout else ""
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                category=category,
                file_path=file_path,
                passed=0, failed=0, errors=1, skipped=0, warnings=0,
                duration=300.0,
                status="⏰ TIMEOUT",
                details="Test execution timed out after 5 minutes"
            )
        except FileNotFoundError:
            return TestResult(
                category=category,
                file_path=file_path,
                passed=0, failed=0, errors=0, skipped=0, warnings=0,
                duration=0.0,
                status="📁 NOT FOUND",
                details=f"Test file {file_path} does not exist"
            )
        except Exception as e:
            return TestResult(
                category=category,
                file_path=file_path,
                passed=0, failed=0, errors=1, skipped=0, warnings=0,
                duration=0.0,
                status="💥 EXCEPTION",
                details=str(e)
            )
    
    def _parse_json_report(self) -> Dict[str, Any]:
        """Parse pytest JSON report if available."""
        try:
            with open("temp_report.json", "r") as f:
                return json.load(f)
        except:
            return {}
    
    def _parse_pytest_output(self, output: str) -> tuple:
        """Parse pytest output to extract test counts."""
        passed = failed = errors = skipped = warnings = 0
        
        # Look for summary line like: "2 passed, 1 failed, 3 warnings in 1.23s"
        summary_pattern = r'(\d+)\s+(\w+)(?:,\s*)?'
        matches = re.findall(summary_pattern, output)
        
        for count, status in matches:
            count = int(count)
            if 'passed' in status:
                passed = count
            elif 'failed' in status:
                failed = count
            elif 'error' in status:
                errors = count
            elif 'skipped' in status:
                skipped = count
            elif 'warning' in status:
                warnings = count
        
        return passed, failed, errors, skipped, warnings
    
    def run_all_tests(self) -> None:
        """Run all test categories."""
        print("🚀 Starting AI Receptionist Test Suite")
        print("=" * 60)
        
        total_start = time.time()
        
        for category, file_path in self.test_categories.items():
            result = self.run_pytest_category(category, file_path)
            self.results.append(result)
        
        total_duration = time.time() - total_start
        
        # Clean up temp files
        try:
            Path("temp_report.json").unlink(missing_ok=True)
        except:
            pass
        
        self.print_summary_report(total_duration)
    
    def print_summary_report(self, total_duration: float) -> None:
        """Print a beautiful tabulated summary report."""
        print("\n" + "=" * 80)
        print("📊 TEST EXECUTION SUMMARY")
        print("=" * 80)
        
        # Prepare table data
        table_data = []
        total_passed = total_failed = total_errors = total_skipped = total_warnings = 0
        
        for result in self.results:
            table_data.append([
                result.category,
                result.status,
                result.passed,
                result.failed,
                result.errors,
                result.skipped,
                result.warnings,
                f"{result.duration:.2f}s"
            ])
            
            total_passed += result.passed
            total_failed += result.failed
            total_errors += result.errors
            total_skipped += result.skipped
            total_warnings += result.warnings
        
        # Add totals row
        table_data.append([
            "─" * 20,
            "─" * 10,
            "─" * 6,
            "─" * 6,
            "─" * 6,
            "─" * 7,
            "─" * 8,
            "─" * 8
        ])
        table_data.append([
            "TOTALS",
            self._get_overall_status(),
            total_passed,
            total_failed,
            total_errors,
            total_skipped,
            total_warnings,
            f"{total_duration:.2f}s"
        ])
        
        # Print main results table
        headers = ["Category", "Status", "Passed", "Failed", "Errors", "Skipped", "Warnings", "Duration"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Print detailed failures if any
        self._print_failure_details()
        
        # Print final summary
        self._print_final_summary(total_passed, total_failed, total_errors, total_duration)
    
    def _get_overall_status(self) -> str:
        """Determine overall test suite status."""
        if any(r.status.startswith("❌") or r.status.startswith("💥") for r in self.results):
            return "❌ FAIL"
        elif any(r.status.startswith("⚠️") or r.status.startswith("⏰") for r in self.results):
            return "⚠️ ISSUES"
        elif any(r.status.startswith("📁") for r in self.results):
            return "📁 INCOMPLETE"
        else:
            return "✅ PASS"
    
    def _print_failure_details(self) -> None:
        """Print detailed information about failed tests."""
        failed_tests = [r for r in self.results if not r.status.startswith("✅")]
        
        if failed_tests:
            print("\n" + "=" * 80)
            print("🔍 DETAILED FAILURE REPORT")
            print("=" * 80)
            
            for result in failed_tests:
                print(f"\n📂 {result.category}")
                print(f"   Status: {result.status}")
                print(f"   File: {result.file_path}")
                if result.details:
                    print(f"   Details: {result.details}")
    
    def _print_final_summary(self, passed: int, failed: int, errors: int, duration: float) -> None:
        """Print final execution summary."""
        print("\n" + "=" * 80)
        print("🎯 FINAL SUMMARY")
        print("=" * 80)
        
        summary_data = [
            ["Total Tests Passed", f"✅ {passed}"],
            ["Total Tests Failed", f"❌ {failed}"],
            ["Total Errors", f"💥 {errors}"],
            ["Total Execution Time", f"⏱️ {duration:.2f} seconds"],
            ["Test Categories", f"📁 {len(self.test_categories)}"],
        ]
        
        print(tabulate(summary_data, tablefmt="simple"))
        
        # Exit code based on results
        if failed > 0 or errors > 0:
            print(f"\n❌ Test suite FAILED with {failed} failures and {errors} errors")
            sys.exit(1)
        else:
            print(f"\n✅ All tests PASSED! 🎉")
            sys.exit(0)


def main():
    """Main entry point."""
    controller = TestController()
    controller.run_all_tests()


if __name__ == "__main__":
    main()