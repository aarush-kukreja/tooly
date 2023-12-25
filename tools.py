import math
from typing import Dict, Any, List
import importlib
import ast
import types

class ToolManager:
    def __init__(self):
        self.tools = {}
        # Initialize with calculator tool
        self.add_tool("Calculator", CalculatorTool)

    def add_tool(self, name: str, tool_class: Any) -> None:
        self.tools[name] = tool_class()

    def get_tool(self, name: str) -> Any:
        return self.tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self.tools.keys())

    def add_tool_from_code(self, code: str) -> None:
        try:
            # Parse the code to ensure it's valid Python
            ast.parse(code)
            
            # Create a new module to execute the code in
            module = types.ModuleType(f"dynamic_tool_{len(self.tools)}")
            
            # Execute the code in the new module's namespace
            exec(code, module.__dict__)
            
            # Find new classes that are subclasses of object (to avoid importing built-ins)
            new_tools = [obj for name, obj in module.__dict__.items() 
                         if isinstance(obj, type) and issubclass(obj, object) and obj.__module__ == module.__name__]
            
            for tool_class in new_tools:
                if hasattr(tool_class, 'name') and hasattr(tool_class, 'run'):
                    self.add_tool(tool_class.name, tool_class)
                else:
                    print(f"Warning: {tool_class.__name__} is missing required attributes (name or run method)")
        except Exception as e:
            print(f"Error adding tool from code: {str(e)}")
            print(f"Problematic code:\n{code}")

class CalculatorTool:
    name = "Calculator"
    description = ("Use this tool to perform basic arithmetic operations. "
                   "Supported operations: addition (+), subtraction (-), "
                   "multiplication (*), division (/), exponentiation (**), "
                   "and modulo (%). Provide the expression as a string.")

    @staticmethod
    def run(expression: str) -> float:
        try:
            # Clean the expression
            expression = expression.strip()
            # Use a safe eval function to calculate the result
            result = eval(expression, {"__builtins__": None}, {"math": math})
            return float(result)
        except Exception as e:
            return f"Error: {str(e)}"

# The 'tools' list is no longer needed in this file, as we're using the ToolManager
