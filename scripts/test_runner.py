#!/usr/bin/env python3
"""
Test Runner for Homeschool Application
Comprehensive test execution with reporting and Docker integration
"""

import subprocess
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import argparse

# Add the app directory to the path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "app"))


class TestRunner:
    """Comprehensive test runner with reporting"""
    
    def __init__(self, output_dir: str = "test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}
        self.start_time = time.time()
        
    def run_all_tests(self, fast_mode: bool = False):
        """Run all test suites"""
        print("🧪 Homeschool Application Test Suite")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Output directory: {self.output_dir.absolute()}")
        print("=" * 60)
        
        # Test categories
        test_suites = [
            ("unit", "Unit Tests", not fast_mode),
            ("integration", "Integration Tests", not fast_mode),
            ("function_calling", "Function Calling Tests", True),
            ("ai_agent", "AI Agent Tests", True),
        ]
        
        for suite_name, suite_description, should_run in test_suites:
            if should_run:
                print(f"\n🔍 Running {suite_description}...")
                self._run_test_suite(suite_name, suite_description)
            else:
                print(f"\n⏭️  Skipping {suite_description} (fast mode)")
                self.results[suite_name] = {"skipped": True, "reason": "fast_mode"}
        
        # Run additional diagnostics if not in fast mode
        if not fast_mode:
            print(f"\n🔧 Running System Diagnostics...")
            self._run_system_diagnostics()
        
        # Generate comprehensive report
        self._generate_comprehensive_report()
        
        # Return overall success status
        return self._calculate_overall_success()
    
    def _run_test_suite(self, suite_name: str, suite_description: str):
        """Run a specific test suite"""
        start_time = time.time()
        
        try:
            # Determine pytest command based on suite
            if suite_name == "unit":
                cmd = ["python", "-m", "pytest", "tests/unit/", "-v", "--tb=short"]
            elif suite_name == "integration":
                cmd = ["python", "-m", "pytest", "tests/integration/", "-v", "--tb=short"]
            elif suite_name == "function_calling":
                cmd = ["python", "-m", "pytest", "-m", "function_calling", "-v", "--tb=short"]
            elif suite_name == "ai_agent":
                cmd = ["python", "-m", "pytest", "-m", "ai_agent", "-v", "--tb=short"]
            else:
                cmd = ["python", "-m", "pytest", f"tests/{suite_name}/", "-v", "--tb=short"]
            
            # Add JSON reporting
            json_report = self.output_dir / f"{suite_name}_report.json"
            cmd.extend(["--json-report", f"--json-report-file={json_report}"])
            
            # Run the tests
            print(f"   Command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            elapsed = time.time() - start_time
            
            # Parse results
            self.results[suite_name] = {
                "command": " ".join(cmd),
                "exit_code": result.returncode,
                "elapsed_time": elapsed,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
            # Try to load JSON report if available
            if json_report.exists():
                try:
                    with open(json_report) as f:
                        json_data = json.load(f)
                        self.results[suite_name]["json_report"] = json_data
                except Exception as e:
                    print(f"   ⚠️  Could not parse JSON report: {e}")
            
            # Print summary
            if result.returncode == 0:
                print(f"   ✅ {suite_description} passed ({elapsed:.2f}s)")
            else:
                print(f"   ❌ {suite_description} failed ({elapsed:.2f}s)")
                print(f"   📋 Exit code: {result.returncode}")
                
                # Print first few lines of error for immediate feedback
                if result.stderr:
                    error_lines = result.stderr.split('\n')[:5]
                    for line in error_lines:
                        if line.strip():
                            print(f"      {line}")
                elif result.stdout:
                    stdout_lines = result.stdout.split('\n')[-10:]  # Last few lines
                    for line in stdout_lines:
                        if line.strip() and ('FAILED' in line or 'ERROR' in line):
                            print(f"      {line}")
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ {suite_description} crashed ({elapsed:.2f}s): {e}")
            self.results[suite_name] = {
                "success": False,
                "error": str(e),
                "elapsed_time": elapsed
            }
    
    def _run_system_diagnostics(self):
        """Run system diagnostics"""
        start_time = time.time()
        
        try:
            # Run our debug script
            debug_script = PROJECT_ROOT / "scripts" / "debug_ai_agent.py"
            
            if debug_script.exists():
                print("   Running AI Agent diagnostics...")
                result = subprocess.run(
                    ["python", str(debug_script)],
                    capture_output=True,
                    text=True,
                    cwd=PROJECT_ROOT,
                    timeout=300  # 5 minute timeout
                )
                
                elapsed = time.time() - start_time
                
                self.results["diagnostics"] = {
                    "exit_code": result.returncode,
                    "elapsed_time": elapsed,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "success": result.returncode == 0
                }
                
                if result.returncode == 0:
                    print(f"   ✅ System diagnostics completed ({elapsed:.2f}s)")
                else:
                    print(f"   ⚠️  System diagnostics had issues ({elapsed:.2f}s)")
            else:
                print("   ⚠️  Debug script not found, skipping diagnostics")
                self.results["diagnostics"] = {"skipped": True, "reason": "script_not_found"}
                
        except subprocess.TimeoutExpired:
            print("   ⚠️  System diagnostics timed out")
            self.results["diagnostics"] = {"error": "timeout", "success": False}
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ System diagnostics failed ({elapsed:.2f}s): {e}")
            self.results["diagnostics"] = {"error": str(e), "success": False, "elapsed_time": elapsed}
    
    def _generate_comprehensive_report(self):
        """Generate comprehensive test report"""
        total_elapsed = time.time() - self.start_time
        
        print(f"\n📋 Test Results Summary")
        print("=" * 60)
        
        # Count results
        passed = sum(1 for r in self.results.values() if r.get("success") == True)
        failed = sum(1 for r in self.results.values() if r.get("success") == False)
        skipped = sum(1 for r in self.results.values() if r.get("skipped") == True)
        
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⏭️  Skipped: {skipped}")
        print(f"⏱️  Total time: {total_elapsed:.2f}s")
        
        # Detailed results
        print(f"\n📊 Detailed Results:")
        for suite_name, result in self.results.items():
            if result.get("skipped"):
                print(f"   ⏭️  {suite_name}: Skipped ({result.get('reason', 'unknown')})")
            elif result.get("success"):
                elapsed = result.get("elapsed_time", 0)
                print(f"   ✅ {suite_name}: Passed ({elapsed:.2f}s)")
            else:
                elapsed = result.get("elapsed_time", 0)
                error = result.get("error", "Unknown error")
                print(f"   ❌ {suite_name}: Failed ({elapsed:.2f}s) - {error}")
        
        # Generate detailed JSON report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_elapsed": total_elapsed,
            "summary": {
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "total": len(self.results)
            },
            "results": self.results
        }
        
        # Save comprehensive report
        report_file = self.output_dir / "comprehensive_test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"\n📄 Comprehensive report saved to: {report_file}")
        
        # Generate HTML report if possible
        self._generate_html_report(report_data)
        
        # Generate recommendations
        self._generate_recommendations()
    
    def _generate_html_report(self, report_data: Dict):
        """Generate HTML test report"""
        try:
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Homeschool Application Test Report</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric {{ background: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; }}
        .passed {{ background: #d4edda; }}
        .failed {{ background: #f8d7da; }}
        .skipped {{ background: #fff3cd; }}
        .results {{ margin: 20px 0; }}
        .result-item {{ margin: 10px 0; padding: 15px; border-radius: 5px; }}
        .result-item.passed {{ background: #d4edda; }}
        .result-item.failed {{ background: #f8d7da; }}
        .result-item.skipped {{ background: #fff3cd; }}
        pre {{ background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }}
        .collapsible {{ cursor: pointer; }}
        .content {{ display: none; margin-top: 10px; }}
    </style>
    <script>
        function toggleContent(id) {{
            var content = document.getElementById(id);
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
        }}
    </script>
</head>
<body>
    <div class="header">
        <h1>🧪 Homeschool Application Test Report</h1>
        <p><strong>Generated:</strong> {report_data['timestamp']}</p>
        <p><strong>Total Time:</strong> {report_data['total_elapsed']:.2f} seconds</p>
    </div>
    
    <div class="summary">
        <div class="metric passed">
            <h3>{report_data['summary']['passed']}</h3>
            <p>Passed</p>
        </div>
        <div class="metric failed">
            <h3>{report_data['summary']['failed']}</h3>
            <p>Failed</p>
        </div>
        <div class="metric skipped">
            <h3>{report_data['summary']['skipped']}</h3>
            <p>Skipped</p>
        </div>
        <div class="metric">
            <h3>{report_data['summary']['total']}</h3>
            <p>Total</p>
        </div>
    </div>
    
    <div class="results">
        <h2>📊 Detailed Results</h2>
"""
            
            for suite_name, result in report_data['results'].items():
                if result.get("skipped"):
                    status_class = "skipped"
                    status_icon = "⏭️"
                    status_text = f"Skipped ({result.get('reason', 'unknown')})"
                elif result.get("success"):
                    status_class = "passed"
                    status_icon = "✅"
                    status_text = f"Passed ({result.get('elapsed_time', 0):.2f}s)"
                else:
                    status_class = "failed"
                    status_icon = "❌"
                    status_text = f"Failed ({result.get('elapsed_time', 0):.2f}s)"
                
                html_content += f"""
        <div class="result-item {status_class}">
            <h3>{status_icon} {suite_name.title()}</h3>
            <p><strong>Status:</strong> {status_text}</p>
"""
                
                if result.get("stdout") or result.get("stderr"):
                    html_content += f"""
            <div class="collapsible" onclick="toggleContent('{suite_name}_details')">
                <strong>🔍 View Details</strong>
            </div>
            <div id="{suite_name}_details" class="content">
"""
                    if result.get("stdout"):
                        html_content += f"<h4>Output:</h4><pre>{result['stdout'][:2000]}{'...' if len(result.get('stdout', '')) > 2000 else ''}</pre>"
                    if result.get("stderr"):
                        html_content += f"<h4>Errors:</h4><pre>{result['stderr'][:2000]}{'...' if len(result.get('stderr', '')) > 2000 else ''}</pre>"
                    html_content += "</div>"
                
                html_content += "</div>"
            
            html_content += """
    </div>
</body>
</html>"""
            
            html_file = self.output_dir / "test_report.html"
            with open(html_file, 'w') as f:
                f.write(html_content)
            
            print(f"📄 HTML report saved to: {html_file}")
            
        except Exception as e:
            print(f"⚠️  Could not generate HTML report: {e}")
    
    def _generate_recommendations(self):
        """Generate recommendations based on test results"""
        print(f"\n💡 Recommendations:")
        
        recommendations = []
        
        # Check for common failure patterns
        for suite_name, result in self.results.items():
            if not result.get("success") and not result.get("skipped"):
                error_output = result.get("stderr", "") + result.get("stdout", "")
                
                if "connection" in error_output.lower():
                    recommendations.append("Check network connectivity (database, Ollama, etc.)")
                if "ollama" in error_output.lower():
                    recommendations.append("Ensure Ollama is running and accessible")
                if "database" in error_output.lower():
                    recommendations.append("Check database connection and run migrations")
                if "import" in error_output.lower():
                    recommendations.append("Check Python dependencies and environment setup")
        
        # Remove duplicates
        recommendations = list(set(recommendations))
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        else:
            if self._calculate_overall_success():
                print("   🎉 All tests passing! System appears to be working correctly.")
            else:
                print("   📋 Check individual test outputs for specific issues.")
        
        print(f"\n🔧 For detailed debugging, run: python scripts/debug_ai_agent.py")
    
    def _calculate_overall_success(self) -> bool:
        """Calculate overall test success"""
        for result in self.results.values():
            if result.get("success") == False:
                return False
        return True
    
    def run_single_test(self, test_name: str):
        """Run a single test or test file"""
        print(f"🧪 Running single test: {test_name}")
        
        cmd = ["python", "-m", "pytest", test_name, "-v", "--tb=short"]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        
        return result.returncode == 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Homeschool Application Test Runner")
    parser.add_argument("--fast", action="store_true", help="Run only essential tests")
    parser.add_argument("--output-dir", default="test_results", help="Output directory for test results")
    parser.add_argument("--single", help="Run a single test file or pattern")
    
    args = parser.parse_args()
    
    runner = TestRunner(output_dir=args.output_dir)
    
    if args.single:
        success = runner.run_single_test(args.single)
        sys.exit(0 if success else 1)
    else:
        success = runner.run_all_tests(fast_mode=args.fast)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 