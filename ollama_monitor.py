#!/usr/bin/env python3
"""
Ollama Model Monitoring Script
Helps debug model loading and generation issues
"""

import httpx
import asyncio
import time
import json
from datetime import datetime

OLLAMA_URL = "http://host.docker.internal:11434"
MODEL = "llama3.2:latest"  # Change this to your model

async def check_running_models():
    """Check which models are currently loaded in Ollama"""
    print(f"🔍 Checking running models at {OLLAMA_URL}/api/ps")
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{OLLAMA_URL}/api/ps")
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                
                print(f"📊 Found {len(models)} running models:")
                
                if not models:
                    print("   ❌ No models currently loaded in memory")
                    return None
                
                total_vram = 0
                for i, model in enumerate(models):
                    name = model.get("name", "unknown")
                    size_vram = model.get("size_vram", 0) 
                    size_mb = size_vram // (1024 * 1024)
                    expires = model.get("expires_at", "unknown")
                    
                    print(f"   {i+1}. {name}")
                    print(f"      VRAM: {size_mb} MB")
                    print(f"      Expires: {expires}")
                    
                    total_vram += size_vram
                
                total_mb = total_vram // (1024 * 1024)
                print(f"📈 Total VRAM used: {total_mb} MB")
                
                # Check if our target model is loaded
                our_model = None
                for model in models:
                    if model.get("name") == MODEL:
                        our_model = model
                        break
                
                if our_model:
                    print(f"✅ Target model '{MODEL}' is loaded in VRAM")
                    return our_model
                else:
                    print(f"❌ Target model '{MODEL}' is NOT loaded")
                    return None
                    
            else:
                print(f"❌ Failed to check models: HTTP {response.status_code}")
                return None
                
    except Exception as e:
        print(f"❌ Error checking models: {e}")
        return None

async def test_simple_generation():
    """Test simple generation and monitor model loading"""
    print(f"\n🧪 Testing generation with {MODEL}")
    
    # Check before generation
    print("Before generation:")
    model_before = await check_running_models()
    
    payload = {
        "model": MODEL,
        "prompt": "Hello, respond with just 'Hi there!'",
        "stream": False,
        "options": {
            "num_predict": 10,
            "temperature": 0.1
        }
    }
    
    print(f"\n🚀 Sending generation request...")
    
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            start_time = time.time()
            
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            elapsed = time.time() - start_time
            print(f"⏱️  Request completed in {elapsed:.2f}s")
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("response", "")
                
                if response_text:
                    print(f"✅ Generation successful!")
                    print(f"📝 Response: '{response_text.strip()}'")
                else:
                    print(f"⚠️  Got 200 OK but empty response")
                    print(f"📋 Raw result: {json.dumps(result, indent=2)}")
            else:
                print(f"❌ Generation failed: HTTP {response.status_code}")
                print(f"📋 Error: {response.text[:300]}")
                
    except httpx.TimeoutException:
        print(f"⏰ Request timed out after 45 seconds")
        print("This might indicate:")
        print("  - Model is still loading into VRAM")
        print("  - GPU memory issues")
        print("  - Network/Docker issues")
        
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    # Check after generation
    print(f"\nAfter generation:")
    model_after = await check_running_models()
    
    # Compare before/after
    if model_before and model_after:
        print(f"✅ Model remained loaded throughout")
    elif not model_before and model_after:
        print(f"📥 Model was loaded during the request")
    elif model_before and not model_after:
        print(f"📤 Model was unloaded (unusual)")
    else:
        print(f"❌ Model was never loaded")

async def monitor_during_generation():
    """Start generation and monitor model loading in parallel"""
    print(f"\n🔬 Advanced monitoring: Generation + Model Status")
    
    async def generation_task():
        payload = {
            "model": MODEL,
            "prompt": "Please write a short haiku about debugging",
            "stream": False,
            "options": {"num_predict": 50, "temperature": 0.7}
        }
        
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.post(
                    f"{OLLAMA_URL}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                return response.status_code, response.json()
            except Exception as e:
                return None, str(e)
    
    async def monitoring_task():
        """Monitor model status every 5 seconds during generation"""
        for i in range(12):  # Monitor for up to 60 seconds
            await asyncio.sleep(5)
            print(f"📡 Status check #{i+1} (at {i*5+5}s):")
            await check_running_models()
    
    # Run both tasks concurrently
    print("🎯 Starting generation...")
    generation_result = await asyncio.create_task(generation_task())
    
    status_code, result = generation_result
    if status_code == 200:
        response_text = result.get("response", "") if isinstance(result, dict) else ""
        print(f"✅ Generation completed successfully!")
        print(f"📝 Response: {response_text[:200]}...")
    else:
        print(f"❌ Generation failed: {result}")

async def main():
    print("🔥 Ollama Model Monitor & Debugger")
    print("=" * 50)
    print(f"Target: {OLLAMA_URL}")
    print(f"Model: {MODEL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Test 1: Check initial state
    print("\n1️⃣  Initial model status:")
    await check_running_models()
    
    # Test 2: Simple generation
    await test_simple_generation()
    
    # Test 3: Advanced monitoring (optional)
    print(f"\n" + "="*50)
    user_input = input("Run advanced monitoring? (y/N): ").strip().lower()
    if user_input in ['y', 'yes']:
        await monitor_during_generation()
    
    print(f"\n🏁 Monitoring complete!")

if __name__ == "__main__":
    asyncio.run(main()) 