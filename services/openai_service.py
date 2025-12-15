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
        function_handlers: Dict[str, callable],
        dangerous_commands_confirmed: Optional[Dict[str, bool]] = None
    ) -> List[Dict[str, Any]]:
        """
        Process function calls from the API response.
        
        Args:
            response: The API response containing function calls
            function_handlers: Dictionary mapping function names to handler functions
            dangerous_commands_confirmed: Optional dict of command -> confirmed status for pre-confirmed dangerous commands
        
        Returns:
            List of function call output objects and/or user messages with image data
        """
        function_outputs = []
        dangerous_commands_confirmed = dangerous_commands_confirmed or {}
        
        for item in response.output:
            if item.type == "function_call":
                handler = function_handlers.get(item.name)
                if handler:
                    # Parse arguments and call the function
                    args = json.loads(item.arguments)
                    
                    # For execute_command, check if we have a pre-confirmation result
                    if item.name == "execute_command":
                        command = args.get("command", "")
                        if command in dangerous_commands_confirmed:
                            # Pass the pre-confirmation result
                            args["_pre_confirmed"] = dangerous_commands_confirmed[command]
                    
                    result = handler(**args)
                    
                    # Special handling for analyze_image
                    if item.name == "analyze_image":
                        # Parse the result JSON
                        result_data = json.loads(result) if isinstance(result, str) else result
                        
                        if result_data.get("status") == "success":
                            # Extract image data and question
                            image_data = result_data.get("image_data", {})
                            question = result_data.get("question")
                            
                            # Build content array for user message
                            content = []
                            
                            # Add question text if provided
                            if question:
                                content.append({
                                    "type": "input_text",
                                    "text": question
                                })
                            else:
                                content.append({
                                    "type": "input_text",
                                    "text": "What's in this image?"
                                })
                            
                            # Add image
                            image_content = {
                                "type": "input_image",
                                "image_url": image_data.get("image_url")
                            }
                            
                            # Add detail if specified
                            detail = image_data.get("detail")
                            if detail and detail != "auto":
                                image_content["detail"] = detail
                            
                            content.append(image_content)
                            
                            # Add as user message with image
                            function_outputs.append({
                                "role": "user",
                                "content": content
                            })
                            
                            # Also add function call output to acknowledge the tool call
                            source = result_data.get("source", "image")
                            token_cost = result_data.get("token_cost", 0)
                            function_outputs.append({
                                "type": "function_call_output",
                                "call_id": item.call_id,
                                "output": f"✓ Image loaded successfully from {source} (estimated {token_cost} tokens). Analyzing..."
                            })
                        else:
                            # Error case - return error message
                            error = result_data.get("error", "Unknown error")
                            suggestion = result_data.get("suggestion", "")
                            error_msg = f"❌ Error: {error}"
                            if suggestion:
                                error_msg += f"\n\n💡 {suggestion}"
                            
                            function_outputs.append({
                                "type": "function_call_output",
                                "call_id": item.call_id,
                                "output": error_msg
                            })
                    else:
                        # Standard function call handling
                        function_outputs.append({
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": json.dumps(result) if not isinstance(result, str) else result
                        })
        
        return function_outputs
