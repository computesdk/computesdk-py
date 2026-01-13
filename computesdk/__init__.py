"""
ComputeSDK - A unified SDK for running code in remote sandboxes.

ComputeSDK provides a consistent interface for executing code in remote
sandbox environments across multiple cloud providers.

Quick Start:
    ```python
    import asyncio
    from computesdk import compute

    async def main():
        # Create a sandbox (auto-config from environment)
        sandbox = await compute.sandbox.create()

        try:
            # Execute Python code
            result = await sandbox.run_code('print("Hello, World!")', 'python')
            print(result.output)

            # Execute shell commands
            cmd = await sandbox.run_command('ls -la')
            print(cmd.stdout)

            # File operations
            await sandbox.filesystem.write_file('/tmp/test.txt', 'Hello!')
            content = await sandbox.filesystem.read_file('/tmp/test.txt')

        finally:
            await sandbox.destroy()

    asyncio.run(main())
    ```

Environment Variables:
    COMPUTESDK_API_KEY: Your ComputeSDK API key (required)
    COMPUTESDK_PROVIDER: Provider to use (optional, auto-detected)
    COMPUTESDK_GATEWAY_URL: Gateway URL (optional)

    Provider-specific variables are also required:
    - E2B: E2B_API_KEY
    - Modal: MODAL_TOKEN_ID, MODAL_TOKEN_SECRET
    - Railway: RAILWAY_API_KEY, RAILWAY_PROJECT_ID, RAILWAY_ENVIRONMENT_ID
    - etc.

For more information, visit: https://docs.computesdk.com
"""

from __future__ import annotations

# Core classes
from .compute import Compute, compute
from .sandbox import FileSystem, Sandbox

# Configuration
from .config import (
    GATEWAY_URL,
    GatewayConfig,
    auto_config,
    create_config,
    detect_provider,
    get_provider_headers,
)

# Types
from .types import (
    # Enums
    CommandStatus,
    FileType,
    Runtime,
    SandboxStatus,
    ServerStatus,
    TerminalStatus,
    WatcherStatus,
    # Result types
    CodeResult,
    CommandResult,
    StreamingCommandResult,
    SandboxInfo,
    # File system types
    FileEntry,
    FileInfo,
    # Terminal types
    TerminalInfo,
    CommandInfo,
    # Server types
    ServerInfo,
    # Watcher types
    WatcherInfo,
    WatcherEvent,
    # Auth types
    SessionToken,
    MagicLink,
    AuthInfo,
    # Signal types
    SignalStatus,
    PortEvent,
    # Options types
    CreateSandboxOptions,
    RunCommandOptions,
    CreateTerminalOptions,
    CreateWatcherOptions,
    StartServerOptions,
    CreateSessionTokenOptions,
    CreateMagicLinkOptions,
    GetUrlOptions,
    # Response types
    SandboxResponse,
    HealthResponse,
    ChildSandboxInfo,
)

# Exceptions
from .exceptions import (
    AuthenticationError,
    ComputeSDKError,
    ConfigurationError,
    ConnectionError,
    ForbiddenError,
    NotFoundError,
    ProviderError,
    RateLimitError,
    SandboxError,
    TimeoutError,
    ValidationError,
    WebSocketError,
)

# WebSocket (optional, may not be available)
try:
    from .websocket_client import TerminalSession, WebSocketClient
except ImportError:
    WebSocketClient = None  # type: ignore
    TerminalSession = None  # type: ignore

# Protocol
from .protocol import BinaryProtocol

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Core
    "compute",
    "Compute",
    "Sandbox",
    "FileSystem",
    # Configuration
    "GatewayConfig",
    "auto_config",
    "create_config",
    "detect_provider",
    "get_provider_headers",
    "GATEWAY_URL",
    # Enums
    "Runtime",
    "SandboxStatus",
    "TerminalStatus",
    "CommandStatus",
    "ServerStatus",
    "WatcherStatus",
    "FileType",
    # Result types
    "CodeResult",
    "CommandResult",
    "StreamingCommandResult",
    "SandboxInfo",
    # File system types
    "FileEntry",
    "FileInfo",
    # Terminal types
    "TerminalInfo",
    "CommandInfo",
    # Server types
    "ServerInfo",
    # Watcher types
    "WatcherInfo",
    "WatcherEvent",
    # Auth types
    "SessionToken",
    "MagicLink",
    "AuthInfo",
    # Signal types
    "SignalStatus",
    "PortEvent",
    # Options types
    "CreateSandboxOptions",
    "RunCommandOptions",
    "CreateTerminalOptions",
    "CreateWatcherOptions",
    "StartServerOptions",
    "CreateSessionTokenOptions",
    "CreateMagicLinkOptions",
    "GetUrlOptions",
    # Response types
    "SandboxResponse",
    "HealthResponse",
    "ChildSandboxInfo",
    # Exceptions
    "ComputeSDKError",
    "AuthenticationError",
    "ForbiddenError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "TimeoutError",
    "WebSocketError",
    "ConnectionError",
    "ConfigurationError",
    "SandboxError",
    "ProviderError",
    # WebSocket
    "WebSocketClient",
    "TerminalSession",
    # Protocol
    "BinaryProtocol",
]
