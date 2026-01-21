"""
Configuration and auto-detection for ComputeSDK.

Supports zero-config mode via environment variables and explicit configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

GATEWAY_URL = "https://gateway.computesdk.com"

PROVIDER_DETECTION_ORDER: List[str] = [
    "e2b",
    "railway",
    "daytona",
    "modal",
    "runloop",
    "vercel",
    "cloudflare",
    "codesandbox",
    "blaxel",
    "fly",
    "render",
    "namespace",
    "lambda",
    "docker",
    "aws-ecs",
    "aws-lambda",
]

# Maps provider name to required environment variables
PROVIDER_ENV_REQUIREMENTS: Dict[str, List[str]] = {
    "e2b": ["E2B_API_KEY"],
    "railway": ["RAILWAY_API_KEY", "RAILWAY_PROJECT_ID", "RAILWAY_ENVIRONMENT_ID"],
    "daytona": ["DAYTONA_API_KEY"],
    "modal": ["MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET"],
    "runloop": ["RUNLOOP_API_KEY"],
    "vercel": ["VERCEL_TOKEN", "VERCEL_TEAM_ID", "VERCEL_PROJECT_ID"],
    "cloudflare": ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"],
    "codesandbox": ["CSB_API_KEY"],
    "blaxel": ["BL_API_KEY", "BL_WORKSPACE"],
    "fly": ["FLY_API_TOKEN"],
    "render": ["RENDER_API_KEY"],
    "namespace": ["NAMESPACE_API_KEY"],
    "lambda": ["LAMBDA_API_KEY"],
    "docker": [],  # No API key needed for local Docker
    "aws-ecs": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
    "aws-lambda": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
}


@dataclass
class GatewayConfig:
    """Configuration for the ComputeSDK gateway."""

    api_key: str
    provider: str
    gateway_url: str = GATEWAY_URL
    provider_headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
    debug: bool = False


def detect_provider() -> Optional[str]:
    """
    Auto-detect provider from environment variables.

    Checks providers in priority order and returns the first one
    that has all required environment variables set.

    Returns:
        Provider name if detected, None otherwise.
    """
    for provider in PROVIDER_DETECTION_ORDER:
        required_vars = PROVIDER_ENV_REQUIREMENTS.get(provider, [])
        # Skip providers with no requirements (like docker) unless explicitly set
        if not required_vars:
            continue
        if all(os.environ.get(var) for var in required_vars):
            return provider
    return None


def get_provider_headers(provider: str) -> Dict[str, str]:
    """
    Build provider-specific headers from environment variables.

    Args:
        provider: Provider name (e.g., 'e2b', 'modal')

    Returns:
        Dictionary of header name to value.
    """
    header_builders: Dict[str, Dict[str, str]] = {
        "e2b": {
            "X-E2B-API-Key": os.environ.get("E2B_API_KEY", ""),
            "X-E2B-Project-ID": os.environ.get("E2B_PROJECT_ID", ""),
            "X-E2B-Template-ID": os.environ.get("E2B_TEMPLATE_ID", ""),
        },
        "railway": {
            "X-Railway-API-Key": os.environ.get("RAILWAY_API_KEY", ""),
            "X-Railway-Project-ID": os.environ.get("RAILWAY_PROJECT_ID", ""),
            "X-Railway-Environment-ID": os.environ.get("RAILWAY_ENVIRONMENT_ID", ""),
        },
        "modal": {
            "X-Modal-Token-ID": os.environ.get("MODAL_TOKEN_ID", ""),
            "X-Modal-Token-Secret": os.environ.get("MODAL_TOKEN_SECRET", ""),
        },
        "daytona": {
            "X-Daytona-API-Key": os.environ.get("DAYTONA_API_KEY", ""),
        },
        "runloop": {
            "X-Runloop-API-Key": os.environ.get("RUNLOOP_API_KEY", ""),
        },
        "vercel": {
            "X-Vercel-Token": os.environ.get("VERCEL_TOKEN", ""),
            "X-Vercel-OIDC-Token": os.environ.get("VERCEL_OIDC_TOKEN", ""),
            "X-Vercel-Team-ID": os.environ.get("VERCEL_TEAM_ID", ""),
            "X-Vercel-Project-ID": os.environ.get("VERCEL_PROJECT_ID", ""),
        },
        "cloudflare": {
            "X-Cloudflare-API-Token": os.environ.get("CLOUDFLARE_API_TOKEN", ""),
            "X-Cloudflare-Account-ID": os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
        },
        "codesandbox": {
            "X-CodeSandbox-API-Key": os.environ.get("CSB_API_KEY", ""),
        },
        "blaxel": {
            "X-Blaxel-API-Key": os.environ.get("BL_API_KEY", ""),
            "X-Blaxel-Workspace": os.environ.get("BL_WORKSPACE", ""),
        },
        "fly": {
            "X-Fly-API-Token": os.environ.get("FLY_API_TOKEN", ""),
        },
        "render": {
            "X-Render-API-Key": os.environ.get("RENDER_API_KEY", ""),
            "X-Render-Owner-ID": os.environ.get("RENDER_OWNER_ID", ""),
        },
        "namespace": {
            "X-Namespace-API-Key": os.environ.get("NAMESPACE_API_KEY", ""),
        },
        "lambda": {
            "X-Lambda-API-Key": os.environ.get("LAMBDA_API_KEY", ""),
        },
        "docker": {},
        "aws-ecs": {
            "X-AWS-Access-Key-ID": os.environ.get("AWS_ACCESS_KEY_ID", ""),
            "X-AWS-Secret-Access-Key": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
            "X-AWS-Region": os.environ.get("AWS_REGION", ""),
        },
        "aws-lambda": {
            "X-AWS-Access-Key-ID": os.environ.get("AWS_ACCESS_KEY_ID", ""),
            "X-AWS-Secret-Access-Key": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
            "X-AWS-Region": os.environ.get("AWS_REGION", ""),
        },
    }

    headers = header_builders.get(provider, {})
    # Filter out empty values
    return {k: v for k, v in headers.items() if v}


def auto_config() -> GatewayConfig:
    """
    Auto-configure from environment variables.

    Reads COMPUTESDK_API_KEY and auto-detects provider from
    provider-specific environment variables.

    Returns:
        GatewayConfig instance.

    Raises:
        ValueError: If COMPUTESDK_API_KEY is not set or provider cannot be detected.
    """
    api_key = os.environ.get("COMPUTESDK_API_KEY")
    if not api_key:
        raise ValueError(
            "COMPUTESDK_API_KEY environment variable is required. "
            "Get your API key at https://computesdk.com"
        )

    # Allow explicit provider override
    provider = os.environ.get("COMPUTESDK_PROVIDER") or detect_provider()
    if not provider:
        raise ValueError(
            "Could not auto-detect provider. Set COMPUTESDK_PROVIDER environment variable "
            "or configure provider credentials (e.g., E2B_API_KEY for E2B)."
        )

    gateway_url = os.environ.get("COMPUTESDK_GATEWAY_URL", GATEWAY_URL)
    debug = os.environ.get("COMPUTESDK_DEBUG", "").lower() in ("true", "1", "yes")

    return GatewayConfig(
        api_key=api_key,
        provider=provider,
        gateway_url=gateway_url,
        provider_headers=get_provider_headers(provider),
        debug=debug,
    )


def create_config(
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
    gateway_url: Optional[str] = None,
    provider_headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
    debug: bool = False,
) -> GatewayConfig:
    """
    Create a configuration with explicit values, falling back to environment variables.

    Args:
        api_key: ComputeSDK API key (falls back to COMPUTESDK_API_KEY)
        provider: Provider name (falls back to auto-detection)
        gateway_url: Gateway URL (falls back to COMPUTESDK_GATEWAY_URL or default)
        provider_headers: Provider-specific headers (falls back to auto-detection)
        timeout: Request timeout in seconds
        debug: Enable debug logging

    Returns:
        GatewayConfig instance.
    """
    resolved_api_key = api_key or os.environ.get("COMPUTESDK_API_KEY")
    if not resolved_api_key:
        raise ValueError("api_key is required")

    resolved_provider = provider or os.environ.get("COMPUTESDK_PROVIDER") or detect_provider()
    if not resolved_provider:
        raise ValueError("provider is required")

    resolved_gateway_url = gateway_url or os.environ.get("COMPUTESDK_GATEWAY_URL", GATEWAY_URL)
    resolved_headers = provider_headers or get_provider_headers(resolved_provider)

    return GatewayConfig(
        api_key=resolved_api_key,
        provider=resolved_provider,
        gateway_url=resolved_gateway_url,
        provider_headers=resolved_headers,
        timeout=timeout,
        debug=debug,
    )
