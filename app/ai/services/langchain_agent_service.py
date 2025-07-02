"""
This service encapsulates the LangChain agent that will replace the custom agent logic.
"""
import json
import os
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.ai.langchain_tools import (add_ticket_type, create_event_draft,
                                  get_tools_definition)

# We'll use a simple dictionary to store history for different chat sessions.
# The key will be the session_id.
chat_history_store: Dict[str, List[Any]] = {}


def get_session_history(session_id: str):
    """Retrieves or creates a chat history for a given session."""
    if session_id not in chat_history_store:
        chat_history_store[session_id] = []
    return chat_history_store[session_id]


async def invoke_agent(session_id: str, user_prompt: str, model: str) -> Dict[str, Any]:
    """
    Invokes a custom, multi-step agent to provide more reliable tool calling.
    """
    ollama_endpoint = os.getenv("OLLAMA_ENDPOINT")
    llm = ChatOllama(model=model, base_url=ollama_endpoint, temperature=0)
    tools = {
        "create_event_draft": create_event_draft,
        "add_ticket_type": add_ticket_type,
    }
    tools_definition = get_tools_definition()

    # Step 1: Reasoning Chain
    reasoning_prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a helpful assistant. Your job is to decide if you should use a tool to answer the user's question.
         Available tools:
         {tools_definition}
         
         Think step-by-step. If a tool is needed, state the tool name and the arguments. If not, just respond to the user."""),
        ("human", "{input}"),
    ])
    reasoning_chain = reasoning_prompt | llm | StrOutputParser()
    reasoning_result = await reasoning_chain.ainvoke({"input": user_prompt})

    # Step 2: Formatting Chain
    formatting_prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are an expert at creating JSON tool calls.
         Based on the user's request and the reasoning, create a JSON object for the tool call.
         If no tool is required, return an empty JSON array: {{\"tool_calls\": []}}.
         
         Available tools:
         {tools_definition}
         
         User Request: {{input}}
         Reasoning: {{reasoning}}
         """),
    ])
    formatting_chain = formatting_prompt | llm | StrOutputParser()
    json_string = await formatting_chain.ainvoke({"input": user_prompt, "reasoning": reasoning_result})

    intermediate_steps = []
    try:
        # The output can sometimes be wrapped in markdown, so we extract it
        if "```json" in json_string:
            json_string = json_string.split("```json")[1].split("```")[0]
        
        tool_call_data = json.loads(json_string)
        tool_calls = tool_call_data.get("tool_calls", [])

        if tool_calls:
            for call in tool_calls:
                tool_name = call["name"]
                tool_args = call["arguments"]
                tool_args["session_id"] = session_id  # Inject session_id
                
                if tool_name in tools:
                    tool_output = tools[tool_name].invoke(tool_args)
                    intermediate_steps.append((call, tool_output))
    except (json.JSONDecodeError, KeyError, IndexError):
        # The model failed to produce a valid tool call.
        pass

    # Step 3: Response Generation
    if intermediate_steps:
        # If a tool was called, formulate a response based on the result
        tool_output_str = "\n".join([f"Tool {step[0]['name']} returned: {step[1]}" for step in intermediate_steps])
        response_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant. You have just used a tool. Summarize the result for the user."),
            ("human", "My original request was: {input}\nThe tool returned: {tool_output}"),
        ])
        response_chain = response_prompt | llm | StrOutputParser()
        final_response = await response_chain.ainvoke({"input": user_prompt, "tool_output": tool_output_str})
    else:
        # If no tool was called, the "reasoning" result is the response.
        final_response = reasoning_result

    chat_history = get_session_history(session_id)
    chat_history.append(HumanMessage(content=user_prompt))
    chat_history.append(AIMessage(content=final_response))

    return {
        "output": final_response,
        "intermediate_steps": intermediate_steps,
    } 