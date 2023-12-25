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
