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
    if any(op in query.lower() for op in ['add', 'subtract', 'multiply', 'divide', 'compute', '+', '-', '*', '/', 'sqrt', 'square root']):
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
    for tool_name in tools:
        tool_instance = tool_manager.get_tool(tool_name)
        if not tool_instance:
            continue
            
        try:
            # Handle Calculator tool specifically
            if tool_name == "Calculator":
                # Extract numbers and basic operations
                import re
                # Clean up the query
                clean_query = query.lower().replace('compute', '').replace('calculate', '').strip()
                
                # For square root
                if "sqrt" in clean_query or "square root" in clean_query:
                    return str(tool_instance.run(clean_query))
                
                # For basic arithmetic
                # First, try to evaluate the entire expression
                try:
                    return str(tool_instance.run(clean_query))
                except:
                    # If that fails, try to parse it piece by piece
                    numbers = re.findall(r'-?\d+\.?\d*', clean_query)
                    operations = re.findall(r'[\+\-\*\/]', clean_query)
                    
                    if not numbers:
                        return "Error: No numbers found in query"
                    
                    if len(numbers) == 1:
                        return numbers[0]
                    
                    if not operations:
                        return "Error: No operation found in query"
                    
                    expression = numbers[0]
                    for i, op in enumerate(operations):
                        if i + 1 < len(numbers):
                            expression += f"{op}{numbers[i+1]}"
                    
                    result = tool_instance.run(expression)
                    return str(result)
            
            # Handle other tools
            else:
                result = tool_instance.run(query)
                if result:
                    return str(result)
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    return "Error: No suitable tool found to process the query"

def process_query_with_tools(query: str) -> Dict[str, Any]:
    steps = []
    
    # Step 1: Record the user query
    steps.append({"details": query})
    
    # Step 2: Determine required tools
    steps.append({"details": "Analyzing query to identify necessary tools."})
    required_tools = get_required_tools(query)
    
    # Step 3: Check for missing tools
    steps.append({"details": f"Tools needed: {', '.join(required_tools)}"})
    
    # Initialize tool manager
    available_tools = tool_manager.list_tools()
    missing_tools = [tool for tool in required_tools if tool not in available_tools]
    
    # Step 4: Construct missing tools if needed
    if missing_tools:
        steps.append({
            "details": f"Currently available tools: {', '.join(available_tools)} "
                      f"Missing tools: {', '.join(missing_tools)}"
        })
        construct_missing_tools(missing_tools)
    
    # Step 5: Use tools
    steps.append({
        "details": f"Using tools to process query: {query}"
    })
    
    # Use the tools to process the query
    final_answer = use_tools(query, required_tools)
    
    return {
        "steps": steps,
        "final_answer": final_answer
    }
