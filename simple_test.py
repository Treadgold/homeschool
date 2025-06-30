#!/usr/bin/env python3
"""
Quick test to see where Ollama testing is hanging
"""

import httpx
import asyncio
import time
import json
from datetime import datetime

OLLAMA_URL = "http://host.docker.internal:11434"
MODEL = "llama3.2:latest"

async def test_with_timeout():
    print(f"🧪 Quick Ollama Test - {datetime.now().strftime('%H:%M:%S')}")
    print(f"Target: {OLLAMA_URL}")
    print(f"Model: {MODEL}")
    print("=" * 50)
    
    # Test 1: Connection
    print("1. Testing connection...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            start = time.time()
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            elapsed = time.time() - start
            print(f"   ✅ Connection: {response.status_code} ({elapsed:.2f}s)")
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                print(f"   Found {len(models)} models: {model_names[:3]}...")
                
                if MODEL in model_names:
                    print(f"   ✅ Model {MODEL} is available")
                else:
                    print(f"   ❌ Model {MODEL} not found")
                    return
            else:
                print(f"   ❌ Bad response: {response.status_code}")
                return
                
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return
    
    # Test 2: Simple generation with timeout
    print("\n2. Testing simple generation...")
    payload = {
        "model": MODEL,
        "prompt": "Hello",
        "stream": False,
        "options": {
            "num_predict": 5,
            "temperature": 0.1
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            print(f"   Sending request...")
            start = time.time()
            
            # Use asyncio.wait_for for additional timeout control
            response = await asyncio.wait_for(
                client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ),
                timeout=25.0  # 25 second timeout
            )
            
            elapsed = time.time() - start
            print(f"   ✅ Response: {response.status_code} ({elapsed:.2f}s)")
            
            if response.status_code == 200:
                result = response.json()
                if "response" in result:
                    print(f"   ✅ Generated: '{result['response']}'")
                    print(f"   🎉 SUCCESS! Generation works.")
                else:
                    print(f"   ❌ No response field: {list(result.keys())}")
            else:
                print(f"   ❌ Bad status: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                
    except asyncio.TimeoutError:
        elapsed = time.time() - start
        print(f"   ❌ TIMEOUT after {elapsed:.1f}s")
        print(f"   This suggests the model is loading or Ollama is stuck")
    except Exception as e:
        elapsed = time.time() - start
        print(f"   ❌ Error after {elapsed:.1f}s: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 50)
    print("💡 If this hangs at 'Sending request...', the issue is:")
    print("   - Model loading taking too long")
    print("   - Ollama server overloaded")
    print("   - Network connectivity issue")

if __name__ == "__main__":
    asyncio.run(test_with_timeout()) 