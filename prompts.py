TOOL_LIST_PROMPT = """
You are a tool selector. Your job is to identify which tools are needed to complete a given task.

Available tools:
- Calculator: For arithmetic operations
- WeatherTool: For current weather and forecasts
- TimeTool: For current time and date information

If the task requires a tool that's not listed above, you should identify what kind of tool would be needed.
For example:
- Astronomy queries need an AstronomyTool
- Recipe queries need a RecipeTool
- Translation needs a TranslationTool

The user has given the following task:

{{context}}

List only the names of the tools needed, one per line. Include any new tools that would need to be created.
For example:
Calculator
AstronomyTool
TranslationTool

Keep tool names simple and consistent. End each tool name with 'Tool' except for Calculator.
"""

TOOL_CONSTRUCTOR_PROMPT = """
You are a tool constructor. You must return ONLY valid Python code between the markers, with no additional text or explanation.

The user needs the following tool:

{{context}}

Create a Python class that implements this tool. If the tool requires external APIs:
1. Use standard APIs like NASA API for astronomy, OpenWeatherMap for weather, etc.
2. Include the API key requirement in the code using a placeholder
3. Document the API requirement in the class description

Your response must follow this EXACT format:

# Start of Example Code File #
import requests
from typing import Dict, Any

class AstronomyTool:
    name = "AstronomyTool"
    description = "Get astronomical data using NASA APIs"
    required_apis = ["NASA_API_KEY"]

    def __init__(self):
        self.api_key = "YOUR_NASA_API_KEY"
        self.base_url = "https://api.nasa.gov/planetary"

    def run(self, query: str) -> Dict[str, Any]:
        try:
            # Example: Get moon phase and position
            params = {
                "api_key": self.api_key,
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            response = requests.get(f"{self.base_url}/moon", params=params)
            data = response.json()
            
            if response.status_code == 200:
                return {
                    "moon_phase": data["moon_phase"],
                    "moon_position": data["position"],
                    "visibility": data["visibility"]
                }
            else:
                return {"error": f"API Error: {data.get('message', 'Unknown error')}"}
        except Exception as e:
            return {"error": f"Error: {str(e)}"}
# End of Example Code File #

IMPORTANT:
1. Include ALL necessary imports
2. Class MUST have 'name' attribute and 'run' method
3. If APIs are needed, include 'required_apis' class variable
4. Handle ALL exceptions
5. NO text before or after the markers
"""
