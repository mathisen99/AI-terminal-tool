"""Image analysis tool definition and implementation."""
import base64
import os
from pathlib import Path
from typing import Dict, Optional
from PIL import Image
import io
import math

# Tool definition for OpenAI function calling (with strict mode)
# Optimized for token efficiency while maintaining clarity
analyze_image_tool_definition = {
    "type": "function",
    "name": "analyze_image",
    "description": "ANALYZE images immediately from file path or URL. Use this when user asks to check/analyze/look at an image. Supports PNG, JPEG, WEBP, GIF (non-animated). Max 50MB. After analyzing, if user asks to fix something, use execute_command to make the changes.",
    "parameters": {
        "type": "object",
        "properties": {
            "image_source": {
                "type": "string",
                "description": "File path or URL. Examples: '~/image.png', 'https://example.com/img.jpg'",
            },
            "detail": {
                "type": ["string", "null"],
                "enum": ["low", "high", "auto", None],
                "description": "Detail level: 'low' (85 tokens, fast), 'high' (detailed), 'auto' (default)",
            },
            "question": {
                "type": ["string", "null"],
                "description": "Optional question about the image",
            },
        },
        "required": ["image_source", "detail", "question"],
        "additionalProperties": False
    },
    "strict": True
}


def validate_image_format(file_path: Path) -> tuple[bool, Optional[str]]:
    """
    Validate that the image is in a supported format.
    
    Args:
        file_path: Path to the image file
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    supported_formats = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
    
    # Check file extension
    extension = file_path.suffix.lower()
    if extension not in supported_formats:
        return False, f"Unsupported format: {extension}. Supported formats: PNG, JPEG, WEBP, GIF"
    
    try:
        # Open and validate with PIL
        with Image.open(file_path) as img:
            # Check if GIF is animated
            if extension == '.gif':
                try:
                    img.seek(1)  # Try to seek to second frame
                    return False, "Animated GIFs are not supported. Only non-animated GIFs are allowed."
                except EOFError:
                    # Only one frame, so it's not animated
                    pass
            
            # Verify it's a valid image
            img.verify()
        
        return True, None
        
    except Exception as e:
        return False, f"Invalid or corrupted image file: {str(e)}"


def validate_file_size(file_path: Path, max_size_mb: int = 50) -> tuple[bool, Optional[str]]:
    """
    Validate that the file size is within limits.
    
    Args:
        file_path: Path to the image file
        max_size_mb: Maximum file size in megabytes
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    file_size = file_path.stat().st_size
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file_size > max_size_bytes:
        size_mb = file_size / (1024 * 1024)
        return False, f"File too large: {size_mb:.2f}MB (max: {max_size_mb}MB)"
    
    return True, None


def encode_image_to_base64(file_path: Path) -> str:
    """
    Encode an image file to base64 string.
    
    Args:
        file_path: Path to the image file
    
    Returns:
        Base64-encoded string of the image
    """
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def calculate_image_tokens(file_path: Path, detail: str = "auto") -> int:
    """
    Calculate the token cost for an image based on its dimensions.
    Uses the formula from docs/image_usage.md for gpt-5.1 (same as gpt-5-mini).
    
    Args:
        file_path: Path to the image file
        detail: Detail level ('low', 'high', 'auto')
    
    Returns:
        Estimated token count for the image
    """
    # Low detail is always 85 tokens
    if detail == "low":
        return 85
    
    try:
        with Image.open(file_path) as img:
            width, height = img.size
        
        # Calculate patches needed (32px x 32px patches)
        raw_patches = math.ceil(width / 32) * math.ceil(height / 32)
        
        # If patches exceed 1536, scale down
        if raw_patches > 1536:
            # Calculate shrink factor
            r = math.sqrt(32 * 32 * 1536 / (width * height))
            
            # Adjust to fit whole patches
            resized_width = width * r
            resized_height = height * r
            
            width_patches = math.floor(resized_width / 32)
            height_patches = math.floor(resized_height / 32)
            
            # Scale again to fit width
            if width_patches > 0:
                scale_factor = width_patches / (resized_width / 32)
                resized_width = resized_width * scale_factor
                resized_height = resized_height * scale_factor
            
            # Calculate final patches
            patches = math.ceil(resized_width / 32) * math.ceil(resized_height / 32)
        else:
            patches = raw_patches
        
        # Cap at 1536 patches
        patches = min(patches, 1536)
        
        # Apply multiplier for gpt-5.1 (1.62)
        tokens = int(patches * 1.62)
        
        return tokens
        
    except Exception:
        # If we can't calculate, return a conservative estimate
        return 1000


