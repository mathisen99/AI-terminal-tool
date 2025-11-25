"""Image generation and editing tools using FLUX.2 API."""
import os
import time
import base64
import requests
from typing import Optional, Dict, Any, List
from PIL import Image
from io import BytesIO


def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    seed: Optional[int] = None,
    output_format: str = "jpeg",
    model: str = "pro",
    safety_tolerance: int = 2,
    steps: Optional[int] = None,
    guidance: Optional[float] = None
) -> str:
    """
    Generate an image from a text prompt using FLUX.2 API.
    Automatically downloads the image to the current directory.
    
    Args:
        prompt: Text description of the desired image (supports up to 32K tokens)
        width: Output width in pixels (must be multiple of 16, default 1024)
        height: Output height in pixels (must be multiple of 16, default 1024)
        seed: Seed for reproducibility (optional)
        output_format: Output format ("jpeg" or "png")
        model: Model to use ("pro" for fast/efficient or "flex" for maximum quality)
        safety_tolerance: Moderation level 0 (strict) to 6 (permissive), default 2
        steps: [flex only] Number of inference steps (max 50, default 50)
        guidance: [flex only] Guidance scale 1.5-10 (default 4.5)
    
    Returns:
        str: Result message with saved filename or error
    """
    api_key = os.environ.get("BFL_API_KEY")
    if not api_key:
        return "❌ Error: BFL_API_KEY not found in environment variables"
    
    # Validate dimensions (must be multiples of 16)
    if width % 16 != 0 or height % 16 != 0:
        return f"❌ Error: Width and height must be multiples of 16. Got {width}x{height}"
    
    # Validate resolution (max 4MP)
    megapixels = (width * height) / 1_000_000
    if megapixels > 4:
        return f"❌ Error: Maximum resolution is 4MP. Got {megapixels:.2f}MP ({width}x{height})"
    
    try:
        # Select endpoint based on model
        endpoint = f'https://api.bfl.ai/v1/flux-2-{model}'
        
        # Create request
        request_data = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "output_format": output_format,
            "safety_tolerance": safety_tolerance
        }
        
        if seed is not None:
            request_data["seed"] = seed
        
        # Add flex-only parameters
        if model == "flex":
            if steps is not None:
                request_data["steps"] = min(steps, 50)
            if guidance is not None:
                request_data["guidance"] = max(1.5, min(guidance, 10.0))
        
        response = requests.post(
            endpoint,
            headers={
                'accept': 'application/json',
                'x-key': api_key,
                'Content-Type': 'application/json',
            },
            json=request_data,
            timeout=30
        )
        
        if response.status_code != 200:
            return f"❌ Error: API request failed with status {response.status_code}: {response.text}"
        
        request_result = response.json()
        request_id = request_result.get("id")
        polling_url = request_result.get("polling_url")
        
        if not polling_url:
            return f"❌ Error: No polling URL returned: {request_result}"
        
        # Poll for result (max 60 seconds)
        max_attempts = 120
        attempt = 0
        
        while attempt < max_attempts:
            time.sleep(0.5)
            attempt += 1
            
            poll_response = requests.get(
                polling_url,
                headers={
                    'accept': 'application/json',
                    'x-key': api_key,
                },
                timeout=10
            )
            
            if poll_response.status_code != 200:
                return f"❌ Error: Polling failed with status {poll_response.status_code}"
            
            result = poll_response.json()
            status = result.get('status')
            
            if status == 'Ready':
                image_url = result.get('result', {}).get('sample')
                if not image_url:
                    return f"❌ Error: No image URL in result: {result}"
                
                # Download the image
                img_response = requests.get(image_url, timeout=30)
                if img_response.status_code != 200:
                    return f"❌ Error: Failed to download image from URL"
                
                # Generate filename from prompt (first 50 chars, sanitized)
                import re
                from datetime import datetime
                
                # Sanitize prompt for filename
                safe_prompt = re.sub(r'[^\w\s-]', '', prompt.lower())
                safe_prompt = re.sub(r'[-\s]+', '_', safe_prompt)
                safe_prompt = safe_prompt[:50].strip('_')
                
                # Add timestamp to ensure uniqueness
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Get current working directory (use ORIGINAL_CWD if set by alias)
                cwd = os.environ.get('ORIGINAL_CWD', os.getcwd())
                
                # Create filename
                extension = output_format if output_format in ['jpeg', 'png'] else 'jpeg'
                if extension == 'jpeg':
                    extension = 'jpg'
                filename = f"generated_{safe_prompt}_{timestamp}.{extension}"
                filepath = os.path.join(cwd, filename)
                
                # Save the image
                with open(filepath, 'wb') as f:
                    f.write(img_response.content)
                
                file_size = len(img_response.content) / 1024  # KB
                cost = request_result.get("cost", "N/A")
                
                return f"✓ Image generated and saved!\n\nFile: {filename}\nLocation: {cwd}\nSize: {file_size:.1f} KB\nCost: {cost} credits\nModel: FLUX.2 [{model}]\n\nPrompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}"
            
            elif status in ['Error', 'Failed']:
                error_msg = result.get('error', 'Unknown error')
                return f"❌ Generation failed: {error_msg}"
        
        return "❌ Error: Timeout waiting for image generation (60 seconds)"
        
    except requests.exceptions.Timeout:
        return "❌ Error: Request timeout. Please try again."
    except Exception as e:
        return f"❌ Error generating image: {str(e)}"


