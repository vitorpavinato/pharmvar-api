"""
Base API client with shared functionality for rate limiting, 
error handling, and retry logic.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientError, ClientTimeout


class APIError(Exception):
    """Custom API error exception."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_second: float = 10.0):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_called = 0.0
    
    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        now = asyncio.get_event_loop().time()
        time_passed = now - self.last_called
        if time_passed < self.min_interval:
            sleep_time = self.min_interval - time_passed
            await asyncio.sleep(sleep_time)
        self.last_called = asyncio.get_event_loop().time()


class BaseAPIClient(ABC):
    """Base class for all API clients with common functionality."""
    
    def __init__(
        self,
        base_url: str,
        rate_limit: float = 10.0,  # calls per second
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.base_url = base_url.rstrip('/')
        self.rate_limiter = RateLimiter(rate_limit)
        self.timeout = ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        return urljoin(self.base_url + '/', endpoint.lstrip('/'))
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with rate limiting and retry logic."""
        
        url = self._build_url(endpoint)
        
        # Default headers
        default_headers = {
            'User-Agent': 'PharmVar-API-Explorer/1.0',
            'Accept': 'application/json'
        }
        if headers:
            default_headers.update(headers)
        
        for attempt in range(self.max_retries + 1):
            try:
                # Respect rate limiting
                await self.rate_limiter.acquire()
                
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    self.logger.debug(f"Making {method} request to {url}")
                    
                    async with session.request(
                        method=method,
                        url=url,
                        params=params,
                        headers=default_headers,
                        json=json_data
                    ) as response:
                        
                        # Log response
                        self.logger.debug(f"Response status: {response.status}")
                        
                        # Handle different status codes
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 404:
                            raise APIError(f"Resource not found: {url}", status_code=404)
                        elif response.status == 429:  # Rate limited
                            if attempt < self.max_retries:
                                wait_time = self.retry_delay * (2 ** attempt)
                                self.logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise APIError("Rate limit exceeded", status_code=429)
                        elif response.status >= 500:  # Server error
                            if attempt < self.max_retries:
                                wait_time = self.retry_delay * (2 ** attempt)
                                self.logger.warning(f"Server error {response.status}. Retrying in {wait_time}s...")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                raise APIError(f"Server error: {response.status}", status_code=response.status)
                        else:
                            # Other client errors
                            error_text = await response.text()
                            raise APIError(
                                f"API error: {response.status} - {error_text}",
                                status_code=response.status
                            )
                            
            except ClientError as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"Network error: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise APIError(f"Network error after {self.max_retries} retries: {e}")
            
            except asyncio.TimeoutError:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(f"Request timeout. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise APIError(f"Request timeout after {self.max_retries} retries")
        
        # This should never be reached, but just in case
        raise APIError("Unexpected error in request handling")
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make GET request."""
        return await self._make_request("GET", endpoint, params=params, **kwargs)
    
    async def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Make POST request."""
        return await self._make_request("POST", endpoint, json_data=json_data, **kwargs)
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the API is accessible and healthy."""
        pass
    
    @abstractmethod
    def get_api_info(self) -> Dict[str, str]:
        """Return basic information about this API client."""
        pass