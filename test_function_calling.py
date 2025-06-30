#!/usr/bin/env python3
"""
Test Ollama function calling with proper JSON schema format
"""

import asyncio
import httpx
import json
from datetime import datetime

OLLAMA_URL = "http://host.docker.internal:11434"
MODEL = "devstral:latest"

async def test_function_calling():
    print(f"🧪 Testing Ollama Function Calling - {datetime.now().strftime('%H:%M:%S')}")
    print(f"Target: {OLLAMA_URL}")
    print(f"Model: {MODEL}")
    print("=" * 60)
    
    # Test payload with proper Ollama function calling format
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user", 
                "content": "Please call the test_function_call function with message='Function calling works!' and status='success'"
            }
        ],
        "stream": False,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "test_function_call",
                    "description": "A simple test function to verify function calling works",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "A test message to return"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["success", "error"],
                                "description": "Status of the test"
                            }
                        },
                        "required": ["message", "status"]
                    }
                }
            }
        ]
    }
    
    print("📋 Payload:")
    print(json.dumps(payload, indent=2))
    print("\n" + "=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            print("🚀 Sending function calling request...")
            start_time = asyncio.get_event_loop().time()
            
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            elapsed = asyncio.get_event_loop().time() - start_time
            
            print(f"⏱️  Response received in {elapsed:.2f}s")
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Response received!")
                print(f"📋 Full Response:")
                print(json.dumps(result, indent=2))
                
                # Check for function calls
                message = result.get("message", {})
                tool_calls = message.get("tool_calls")
                content = message.get("content", "")
                
                if tool_calls:
                    print(f"\n🎉 FUNCTION CALLS DETECTED!")
                    print(f"📞 Tool calls: {len(tool_calls)}")
                    for i, call in enumerate(tool_calls):
                        print(f"  Call {i+1}: {call}")
                elif content:
                    print(f"\n📝 Text Response: {content}")
                    if "test_function_call" in content.lower():
                        print("⚠️  Model acknowledged function but didn't call it")
                    else:
                        print("❌ Model doesn't seem to support function calling")
                else:
                    print("❌ No content or tool calls in response")
                    
            elif response.status_code == 404:
                print("❌ /api/chat endpoint not available")
                print("💡 Try using /api/generate instead")
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"📋 Error: {response.text[:300]}")
                
    except httpx.ConnectError:
        print("❌ Connection failed - is Ollama running?")
        print("💡 Make sure Ollama is accessible at http://host.docker.internal:11434")
    except asyncio.TimeoutError:
        print("❌ Request timed out after 30 seconds")
        print("💡 Model might be loading or overloaded")
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_function_calling()) 