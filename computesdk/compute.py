"""
Gateway client for ComputeSDK.

Provides the main `compute` singleton for interacting with sandboxes
through the ComputeSDK gateway.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Optional

from .config import GatewayConfig, auto_config
from .http_client import HTTPClient
from .types import CreateSandboxOptions

if TYPE_CHECKING:
    from .sandbox import Sandbox


class SandboxResource:
    """
    Sandbox CRUD operations via the gateway.

    Provides methods for creating, retrieving, finding, and managing sandboxes.
    """

    def __init__(self, client: HTTPClient, config: GatewayConfig):
        self._client = client
        self._config = config

    async def create(self, options: Optional[CreateSandboxOptions] = None) -> "Sandbox":
        """
        Create a new sandbox.

        Args:
            options: Sandbox creation options (timeout, template, metadata, etc.)

        Returns:
            A Sandbox instance ready for use.

        Example:
            sandbox = await compute.sandbox.create()
            sandbox = await compute.sandbox.create(CreateSandboxOptions(
                timeout=300000,
                template_id="python-dev",
                metadata={"project": "my-app"},
            ))
        """
        from .sandbox import Sandbox

        body = {}
        if options:
            # Convert dataclass to dict, filtering None values
            body = {
                k: v
                for k, v in {
                    "timeout": options.timeout,
                    "templateId": options.template_id,
                    "metadata": options.metadata,
                    "envs": options.envs,
                    "name": options.name,
                    "namespace": options.namespace,
                }.items()
                if v is not None
            }

        response = await self._client.post("/v1/sandboxes", json=body)

        # Extract data from wrapped response
        data = response.get("data", response)

        return Sandbox(
            sandbox_id=data["sandboxId"],
            sandbox_url=data["url"],
            token=data["token"],
            provider=data["provider"],
            metadata=data.get("metadata"),
            name=data.get("name"),
            namespace=data.get("namespace"),
            gateway_client=self._client,
        )

    async def get_by_id(self, sandbox_id: str) -> "Sandbox":
        """
        Get an existing sandbox by its ID.

        Args:
            sandbox_id: The unique sandbox identifier

        Returns:
            A Sandbox instance for the existing sandbox.

        Raises:
            NotFoundError: If the sandbox does not exist.
        """
        from .sandbox import Sandbox

        response = await self._client.get(f"/v1/sandboxes/{sandbox_id}")

        # Extract data from wrapped response
        data = response.get("data", response)

        return Sandbox(
            sandbox_id=sandbox_id,
            sandbox_url=data["url"],
            token=data["token"],
            provider=data["provider"],
            metadata=data.get("metadata"),
            gateway_client=self._client,
        )

    async def find(
        self,
        name: str,
        namespace: str = "default",
    ) -> Optional["Sandbox"]:
        """
        Find a sandbox by name and namespace.

        Args:
            name: Sandbox name
            namespace: Sandbox namespace (default: "default")

        Returns:
            A Sandbox instance if found, None otherwise.
        """
        from .sandbox import Sandbox

        response = await self._client.post(
            "/v1/sandboxes/find",
            json={
                "name": name,
                "namespace": namespace,
            },
        )

        if response is None:
            return None

        # Extract data from wrapped response
        data = response.get("data", response)
        if data is None:
            return None

        return Sandbox(
            sandbox_id=data["sandboxId"],
            sandbox_url=data["url"],
            token=data["token"],
            provider=data["provider"],
            metadata=data.get("metadata"),
            name=data.get("name"),
            namespace=data.get("namespace"),
            gateway_client=self._client,
        )

    async def find_or_create(
        self,
        name: str,
        namespace: str = "default",
        options: Optional[CreateSandboxOptions] = None,
    ) -> "Sandbox":
        """
        Find an existing sandbox or create a new one.

        This is useful for persistent sandboxes that should survive
        across sessions.

        Args:
            name: Sandbox name (must be unique within namespace)
            namespace: Sandbox namespace (default: "default")
            options: Creation options (used only if creating)

        Returns:
            A Sandbox instance (existing or newly created).

        Example:
            # Get or create a development sandbox
            sandbox = await compute.sandbox.find_or_create(
                name="my-dev-sandbox",
                namespace="development",
            )
        """
        from .sandbox import Sandbox

        body: dict = {
            "name": name,
            "namespace": namespace,
        }

        if options:
            if options.timeout is not None:
                body["timeout"] = options.timeout
            if options.template_id is not None:
                body["templateId"] = options.template_id
            if options.metadata is not None:
                body["metadata"] = options.metadata
            if options.envs is not None:
                body["envs"] = options.envs

        response = await self._client.post("/v1/sandboxes/find-or-create", json=body)

        # Extract data from wrapped response
        data = response.get("data", response)

        return Sandbox(
            sandbox_id=data["sandboxId"],
            sandbox_url=data["url"],
            token=data["token"],
            provider=data["provider"],
            metadata=data.get("metadata"),
            name=data.get("name"),
            namespace=data.get("namespace"),
            gateway_client=self._client,
        )


class Compute:
    """
    Main ComputeSDK gateway client.

    Provides access to sandbox operations through the ComputeSDK gateway.
    Can be used with auto-configuration from environment variables or
    explicit configuration.

    Example (auto-config):
        from computesdk import compute

        sandbox = await compute.sandbox.create()
        result = await sandbox.run_code('print("Hello!")', 'python')
        await sandbox.destroy()

    Example (explicit config):
        from computesdk import Compute, GatewayConfig

        config = GatewayConfig(
            api_key="your-api-key",
            provider="e2b",
            provider_headers={"X-E2B-API-Key": "your-e2b-key"},
        )
        compute = Compute(config=config)
        sandbox = await compute.sandbox.create()
    """

    def __init__(self, config: Optional[GatewayConfig] = None):
        """
        Initialize the Compute client.

        Args:
            config: Optional explicit configuration. If not provided,
                   configuration will be auto-detected from environment
                   variables on first use.
        """
        self._config = config
        self._client: Optional[HTTPClient] = None
        self._sandbox: Optional[SandboxResource] = None

    def _ensure_config(self) -> GatewayConfig:
        """Ensure configuration is available, auto-detecting if needed."""
        if self._config is None:
            self._config = auto_config()
        return self._config

    def _ensure_client(self) -> HTTPClient:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            config = self._ensure_config()
            headers = {
                "X-ComputeSDK-API-Key": config.api_key,
                "X-Provider": config.provider,
                "Content-Type": "application/json",
                **config.provider_headers,
            }
            self._client = HTTPClient(
                base_url=config.gateway_url,
                headers=headers,
                timeout=config.timeout,
            )
        return self._client

    @property
    def sandbox(self) -> SandboxResource:
        """
        Access sandbox operations.

        Returns:
            SandboxResource for creating and managing sandboxes.
        """
        if self._sandbox is None:
            self._sandbox = SandboxResource(
                self._ensure_client(),
                self._ensure_config(),
            )
        return self._sandbox

    def set_config(self, config: GatewayConfig) -> None:
        """
        Set explicit configuration.

        This resets any existing client connections.

        Args:
            config: New gateway configuration
        """
        self._config = config
        self._client = None
        self._sandbox = None

    async def close(self) -> None:
        """Close HTTP client connections and release resources."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def __aenter__(self) -> "Compute":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Async context manager exit."""
        await self.close()


# Default singleton instance for convenience
compute = Compute()
