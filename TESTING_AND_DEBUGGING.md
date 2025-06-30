# Testing and Debugging Guide

Comprehensive testing framework for the Homeschool Application with Docker integration and environment-based configuration.

## Overview

The testing framework is designed to run primarily within Docker containers where all services (database, AI providers, etc.) are properly configured and available. Tests are controlled via environment variables in the `.env` file.

## Quick Start

### 1. Run Tests During Docker Build (Recommended)
```bash
# Build with tests enabled (default)
docker-compose up --build

# Build without tests (faster)
RUN_TESTS_ON_BUILD=false docker-compose up --build
```

### 2. Run Dedicated Test Suite
```bash
# Run comprehensive test suite in isolated container
docker-compose --profile test up test

# Run specific test categories
docker-compose --profile test run test python run_tests.py --unit --integration
```

### 3. Debug AI Agent Issues
```bash
# Run diagnostics in debug container
docker-compose --profile debug up debug
```

## Test Configuration

### Environment Variables

Configure tests in your `.env` file:

```bash
# ================================
# TEST CONFIGURATION
# ================================

# Master toggle for running tests during Docker build
RUN_TESTS_ON_BUILD=true

# Test Categories (can be enabled/disabled independently)
RUN_UNIT_TESTS=true                        # Fast tests, no external dependencies
RUN_INTEGRATION_TESTS=true                 # Database and system integration tests  
RUN_AI_TESTS=true                          # AI provider and function calling tests (Docker only)
RUN_DATABASE_TESTS=true                    # Database connectivity and schema tests
RUN_E2E_TESTS=false                        # End-to-end workflow tests (slow)

# Test Configuration
TEST_TIMEOUT=300                           # Test timeout in seconds
TEST_DATABASE_URL=sqlite:///./test.db      # Separate database for testing
TEST_FAST_MODE=false                       # Skip slow tests when true
```

### Test Categories

| Category | Description | Dependencies | Speed |
|----------|-------------|--------------|-------|
| **Unit Tests** | Pure code logic, no external dependencies | None | Fast |
| **Integration Tests** | Database and system integration | Database | Medium |
| **AI Tests** | AI provider and function calling | AI services (Docker only) | Medium |
| **Database Tests** | Database connectivity and schema | Database | Fast |
| **E2E Tests** | End-to-end workflow testing | All services | Slow |

## Running Tests

### Docker Environment (Recommended)

**🚨 Important:** AI tests can only run in Docker environment due to network configuration.

#### 1. Automatic Tests During Build
```bash
# Tests run automatically during build (controlled by RUN_TESTS_ON_BUILD)
docker-compose up --build
```

#### 2. Dedicated Test Container
```bash
# Run comprehensive test suite
docker-compose --profile test up test

# Run specific test categories
docker-compose --profile test run test python run_tests.py --unit
docker-compose --profile test run test python run_tests.py --integration --ai
docker-compose --profile test run test python run_tests.py --comprehensive
```

#### 3. Interactive Testing
```bash
# Get shell in test environment
docker-compose --profile test run test bash

# Run tests interactively
python run_tests.py --verbose --html
python -m pytest tests/unit/ -v
```

### Local Environment (Limited)

**⚠️ Warning:** Local testing has limitations - AI tests won't work outside Docker.

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-html pytest-json-report pytest-timeout

# Run only unit tests (no external dependencies)
python run_tests.py --unit --skip-external

# Run unit tests directly
python -m pytest tests/unit/ -v
```

## Test Commands Reference

### Basic Commands
```bash
# Default test run (respects .env configuration)
python run_tests.py

# Comprehensive test run (all categories)
python run_tests.py --comprehensive

# Fast test run (skip slow tests)
python run_tests.py --fast

# Verbose output with HTML report
python run_tests.py --verbose --html
```

### Category-Specific Commands
```bash
# Unit tests only
python run_tests.py --unit

# Integration tests only  
python run_tests.py --integration

# AI provider tests (Docker only)
python run_tests.py --ai

# Database tests only
python run_tests.py --database

# End-to-end tests
python run_tests.py --e2e
```

### Advanced Options
```bash
# Skip external service tests
python run_tests.py --skip-external

# Generate reports
python run_tests.py --html --json

# Custom timeout
TEST_TIMEOUT=600 python run_tests.py --comprehensive
```

## Debugging Tools

### 1. AI Agent Diagnostics
```bash
# Run comprehensive AI agent diagnostics (Docker only)
docker-compose --profile debug up debug

