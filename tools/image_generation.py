"""Image generation and editing tools using FLUX.1 Kontext API."""
import os
import time
import base64
import requests
from typing import Optional, Dict, Any
from PIL import Image
from io import BytesIO


def generate_image(
    prompt: str,
    aspect_ratio: str = "1:1",
    seed: Optional[int] = None,
    output_format: str = "jpeg"
) -> str:
    """
    Generate an image from a text prompt using FLUX.1 Kontext API.
    Automatically downloads the image to the current directory.
    
    Args:
        prompt: Text description of the desired image
        aspect_ratio: Desired aspect ratio (e.g., "16:9", "1:1"). Supports 3:7 to 7:3
        seed: Seed for reproducibility (optional)
        output_format: Output format ("jpeg" or "png")
    
    Returns:
        str: Result message with saved filename or error
    """
    api_key = os.environ.get("BFL_API_KEY")
    if not api_key:
        return "❌ Error: BFL_API_KEY not found in environment variables"
    
    try:
        # Create request
        request_data = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "output_format": output_format
        }
        
        if seed is not None:
            request_data["seed"] = seed
        
        response = requests.post(
            'https://api.bfl.ai/v1/flux-kontext-pro',
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
                
                return f"✓ Image generated and saved!\n\nFile: {filename}\nLocation: {cwd}\nSize: {file_size:.1f} KB\n\nPrompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}"
            
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
    aspect_ratio: Optional[str] = None,
    seed: Optional[int] = None,
    output_format: str = "jpeg"
) -> str:
    """
    Edit an existing image using a text prompt with FLUX.1 Kontext API.
    
    Args:
        prompt: Text description of the edit to apply
        input_image: File path or URL of the image to edit
        aspect_ratio: Desired aspect ratio (optional, defaults to input image dimensions)
        seed: Seed for reproducibility (optional)
        output_format: Output format ("jpeg" or "png")
    
    Returns:
        str: Result message with edited image URL or error
    """
    api_key = os.environ.get("BFL_API_KEY")
    if not api_key:
        return "❌ Error: BFL_API_KEY not found in environment variables"
    
    try:
        # Load and encode image
        img_str = None
        
        # Check if input is a URL
        if input_image.startswith(('http://', 'https://')):
            # Download image from URL
            img_response = requests.get(input_image, timeout=30)
            if img_response.status_code != 200:
                return f"❌ Error: Failed to download image from URL: {input_image}"
            
            img = Image.open(BytesIO(img_response.content))
        else:
            # Load from file path
            if not os.path.exists(input_image):
                return f"❌ Error: Image file not found: {input_image}"
            
            img = Image.open(input_image)
        
        # Convert to base64
        buffered = BytesIO()
        # Determine format from image or use output_format
        img_format = img.format if img.format else output_format.upper()
        if img_format not in ['JPEG', 'PNG']:
            img_format = 'JPEG'
        
        img.save(buffered, format=img_format)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Create request
        request_data = {
            "prompt": prompt,
            "input_image": img_str,
            "output_format": output_format
        }
        
        if aspect_ratio:
            request_data["aspect_ratio"] = aspect_ratio
        
        if seed is not None:
            request_data["seed"] = seed
        
        response = requests.post(
            'https://api.bfl.ai/v1/flux-kontext-pro',
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
                
                return f"✓ Image edited and saved!\n\nFile: {filename}\nLocation: {cwd}\nSize: {file_size:.1f} KB\n\nEdit: {prompt[:100]}{'...' if len(prompt) > 100 else ''}"
            
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
    "description": "Generate images from text prompts using FLUX.1 Kontext. Creates 1024x1024 images, adjustable aspect ratio (3:7 to 7:3).",
    "parameters": {
        "type": "object",
        "required": ["prompt", "aspect_ratio", "seed", "output_format"],
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text description of the desired image"
            },
            "aspect_ratio": {
                "type": "string",
                "description": "Aspect ratio like '16:9' or '1:1'. Supports 3:7 to 7:3. Use '1:1' for square"
            },
            "seed": {
                "type": ["integer", "null"],
                "description": "Seed for reproducibility. Use null for random"
            },
            "output_format": {
                "type": "string",
                "enum": ["jpeg", "png"],
                "description": "Output format: 'jpeg' or 'png'"
            }
        },
        "additionalProperties": False
    },
    "strict": True
}

edit_image_tool_definition = {
    "type": "function",
    "name": "edit_image",
    "description": "Edit images with text prompts using FLUX.1 Kontext. Supports object/text edits, iterative changes. Input: file path or URL.",
    "parameters": {
        "type": "object",
        "required": ["prompt", "input_image", "aspect_ratio", "seed", "output_format"],
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text description of the edit. For text edits: Replace '[old]' with '[new]'"
            },
            "input_image": {
                "type": "string",
                "description": "File path or URL of the image to edit"
            },
            "aspect_ratio": {
                "type": ["string", "null"],
                "description": "Override aspect ratio or use null to match input dimensions"
            },
            "seed": {
                "type": ["integer", "null"],
                "description": "Seed for reproducibility. Use null for random"
            },
            "output_format": {
                "type": "string",
                "enum": ["jpeg", "png"],
                "description": "Output format: 'jpeg' or 'png'"
            }
        },
        "additionalProperties": False
    },
    "strict": True
}
