"""Web search function tool that uses OpenAI's web search internally."""
from openai import OpenAI

# Tool definition for function calling (used in voice mode)
web_search_function_tool_definition = {
    "type": "function",
    "name": "web_search",
    "description": "Search the web for current information using OpenAI's web search. Returns relevant results with sources. Use this when you need to find up-to-date information online.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query (e.g., 'weather in Tokyo', 'latest Python news')",
            },
        },
        "required": ["query"],
        "additionalProperties": False
    },
    "strict": True
}


def web_search(query: str) -> str:
    """
    Search the web using OpenAI's built-in web search tool.
    
    This makes a separate API call to the Responses API with web_search enabled,
    allowing voice mode to have web search capabilities.
    
    Args:
        query: Search query
        
    Returns:
        Search results as formatted string
    """
    try:
        client = OpenAI()
        
        # Use a fast model with web search enabled
        response = client.responses.create(
            model="gpt-4o-mini",
            tools=[{"type": "web_search"}],
            input=f"Search the web and provide a summary of results for: {query}",
            tool_choice="required",  # Force web search
        )
        
        # Extract the response text
        result_text = ""
        citations = []
        
        if hasattr(response, "output_text") and response.output_text:
            result_text = response.output_text
        
        # Extract citations from the response
        for item in response.output:
            if item.type == "message" and hasattr(item, "content"):
                for content in item.content:
                    if hasattr(content, "annotations"):
                        for annotation in content.annotations:
                            if annotation.type == "url_citation":
                                citations.append({
                                    "url": annotation.url,
                                    "title": getattr(annotation, "title", ""),
                                })
        
        # Format output
        output = f"🔍 Web search results for: {query}\n"
        output += "=" * 60 + "\n\n"
        output += result_text
        
        if citations:
            output += "\n\n📚 Sources:\n"
            for i, cite in enumerate(citations[:5], 1):  # Limit to 5 sources
                title = cite["title"] or "Source"
                output += f"{i}. {title}\n   {cite['url']}\n"
        
        return output
        
    except Exception as e:
        return f"❌ Web search error: {str(e)}\n\nTry using fetch_webpage with a specific URL instead."
