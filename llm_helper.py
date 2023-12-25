from typing import List, Optional, Dict, Any
import json
import os

from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Data model for LLM to generate
class ReasonedResponse(BaseModel):
    reasoning: str
    answer: str

tools = [
    {
        "type": "function",
        "function": {
            "name": "provide_reasoned_response",
            "description": "Provide a response with reasoning and a final answer",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "The step-by-step reasoning or thought process",
                    },
                    "answer": {
                        "type": "string",
                        "description": "The final concise answer",
                    },
                },
                "required": ["reasoning", "answer"],
            },
        },
    }
]

def get_llm_response(prompt: str) -> ReasonedResponse:
    """
    Get the response from the LLM using function calling to ensure the desired structure.
    """
    chat_completion = groq.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant that provides responses with reasoning and a final answer.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        model="llama3-8b-8192",
        temperature=1,
        max_tokens=1024,
        top_p=1,
        stream=False,
        tools=tools,
        tool_choice={"type": "function", "function": {"name": "provide_reasoned_response"}},
    )
    
    function_call = chat_completion.choices[0].message.tool_calls[0].function
    response_dict = json.loads(function_call.arguments)
    return ReasonedResponse(**response_dict)

def get_llm_response_with_context(prompt: str, context: str) -> ReasonedResponse:
    """
    Get the response from the LLM with context, using function calling to ensure the desired structure.
    """
    chat_completion = groq.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": f"{context}\nYou are an AI assistant that provides responses with reasoning and a final answer.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        model="llama3-8b-8192",
        temperature=1,
        max_tokens=1024,
        top_p=1,
        stream=False,
        tools=tools,
        tool_choice={"type": "function", "function": {"name": "provide_reasoned_response"}},
    )
    
    function_call = chat_completion.choices[0].message.tool_calls[0].function
    response_dict = json.loads(function_call.arguments)
    return ReasonedResponse(**response_dict)

def print_response(response: ReasonedResponse):
    print(json.dumps(response.model_dump(), indent=2))

def main():
    prompt = "What is the capital of France? Explain your reasoning."
    
    # JSON response
    response = get_llm_response(prompt)
    print("Response:")
    print_response(response)
    
    # JSON response with context
    context = "You are a geography expert."
    response_with_context = get_llm_response_with_context(prompt, context)
    print("\nResponse with context:")
    print_response(response_with_context)

if __name__ == "__main__":
    main()
