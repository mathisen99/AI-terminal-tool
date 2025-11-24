"""Web fetch tool definition and implementation."""
import requests
from bs4 import BeautifulSoup
import random
import time
from typing import Dict

# Rotating user agents to avoid bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Tool definition for OpenAI function calling (with strict mode)
# Optimized for token efficiency while maintaining clarity
web_fetch_tool_definition = {
    "type": "function",
    "name": "fetch_webpage",
    "description": "FETCH webpage content immediately when user asks to read/check a webpage. Handles JS-rendered pages, bypasses bot protection. Returns up to 25k chars. Use this to get information from specific URLs.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Full URL (e.g., 'https://example.com')",
            },
        },
        "required": ["url"],
        "additionalProperties": False
    },
    "strict": True
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


def fetch_with_requests(url: str, max_retries: int = 3) -> Dict[str, str]:
    """
    Fetch webpage using requests library with rotating user agents and retry logic.
    
    Args:
        url: URL to fetch
        max_retries: Maximum number of retry attempts
    
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
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            # Check if we got a Cloudflare challenge page
            if "cloudflare" in response.text.lower() and "challenge" in response.text.lower():
                return {"status": "cloudflare", "error": "Cloudflare challenge detected"}
            
            return {"status": "success", "content": response.text}
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff
                time.sleep(wait_time)
                continue
            return {"status": "error", "error": "Request timed out after multiple attempts"}
            
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
                continue
            return {"status": "error", "error": "Connection failed - unable to reach server"}
            
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 403:
                return {"status": "error", "error": "Access forbidden (403) - site may be blocking automated requests"}
            elif status_code == 404:
                return {"status": "error", "error": "Page not found (404)"}
            elif status_code == 429:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 2 + random.uniform(0, 1)  # Longer backoff for rate limits
                    time.sleep(wait_time)
                    continue
                return {"status": "error", "error": "Rate limited (429) - too many requests"}
            elif status_code >= 500:
                return {"status": "error", "error": f"Server error ({status_code}) - site may be down"}
            else:
                return {"status": "error", "error": f"HTTP error {status_code}: {str(e)}"}
                
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
    
    return {"status": "error", "error": "Max retries exceeded"}


def fetch_with_selenium(url: str, use_undetected: bool = True) -> Dict[str, str]:
    """
    Fetch webpage using Selenium with undetected-chromedriver for JavaScript-rendered content.
    Handles Cloudflare challenges and cookie dialogs automatically.
    
    Args:
        url: URL to fetch
        use_undetected: Whether to use undetected-chromedriver (better for bot protection)
    
    Returns:
        Dictionary with status and content or error
    """
    driver = None
    
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException
        
        # Try to use undetected-chromedriver first (better for Cloudflare)
        if use_undetected:
            try:
                import undetected_chromedriver as uc
                
                options = uc.ChromeOptions()
                options.add_argument("--headless=new")  # New headless mode
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
                
                # Create undetected Chrome driver
                driver = uc.Chrome(options=options, version_main=None)
                
            except ImportError:
                # Fall back to regular Selenium if undetected-chromedriver not available
                use_undetected = False
        
        # Fall back to regular Selenium
        if not use_undetected:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            
            driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to URL
        driver.get(url)
        
        # Wait for body to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Wait a bit for JavaScript to execute
        time.sleep(2)
        
        # Try to handle common cookie consent dialogs
        cookie_button_selectors = [
            "button[id*='accept']",
            "button[class*='accept']",
            "button[id*='cookie']",
            "button[class*='cookie']",
            "button[id*='consent']",
            "button[class*='consent']",
            "a[id*='accept']",
            "a[class*='accept']",
            ".cookie-accept",
            "#cookie-accept",
            ".accept-cookies",
            "#accept-cookies",
        ]
        
        for selector in cookie_button_selectors:
            try:
                button = driver.find_element(By.CSS_SELECTOR, selector)
                if button.is_displayed():
                    button.click()
                    time.sleep(1)
                    break
            except (NoSuchElementException, Exception):
                continue
        
        # Check for Cloudflare challenge
        page_text = driver.page_source.lower()
        if "cloudflare" in page_text and "checking your browser" in page_text:
            # Wait longer for Cloudflare to resolve (up to 10 seconds)
            time.sleep(10)
            page_text = driver.page_source.lower()
            
            # If still showing challenge, return error
            if "checking your browser" in page_text:
                return {"status": "error", "error": "Cloudflare challenge could not be bypassed"}
        
        # Get final page content
        content = driver.page_source
        return {"status": "success", "content": content}
        
    except ImportError as e:
        missing_lib = "undetected-chromedriver" if "undetected" in str(e) else "selenium"
        return {"status": "error", "error": f"{missing_lib} not installed. Install with: uv pip install {missing_lib}"}
        
    except TimeoutException:
        return {"status": "error", "error": "Page load timeout - site took too long to respond"}
        
    except Exception as e:
        error_msg = str(e)
        if "chrome" in error_msg.lower() or "chromedriver" in error_msg.lower():
            return {"status": "error", "error": "ChromeDriver error - ensure Chrome/Chromium is installed"}
        return {"status": "error", "error": f"Browser automation error: {error_msg}"}
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def fetch_webpage(url: str) -> str:
    """
    Fetch and extract clean text content from a webpage.
    Automatically handles bot protection, Cloudflare challenges, and cookie dialogs.
    Uses caching to avoid repeated fetches (1 hour TTL).
    
    Args:
        url: The URL of the webpage to fetch
    
    Returns:
        Clean text content from the webpage (max 25,000 characters)
    """
    # Validate URL
    if not url.startswith(("http://", "https://")):
        return "❌ Error: Invalid URL format\n\nURL must start with http:// or https://\nExample: https://example.com"
    
    # Check cache first
    try:
        from services.cache_manager import web_cache
        cached_content = web_cache.get(url)
        if cached_content:
            return f"✓ Successfully fetched (cached): {url}\n{cached_content}"
    except ImportError:
        # If cache not available, continue without caching
        pass
    
    # Try fetching with requests first (faster, with retry logic)
    result = fetch_with_requests(url, max_retries=3)
    
    # If requests fails or hits Cloudflare, try Selenium with undetected-chromedriver
    if result["status"] in ["error", "cloudflare"]:
        # Store the requests error for fallback message
        requests_error = result.get("error", "Unknown error")
        
        # Try Selenium as fallback
        result = fetch_with_selenium(url, use_undetected=True)
        
        # If Selenium also fails, provide detailed error
        if result["status"] == "error":
            selenium_error = result.get("error", "Unknown error")
            
            # Provide helpful error message based on failure type
            error_output = "❌ Error: Unable to fetch webpage\n\n"
            error_output += f"URL: {url}\n\n"
            error_output += "Attempted methods:\n"
            error_output += f"1. HTTP Request: {requests_error}\n"
            error_output += f"2. Browser Automation: {selenium_error}\n\n"
            
            # Add suggestions based on error type
            if "403" in requests_error or "forbidden" in requests_error.lower():
                error_output += "💡 Suggestion: This site blocks automated access. Try accessing it manually."
            elif "404" in requests_error:
                error_output += "💡 Suggestion: Check if the URL is correct and the page exists."
            elif "timeout" in requests_error.lower() or "timeout" in selenium_error.lower():
                error_output += "💡 Suggestion: The site is slow or unresponsive. Try again later."
            elif "cloudflare" in requests_error.lower() or "cloudflare" in selenium_error.lower():
                error_output += "💡 Suggestion: Cloudflare protection is too strong. Manual access may be required."
            elif "chromedriver" in selenium_error.lower():
                error_output += "💡 Suggestion: Install Chrome/Chromium browser for JavaScript-rendered pages."
            
            return error_output
    
    # Extract clean text from HTML
    try:
        clean_text = extract_text_from_html(result["content"])
    except Exception as e:
        return f"❌ Error: Failed to parse webpage content\n\nDetails: {str(e)}\n\n💡 The page may have an unusual structure or encoding."
    
    # Check if we got meaningful content
    if len(clean_text.strip()) < 50:
        return f"⚠️  Warning: Very little content extracted\n\nURL: {url}\n\nThe page may be empty, require authentication, or use complex JavaScript rendering."
    
    # Limit to 25,000 characters
    truncated = False
    if len(clean_text) > 25000:
        clean_text = clean_text[:25000]
        truncated = True
    
    # Add metadata header
    output = f"Content length: {len(clean_text):,} characters"
    if truncated:
        output += " (truncated)"
    output += f"\n{'-' * 80}\n\n"
    output += clean_text
    
    if truncated:
        output += "\n\n[Content truncated at 25,000 characters]"
    
    # Cache the result for future requests
    try:
        from services.cache_manager import web_cache
        web_cache.set(url, output)
    except ImportError:
        pass
    
    return f"✓ Successfully fetched: {url}\n{output}"