# Or run directly in container
docker-compose --profile debug run debug python scripts/debug_ai_agent.py
```

### 2. Function Calling Test
```bash
# Detailed function calling diagnostics
docker-compose --profile debug run debug python enhanced_function_calling_test.py
```

### 3. Code Analysis
```bash
# Analyze code structure and find unused code
python analyze_code.py
python scripts/code_analyzer.py
```

## Test Output and Reports

### File Locations
- `test_results/test_report.json` - Main test report
- `test_results/docker_test_report.json` - Docker-specific report  
- `test_results/pytest_report.html` - HTML test report
- `test_results/pytest_report.json` - Pytest JSON report

### Understanding Reports

#### JSON Report Structure
```json
{
  "timestamp": "2024-01-01T12:00:00",
  "total_elapsed": 45.2,
  "configuration": {
    "run_unit_tests": true,
    "run_ai_tests": true
  },
  "summary": {
    "total": 5,
    "passed": 4,
    "failed": 1,
    "critical_failures": 0
  },
  "results": [...]
}
```

#### Test Result Indicators
- ✅ **Passed**: Test completed successfully
- ❌ **Failed (Critical)**: Critical test failed - may indicate serious issues
- ⚠️ **Failed (Non-Critical)**: Non-critical test failed - warning only
- ⏰ **Timeout**: Test exceeded timeout limit
- 💥 **Crashed**: Test crashed with exception

## Troubleshooting

### Common Issues

#### 1. Import Errors in Unit Tests
```
ModuleNotFoundError: No module named 'app.models'
```
**Solution**: Fix import paths in test files:
```python
# Use absolute imports
from app.models import User, Event
from app.database import Base
```

#### 2. AI Tests Failing Outside Docker
```
Connection refused: http://localhost:11434
```
**Solution**: AI tests only work in Docker environment:
```bash
# Run AI tests in Docker
docker-compose --profile test run test python run_tests.py --ai
```

#### 3. Database Connection Issues
```
could not connect to server: Connection refused
```
**Solution**: Ensure database service is running:
```bash
# Check database status
docker-compose ps
docker-compose logs db

# Use test database for local testing
export TEST_DATABASE_URL=sqlite:///./test.db
```

#### 4. Tests Taking Too Long
```
Test timed out after 300 seconds
```
**Solution**: Increase timeout or use fast mode:
```bash
# Increase timeout
export TEST_TIMEOUT=600

# Use fast mode
python run_tests.py --fast
```

### Debug Strategies

#### 1. Isolate Test Categories
```bash
# Test categories one by one
python run_tests.py --unit
python run_tests.py --integration  
python run_tests.py --ai
```

#### 2. Use Verbose Mode
```bash
# Get detailed output
python run_tests.py --verbose
```

#### 3. Check Individual Components
```bash
# Test database connectivity
python -c "
from app.database import get_db
from sqlalchemy import text
db = next(get_db())
print(db.execute(text('SELECT 1')).scalar())
"

# Test AI provider
python -c "
import asyncio
from app.ai_providers import ai_manager
async def test():
    provider = ai_manager.get_current_provider()
    print(f'Provider: {provider.__class__.__name__}')
asyncio.run(test())
"
```

#### 4. Review Logs
```bash
# Check application logs
docker-compose logs app

# Check test-specific logs
docker-compose --profile test logs test

# Check debug output
docker-compose --profile debug logs debug
```

## Best Practices

### 1. Test Environment Setup
- Always use Docker for AI-related tests
- Keep unit tests independent of external services
- Use separate test database
- Set appropriate timeouts

### 2. Test Organization
- Group related tests in appropriate categories
- Use descriptive test names
- Keep tests focused and atomic
- Mock external dependencies in unit tests

### 3. Continuous Integration
- Enable `RUN_TESTS_ON_BUILD=true` for development
- Use `RUN_TESTS_ON_BUILD=false` for production builds
- Configure appropriate test categories for CI/CD

### 4. Debugging Workflow
1. Start with unit tests (fastest feedback)
2. Check database connectivity
3. Verify AI provider configuration
4. Run integration tests
5. Use debug tools for deeper analysis

## Configuration Examples

### Development Environment
```bash
# .env - Development setup
RUN_TESTS_ON_BUILD=true
RUN_UNIT_TESTS=true
RUN_INTEGRATION_TESTS=true
RUN_AI_TESTS=true
RUN_DATABASE_TESTS=true
RUN_E2E_TESTS=false      # Skip slow tests
TEST_FAST_MODE=false
TEST_TIMEOUT=300
```

### Production Build
```bash
# .env - Production setup  
RUN_TESTS_ON_BUILD=false  # Skip tests in production
RUN_UNIT_TESTS=false
RUN_INTEGRATION_TESTS=false
RUN_AI_TESTS=false
RUN_DATABASE_TESTS=false
RUN_E2E_TESTS=false
```

### CI/CD Pipeline
```bash
# .env - CI/CD setup
RUN_TESTS_ON_BUILD=true
RUN_UNIT_TESTS=true
RUN_INTEGRATION_TESTS=true
RUN_AI_TESTS=true
RUN_DATABASE_TESTS=true
RUN_E2E_TESTS=true       # Run all tests in CI
TEST_FAST_MODE=false
TEST_TIMEOUT=600         # Longer timeout for CI
```

This testing framework provides comprehensive coverage while being flexible enough to adapt to different environments and requirements. 