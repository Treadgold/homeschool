#!/usr/bin/env python3
"""
Standalone ReAct Test - No imports, pure logic test
This recreates the ReAct agent logic to test our fixes without circular imports
"""
import asyncio
import json
import re
import os
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from langchain_ollama import ChatOllama

class StandaloneReActAgent:
    """Standalone ReAct agent for testing our fixes"""
    
    def __init__(self, model: str, session_id: str):
        self.model = model
        self.session_id = session_id
        self.ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "http://host.docker.internal:11434")
        
        # Use our fixed LLM configuration
        self.llm = ChatOllama(
            model=model, 
            base_url=self.ollama_endpoint, 
            temperature=0.5,  # Better for reasoning
            timeout=60,       # More time for thinking
            num_predict=1024, # Allow longer responses
        )
        
        # Mock tools
        self.tools = {
            "create_event_draft": self._mock_create_event,
            "add_ticket_type": self._mock_add_ticket,
        }
        
        self.max_iterations = 3
    
    def _mock_create_event(self, params):
        """Mock event creation tool"""
        return {
            "event_id": "test_123",
            "title": params.get("title", "Test Event"),
            "status": "draft"
        }
    
    def _mock_add_ticket(self, params):
        """Mock ticket addition tool"""
        return {
            "ticket_id": "ticket_456",
            "name": params.get("name", "General Ticket"),
            "price": params.get("price", 0)
        }
    
    def _create_react_prompt(self) -> str:
        """Our fixed ReAct prompt that encourages iterative reasoning"""
        return """You are an expert AI assistant that uses the ReAct (Reasoning and Acting) approach.

CRITICAL INSTRUCTIONS:
1. You MUST think step by step before taking any action
2. You MUST use the exact format: Thought: / Action: / Action Input: / Observation:
3. You MUST continue reasoning after each observation
4. You MUST provide a Final Answer only when the task is complete

REASONING LOOP:
Thought: [Analyze the situation, consider what you know, decide next steps]
Action: [Tool name if needed, or skip if no action needed]  
Action Input: [JSON parameters for the tool]
Observation: [Result will be provided automatically]
[Continue with next Thought based on the Observation]

Available Tools:
- create_event_draft: Create event with title, description, date
- add_ticket_type: Add tickets to existing event

Think carefully and work through this step by step.

User Request: {user_input}

Begin your reasoning:

Thought:"""

    def _parse_react_response_proper(self, response: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Parse ReAct response following proper format"""
        print(f"\n🔍 Parsing response: {response[:200]}...")
        
        thought_match = re.search(r'Thought:\s*(.*?)(?=\n(?:Action|Final Answer):|$)', response, re.DOTALL)
        action_match = re.search(r'Action:\s*(.*?)(?=\n(?:Action Input|Observation):|$)', response, re.DOTALL)
        action_input_match = re.search(r'Action Input:\s*(.*?)(?=\n(?:Observation|Final Answer):|$)', response, re.DOTALL)
        final_answer_match = re.search(r'Final Answer:\s*(.*?)$', response, re.DOTALL)
        
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        action_input = action_input_match.group(1).strip() if action_input_match else None
        final_answer = final_answer_match.group(1).strip() if final_answer_match else None
        
        print(f"📝 Parsed - Thought: {bool(thought)}, Action: {bool(action)}, Input: {bool(action_input)}, Final: {bool(final_answer)}")
        if thought: print(f"   💭: {thought[:100]}...")
        if action: print(f"   🔧: {action}")
        if final_answer: print(f"   ✅: {final_answer[:100]}...")
        
        return thought, action, action_input, final_answer
    
    async def _execute_action_proper(self, action: str, action_input: str) -> str:
        """Execute action with proper parameter handling for ReAct format"""
        try:
            print(f"🛠️ Executing: {action} with input: {action_input}")
            
            # Clean action name
            action = action.strip()
            
            # Parse action input as JSON
            params = {"session_id": self.session_id}
            if action_input:
                try:
                    parsed_params = json.loads(action_input)
                    params.update(parsed_params)
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON in action input: {action_input}"
            
            # Execute the tool
            if action in self.tools:
                result = self.tools[action](params)
                return f"Success: {json.dumps(result, indent=2)}"
            else:
                return f"Error: Unknown tool '{action}'. Available tools: {list(self.tools.keys())}"
                
        except Exception as e:
            return f"Error executing action: {str(e)}"
    
    async def run_react_loop(self, user_input: str) -> Dict[str, Any]:
        """Proper ReAct loop with true multi-iteration reasoning"""
        conversation_history = []
        intermediate_steps = []
        
        # Start with proper ReAct prompt
        current_input = self._create_react_prompt().format(
            session_id=self.session_id,
            user_input=user_input
        )
        
        print(f"🚀 Starting ReAct loop for: {user_input}")
        
        # TRUE MULTI-ITERATION LOOP
        for iteration in range(self.max_iterations):
            print(f"\n🔄 Iteration {iteration + 1}/{self.max_iterations}")
            
            # Get LLM response
            start_time = datetime.now()
            response = await self.llm.ainvoke([{"role": "user", "content": current_input}])
            elapsed = (datetime.now() - start_time).total_seconds()
            
            response_content = response.content if hasattr(response, 'content') else str(response)
            print(f"🤖 LLM responded ({elapsed:.1f}s)")
            
            # Parse ReAct components
            thought, action, action_input, final_answer = self._parse_react_response_proper(response_content)
            
            if final_answer:
                # Task complete!
                print(f"✅ Task completed with final answer!")
                return {
                    "output": final_answer,
                    "intermediate_steps": intermediate_steps,
                    "iterations": iteration + 1,
                    "success": True
                }
            
            if action and action_input:
                # Execute tool and get observation
                observation = await self._execute_action_proper(action, action_input)
                
                # Record step
                intermediate_steps.append({
                    "iteration": iteration + 1,
                    "thought": thought,
                    "action": action,
                    "observation": observation
                })
                
                print(f"👁️ Observation: {observation[:100]}...")
                
                # CRITICAL: Feed observation back for next iteration
                current_input = f"""Previous step:
Thought: {thought}
Action: {action}
Action Input: {action_input}
Observation: {observation}

Continue your reasoning. What should you do next?

Thought:"""
            else:
                # No action but no final answer either - reasoning error
                print(f"❌ No action or final answer found in iteration {iteration + 1}")
                print(f"Raw response: {response_content[:300]}...")
                break
        
        print(f"⚠️ Loop completed without final answer after {self.max_iterations} iterations")
        return {"output": "Reasoning incomplete", "success": False, "intermediate_steps": intermediate_steps}

async def test_standalone_react():
    """Test our standalone ReAct implementation"""
    print("🧪 Testing Standalone ReAct Agent")
    print("=" * 50)
    
    # Create agent
    model = "qwen3:14b"
    session_id = f"standalone_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    agent = StandaloneReActAgent(model, session_id)
    print(f"✅ Agent created with model: {model}")
    
    # Test cases
    test_cases = [
        {
            "name": "Simple Event Creation", 
            "input": "Create a birthday party for Emma"
        },
        {
            "name": "Complex Multi-Step", 
            "input": "Create a science workshop for kids with $15 tickets, max 20 participants"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print(f"Input: {test_case['input']}")
        print("-" * 40)
        
        try:
            result = await agent.run_react_loop(test_case['input'])
            
            success = result.get('success', False)
            output = result.get('output', 'No output')
            iterations = result.get('iterations', 0)
            steps = result.get('intermediate_steps', [])
            
            print(f"\n📊 Results:")
            print(f"✅ Success: {success}")
            print(f"🔄 Iterations: {iterations}")
            print(f"🛠️ Steps: {len(steps)}")
            print(f"📤 Output: {output}")
            
            results.append({
                "test": test_case['name'],
                "success": success,
                "iterations": iterations,
                "steps": len(steps)
            })
            
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
            results.append({
                "test": test_case['name'],
                "success": False,
                "error": str(e)
            })
    
    # Summary
    print(f"\n📊 Final Summary")
    print("=" * 30)
    for result in results:
        test_name = result['test']
        success = result.get('success', False)
        iterations = result.get('iterations', 0)
        steps = result.get('steps', 0)
        
        print(f"🔍 {test_name}")
        print(f"   ✅ Success: {success}")
        print(f"   🔄 Iterations: {iterations}")
        print(f"   🛠️ Steps: {steps}")
        if 'error' in result:
            print(f"   ❌ Error: {result['error']}")
        print()
    
    overall_success = any(r.get('success', False) for r in results)
    
    if overall_success:
        print("🎉 ReAct fixes are working!")
    else:
        print("⚠️ ReAct implementation needs more work")

if __name__ == "__main__":
    asyncio.run(test_standalone_react()) 