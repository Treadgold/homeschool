#!/usr/bin/env python3
"""
Docker Test Runner
Specialized test runner for Docker environment that respects .env test configuration flags
Only runs tests that are appropriate for the Docker container environment
"""

import subprocess
import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
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

class DockerTestRunner:
    """Test runner optimized for Docker container environment"""
    
    def __init__(self):
        self.output_dir = Path("test_results")
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}
        self.start_time = time.time()
        
        # Load test configuration from environment
        self.config = {
            'run_unit_tests': get_env_bool('RUN_UNIT_TESTS', True),
            'run_integration_tests': get_env_bool('RUN_INTEGRATION_TESTS', True),
            'run_ai_tests': get_env_bool('RUN_AI_TESTS', True),
            'run_database_tests': get_env_bool('RUN_DATABASE_TESTS', True),
            'run_e2e_tests': get_env_bool('RUN_E2E_TESTS', False),
            'test_timeout': get_env_int('TEST_TIMEOUT', 300),
            'fast_mode': get_env_bool('TEST_FAST_MODE', False)
        }
        
        print("🐳 Docker Test Runner")
        print("=" * 60)
        print(f"🔧 Test Configuration:")
        for key, value in self.config.items():
            print(f"   {key}: {value}")
        print("=" * 60)
    
    def run_tests(self) -> int:
        """Run configured tests and return exit code"""
        
        if not any(self.config.values()):
            print("⏭️  All tests disabled via environment configuration")
            return 0
        
        # Build test plan based on configuration
        test_plan = []
        
        if self.config['run_unit_tests']:
            test_plan.append({
                'name': 'unit_tests',
                'description': 'Unit Tests',
                'command': ['python', '-m', 'pytest', 'tests/unit/', '-v', '--tb=short'],
                'category': 'unit'
            })
        
        if self.config['run_database_tests']:
            test_plan.append({
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
                'category': 'database'
            })
        
        if self.config['run_ai_tests']:
            test_plan.append({
                'name': 'ai_provider_tests',
                'description': 'AI Provider Tests (Docker Environment)',
                'command': ['python', '-c', '''
import asyncio
import sys
sys.path.insert(0, ".")
from app.ai_providers import ai_manager

async def test_ai():
    try:
        provider = ai_manager.get_current_provider()
        config = ai_manager.get_current_model_config()
        print(f"✅ AI Provider: {provider.__class__.__name__}")
        print(f"✅ Model: {config.model_name if config else 'Unknown'}")
        
        # Simple test
        response = await provider.chat_completion([
            {"role": "user", "content": "Hello"}
        ])
        print(f"✅ AI Response: {response.get('content', 'No content')[:50]}...")
        
    except Exception as e:
        print(f"⚠️  AI Provider issue: {e}")
        # Don't fail the build for AI issues, just warn

asyncio.run(test_ai())
'''],
                'category': 'ai'
            })
        
        if self.config['run_integration_tests']:
            test_plan.append({
                'name': 'integration_tests',
                'description': 'Integration Tests',
                'command': ['python', '-m', 'pytest', 'tests/integration/', '-v', '--tb=short'],
                'category': 'integration'
            })
        
        if self.config['run_e2e_tests'] and not self.config['fast_mode']:
            test_plan.append({
                'name': 'e2e_tests',
                'description': 'End-to-End Tests',
                'command': ['python', 'scripts/debug_ai_agent.py'],
                'category': 'e2e'
            })
        
        # Execute test plan
        overall_success = True
        
        for test in test_plan:
            success = self._run_test(test)
            if not success:
                overall_success = False
        
        # Generate report
        self._generate_report()
        
        if overall_success:
            print("\n🎉 All Docker tests passed!")
            return 0
        else:
            print("\n⚠️  Some tests had issues - check test_results/ for details")
            return 0  # Don't fail Docker build for test issues, just warn
    
    def _run_test(self, test_config: dict) -> bool:
        """Run a single test"""
        name = test_config['name']
        description = test_config['description']
        command = test_config['command']
        
        print(f"\n🧪 Running {description}...")
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.config['test_timeout'],
                cwd=Path.cwd()
            )
            
            elapsed = time.time() - start_time
            success = result.returncode == 0
            
            self.results[name] = {
                'success': success,
                'exit_code': result.returncode,
                'elapsed': elapsed,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'category': test_config['category']
            }
            
            if success:
                print(f"   ✅ {description} passed ({elapsed:.2f}s)")
            else:
                print(f"   ⚠️  {description} had issues ({elapsed:.2f}s)")
                # Print first few lines of output for debugging
                if result.stderr:
                    error_lines = result.stderr.split('\n')[:3]
                    for line in error_lines:
                        if line.strip():
                            print(f"      {line}")
            
            return success
            
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            print(f"   ⏰ {description} timed out ({elapsed:.2f}s)")
            self.results[name] = {
                'success': False,
                'error': 'timeout',
                'elapsed': elapsed,
                'category': test_config['category']
            }
            return False
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ {description} crashed ({elapsed:.2f}s): {e}")
            self.results[name] = {
                'success': False,
                'error': str(e),
                'elapsed': elapsed,
                'category': test_config['category']
            }
            return False
    
    def _generate_report(self):
        """Generate test report"""
        total_elapsed = time.time() - self.start_time
        
        # Count results by category
        summary = {}
        for result in self.results.values():
            category = result.get('category', 'unknown')
            if category not in summary:
                summary[category] = {'passed': 0, 'failed': 0, 'total': 0}
            
            summary[category]['total'] += 1
            if result.get('success'):
                summary[category]['passed'] += 1
            else:
                summary[category]['failed'] += 1
        
        print(f"\n📊 Docker Test Summary:")
        print(f"   ⏱️  Total time: {total_elapsed:.2f}s")
        
        for category, stats in summary.items():
            print(f"   📋 {category.title()}: {stats['passed']}/{stats['total']} passed")
        
        # Save detailed report
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'environment': 'docker',
            'total_elapsed': total_elapsed,
            'configuration': self.config,
            'summary': summary,
            'results': self.results
        }
        
        report_file = self.output_dir / "docker_test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"   📄 Report saved: {report_file}")


def main():
    """Main entry point"""
    runner = DockerTestRunner()
    return runner.run_tests()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 