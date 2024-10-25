# Tooly

This project is a web application that processes user queries using a Large Language Model (LLM) and provides reasoned responses. It includes a calculator tool for arithmetic operations and can be extended with additional tools.

## Features

- Web interface for submitting queries
- LLM-powered responses with reasoning and final answers
- Calculator tool for arithmetic operations
- Extensible architecture for adding more tools

## Technologies Used

- Python 3.x
- FastAPI
- Jinja2 Templates
- Groq API (LLM provider)
- HTML/CSS/JavaScript

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/llm-query-processor.git
   cd llm-query-processor
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root and add your Groq API key:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```

5. Run the application:
   ```
   python main.py
   ```

6. Open your web browser and navigate to `http://localhost:8000` to use the application.

## Project Structure

- `main.py`: FastAPI application setup and routes
- `llm_helper.py`: Functions for interacting with the LLM
- `tools.py`: Definitions for tools (e.g., Calculator)
- `prompts.py`: Prompt templates for tool generation
- `templates/index.html`: HTML template for the web interface
- `static/styles.css`: CSS styles for the web interface
- `static/app.js`: JavaScript for handling form submission

## Extending the Project

To add new tools or functionality:

1. Define new tool classes in `tools.py`
2. Update the `tools` list in `tools.py` with the new tool definitions
3. Modify `llm_helper.py` to handle the new tools if necessary
4. Update the web interface in `templates/index.html` to accommodate new features

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open-source and available under the [MIT License](LICENSE).
