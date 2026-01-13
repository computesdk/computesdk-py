"""
Custom exceptions for ComputeSDK.
"""

from __future__ import annotations

from typing import Optional


class ComputeSDKError(Exception):
    """Base exception for all ComputeSDK errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthenticationError(ComputeSDKError):
    """
    Authentication failed.

    Raised when the ComputeSDK API key or provider credentials are invalid.
    HTTP status code: 401
    """

    def __init__(self, message: str = "Invalid API key"):
        super().__init__(message, status_code=401)


class ForbiddenError(ComputeSDKError):
    """
    Access forbidden.

    Raised when the request is authenticated but not authorized
    for the requested resource or action.
    HTTP status code: 403
    """

    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message, status_code=403)


class NotFoundError(ComputeSDKError):
    """
    Resource not found.

    Raised when the requested sandbox, file, or other resource
    does not exist.
    HTTP status code: 404
    """

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationError(ComputeSDKError):
    """
    Validation error.

    Raised when request parameters fail validation.
    HTTP status code: 400
    """

    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=400)


class RateLimitError(ComputeSDKError):
    """
    Rate limit exceeded.

    Raised when too many requests have been made in a short period.
    HTTP status code: 429
    """

    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class TimeoutError(ComputeSDKError):
    """
    Request timed out.

    Raised when a request exceeds the configured timeout.
    """

    def __init__(self, message: str = "Request timed out"):
        super().__init__(message)


class WebSocketError(ComputeSDKError):
    """
    WebSocket connection or protocol error.

    Raised when there's an issue with the WebSocket connection
    used for real-time features.
    """

    def __init__(self, message: str = "WebSocket error"):
        super().__init__(message)


class ConnectionError(ComputeSDKError):
    """
    Connection error.

    Raised when unable to connect to the gateway or sandbox.
    """

    def __init__(self, message: str = "Connection error"):
        super().__init__(message)


class ConfigurationError(ComputeSDKError):
    """
    Configuration error.

    Raised when there's an issue with the SDK configuration,
    such as missing environment variables or invalid settings.
    """

    def __init__(self, message: str = "Configuration error"):
        super().__init__(message)


class SandboxError(ComputeSDKError):
    """
    Sandbox execution error.

    Raised when there's an error during code or command execution
    in the sandbox.
    """

    def __init__(self, message: str, exit_code: Optional[int] = None):
        super().__init__(message)
        self.exit_code = exit_code


class ProviderError(ComputeSDKError):
    """
    Provider-specific error.

    Raised when the underlying provider returns an error.
    """

    def __init__(self, message: str, provider: Optional[str] = None):
        super().__init__(message)
        self.provider = provider