def format_image_for_api(image_source: str, detail: str = "auto") -> Dict:
    """
    Format image for OpenAI API input.
    Handles both file paths and URLs.
    
    Args:
        image_source: File path or URL to the image
        detail: Detail level for analysis
    
    Returns:
        Dictionary formatted for API input with image data
    """
    # Check if it's a URL
    if image_source.startswith(("http://", "https://")):
        # For URLs, return the URL directly
        return {
            "type": "input_image",
            "image_url": image_source,
            "detail": detail if detail != "auto" else None
        }
    
    # Handle file path
    # Expand user home directory
    file_path = Path(image_source).expanduser()
    
    # Make absolute if relative
    if not file_path.is_absolute():
        # Use ORIGINAL_CWD if set by alias, otherwise use current directory
        cwd = Path(os.environ.get('ORIGINAL_CWD', os.getcwd()))
        file_path = cwd / file_path
    
    # Check if file exists
    if not file_path.exists():
        raise FileNotFoundError(f"Image file not found: {file_path}")
    
    # Validate format
    is_valid, error = validate_image_format(file_path)
    if not is_valid:
        raise ValueError(error)
    
    # Validate size
    is_valid, error = validate_file_size(file_path)
    if not is_valid:
        raise ValueError(error)
    
    # Encode to base64
    base64_image = encode_image_to_base64(file_path)
    
    # Determine MIME type from extension
    extension = file_path.suffix.lower()
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.webp': 'image/webp',
        '.gif': 'image/gif'
    }
    mime_type = mime_types.get(extension, 'image/jpeg')
    
    # Format as data URL
    data_url = f"data:{mime_type};base64,{base64_image}"
    
    # Calculate token cost
    token_cost = calculate_image_tokens(file_path, detail)
    
    return {
        "type": "input_image",
        "image_url": data_url,
        "detail": detail if detail != "auto" else None,
        "token_cost": token_cost,
        "file_path": str(file_path)
    }


def smart_detail_selection(file_path: Path, detail: str = "auto") -> str:
    """
    Intelligently select detail level based on image characteristics.
    Optimizes token usage while maintaining quality.
    
    Args:
        file_path: Path to the image file
        detail: Requested detail level
    
    Returns:
        Optimized detail level ('low' or 'high')
    """
    if detail != "auto":
        return detail
    
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            
            # Use low detail for small images (< 512x512)
            if width < 512 and height < 512:
                return "low"
            
            # Use low detail for very large images to save tokens
            # (they'll be downscaled anyway)
            if width > 2048 or height > 2048:
                return "low"
            
            # Use high detail for medium-sized images where detail matters
            return "high"
    except:
        # Default to low if we can't determine
        return "low"


def analyze_image(image_source: str, detail: str = "auto", question: Optional[str] = None) -> str:
    """
    Analyze an image from a file path or URL.
    
    This function prepares the image for analysis by the OpenAI API.
    Returns a JSON string that will be parsed by the service layer.
    
    Args:
        image_source: File path or URL to the image
        detail: Detail level ('low', 'high', 'auto')
        question: Optional specific question about the image
    
    Returns:
        JSON string with image data formatted for API and metadata
    """
    try:
        # For file paths, apply smart detail selection
        if not image_source.startswith(("http://", "https://")):
            file_path = Path(image_source).expanduser()
            if not file_path.is_absolute():
                # Use ORIGINAL_CWD if set by alias, otherwise use current directory
                cwd = Path(os.environ.get('ORIGINAL_CWD', os.getcwd()))
                file_path = cwd / file_path
            
            # Smart detail selection for auto mode
            if detail == "auto" and file_path.exists():
                detail = smart_detail_selection(file_path, detail)
        
        # Format image for API
        image_data = format_image_for_api(image_source, detail)
        
        # Build response
        result = {
            "status": "success",
            "image_data": image_data,
            "detail": detail,
            "question": question
        }
        
        # Add metadata for display
        if "file_path" in image_data:
            result["source_type"] = "file"
            result["source"] = image_data["file_path"]
            result["token_cost"] = image_data.get("token_cost", 0)
        else:
            result["source_type"] = "url"
            result["source"] = image_source
            result["token_cost"] = 85 if detail == "low" else 1000  # Estimate for URLs
        
        # Return as JSON string for the service layer
        import json
        return json.dumps(result)
        
    except FileNotFoundError as e:
        import json
        return json.dumps({
            "status": "error",
            "error": str(e),
            "suggestion": "Check that the file path is correct and the file exists."
        })
    
    except ValueError as e:
        import json
        return json.dumps({
            "status": "error",
            "error": str(e),
            "suggestion": "Ensure the image is in a supported format (PNG, JPEG, WEBP, non-animated GIF) and under 50MB."
        })
    
    except Exception as e:
        import json
        return json.dumps({
            "status": "error",
            "error": f"Failed to process image: {str(e)}",
            "suggestion": "Verify the image file is valid and accessible."
        })
