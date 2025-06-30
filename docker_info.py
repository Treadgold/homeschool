#!/usr/bin/env python3
"""
Docker Environment Information Script
Shows useful diagnostic information about the container environment
"""

import os
import sys
import asyncio
import httpx
import json
from datetime import datetime

def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*50}")
    print(f"📋 {title}")
    print('='*50)

def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n--- {title} ---")

async def main():
    print("🐳 Docker Environment Diagnostic Information")
    print(f"🕒 Generated: {datetime.now()}")
    
    # Environment Variables
    print_section("Environment Variables")
    important_vars = [
        'DATABASE_URL',
        'OLLAMA_ENDPOINT', 
        'CURRENT_AI_MODEL',
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY',
        'ENVIRONMENT',
        'FACEBOOK_CLIENT_ID',
        'GOOGLE_CLIENT_ID',
        'STRIPE_PUBLISHABLE_KEY',
        'RUN_TESTS_ON_BUILD',
        'RUN_AI_TESTS'
    ]
    
    for var in important_vars:
        value = os.getenv(var, 'NOT_SET')
        # Hide sensitive values
        if 'KEY' in var or 'SECRET' in var:
            display_value = 'SET' if value != 'NOT_SET' else 'NOT_SET'
        elif 'CLIENT_ID' in var and value != 'NOT_SET':
            display_value = f"{value[:10]}..." if len(value) > 10 else value
        elif 'URL' in var and len(value) > 50:
            display_value = f"{value[:50]}..."
        else:
            display_value = value
        
        print(f"  {var}: {display_value}")
    
    # Network Connectivity Tests
    print_section("Network Connectivity Tests")
    
    # Test database connectivity
    print_subsection("Database Connection")
    try:
        # Try to import and test database
        sys.path.insert(0, "/app")
        from app.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        result = db.execute(text("SELECT 1"))
        db.close()
        print("  ✅ Database: Connected")
        
    except Exception as e:
        print(f"  ❌ Database: Failed - {e}")
    
    # Test Ollama connectivity
    print_subsection("Ollama AI Service")
    ollama_endpoint = os.getenv('OLLAMA_ENDPOINT', 'http://host.docker.internal:11434')
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            print(f"  🔗 Testing: {ollama_endpoint}")
            response = await client.get(f"{ollama_endpoint}/api/tags")
            
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                print(f"  ✅ Ollama: Connected ({len(models)} models)")
                
                if models:
                    print("  📋 Available models:")
                    for model in models[:5]:  # Show first 5 models
                        name = model.get('name', 'unknown')
                        size = model.get('size', 0)
                        size_mb = size / (1024*1024) if size else 0
                        print(f"    - {name} ({size_mb:.1f}MB)")
                    
                    if len(models) > 5:
                        print(f"    ... and {len(models) - 5} more")
                else:
                    print("  ⚠️  No models available")
                    
            else:
                print(f"  ❌ Ollama: HTTP {response.status_code}")
                
    except httpx.ConnectError:
        print(f"  ❌ Ollama: Connection failed")
        print("  💡 Possible solutions:")
        print("    - Check if Ollama is running on host: 'ollama serve'")
        print("    - Verify host.docker.internal resolution")
        print("    - For WSL2: Check port forwarding settings")
        
    except Exception as e:
        print(f"  ❌ Ollama: Error - {e}")
    
    # Test Redis connectivity
    print_subsection("Redis Cache")
    try:
        import redis
        redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
        r = redis.from_url(redis_url)
        r.ping()
        print("  ✅ Redis: Connected")
        
    except Exception as e:
        print(f"  ❌ Redis: Failed - {e}")
    
    # File System Info
    print_section("File System Information")
    
    app_dir = "/app"
    if os.path.exists(app_dir):
        print(f"  📁 App directory: {app_dir}")
        
        # Check important files
        important_files = [
            "app/main.py",
            "app/ai/router.py", 
            "app/ai_providers.py",
            "requirements.txt",
            "docker-compose.yml"
        ]
        
        for file_path in important_files:
            full_path = os.path.join(app_dir, file_path)
            if os.path.exists(full_path):
                size = os.path.getsize(full_path)
                print(f"    ✅ {file_path} ({size:,} bytes)")
            else:
                print(f"    ❌ {file_path} (missing)")
    
    # AI System Status
    print_section("AI System Status")
    
    try:
        from app.ai_providers import ai_manager
        
        # Get available models
        available_models = ai_manager.get_available_models()
        print(f"  📊 Available AI models: {len(available_models)}")
        
        for model_key, config in available_models.items():
            status = "✅ Enabled" if config.enabled else "❌ Disabled"
            print(f"    {status} {model_key} ({config.provider})")
        
        # Test current provider
        try:
            current_provider = ai_manager.get_current_provider()
            print(f"  🤖 Current provider: {current_provider.__class__.__name__}")
            
        except Exception as e:
            print(f"  ⚠️  Current provider error: {e}")
            
    except Exception as e:
        print(f"  ❌ AI system error: {e}")
    
    # System Resources
    print_section("System Resources")
    
    try:
        import psutil
        
        # Memory usage
        memory = psutil.virtual_memory()
        print(f"  💾 Memory: {memory.percent}% used ({memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB)")
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        print(f"  🖥️  CPU: {cpu_percent}% used")
        
        # Disk usage
        disk = psutil.disk_usage('/')
        print(f"  💿 Disk: {disk.percent}% used ({disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB)")
        
    except ImportError:
        print("  ⚠️  psutil not available - install for resource monitoring")
    except Exception as e:
        print(f"  ❌ Resource check failed: {e}")
    
    # Troubleshooting Tips
    print_section("Troubleshooting Tips")
    print("""
🔧 Common Issues and Solutions:

1. Ollama Connection Failed:
   - Check if Ollama is running: 'ollama serve'
   - Test from host: 'curl http://localhost:11434/api/tags'
   - For WSL2, check port forwarding:
     netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=11434 connectaddress=127.0.0.1 connectport=11434

2. Database Connection Issues:
   - Check if PostgreSQL container is running: 'docker ps'
   - Check database logs: 'docker logs homeschool-db'

3. AI Tests Failing:
   - Set RUN_AI_TESTS=false to skip AI tests during build
   - Check model availability in Ollama
   - Verify network connectivity between containers

4. Port Conflicts:
   - Check if ports 8000, 5432, 6379, 11434 are available
   - Use 'netstat -an | grep :PORT' to check port usage

5. Performance Issues:
   - Ensure adequate RAM (8GB+ recommended for AI models)
   - Check if AI models are pre-downloaded
   - Consider using smaller models for development
""")
    
    print("\n🎉 Diagnostic complete!")

if __name__ == "__main__":
    asyncio.run(main()) 