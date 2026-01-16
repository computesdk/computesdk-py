"""
Sandbox class for ComputeSDK.

Provides the main interface for interacting with remote sandbox environments.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlparse

from .http_client import HTTPClient
from .types import (
    CodeResult,
    CommandResult,
    CreateSessionTokenOptions,
    CreateTerminalOptions,
    CreateWatcherOptions,
    FileEntry,
    MagicLink,
    RunCommandOptions,
    SandboxInfo,
    SandboxStatus,
    ServerInfo,
    SessionToken,
    SignalStatus,
    StartServerOptions,
    TerminalInfo,
    WatcherInfo,
)


class FileSystem:
    """
    File system operations for a sandbox.

    Provides methods for reading, writing, and managing files
    within the sandbox environment.
    """

    def __init__(self, client: HTTPClient):
        self._client = client

    def _encode_path(self, path: str) -> str:
        """URL-encode path segments while preserving structure."""
        # Split path, encode each segment, rejoin
        segments = path.split("/")
        encoded = [quote(segment, safe="") for segment in segments]
        return "/".join(encoded)

    async def read_file(self, path: str) -> str:
        """
        Read the contents of a file.

        Args:
            path: Absolute path to the file

        Returns:
            File contents as a string.

        Raises:
            NotFoundError: If the file does not exist.
        """
        encoded = self._encode_path(path)
        response = await self._client.get(f"/files/{encoded}", params={"content": "true"})

        if isinstance(response, dict):
            return response.get("content", response.get("data", ""))
        return str(response)

    async def write_file(self, path: str, content: str) -> None:
        """
        Write content to a file.

        Creates the file if it doesn't exist, overwrites if it does.

        Args:
            path: Absolute path to the file
            content: Content to write
        """
        await self._client.post("/files", json={"path": path, "content": content})

    async def readdir(self, path: str) -> List[FileEntry]:
        """
        List contents of a directory.

        Args:
            path: Absolute path to the directory

        Returns:
            List of FileEntry objects.
        """
        response = await self._client.get("/files", params={"path": path})

        # Handle wrapped response: {data: {files: [...]}}
        if isinstance(response, dict):
            data = response.get("data", response)
            if isinstance(data, dict):
                entries = data.get("files", [])
            elif isinstance(data, list):
                entries = data
            else:
                entries = []
        else:
            entries = []

        return [
            FileEntry(
                name=e.get("name", ""),
                type="directory" if e.get("is_dir") else "file",
                size=e.get("size"),
                modified=e.get("modified_at"),
            )
            for e in entries
        ]

    async def mkdir(self, path: str) -> None:
        """
        Create a directory.

        Note: This uses run_command internally as the /files API
        does not currently support directory creation.

        Args:
            path: Absolute path to the directory
        """
        # The /files API doesn't support creating directories,
        # so we use run_command as a workaround
        from .sandbox import Sandbox

        # Get parent sandbox instance to call run_command
        # This is a bit of a hack - mkdir needs access to run_command
        await self._client.post("/run/command", json={"command": f"mkdir -p {path}"})

    async def exists(self, path: str) -> bool:
        """
        Check if a file or directory exists.

        Args:
            path: Absolute path to check

        Returns:
            True if the path exists, False otherwise.
        """
        encoded = self._encode_path(path)
        return await self._client.head(f"/files/{encoded}")

    async def remove(self, path: str) -> None:
        """
        Delete a file or directory.

        Args:
            path: Absolute path to delete
        """
        encoded = self._encode_path(path)
        await self._client.delete(f"/files/{encoded}")

    async def batch_write(self, files: List[Dict[str, str]]) -> None:
        """
        Write multiple files in a single operation.

        Args:
            files: List of dicts with 'path' and 'content' keys

        Example:
            await sandbox.filesystem.batch_write([
                {"path": "/app/main.py", "content": "print('hello')"},
                {"path": "/app/utils.py", "content": "def helper(): pass"},
            ])
        """
        operations = [
            {"path": f["path"], "operation": "write", "content": f["content"]}
            for f in files
        ]
        await self._client.post("/files/batch", json={"files": operations})


class Sandbox:
    """
    Sandbox instance for executing code and commands.

    This class provides the main interface for interacting with a remote
    sandbox environment through the ComputeSDK gateway.

    Use `compute.sandbox.create()` to obtain a Sandbox instance.

    Example:
        from computesdk import compute

        sandbox = await compute.sandbox.create()
        try:
            result = await sandbox.run_code('print("Hello!")', 'python')
            print(result.output)
        finally:
            await sandbox.destroy()
    """

    def __init__(
        self,
        sandbox_id: str,
        sandbox_url: str,
        token: str,
        provider: str,
        metadata: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        namespace: Optional[str] = None,
        gateway_client: Optional[HTTPClient] = None,
    ):
        """
        Initialize a Sandbox instance.

        Note: Use compute.sandbox.create() instead of instantiating directly.
        """
        self._sandbox_id = sandbox_id
        self._sandbox_url = sandbox_url.rstrip("/")
        self._token = token
        self._provider = provider
        self._metadata = metadata
        self._name = name
        self._namespace = namespace
        self._gateway_client = gateway_client

        # Create sandbox-specific HTTP client
        self._client = HTTPClient(
            base_url=self._sandbox_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

        # Initialize filesystem
        self._filesystem = FileSystem(self._client)

    # ==================== Properties ====================

    @property
    def sandbox_id(self) -> str:
        """Unique identifier for this sandbox."""
        return self._sandbox_id

    @property
    def provider(self) -> str:
        """Provider name (e.g., 'e2b', 'modal', 'railway')."""
        return self._provider

    @property
    def filesystem(self) -> FileSystem:
        """File system operations."""
        return self._filesystem

    @property
    def name(self) -> Optional[str]:
        """Sandbox name (for named sandboxes)."""
        return self._name

    @property
    def namespace(self) -> Optional[str]:
        """Sandbox namespace (for named sandboxes)."""
        return self._namespace

    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        """Custom metadata associated with the sandbox."""
        return self._metadata

    # ==================== Core Methods ====================

    async def run_code(self, code: str, language: str = "python") -> CodeResult:
        """
        Execute code in the sandbox.

        Args:
            code: Source code to execute
            language: Runtime to use ('python', 'node', 'deno', 'bun')

        Returns:
            CodeResult with output, exit_code, and language.

        Example:
            result = await sandbox.run_code('''
            import sys
            print(f"Python {sys.version}")
            ''', 'python')
            print(result.output)
        """
        response = await self._client.post(
            "/run/code",
            json={
                "code": code,
                "language": language,
            },
        )

        data = response.get("data", response) if isinstance(response, dict) else {}

        return CodeResult(
            output=data.get("output", ""),
            exit_code=data.get("exit_code", 0),
            language=data.get("language", language),
        )

    async def run_command(
        self,
        command: str,
        options: Optional[RunCommandOptions] = None,
    ) -> CommandResult:
        """
        Execute a shell command in the sandbox.

        Args:
            command: Shell command to execute
            options: Command options (cwd, env, shell, background, etc.)

        Returns:
            CommandResult with stdout, stderr, exit_code, and duration_ms.

        Example:
            result = await sandbox.run_command('ls -la /app')
            print(result.stdout)

            result = await sandbox.run_command(
                'npm install',
                RunCommandOptions(cwd='/app', timeout=60000)
            )
        """
        body: Dict[str, Any] = {"command": command}

        if options:
            if options.shell is not None:
                body["shell"] = options.shell
            if options.cwd is not None:
                body["cwd"] = options.cwd
            if options.env is not None:
                body["env"] = options.env
            if options.background:
                body["background"] = options.background
            if options.stream:
                body["stream"] = options.stream

        response = await self._client.post("/run/command", json=body)

        data = response.get("data", response) if isinstance(response, dict) else {}

        return CommandResult(
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            exit_code=data.get("exit_code", 0),
            duration_ms=data.get("duration_ms", 0),
        )

    async def get_info(self) -> SandboxInfo:
        """
        Get information about the sandbox.

        Returns:
            SandboxInfo with id, provider, status, and other details.
        """
        response = await self._client.get("/info")

        data = response.get("data", response) if isinstance(response, dict) else {}

        return SandboxInfo(
            id=self._sandbox_id,
            provider=self._provider,
            status=SandboxStatus(data.get("status", "running")),
            timeout=data.get("timeout"),
            metadata=self._metadata,
            name=self._name,
            namespace=self._namespace,
        )

    async def get_url(self, port: int, protocol: str = "https") -> str:
        """
        Get the public URL for a service running on a port.

        Args:
            port: Port number the service is running on
            protocol: URL protocol ('http' or 'https')

        Returns:
            Public URL for accessing the service.

        Example:
            # Start a server on port 3000
            await sandbox.run_command('node server.js &')

            # Get the public URL
            url = await sandbox.get_url(3000)
            print(f"Server available at: {url}")
        """
        # Extract subdomain from sandbox URL
        # e.g., https://sandbox-123.sandbox.computesdk.com -> sandbox-123
        parsed = urlparse(self._sandbox_url)
        subdomain = parsed.netloc.split(".")[0]
        return f"{protocol}://{subdomain}-{port}.preview.computesdk.com"

    async def destroy(self) -> None:
        """
        Destroy this sandbox and release all resources.

        After calling destroy(), the sandbox instance should not be used.
        """
        if self._gateway_client:
            await self._gateway_client.delete(f"/v1/sandboxes/{self._sandbox_id}")
        await self._client.close()

    async def extend(self, duration: int = 900000) -> None:
        """
        Extend the sandbox timeout.

        Args:
            duration: Extension duration in milliseconds (default: 15 minutes)
        """
        if self._gateway_client:
            await self._gateway_client.post(
                f"/v1/sandboxes/{self._sandbox_id}/extend",
                json={"duration": duration},
            )

    async def health(self) -> bool:
        """
        Check if the sandbox is healthy and responding.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            await self._client.get("/health")
            return True
        except Exception:
            return False

    # ==================== Terminal Operations ====================

    async def create_terminal(
        self,
        options: Optional[CreateTerminalOptions] = None,
    ) -> TerminalInfo:
        """
        Create a new terminal session.

        Args:
            options: Terminal options (shell, encoding, pty mode)

        Returns:
            TerminalInfo with id, status, and connection details.
        """
        body: Dict[str, Any] = {}

        if options:
            if options.shell is not None:
                body["shell"] = options.shell
            if options.encoding is not None:
                body["encoding"] = options.encoding
            if options.pty:
                body["pty"] = options.pty

        response = await self._client.post("/terminals", json=body or None)

        data = response.get("data", response) if isinstance(response, dict) else {}

        return TerminalInfo(
            id=data["id"],
            pty=data.get("pty", False),
            status=data.get("status", "running"),
            channel=data.get("channel"),
            ws_url=data.get("ws_url"),
            encoding=data.get("encoding"),
        )

    async def list_terminals(self) -> List[TerminalInfo]:
        """
        List all terminal sessions.

        Returns:
            List of TerminalInfo objects.
        """
        response = await self._client.get("/terminals")

        data = response.get("data", response) if isinstance(response, dict) else response

        if not isinstance(data, list):
            data = []

        return [
            TerminalInfo(
                id=t["id"],
                pty=t.get("pty", False),
                status=t.get("status", "running"),
                channel=t.get("channel"),
                ws_url=t.get("ws_url"),
            )
            for t in data
        ]

    async def get_terminal(self, terminal_id: str) -> TerminalInfo:
        """
        Get a terminal session by ID.

        Args:
            terminal_id: Terminal identifier

        Returns:
            TerminalInfo for the terminal.
        """
        response = await self._client.get(f"/terminals/{terminal_id}")

        data = response.get("data", response) if isinstance(response, dict) else {}

        return TerminalInfo(
            id=data["id"],
            pty=data.get("pty", False),
            status=data.get("status", "running"),
            channel=data.get("channel"),
            ws_url=data.get("ws_url"),
        )

    async def destroy_terminal(self, terminal_id: str) -> None:
        """
        Destroy a terminal session.

        Args:
            terminal_id: Terminal identifier
        """
        await self._client.delete(f"/terminals/{terminal_id}")

    async def execute_in_terminal(
        self,
        terminal_id: str,
        command: str,
        background: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a command in an existing terminal.

        Args:
            terminal_id: Terminal identifier
            command: Command to execute
            background: Run in background

        Returns:
            Execution result with cmd_id and channel.
        """
        response = await self._client.post(
            f"/terminals/{terminal_id}/execute",
            json={"command": command, "background": background},
        )

        return response.get("data", response) if isinstance(response, dict) else {}

    async def wait_for_command(
        self,
        terminal_id: str,
        cmd_id: str,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Wait for a command to complete.

        Args:
            terminal_id: Terminal identifier
            cmd_id: Command identifier
            timeout: Timeout in seconds

        Returns:
            Command result.
        """
        params: Dict[str, Any] = {}
        if timeout is not None:
            params["timeout"] = timeout

        response = await self._client.get(
            f"/terminals/{terminal_id}/commands/{cmd_id}/wait",
            params=params or None,
        )

        return response.get("data", response) if isinstance(response, dict) else {}

    # ==================== File Watcher Operations ====================

    async def create_watcher(
        self,
        path: str,
        options: Optional[CreateWatcherOptions] = None,
    ) -> WatcherInfo:
        """
        Create a file watcher.

        Args:
            path: Directory path to watch
            options: Watcher options (include_content, ignored patterns)

        Returns:
            WatcherInfo with id, channel, and ws_url for events.
        """
        body: Dict[str, Any] = {"path": path}

        if options:
            if options.include_content:
                body["includeContent"] = options.include_content
            if options.ignored:
                body["ignored"] = options.ignored
            if options.encoding:
                body["encoding"] = options.encoding

        response = await self._client.post("/watchers", json=body)

        data = response.get("data", response) if isinstance(response, dict) else {}

        return WatcherInfo(
            id=data["id"],
            path=data["path"],
            status=data.get("status", "active"),
            channel=data["channel"],
            ws_url=data["ws_url"],
            include_content=data.get("includeContent", False),
            ignored=data.get("ignored", []),
            encoding=data.get("encoding"),
        )

    async def list_watchers(self) -> List[WatcherInfo]:
        """
        List all file watchers.

        Returns:
            List of WatcherInfo objects.
        """
        response = await self._client.get("/watchers")

        data = response.get("data", response) if isinstance(response, dict) else response

        if not isinstance(data, list):
            data = []

        return [
            WatcherInfo(
                id=w["id"],
                path=w["path"],
                status=w.get("status", "active"),
                channel=w["channel"],
                ws_url=w["ws_url"],
                include_content=w.get("includeContent", False),
                ignored=w.get("ignored", []),
            )
            for w in data
        ]

    async def get_watcher(self, watcher_id: str) -> WatcherInfo:
        """
        Get a file watcher by ID.

        Args:
            watcher_id: Watcher identifier

        Returns:
            WatcherInfo for the watcher.
        """
        response = await self._client.get(f"/watchers/{watcher_id}")

        data = response.get("data", response) if isinstance(response, dict) else {}

        return WatcherInfo(
            id=data["id"],
            path=data["path"],
            status=data.get("status", "active"),
            channel=data["channel"],
            ws_url=data["ws_url"],
            include_content=data.get("includeContent", False),
            ignored=data.get("ignored", []),
        )

    async def destroy_watcher(self, watcher_id: str) -> None:
        """
        Destroy a file watcher.

        Args:
            watcher_id: Watcher identifier
        """
        await self._client.delete(f"/watchers/{watcher_id}")

    # ==================== Server Operations ====================

    async def start_server(self, options: StartServerOptions) -> ServerInfo:
        """
        Start a server process.

        Args:
            options: Server options (slug, command, path, env_file)

        Returns:
            ServerInfo with slug, status, and url.

        Example:
            server = await sandbox.start_server(StartServerOptions(
                slug="api",
                command="node server.js",
                path="/app",
            ))
            print(f"Server running at: {server.url}")
        """
        body: Dict[str, Any] = {
            "slug": options.slug,
            "start": options.command,
        }

        if options.path is not None:
            body["path"] = options.path
        if options.env_file is not None:
            body["env_file"] = options.env_file

        response = await self._client.post("/servers", json=body)

        data = response.get("data", response) if isinstance(response, dict) else {}
        if "server" in data:
            data = data["server"]

        return ServerInfo(
            slug=data.get("slug", options.slug),
            command=data.get("command", options.command),
            status=data.get("status", "running"),
            path=data.get("path"),
            port=data.get("port"),
            url=data.get("url"),
        )

    async def list_servers(self) -> List[ServerInfo]:
        """
        List all running servers.

        Returns:
            List of ServerInfo objects.
        """
        response = await self._client.get("/servers")

        data = response.get("data", response) if isinstance(response, dict) else response

        if not isinstance(data, list):
            data = []

        return [
            ServerInfo(
                slug=s["slug"],
                command=s["command"],
                status=s.get("status", "running"),
                path=s.get("path"),
                port=s.get("port"),
                url=s.get("url"),
            )
            for s in data
        ]

    async def get_server(self, slug: str) -> ServerInfo:
        """
        Get a server by slug.

        Args:
            slug: Server identifier

        Returns:
            ServerInfo for the server.
        """
        response = await self._client.get(f"/servers/{slug}")

        data = response.get("data", response) if isinstance(response, dict) else {}

        return ServerInfo(
            slug=data["slug"],
            command=data["command"],
            status=data.get("status", "running"),
            path=data.get("path"),
            port=data.get("port"),
            url=data.get("url"),
        )

    async def stop_server(self, slug: str) -> None:
        """
        Stop a server.

        Args:
            slug: Server identifier
        """
        await self._client.delete(f"/servers/{slug}")

    async def restart_server(self, slug: str) -> None:
        """
        Restart a server.

        Args:
            slug: Server identifier
        """
        await self._client.post(f"/servers/{slug}/restart")

    async def update_server_status(self, slug: str, status: str) -> None:
        """
        Update a server's status.

        Args:
            slug: Server identifier
            status: New status
        """
        await self._client.patch(f"/servers/{slug}/status", json={"status": status})

    # ==================== Environment Operations ====================

    async def get_env(self, file: str = ".env") -> Dict[str, str]:
        """
        Get environment variables from a file.

        Args:
            file: Path to env file (default: ".env")

        Returns:
            Dictionary of environment variables.
        """
        response = await self._client.get("/env", params={"file": file})

        data = response.get("data", response) if isinstance(response, dict) else {}

        if not isinstance(data, dict):
            return {}

        return data

    async def set_env(self, variables: Dict[str, str], file: str = ".env") -> None:
        """
        Set environment variables in a file.

        Args:
            variables: Dictionary of variables to set
            file: Path to env file (default: ".env")
        """
        await self._client.post("/env", json={"variables": variables}, params={"file": file})

    async def delete_env(self, keys: List[str], file: str = ".env") -> None:
        """
        Delete environment variables from a file.

        Args:
            keys: List of variable names to delete
            file: Path to env file (default: ".env")
        """
        await self._client.delete("/env", json={"keys": keys}, params={"file": file})

    async def env_exists(self, file: str = ".env") -> bool:
        """
        Check if an environment file exists.

        Args:
            file: Path to env file (default: ".env")

        Returns:
            True if the file exists, False otherwise.
        """
        return await self._client.head("/env", params={"file": file})

    # ==================== Authentication Operations ====================

    async def create_session_token(
        self,
        options: Optional[CreateSessionTokenOptions] = None,
    ) -> SessionToken:
        """
        Create a session token for sandbox access.

        Args:
            options: Token options (description, expires_in)

        Returns:
            SessionToken with id, token, and expiration.
        """
        body: Dict[str, Any] = {}

        if options:
            if options.description is not None:
                body["description"] = options.description
            body["expiresIn"] = options.expires_in
        else:
            body["expiresIn"] = 604800  # 7 days default

        response = await self._client.post("/auth/session_tokens", json=body)

        data = response.get("data", response) if isinstance(response, dict) else response

        return SessionToken(
            id=data["id"],
            token=data["token"],
            expires_at=data["expiresAt"],
            expires_in=data.get("expiresIn", 604800),
            description=data.get("description"),
        )

    async def list_session_tokens(self) -> List[SessionToken]:
        """
        List all session tokens.

        Returns:
            List of SessionToken objects.
        """
        response = await self._client.get("/auth/session_tokens")

        data = response.get("data", response) if isinstance(response, dict) else response

        if not isinstance(data, list):
            data = []

        return [
            SessionToken(
                id=t["id"],
                token=t.get("token", ""),
                expires_at=t["expiresAt"],
                expires_in=t.get("expiresIn", 0),
                description=t.get("description"),
            )
            for t in data
        ]

    async def get_session_token(self, token_id: str) -> SessionToken:
        """
        Get a session token by ID.

        Args:
            token_id: Token identifier

        Returns:
            SessionToken for the token.
        """
        response = await self._client.get(f"/auth/session_tokens/{token_id}")

        data = response.get("data", response) if isinstance(response, dict) else {}

        return SessionToken(
            id=data["id"],
            token=data.get("token", ""),
            expires_at=data["expiresAt"],
            expires_in=data.get("expiresIn", 0),
            description=data.get("description"),
        )

    async def revoke_session_token(self, token_id: str) -> None:
        """
        Revoke a session token.

        Args:
            token_id: Token identifier
        """
        await self._client.delete(f"/auth/session_tokens/{token_id}")

    async def create_magic_link(self, redirect_url: Optional[str] = None) -> MagicLink:
        """
        Create a magic link for web-based authentication.

        Args:
            redirect_url: URL to redirect after authentication

        Returns:
            MagicLink with magic_url and expiration.
        """
        body: Dict[str, Any] = {}

        if redirect_url is not None:
            body["redirectUrl"] = redirect_url

        response = await self._client.post("/auth/magic-links", json=body or None)

        data = response.get("data", response) if isinstance(response, dict) else {}

        return MagicLink(
            magic_url=data["magic_url"],
            expires_at=data["expires_at"],
            redirect_url=data.get("redirect_url"),
        )

    async def get_auth_status(self) -> Dict[str, Any]:
        """
        Get authentication status.

        Returns:
            Authentication status information.
        """
        response = await self._client.get("/auth/status")
        return response.get("data", response) if isinstance(response, dict) else {}

    async def get_auth_info(self) -> Dict[str, Any]:
        """
        Get authentication info.

        Returns:
            Authentication information.
        """
        response = await self._client.get("/auth/info")
        return response.get("data", response) if isinstance(response, dict) else {}

    # ==================== Signal Service ====================

    async def start_signals(self) -> SignalStatus:
        """
        Start the signal service for port notifications.

        Returns:
            SignalStatus with channel and ws_url for events.
        """
        response = await self._client.post("/signals/start")

        data = response.get("data", response) if isinstance(response, dict) else {}

        return SignalStatus(
            status=data.get("status", "active"),
            channel=data.get("channel"),
            ws_url=data.get("ws_url"),
        )

    async def get_signal_status(self) -> SignalStatus:
        """
        Get the signal service status.

        Returns:
            SignalStatus with current state.
        """
        response = await self._client.get("/signals/status")

        data = response.get("data", response) if isinstance(response, dict) else {}

        return SignalStatus(
            status=data.get("status", "stopped"),
            channel=data.get("channel"),
            ws_url=data.get("ws_url"),
        )

    async def stop_signals(self) -> None:
        """Stop the signal service."""
        await self._client.post("/signals/stop")

    async def emit_port_signal(self, port: int, type: str, url: str) -> None:
        """
        Emit a port open/close signal.

        Args:
            port: Port number
            type: Signal type ('open' or 'close')
            url: Service URL
        """
        await self._client.post("/signals/port", json={"port": port, "type": type, "url": url})

    async def emit_error_signal(self, message: str) -> None:
        """
        Emit an error signal.

        Args:
            message: Error message
        """
        await self._client.post("/signals/error", json={"message": message})

    async def emit_server_ready_signal(self, port: int, url: str) -> None:
        """
        Emit a server ready signal.

        Args:
            port: Server port
            url: Server URL
        """
        await self._client.post("/signals/server-ready", json={"port": port, "url": url})

    # ==================== Child Sandbox Operations ====================

    async def create_child_sandbox(self) -> Dict[str, Any]:
        """
        Create a child sandbox.

        Returns:
            Child sandbox information.
        """
        response = await self._client.post("/sandboxes")
        return response.get("data", response) if isinstance(response, dict) else {}

    async def list_child_sandboxes(self) -> List[Dict[str, Any]]:
        """
        List all child sandboxes.

        Returns:
            List of child sandbox information.
        """
        response = await self._client.get("/sandboxes")
        data = response.get("data", response) if isinstance(response, dict) else response
        return data if isinstance(data, list) else []

    async def get_child_sandbox(self, subdomain: str) -> Dict[str, Any]:
        """
        Get a child sandbox by subdomain.

        Args:
            subdomain: Child sandbox subdomain

        Returns:
            Child sandbox information.
        """
        response = await self._client.get(f"/sandboxes/{subdomain}")
        return response.get("data", response) if isinstance(response, dict) else {}

    async def destroy_child_sandbox(
        self, subdomain: str, delete_files: bool = False
    ) -> None:
        """
        Destroy a child sandbox.

        Args:
            subdomain: Child sandbox subdomain
            delete_files: Whether to delete files
        """
        await self._client.delete(
            f"/sandboxes/{subdomain}",
            params={"delete_files": str(delete_files).lower()},
        )

    # ==================== Utility Methods ====================

    def get_sandbox_url(self) -> str:
        """
        Get the sandbox API URL.

        Returns:
            Sandbox API base URL.
        """
        return self._sandbox_url

    def get_token(self) -> str:
        """
        Get the current access token.

        Returns:
            Current authentication token.
        """
        return self._token

    def set_token(self, token: str) -> None:
        """
        Set a new access token.

        Useful for switching to a session token.

        Args:
            token: New authentication token
        """
        self._token = token
        # Update client headers
        self._client = HTTPClient(
            base_url=self._sandbox_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        self._filesystem = FileSystem(self._client)

    # ==================== Context Manager ====================

    async def __aenter__(self) -> "Sandbox":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ) -> None:
        """Async context manager exit - closes client but does NOT destroy sandbox."""
        await self._client.close()

    # ==================== Representation ====================

    def __repr__(self) -> str:
        return (
            f"Sandbox(sandbox_id={self._sandbox_id!r}, "
            f"provider={self._provider!r}, "
            f"name={self._name!r})"
        )
