"""OpenAI service for handling API interactions."""
import json
from openai import OpenAI
from typing import List, Dict, Any, Optional


class OpenAIService:
    """Service class to handle OpenAI API interactions using Responses API."""
    
    def __init__(
        self, 
        model: str = "gpt-5.1",
        reasoning: str = "none",
        verbosity: str = "medium"
    ):
        """
        Initialize the OpenAI service.
        
        Args:
            model: The model to use for completions (default: gpt-5.1)
            reasoning: Reasoning effort level (none, low, medium, high)
            verbosity: Output verbosity level (low, medium, high)
        """
        self.client = OpenAI()
        self.model = model
        self.reasoning = reasoning
        self.verbosity = verbosity
    
    def create_response(
        self,
        input_list: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        reasoning: Optional[Dict[str, str]] = None,
        text: Optional[Dict[str, str]] = None,
        tool_choice: str = "auto"
    ) -> Any:
        """
        Create a response using the Responses API with GPT-5.1.
        
        Args:
            input_list: List of input messages and function calls
            tools: List of available tools for function calling
            reasoning: Optional reasoning configuration dict (e.g., {"effort": "low"})
            text: Optional text configuration dict (e.g., {"verbosity": "low"})
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
        
        # Add reasoning configuration
        if reasoning:
            kwargs["reasoning"] = reasoning
        else:
            kwargs["reasoning"] = {"effort": self.reasoning}
        
        # Add verbosity configuration
        if text:
            kwargs["text"] = text
        else:
            kwargs["text"] = {"verbosity": self.verbosity}
        
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
                        "output": json.dumps(result) if not isinstance(result, str) else result
                    })
        
        return function_outputs