def edit_image(
    prompt: str,
    input_image: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    seed: Optional[int] = None,
    output_format: str = "jpeg",
    model: str = "pro",
    safety_tolerance: int = 2,
    steps: Optional[int] = None,
    guidance: Optional[float] = None,
    reference_images: Optional[List[str]] = None
) -> str:
    """
    Edit an existing image using a text prompt with FLUX.2 API.
    Supports multi-reference editing with up to 8 additional images (pro) or 10 (flex).
    
    Args:
        prompt: Text description of the edit to apply (supports up to 32K tokens)
        input_image: File path or URL of the main image to edit
        width: Output width in pixels (optional, defaults to input image width)
        height: Output height in pixels (optional, defaults to input image height)
        seed: Seed for reproducibility (optional)
        output_format: Output format ("jpeg" or "png")
        model: Model to use ("pro" for fast or "flex" for maximum quality)
        safety_tolerance: Moderation level 0 (strict) to 6 (permissive), default 2
        steps: [flex only] Number of inference steps (max 50, default 50)
        guidance: [flex only] Guidance scale 1.5-10 (default 4.5)
        reference_images: List of additional reference image paths/URLs (max 8 for pro, 10 for flex)
    
    Returns:
        str: Result message with edited image filename or error
    """
    api_key = os.environ.get("BFL_API_KEY")
    if not api_key:
        return "❌ Error: BFL_API_KEY not found in environment variables"
    
    # Validate reference images count
    max_refs = 10 if model == "flex" else 8
    if reference_images and len(reference_images) > max_refs:
        return f"❌ Error: Maximum {max_refs} reference images for {model} model. Got {len(reference_images)}"
    
    # Validate dimensions if provided
    if width is not None and width % 16 != 0:
        return f"❌ Error: Width must be a multiple of 16. Got {width}"
    if height is not None and height % 16 != 0:
        return f"❌ Error: Height must be a multiple of 16. Got {height}"
    
    try:
        def load_and_encode_image(image_path_or_url: str) -> str:
            """Load image from path or URL and encode to base64."""
            if image_path_or_url.startswith(('http://', 'https://')):
                # Use URL directly (API supports URLs)
                return image_path_or_url
            else:
                # Load from file path and encode
                if not os.path.exists(image_path_or_url):
                    raise FileNotFoundError(f"Image file not found: {image_path_or_url}")
                
                img = Image.open(image_path_or_url)
                buffered = BytesIO()
                img_format = img.format if img.format else 'JPEG'
                if img_format not in ['JPEG', 'PNG']:
                    img_format = 'JPEG'
                
                img.save(buffered, format=img_format)
                return base64.b64encode(buffered.getvalue()).decode()
        
        # Load and encode main input image
        input_img_data = load_and_encode_image(input_image)
        
        # Select endpoint based on model
        endpoint = f'https://api.bfl.ai/v1/flux-2-{model}'
        
        # Create request
        request_data = {
            "prompt": prompt,
            "input_image": input_img_data,
            "output_format": output_format,
            "safety_tolerance": safety_tolerance
        }
        
        if width is not None:
            request_data["width"] = width
        if height is not None:
            request_data["height"] = height
        
        if seed is not None:
            request_data["seed"] = seed
        
        # Add flex-only parameters
        if model == "flex":
            if steps is not None:
                request_data["steps"] = min(steps, 50)
            if guidance is not None:
                request_data["guidance"] = max(1.5, min(guidance, 10.0))
        
        # Add reference images
        if reference_images:
            for idx, ref_img in enumerate(reference_images, start=2):
                ref_data = load_and_encode_image(ref_img)
                request_data[f"input_image_{idx}"] = ref_data
        
        response = requests.post(
            endpoint,
            headers={
                'accept': 'application/json',
                'x-key': api_key,
                'Content-Type': 'application/json',
            },
            json=request_data,
            timeout=30
        )
        
        if response.status_code != 200:
            return f"❌ Error: API request failed with status {response.status_code}: {response.text}"
        
        request_result = response.json()
        polling_url = request_result.get("polling_url")
        
        if not polling_url:
            return f"❌ Error: No polling URL returned: {request_result}"
        
        # Poll for result (max 60 seconds)
        max_attempts = 120
        attempt = 0
        
        while attempt < max_attempts:
            time.sleep(0.5)
            attempt += 1
            
            poll_response = requests.get(
                polling_url,
                headers={
                    'accept': 'application/json',
                    'x-key': api_key,
                },
                timeout=10
            )
            
            if poll_response.status_code != 200:
                return f"❌ Error: Polling failed with status {poll_response.status_code}"
            
            result = poll_response.json()
            status = result.get('status')
            
            if status == 'Ready':
                image_url = result.get('result', {}).get('sample')
                if not image_url:
                    return f"❌ Error: No image URL in result: {result}"
                
                # Download the edited image
                img_response = requests.get(image_url, timeout=30)
                if img_response.status_code != 200:
                    return f"❌ Error: Failed to download edited image from URL"
                
                # Generate filename from original image and prompt
                import re
                from datetime import datetime
                
                # Get base name from input image
                if input_image.startswith(('http://', 'https://')):
                    base_name = "edited_image"
                else:
                    base_name = os.path.splitext(os.path.basename(input_image))[0]
                
                # Sanitize prompt for filename (first 30 chars)
                safe_prompt = re.sub(r'[^\w\s-]', '', prompt.lower())
                safe_prompt = re.sub(r'[-\s]+', '_', safe_prompt)
                safe_prompt = safe_prompt[:30].strip('_')
                
                # Add timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Get current working directory (use ORIGINAL_CWD if set by alias)
                cwd = os.environ.get('ORIGINAL_CWD', os.getcwd())
                
                # Create filename
                extension = output_format if output_format in ['jpeg', 'png'] else 'jpeg'
                if extension == 'jpeg':
                    extension = 'jpg'
                filename = f"{base_name}_edited_{safe_prompt}_{timestamp}.{extension}"
                filepath = os.path.join(cwd, filename)
                
                # Save the image
                with open(filepath, 'wb') as f:
                    f.write(img_response.content)
                
                file_size = len(img_response.content) / 1024  # KB
                cost = request_result.get("cost", "N/A")
                ref_count = len(reference_images) if reference_images else 0
                
                return f"✓ Image edited and saved!\n\nFile: {filename}\nLocation: {cwd}\nSize: {file_size:.1f} KB\nCost: {cost} credits\nModel: FLUX.2 [{model}]\nReferences: {ref_count + 1} image(s)\n\nEdit: {prompt[:100]}{'...' if len(prompt) > 100 else ''}"
            
            elif status in ['Error', 'Failed']:
                error_msg = result.get('error', 'Unknown error')
                return f"❌ Edit failed: {error_msg}"
        
        return "❌ Error: Timeout waiting for image editing (60 seconds)"
        
    except requests.exceptions.Timeout:
        return "❌ Error: Request timeout. Please try again."
    except Exception as e:
        return f"❌ Error editing image: {str(e)}"


