from typing import List, Dict, Any
import json
import os
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from tools import ToolManager, CalculatorTool
from prompts import TOOL_LIST_PROMPT, TOOL_CONSTRUCTOR_PROMPT

load_dotenv()

groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
tool_manager = ToolManager()

# Load API keys from a JSON file
def load_api_keys() -> Dict[str, str]:
    try:
        with open('api_keys.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save API keys to a JSON file
def save_api_key(service: str, key: str) -> None:
    api_keys = load_api_keys()
    api_keys[service] = key
    with open('api_keys.json', 'w') as f:
        json.dump(api_keys, f)

class ProcessResult(BaseModel):
    steps: List[Dict[str, str]]
    final_answer: str
    needs_api_key: Dict[str, str] = None  # Service name and description if API key needed

def check_for_api_key_requirement(code: str) -> Dict[str, str]:
    api_patterns = {
        'OpenWeatherMap': 'YOUR_API_KEY',
        'Google': 'YOUR_GOOGLE_API_KEY',
        'Twitter': 'YOUR_TWITTER_API_KEY'
        # Add more API services as needed
    }
    
    for service, pattern in api_patterns.items():
        if pattern in code:
            return {
                'service': service,
                'message': f"This tool requires an {service} API key. Please provide your API key."
            }
    return None

def get_required_tools(query: str) -> List[str]:
    # For arithmetic operations, always return Calculator
    if any(op in query.lower() for op in ['add', 'subtract', 'multiply', 'divide', 'compute', '+', '-', '*', '/']):
        return ["Calculator"]
    
    # For other queries, ask the LLM
    prompt = TOOL_LIST_PROMPT.replace("{{context}}", query)
    response = groq.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama3-8b-8192",
        temperature=0.7,
        max_tokens=1024,
    )
    
    content = response.choices[0].message.content
    tools = []
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith(('Based on', 'This tool', 'These tools')):
            # Only add tools we know how to handle
            if line.lower() in ['calculator', 'weathertool', 'internettool']:
                tools.append(line)
    
    return tools if tools else ["Calculator"]  # Default to Calculator if no valid tools found

def construct_missing_tools(missing_tools: List[str]) -> Dict[str, str]:
    for tool in missing_tools:
        prompt = TOOL_CONSTRUCTOR_PROMPT.replace("{{context}}", f"Tool to construct: {tool}")
        response = groq.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=2048,
        )
        tool_code = response.choices[0].message.content
        
        # Extract the Python code from the response
        code_start = tool_code.find("```python")
        code_end = tool_code.rfind("```")
        if code_start != -1 and code_end != -1:
            tool_code = tool_code[code_start+9:code_end].strip()
            
            # Check if tool requires API key
            api_requirement = check_for_api_key_requirement(tool_code)
            if api_requirement:
                return api_requirement
            
            # Replace API key placeholders with actual keys if available
            api_keys = load_api_keys()
            for service, key in api_keys.items():
                tool_code = tool_code.replace(f'YOUR_{service.upper()}_API_KEY', key)
        
        try:
            tool_manager.add_tool_from_code(tool_code)
        except Exception as e:
            return {
                'service': tool,
                'message': f"Error creating tool: {str(e)}\nGenerated code had issues: {tool_code}"
            }
    return None

def use_tools(query: str, tools: List[str]) -> str:
    result = query
    tool_results = []
    
    for tool_name in tools:
        tool_instance = tool_manager.get_tool(tool_name)
        if not tool_instance:
            tool_results.append(f"Error: Tool '{tool_name}' is not available")
            continue
            
        try:
            # Handle Calculator tool specifically
            if tool_name == "Calculator":
                import re
                numbers = re.findall(r'-?\d+\.?\d*', query)
                operation = re.findall(r'[\+\-\*\/]', query)
                if numbers and operation:
                    expression = f"{numbers[0]}{operation[0]}{numbers[1]}"
                    result = tool_instance.run(expression)
                    if isinstance(result, str) and result.startswith("Error"):
                        tool_results.append(f"Error using Calculator: {result}")
                    else:
                        return f"{numbers[0]} {operation[0]} {numbers[1]} = {result}"
                else:
                    tool_results.append("Error: Could not extract numbers and operation from query")
            
            # Handle other tools
            elif hasattr(tool_instance, 'run'):
                try:
                    result = tool_instance.run(query)  # Pass the original query
                    if result:
                        if isinstance(result, str) and result.startswith("Error"):
                            tool_results.append(f"Error using {tool_name}: {result}")
                        else:
                            return str(result)
                except Exception as e:
                    tool_results.append(f"Error using {tool_name}: {str(e)}")
            else:
                tool_results.append(f"Error: {tool_name} does not have a 'run' method")
                
        except Exception as e:
            tool_results.append(f"Error using {tool_name}: {str(e)}")
    
    # If we get here, no tool was successful
    return "\n".join(tool_results) if tool_results else "Error: No tools were successfully applied"

def process_query_with_tools(query: str) -> ProcessResult:
    try:
        steps = []
        
        # Step 0: User Query
        steps.append({"step": "User Query", "details": query})
        
        try:
            # Step 1: Determine required tools
            steps.append({"step": "Determine required tools", "details": "Analyzing query to identify necessary tools."})
            required_tools = get_required_tools(query)
            if not required_tools:
                return ProcessResult(
                    steps=steps,
                    final_answer="Error: Could not determine required tools"
                )
            steps.append({"step": "Required tools identified", "details": f"Tools needed: {', '.join(required_tools)}"})
            
            # Step 2: Check for missing tools
            existing_tools = tool_manager.list_tools()
            missing_tools = [tool for tool in required_tools if tool not in existing_tools]
            steps.append({"step": "Check for missing tools", 
                         "details": f"Currently available tools: {', '.join(existing_tools)}\nMissing tools: {', '.join(missing_tools) if missing_tools else 'None'}"})
            
            # Step 3: Construct missing tools
            if missing_tools:
                steps.append({"step": "Construct missing tools", 
                             "details": f"Attempting to create: {', '.join(missing_tools)}"})
                api_requirement = construct_missing_tools(missing_tools)
                if api_requirement:
                    return ProcessResult(
                        steps=steps,
                        final_answer=f"Tool creation requires API key: {api_requirement['message']}",
                        needs_api_key=api_requirement
                    )
            
            # Step 4: Use tools
            steps.append({"step": "Use tools", "details": f"Using tools: {', '.join(required_tools)}"})
            result = use_tools(query, required_tools)
            
            return ProcessResult(steps=steps, final_answer=result)
            
        except Exception as e:
            return ProcessResult(
                steps=steps,
                final_answer=f"Error during processing: {str(e)}"
            )
            
    except Exception as e:
        return ProcessResult(
            steps=[{"step": "Error", "details": f"Critical error: {str(e)}"}],
            final_answer="Failed to process query due to system error"
        )
