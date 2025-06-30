#!/usr/bin/env python3
"""
Enhanced Test Runner
Comprehensive test runner that respects environment configuration flags
Supports both Docker and local development environments
"""

import subprocess
import sys
import time
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_env_bool(var_name: str, default: bool = False) -> bool:
    """Get boolean value from environment variable"""
    value = os.getenv(var_name, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')

def get_env_int(var_name: str, default: int) -> int:
    """Get integer value from environment variable"""
    try:
        return int(os.getenv(var_name, str(default)))
    except ValueError:
        return default

class TestRunner:
    def __init__(self, args):
        self.args = args
        self.output_dir = Path("test_results")
        self.output_dir.mkdir(exist_ok=True)
        self.results = []
        self.start_time = time.time()
        
        # Load configuration from environment or override with args
        self.config = {
            'run_unit_tests': args.unit or get_env_bool('RUN_UNIT_TESTS', True),
            'run_integration_tests': args.integration or get_env_bool('RUN_INTEGRATION_TESTS', True),
            'run_ai_tests': args.ai or get_env_bool('RUN_AI_TESTS', True),
            'run_database_tests': args.database or get_env_bool('RUN_DATABASE_TESTS', True),
            'run_e2e_tests': args.e2e or get_env_bool('RUN_E2E_TESTS', False),
            'test_timeout': get_env_int('TEST_TIMEOUT', 300),
            'fast_mode': args.fast or get_env_bool('TEST_FAST_MODE', False),
            'comprehensive': args.comprehensive
        }
        
        # Override with command line flags
        if args.comprehensive:
            # Enable all tests for comprehensive mode
            for key in ['run_unit_tests', 'run_integration_tests', 'run_ai_tests', 'run_database_tests', 'run_e2e_tests']:
                self.config[key] = True
        
        if args.skip_external:
            # Skip tests that require external services
            self.config['run_ai_tests'] = False
            self.config['run_database_tests'] = False
            
        self._print_config()
    
    def _print_config(self):
        """Print current test configuration"""
        print(f"🧪 Test Runner Configuration")
        print("=" * 60)
        environment = "Docker" if os.getenv('DOCKER_CONTAINER') else "Local"
        print(f"🌍 Environment: {environment}")
        print(f"⚡ Fast Mode: {self.config['fast_mode']}")
        print(f"🔍 Comprehensive: {self.config['comprehensive']}")
        print()
        print("📋 Test Categories:")
        for key, value in self.config.items():
            if key.startswith('run_') and key != 'comprehensive':
                category = key.replace('run_', '').replace('_', ' ').title()
                status = "✅ Enabled" if value else "⏭️  Disabled"
                print(f"   {category}: {status}")
        print("=" * 60)
    
    def run_tests(self) -> int:
        """Run configured tests"""
        
        if not self._should_run_any_tests():
            print("⏭️  All tests disabled - nothing to run")
            return 0
        
        test_suites = self._build_test_plan()
        
        if not test_suites:
            print("❌ No test suites available to run")
            return 1
        
        print(f"\n🚀 Running {len(test_suites)} test suite(s)...")
        
        overall_success = True
        for suite in test_suites:
            success = self._run_test_suite(suite)
            if not success:
                overall_success = False
        
        self._generate_reports()
        
        if overall_success:
            print("\n🎉 All tests passed!")
            return 0
        else:
            print("\n❌ Some tests failed")
            return 1
    
    def _should_run_any_tests(self) -> bool:
        """Check if any tests should run"""
        return any([
            self.config['run_unit_tests'],
            self.config['run_integration_tests'], 
            self.config['run_ai_tests'],
            self.config['run_database_tests'],
            self.config['run_e2e_tests']
        ])
    
    def _build_test_plan(self) -> List[Dict[str, Any]]:
        """Build test plan based on configuration"""
        test_suites = []
        
        if self.config['run_unit_tests']:
            test_suites.append({
                'name': 'unit_tests',
                'description': 'Unit Tests',
                'command': self._build_pytest_command(['tests/unit/']),
                'critical': True
            })
        
        if self.config['run_integration_tests']:
            test_suites.append({
                'name': 'integration_tests',
                'description': 'Integration Tests',
                'command': self._build_pytest_command(['tests/integration/']),
                'critical': True
            })
        
        if self.config['run_database_tests']:
            test_suites.append({
                'name': 'database_tests',
                'description': 'Database Tests',
                'command': ['python', '-c', '''
import sys
sys.path.insert(0, ".")
from app.database import get_db
from sqlalchemy import text
try:
    db = next(get_db())
    db.execute(text("SELECT 1"))
    print("✅ Database connectivity: OK")
    db.close()
except Exception as e:
    print(f"❌ Database connectivity failed: {e}")
    sys.exit(1)
'''],
                'critical': False
            })
        
        if self.config['run_ai_tests'] and not self.args.skip_external:
            test_suites.append({
                'name': 'ai_tests',
                'description': 'AI Provider Tests',
                'command': ['python', 'enhanced_function_calling_test.py'],
                'critical': False
            })
        
        if self.config['run_e2e_tests'] and not self.config['fast_mode']:
            test_suites.append({
                'name': 'e2e_tests',
                'description': 'End-to-End Tests',
                'command': ['python', 'scripts/debug_ai_agent.py'],
                'critical': False
            })
        
        return test_suites
    
    def _build_pytest_command(self, test_paths: List[str]) -> List[str]:
        """Build pytest command with appropriate flags"""
        cmd = ['python', '-m', 'pytest'] + test_paths
        
        if self.args.verbose:
            cmd.append('-v')
        else:
            cmd.append('-q')
        
        if self.config['fast_mode']:
            cmd.extend(['-x', '--tb=short'])  # Stop on first failure, short traceback
        else:
            cmd.append('--tb=line')
        
        if self.args.html:
            cmd.extend(['--html', str(self.output_dir / 'pytest_report.html'), '--self-contained-html'])
        
        if self.args.json:
            cmd.extend(['--json-report', '--json-report-file', str(self.output_dir / 'pytest_report.json')])
        
        # Add timeout
        timeout = self.config['test_timeout']
        cmd.extend(['--timeout', str(timeout)])
        
        return cmd
    
    def _run_test_suite(self, suite: Dict[str, Any]) -> bool:
        """Run a single test suite"""
        name = suite['name']
        description = suite['description']
        command = suite['command']
        critical = suite.get('critical', True)
        
        print(f"\n🧪 Running {description}...")
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.config['test_timeout']
            )
            
            elapsed = time.time() - start_time
            success = result.returncode == 0
            
            self.results.append({
                'name': name,
                'description': description,
                'success': success,
                'critical': critical,
                'exit_code': result.returncode,
                'elapsed': elapsed,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(command)
            })
            
            if success:
                print(f"   ✅ {description} passed ({elapsed:.2f}s)")
            else:
                icon = "❌" if critical else "⚠️ "
                print(f"   {icon} {description} failed ({elapsed:.2f}s)")
                if result.stderr:
                    # Print first few lines of error for quick debugging
                    error_lines = result.stderr.split('\n')[:5]
                    for line in error_lines:
                        if line.strip():
                            print(f"      {line}")
            
            return success
            
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            print(f"   ⏰ {description} timed out after {elapsed:.2f}s")
            
            self.results.append({
                'name': name,
                'description': description,
                'success': False,
                'critical': critical,
                'error': 'timeout',
                'elapsed': elapsed,
                'command': ' '.join(command)
            })
            
            return False
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   💥 {description} crashed: {e}")
            
            self.results.append({
                'name': name,
                'description': description,
                'success': False,
                'critical': critical,
                'error': str(e),
                'elapsed': elapsed,
                'command': ' '.join(command)
            })
            
            return False
    
    def _generate_reports(self):
        """Generate test reports"""
        total_elapsed = time.time() - self.start_time
        
        # Summary statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - passed_tests
        critical_failures = sum(1 for r in self.results if not r['success'] and r.get('critical', True))
        
        print(f"\n📊 Test Summary:")
        print(f"   ⏱️  Total time: {total_elapsed:.2f}s")
        print(f"   📋 Total tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        if critical_failures > 0:
            print(f"   🚨 Critical failures: {critical_failures}")
        
        # Detailed results
        if failed_tests > 0:
            print(f"\n📋 Failed Tests:")
            for result in self.results:
                if not result['success']:
                    icon = "🚨" if result.get('critical', True) else "⚠️ "
                    print(f"   {icon} {result['description']}: {result.get('error', 'failed')}")
        
        # Save JSON report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_elapsed': total_elapsed,
            'configuration': self.config,
            'summary': {
                'total': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'critical_failures': critical_failures
            },
            'results': self.results
        }
        
        json_file = self.output_dir / "test_report.json"
        with open(json_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"   📄 Report saved: {json_file}")


def main():
    parser = argparse.ArgumentParser(description="Enhanced Test Runner")
    
    # Test category flags
    parser.add_argument('--unit', action='store_true', help='Run unit tests')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--ai', action='store_true', help='Run AI provider tests')
    parser.add_argument('--database', action='store_true', help='Run database tests')
    parser.add_argument('--e2e', action='store_true', help='Run end-to-end tests')
    
    # Control flags
    parser.add_argument('--comprehensive', action='store_true', help='Run all available tests')
    parser.add_argument('--fast', action='store_true', help='Fast mode - skip slow tests')
    parser.add_argument('--skip-external', action='store_true', help='Skip tests requiring external services')
    
    # Output flags
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--html', action='store_true', help='Generate HTML report')
    parser.add_argument('--json', action='store_true', help='Generate JSON report')
    
    args = parser.parse_args()
    
    # If no specific tests requested, use environment configuration
    if not any([args.unit, args.integration, args.ai, args.database, args.e2e, args.comprehensive]):
        # Use environment defaults
        pass
    
    runner = TestRunner(args)
    return runner.run_tests()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 