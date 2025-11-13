"""Web fetch tool definition and implementation."""
import requests
from bs4 import BeautifulSoup
import random
from typing import Dict

# Rotating user agents to avoid bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Tool definition for OpenAI function calling
web_fetch_tool_definition = {
    "type": "function",
    "name": "fetch_webpage",
    "description": "Fetch and extract clean text content from a webpage URL. Handles JavaScript-rendered pages and bypasses basic bot protection. Returns up to 25,000 characters of clean text.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The full URL of the webpage to fetch (e.g., 'https://example.com/article')",
            },
        },
        "required": ["url"],
    },
}


def extract_text_from_html(html_content: str) -> str:
    """
    Extract clean text from HTML content.
    
    Args:
        html_content: Raw HTML content
    
    Returns:
        Clean text extracted from HTML
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove script and style elements
    for script in soup(["script", "style", "noscript", "iframe"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = "\n".join(chunk for chunk in chunks if chunk)
    
    return text


def fetch_with_requests(url: str) -> Dict[str, str]:
    """
    Fetch webpage using requests library with rotating user agents.
    
    Args:
        url: URL to fetch
    
    Returns:
        Dictionary with status and content or error
    """
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        return {"status": "success", "content": response.text}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": str(e)}


def fetch_with_selenium(url: str) -> Dict[str, str]:
    """
    Fetch webpage using Selenium for JavaScript-rendered content.
    
    Args:
        url: URL to fetch
    
    Returns:
        Dictionary with status and content or error
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Create driver
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            driver.get(url)
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            content = driver.page_source
            return {"status": "success", "content": content}
        finally:
            driver.quit()
            
    except ImportError:
        return {"status": "error", "error": "Selenium not installed. Install with: pip install selenium"}
    except Exception as e:
        return {"status": "error", "error": f"Selenium error: {str(e)}"}


def fetch_webpage(url: str) -> str:
    """
    Fetch and extract clean text content from a webpage.
    
    Args:
        url: The URL of the webpage to fetch
    
    Returns:
        Clean text content from the webpage (max 25,000 characters)
    """
    # Validate URL
    if not url.startswith(("http://", "https://")):
        return f"Error: Invalid URL. URL must start with http:// or https://"
    
    # Try fetching with requests first (faster)
    result = fetch_with_requests(url)
    
    # If requests fails, try Selenium for JavaScript-rendered content
    if result["status"] == "error":
        result = fetch_with_selenium(url)
    
    # Handle errors
    if result["status"] == "error":
        return f"Error fetching webpage: {result['error']}"
    
    # Extract clean text from HTML
    try:
        clean_text = extract_text_from_html(result["content"])
    except Exception as e:
        return f"Error parsing webpage: {str(e)}"
    
    # Limit to 25,000 characters
    if len(clean_text) > 25000:
        clean_text = clean_text[:25000] + "\n\n[Content truncated at 25,000 characters]"
    
    # Add metadata
    output = f"URL: {url}\n"
    output += f"Content length: {len(clean_text)} characters\n"
    output += f"{'-' * 60}\n\n"
    output += clean_text
    
    return output
