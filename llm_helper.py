from typing import List, Optional, Dict, Any
import json
import os
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from tools import CalculatorTool, tools

load_dotenv()

groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Data model for LLM to generate
class ReasonedResponse(BaseModel):
    reasoning: str
    answer: str

def get_llm_response(prompt: str) -> ReasonedResponse:
    chat_completion = groq.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant that provides responses with reasoning and a final answer. You have access to a calculator tool for arithmetic operations.",
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
        tool_choice="auto",
    )
    
    if chat_completion.choices[0].message.tool_calls:
        for tool_call in chat_completion.choices[0].message.tool_calls:
            if tool_call.function.name == "calculator":
                args = json.loads(tool_call.function.arguments)
                result = CalculatorTool.run(args["expression"])
                return get_llm_response(f"The result of the calculation {args['expression']} is {result}. Please provide a reasoned response based on this result.")
            elif tool_call.function.name == "provide_reasoned_response":
                response_dict = json.loads(tool_call.function.arguments)
                return ReasonedResponse(**response_dict)
    else:
        # If no tool was called, extract the content from the message
        content = chat_completion.choices[0].message.content
        # Split the content into reasoning and answer
        parts = content.split("\n\n", 1)
        if len(parts) == 2:
            reasoning, answer = parts
        else:
            reasoning = "No specific reasoning provided."
            answer = content
        return ReasonedResponse(reasoning=reasoning, answer=answer)

def get_llm_response_with_context(prompt: str, context: str) -> ReasonedResponse:
    """
    Get the response from the LLM with context, using function calling to ensure the desired structure.
    """
    chat_completion = groq.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": f"{context}\nYou are an AI assistant that provides responses with reasoning and a final answer. You have access to a calculator tool for arithmetic operations.",
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
        tool_choice="auto",
    )
    
    if chat_completion.choices[0].message.tool_calls:
        for tool_call in chat_completion.choices[0].message.tool_calls:
            if tool_call.function.name == "calculator":
                args = json.loads(tool_call.function.arguments)
                result = CalculatorTool.run(args["expression"])
                return get_llm_response_with_context(f"The result of the calculation {args['expression']} is {result}. Please provide a reasoned response based on this result.", context)
            elif tool_call.function.name == "provide_reasoned_response":
                response_dict = json.loads(tool_call.function.arguments)
                return ReasonedResponse(**response_dict)
    else:
        # If no tool was called, return a default response
        return ReasonedResponse(reasoning="No specific reasoning provided.", answer="Unable to process the request.")

def print_response(response: ReasonedResponse):
    print(json.dumps(response.model_dump(), indent=2))

def main():
    prompt = "What is the result of 586829*123? Explain your reasoning."
    
    try:
        # JSON response
        response = get_llm_response(prompt)
        print("Response:")
        print_response(response)
    except Exception as e:
        print(f"Error in get_llm_response: {str(e)}")
    
    try:
        # JSON response with context
        context = "You are a math tutor."
        response_with_context = get_llm_response_with_context(prompt, context)
        print("\nResponse with context:")
        print_response(response_with_context)
    except Exception as e:
        print(f"Error in get_llm_response_with_context: {str(e)}")

if __name__ == "__main__":
    main()
