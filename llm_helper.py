from typing import List, Dict, Any, Optional
import json
import os
from pydantic import BaseModel
from groq import Groq
import google.generativeai as genai
from dotenv import load_dotenv
from tools import ToolManager, CalculatorTool
from prompts import TOOL_LIST_PROMPT, TOOL_CONSTRUCTOR_PROMPT

load_dotenv()

# Initialize LLM clients
groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Gemini model configuration
GEMINI_CONFIG = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

gemini_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=GEMINI_CONFIG,
)

tool_manager = ToolManager()

# Add new LLM interface class
class LLMInterface:
    def __init__(self, provider: str = "groq"):
        self.provider = provider.lower()
        
    async def get_completion(self, prompt: str, temperature: Optional[float] = None) -> str:
        try:
            if self.provider == "groq":
                response = groq.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama3-8b-8192",
                    temperature=temperature or 0.7,
                    max_tokens=1024,
                )
                return response.choices[0].message.content
                
            elif self.provider == "gemini":
                chat = gemini_model.start_chat(history=[])
                response = chat.send_message(prompt)
                return response.text
                
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
        except Exception as e:
            print(f"Error in get_completion: {str(e)}")
            raise

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

async def get_required_tools(query: str, llm_provider: str = "groq") -> List[str]:
    llm = LLMInterface(llm_provider)
    prompt = TOOL_LIST_PROMPT.replace("{{context}}", query)
    content = await llm.get_completion(prompt)
    
    tools = []
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith(('Based on', 'This tool', 'These tools')):
            tools.append(line)
    
    return tools if tools else ["NoTool"]

async def construct_missing_tools(missing_tools: List[str], llm_provider: str = "groq") -> Dict[str, str]:
    llm = LLMInterface(llm_provider)
    
    for tool in missing_tools:
        prompt = TOOL_CONSTRUCTOR_PROMPT.replace("{{context}}", f"Tool to construct: {tool}")
        tool_code = await llm.get_completion(prompt, temperature=0.1)
        
        # Extract the Python code between the markers
        start_marker = "# Start of Example Code File #"
        end_marker = "# End of Example Code File #"
        
        start_idx = tool_code.find(start_marker)
        end_idx = tool_code.find(end_marker)
        
        if start_idx == -1 or end_idx == -1:
            print(f"Invalid response format. Response: {tool_code}")
            return {
                'service': tool,
                'message': "Error: Invalid response format from LLM"
            }
            
        # Extract just the code between the markers
        tool_code = tool_code[start_idx + len(start_marker):end_idx].strip()
        
        try:
            # Execute the code to get the class definition
            namespace = {}
            exec(tool_code, namespace)
            
            # Find the tool class in the namespace
            tool_class = None
            for item in namespace.values():
                if isinstance(item, type) and hasattr(item, 'name') and item.name == tool:
                    tool_class = item
                    break
            
            if not tool_class:
                return {
                    'service': tool,
                    'message': "Error: Could not find tool class in generated code"
                }
            
            # Check for required APIs
            if hasattr(tool_class, 'required_apis') and tool_class.required_apis:
                api_keys = load_api_keys()
                missing_apis = [api for api in tool_class.required_apis if api not in api_keys]
                if missing_apis:
                    return {
                        'service': tool,
                        'message': f"This tool requires the following API keys: {', '.join(missing_apis)}. Please provide them.",
                        'required_apis': missing_apis
                    }
            
            # Replace API key placeholders with actual keys if available
            api_keys = load_api_keys()
            for api_name, key in api_keys.items():
                tool_code = tool_code.replace(f'YOUR_{api_name}', key)
        
            # Add the tool to the manager
            tool_manager.add_tool_from_code(tool_code)
            print(f"Successfully added tool: {tool}")
            return None
            
        except Exception as e:
            print(f"Error constructing tool: {str(e)}")
            print(f"Problematic code:\n{tool_code}")
            return {
                'service': tool,
                'message': f"Error creating tool: {str(e)}"
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
                clean_query = query.lower().replace('what', '').replace('whats', '').replace('what\'s', '')
                clean_query = clean_query.replace('compute', '').replace('calculate', '').strip()
                
                # For square root
                if "sqrt" in clean_query or "square root" in clean_query:
                    return str(tool_instance.run(clean_query))
                
                # For basic arithmetic
                # First, try to extract numbers and operations
                numbers = re.findall(r'-?\d+\.?\d*', clean_query)
                operations = re.findall(r'[\+\-\*\/]', clean_query)
                
                if not numbers:
                    return "Error: No numbers found in query"
                
                if len(numbers) == 1:
                    return numbers[0]
                
                if not operations:
                    return "Error: No operation found in query"
                
                # Construct the expression
                expression = numbers[0]
                for i, op in enumerate(operations):
                    if i + 1 < len(numbers):
                        expression += f"{op}{numbers[i+1]}"
                
                result = tool_instance.run(expression)
                return str(result)
            
            # Handle other tools
            else:
                # Check if the run method expects a query parameter
                import inspect
                sig = inspect.signature(tool_instance.run)
                if len(sig.parameters) > 1:  # More than just self
                    result = tool_instance.run(query)
                else:
                    result = tool_instance.run()
                    
                if isinstance(result, dict):
                    # Format dictionary results nicely
                    return "\n".join(f"{k}: {v}" for k, v in result.items())
                return str(result)
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    return "Error: No suitable tool found to process the query"

async def process_query_with_tools(query: str, llm_provider: str = "groq") -> Dict[str, Any]:
    steps = []
    
    # Step 1: Record the user query and LLM provider
    steps.append({
        "details": f"Query: {query}\nUsing LLM: {llm_provider}"
    })
    
    # Step 2: Determine required tools
    required_tools = await get_required_tools(query, llm_provider)
    steps.append({"details": f"Required tools: {', '.join(required_tools)}"})
    
    # Step 3: Check tool availability
    available_tools = tool_manager.list_tools()
    missing_tools = [tool for tool in required_tools if tool not in available_tools]
    
    if missing_tools:
        steps.append({
            "details": f"Available tools: {', '.join(available_tools)}\n"
                      f"Need to construct: {', '.join(missing_tools)}"
        })
        
        # Step 4: Construct missing tools
        construct_result = await construct_missing_tools(missing_tools, llm_provider)
        if construct_result:
            # If there was an error or API key requirement
            steps.append({"details": f"Construction error: {construct_result['message']}"})
        else:
            # Successfully constructed tools
            steps.append({
                "details": f"Successfully constructed: {', '.join(missing_tools)}\n"
                          f"Now available: {', '.join(tool_manager.list_tools())}"
            })
    else:
        steps.append({"details": f"All required tools are available: {', '.join(required_tools)}"})
    
    # Step 5: Use tools
    steps.append({"details": f"Processing query using {', '.join(required_tools)}"})
    
    # Use the tools to process the query
    final_answer = use_tools(query, required_tools)
    
    return {
        "steps": steps,
        "final_answer": final_answer
    }