# Tool definitions for OpenAI function calling
generate_image_tool_definition = {
    "type": "function",
    "name": "generate_image",
    "description": "Generate images from text prompts using FLUX.2. Supports up to 4MP output, hex color codes, typography. [pro]=fast/efficient, [flex]=max quality.",
    "parameters": {
        "type": "object",
        "required": ["prompt", "width", "height", "seed", "output_format", "model", "safety_tolerance", "steps", "guidance"],
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text description of desired image. Supports hex colors (e.g., 'color #ff0088'), structured prompts, up to 32K tokens"
            },
            "width": {
                "type": "integer",
                "description": "Output width in pixels (multiple of 16, max 4MP total). Default 1024"
            },
            "height": {
                "type": "integer",
                "description": "Output height in pixels (multiple of 16, max 4MP total). Default 1024"
            },
            "seed": {
                "type": ["integer", "null"],
                "description": "Seed for reproducibility. Use null for random"
            },
            "output_format": {
                "type": "string",
                "enum": ["jpeg", "png"],
                "description": "Output format: 'jpeg' or 'png'"
            },
            "model": {
                "type": "string",
                "enum": ["pro", "flex"],
                "description": "'pro' for fast/efficient (<10s, $0.03), 'flex' for max quality (higher latency, $0.06)"
            },
            "safety_tolerance": {
                "type": "integer",
                "description": "Moderation level: 0 (strict) to 6 (permissive). Default 2"
            },
            "steps": {
                "type": ["integer", "null"],
                "description": "[flex only] Inference steps (max 50). Higher=more detail. Default 50"
            },
            "guidance": {
                "type": ["number", "null"],
                "description": "[flex only] Guidance scale 1.5-10. Higher=closer prompt adherence. Default 4.5"
            }
        },
        "additionalProperties": False
    },
    "strict": True
}

