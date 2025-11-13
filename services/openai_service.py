"""OpenAI service for handling API interactions."""
import json
from openai import OpenAI
from typing import List, Dict, Any


class OpenAIService:
    """Service class to handle OpenAI API interactions."""
    
    def __init__(self, model: str = "gpt-5"):
        """
        Initialize the OpenAI service.
        
        Args:
            model: The model to use for completions
        """
        self.client = OpenAI()
        self.model = model
    
    def create_response(
        self,
        input_list: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        instructions: str = None,
        tool_choice: str = "auto"
    ) -> Any:
        """
        Create a response using the OpenAI API.
        
        Args:
            input_list: List of input messages and function calls
            tools: List of available tools for function calling
            instructions: Optional instructions for the model
            tool_choice: Controls tool usage ("auto", "required", "none")
        
        Returns:
            The API response object
        """
        kwargs = {
            "model": self.model,
            "tools": tools,
            "input": input_list,
            "tool_choice": tool_choice,
        }
        
        if instructions:
            kwargs["instructions"] = instructions
        
        return self.client.responses.create(**kwargs)
    
    def process_function_calls(
        self,
        response: Any,
        function_handlers: Dict[str, callable]
    ) -> List[Dict[str, Any]]:
        """
        Process function calls from the API response.
        
        Args:
            response: The API response containing function calls
            function_handlers: Dictionary mapping function names to handler functions
        
        Returns:
            List of function call output objects
        """
        function_outputs = []
        
        for item in response.output:
            if item.type == "function_call":
                handler = function_handlers.get(item.name)
                if handler:
                    # Parse arguments and call the function
                    args = json.loads(item.arguments)
                    result = handler(**args)
                    
                    # Format the output for the API
                    function_outputs.append({
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps({"horoscope": result})
                    })
        
        return function_outputs
