"""
Async HTTP client wrapper for ComputeSDK.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

import httpx

from .exceptions import (
    AuthenticationError,
    ComputeSDKError,
    ConnectionError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)

DEFAULT_TIMEOUT = 30.0


class HTTPClient:
    """
    Async HTTP client for making requests to the gateway and sandbox APIs.

    Uses httpx for async HTTP operations with proper error handling
    and automatic response parsing.
    """

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the HTTP client.

        Args:
            base_url: Base URL for all requests
            headers: Default headers to include in all requests
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _handle_error(self, response: httpx.Response) -> None:
        """
        Handle HTTP error responses.

        Args:
            response: The HTTP response to check

        Raises:
            Appropriate exception based on status code
        """
        if response.status_code < 400:
            return

        # Try to extract error message from response
        try:
            data = response.json()
            message = data.get("error", data.get("message", response.text))
        except Exception:
            message = response.text or f"HTTP {response.status_code}"

        if response.status_code == 400:
            raise ValidationError(message)
        elif response.status_code == 401:
            raise AuthenticationError(message)
        elif response.status_code == 403:
            raise ForbiddenError(message)
        elif response.status_code == 404:
            raise NotFoundError(message)
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                message,
                retry_after=int(retry_after) if retry_after else None,
            )
        else:
            raise ComputeSDKError(message, status_code=response.status_code)

    def _parse_response(self, response: httpx.Response) -> Any:
        """
        Parse HTTP response and handle errors.

        Args:
            response: The HTTP response

        Returns:
            Parsed response data (JSON or text)

        Raises:
            Appropriate exception on error
        """
        self._handle_error(response)

        # Handle empty responses
        if response.status_code == 204 or not response.content:
            return None

        # Try JSON parsing
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()

        return response.text

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        Make a GET request.

        Args:
            path: Request path (relative to base URL)
            params: Query parameters
            headers: Additional headers

        Returns:
            Parsed response data
        """
        client = await self._get_client()
        try:
            response = await client.get(path, params=params, headers=headers)
            return self._parse_response(response)
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request to {path} timed out") from e
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}") from e

    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        Make a POST request.

        Args:
            path: Request path (relative to base URL)
            json: JSON body data
            data: Form data
            headers: Additional headers

        Returns:
            Parsed response data
        """
        client = await self._get_client()
        try:
            response = await client.post(path, json=json, data=data, headers=headers)
            return self._parse_response(response)
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request to {path} timed out") from e
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}") from e

    async def put(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        Make a PUT request.

        Args:
            path: Request path (relative to base URL)
            json: JSON body data
            headers: Additional headers

        Returns:
            Parsed response data
        """
        client = await self._get_client()
        try:
            response = await client.put(path, json=json, headers=headers)
            return self._parse_response(response)
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request to {path} timed out") from e
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}") from e

    async def patch(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        Make a PATCH request.

        Args:
            path: Request path (relative to base URL)
            json: JSON body data
            headers: Additional headers

        Returns:
            Parsed response data
        """
        client = await self._get_client()
        try:
            response = await client.patch(path, json=json, headers=headers)
            return self._parse_response(response)
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request to {path} timed out") from e
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}") from e

    async def delete(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        Make a DELETE request.

        Args:
            path: Request path (relative to base URL)
            params: Query parameters
            json: JSON body data (some APIs accept body in DELETE)
            headers: Additional headers

        Returns:
            Parsed response data
        """
        client = await self._get_client()
        try:
            # httpx doesn't support json in delete directly, use request
            response = await client.request(
                "DELETE",
                path,
                params=params,
                json=json,
                headers=headers,
            )
            return self._parse_response(response)
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request to {path} timed out") from e
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}") from e

    async def head(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Make a HEAD request to check resource existence.

        Args:
            path: Request path (relative to base URL)
            params: Query parameters
            headers: Additional headers

        Returns:
            True if resource exists (2xx), False otherwise
        """
        client = await self._get_client()
        try:
            response = await client.head(path, params=params, headers=headers)
            return 200 <= response.status_code < 300
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request to {path} timed out") from e
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}") from e

    async def __aenter__(self) -> "HTTPClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