edit_image_tool_definition = {
    "type": "function",
    "name": "edit_image",
    "description": "Edit images with FLUX.2. Multi-reference support (up to 8 refs for pro, 10 for flex). Photorealistic edits, text changes, object replacement, pose guidance.",
    "parameters": {
        "type": "object",
        "required": ["prompt", "input_image", "width", "height", "seed", "output_format", "model", "safety_tolerance", "steps", "guidance", "reference_images"],
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Edit description. Reference images by index: 'person from image 1', 'cat from image 2'. Supports hex colors, up to 32K tokens"
            },
            "input_image": {
                "type": "string",
                "description": "Main image file path or URL to edit"
            },
            "width": {
                "type": ["integer", "null"],
                "description": "Output width (multiple of 16). Null=match input. Max 4MP total"
            },
            "height": {
                "type": ["integer", "null"],
                "description": "Output height (multiple of 16). Null=match input. Max 4MP total"
            },
            "seed": {
                "type": ["integer", "null"],
                "description": "Seed for reproducibility. Use null for random"
            },
            "output_format": {
                "type": "string",
                "enum": ["jpeg", "png"],
                "description": "Output format: 'jpeg' or 'png'"
            },
            "model": {
                "type": "string",
                "enum": ["pro", "flex"],
                "description": "'pro' for fast (<10s, $0.045), 'flex' for max quality ($0.12)"
            },
            "safety_tolerance": {
                "type": "integer",
                "description": "Moderation level: 0 (strict) to 6 (permissive). Default 2"
            },
            "steps": {
                "type": ["integer", "null"],
                "description": "[flex only] Inference steps (max 50). Default 50"
            },
            "guidance": {
                "type": ["number", "null"],
                "description": "[flex only] Guidance scale 1.5-10. Default 4.5"
            },
            "reference_images": {
                "type": ["array", "null"],
                "items": {
                    "type": "string"
                },
                "description": "Additional reference image paths/URLs. Max 8 for pro, 10 for flex. Use for multi-reference editing"
            }
        },
        "additionalProperties": False
    },
    "strict": True
}
