TOOL_LIST_PROMPT = """
You are a tool selector. Your job is to identify which tools are needed to complete a given task.

For arithmetic operations (add, subtract, multiply, divide), always use the Calculator tool.

The user has given the following task:

{{context}}

List only the names of the tools needed, one per line. Do not include explanations or numbering.
For example:
Calculator
WeatherTool
RecipeTool

Keep tool names simple and consistent.
"""

TOOL_CONSTRUCTOR_PROMPT = """
The user has provided a list of tools the agent would need to complete a task. The user has provided the following information:

{{context}}

Based on the context and the list of tools, construct the tools. Return the code, classes, or functions that would be used to construct the tools.

You must write the code file in its entirety.

For example, if the user has provided a calculator tool, the agent would need to construct a calculator tool class or function. Here is an example of a calculator tool class:

# Start of Example Code File #


import math
from typing import Dict, Any

class CalculatorTool:
    name = "Calculator"
    description = ("Use this tool to perform basic arithmetic operations. "
                   "Supported operations: addition (+), subtraction (-), "
                   "multiplication (*), division (/), exponentiation (**), "
                   "and modulo (%). Provide the expression as a string.")

    @staticmethod
    def run(expression: str) -> float:
        try:
            # Use a safe eval function to calculate the result
            result = eval(expression, {"__builtins__": None}, {"math": math})
            return float(result)
        except Exception as e:
            return f"Error: {str(e)}"

tools: list[Dict[str, Any]] = [
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
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": CalculatorTool.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The arithmetic expression to evaluate",
                    },
                },
                "required": ["expression"],
            },
        },
    }
]


# End of Example Code File #


"""
