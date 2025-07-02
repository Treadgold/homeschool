#!/usr/bin/env python3
"""
Simple test without f-strings to avoid template conflicts.
"""

import asyncio
import json
import os
import sys
import uuid

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_simple_prompt():
    """Test the LangChain agent without f-strings."""
    
    print("🧪 Testing LangChain Agent (Simple Prompt)...")
    print("=" * 50)
    
    # Set up environment
    os.environ.setdefault("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
    
    # Import the specific modules we need
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_ollama import ChatOllama
    
    # Use a test model
    model_name = "qwen3:14b"
    print(f"   Using Model: {model_name}")
    
    # Create LLM instance
    ollama_endpoint = os.getenv("OLLAMA_ENDPOINT")
    llm = ChatOllama(model=model_name, base_url=ollama_endpoint, temperature=0)
    
    # Test 1: Basic LLM functionality
    print("\n📝 Test 1: Basic LLM Response")
    print("-" * 30)
    
    try:
        basic_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant."),
            ("human", "{input}"),
        ])
        
        basic_chain = basic_prompt | llm | StrOutputParser()
        basic_response = await basic_chain.ainvoke({"input": "Hello! Can you tell me what 2+2 equals?"})
        
        print(f"✅ Basic Response: {basic_response}")
        
    except Exception as e:
        print(f"❌ Basic test failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 2: Tool calling prompt without f-strings
    print("\n🔧 Test 2: Tool Calling Prompt")
    print("-" * 30)
    
    try:
        tools_definition = """
        Available tools:
        1. create_event_draft: Creates a draft event
           Parameters: title (string), description (string), start_date (string), end_date (string)
        2. add_ticket_type: Adds a ticket type to an event
           Parameters: event_id (string), name (string), price (number), quantity (number)
        """
        
        # Build system message without f-strings
        system_message = "You are a helpful assistant that can use tools to help users.\n"
        system_message += tools_definition
        system_message += "\n\nIf the user asks for something that requires a tool, respond with JSON in this format:\n"
        system_message += '{"tool_calls": [{"name": "tool_name", "arguments": {"param": "value"}}]}\n\n'
        system_message += "If no tool is needed, just respond normally."
        
        tool_prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "{input}"),
        ])
        
        tool_chain = tool_prompt | llm | StrOutputParser()
        tool_response = await tool_chain.ainvoke({
            "input": "I'd like to create an event for a 'Homeschool Science Fair' on August 1st, 2025."
        })
        
        print(f"✅ Tool Response: {tool_response}")
        
        # Try to parse as JSON
        try:
            if "```json" in tool_response:
                json_part = tool_response.split("```json")[1].split("```")[0]
            else:
                json_part = tool_response
                
            parsed = json.loads(json_part)
            if "tool_calls" in parsed:
                print(f"🎯 Parsed tool calls: {parsed['tool_calls']}")
            else:
                print("⚠️ No tool_calls in response")
        except json.JSONDecodeError:
            print("⚠️ Response is not valid JSON")
        
    except Exception as e:
        print(f"❌ Tool calling test failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 3: Multi-step reasoning
    print("\n🧠 Test 3: Multi-step Reasoning")
    print("-" * 30)
    
    try:
        reasoning_system = "You are a helpful assistant. Your job is to decide if you should use a tool to answer the user's question.\n"
        reasoning_system += tools_definition
        reasoning_system += "\n\nThink step-by-step. If a tool is needed, state the tool name and the arguments. If not, just respond to the user."
        
        reasoning_prompt = ChatPromptTemplate.from_messages([
            ("system", reasoning_system),
            ("human", "{input}"),
        ])
        
        reasoning_chain = reasoning_prompt | llm | StrOutputParser()
        reasoning_response = await reasoning_chain.ainvoke({
            "input": "I'd like to create an event for a 'Homeschool Science Fair' on August 1st, 2025."
        })
        
        print(f"✅ Reasoning Response: {reasoning_response}")
        
    except Exception as e:
        print(f"❌ Reasoning test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_simple_prompt()) 