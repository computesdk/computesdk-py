"""
Type definitions for ComputeSDK.

All types are implemented as dataclasses for easy serialization and type safety.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional


class Runtime(str, Enum):
    """Supported code execution runtimes."""

    NODE = "node"
    PYTHON = "python"
    DENO = "deno"
    BUN = "bun"


class SandboxStatus(str, Enum):
    """Sandbox lifecycle status."""

    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class TerminalStatus(str, Enum):
    """Terminal session status."""

    RUNNING = "running"
    STOPPED = "stopped"
    READY = "ready"
    ACTIVE = "active"


class CommandStatus(str, Enum):
    """Command execution status."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ServerStatus(str, Enum):
    """Server process status."""

    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    ERROR = "error"


class WatcherStatus(str, Enum):
    """File watcher status."""

    ACTIVE = "active"
    STOPPED = "stopped"


class FileType(str, Enum):
    """File system entry type."""

    FILE = "file"
    DIRECTORY = "directory"


# ==================== Result Types ====================


@dataclass
class CodeResult:
    """Result from code execution."""

    output: str
    exit_code: int
    language: str


@dataclass
class CommandResult:
    """Result from command execution."""

    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int


@dataclass
class StreamingCommandResult:
    """Result from streaming command execution."""

    cmd_id: str
    terminal_id: str
    channel: str
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None


@dataclass
class SandboxInfo:
    """Sandbox information and status."""

    id: str
    provider: str
    status: SandboxStatus
    created_at: Optional[datetime] = None
    timeout: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    name: Optional[str] = None
    namespace: Optional[str] = None


# ==================== File System Types ====================


@dataclass
class FileEntry:
    """File system entry (file or directory)."""

    name: str
    type: Literal["file", "directory"]
    size: Optional[int] = None
    modified: Optional[datetime] = None


@dataclass
class FileInfo:
    """Detailed file information."""

    path: str
    name: str
    type: Literal["file", "directory"]
    size: Optional[int] = None
    modified: Optional[datetime] = None
    content: Optional[str] = None


# ==================== Terminal Types ====================


@dataclass
class TerminalInfo:
    """Terminal session information."""

    id: str
    pty: bool
    status: TerminalStatus
    channel: Optional[str] = None
    ws_url: Optional[str] = None
    encoding: Optional[Literal["raw", "base64"]] = None


@dataclass
class CommandInfo:
    """Information about an executed command."""

    cmd_id: str
    terminal_id: str
    command: str
    status: CommandStatus
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


# ==================== Server Types ====================


@dataclass
class ServerInfo:
    """Server process information."""

    slug: str
    start: str
    status: str
    path: Optional[str] = None
    port: Optional[int] = None
    url: Optional[str] = None
    env_file: Optional[str] = None


# ==================== Watcher Types ====================


@dataclass
class WatcherInfo:
    """File watcher information."""

    id: str
    path: str
    status: str
    channel: str
    ws_url: str
    include_content: bool = False
    ignored: List[str] = field(default_factory=list)
    encoding: Optional[Literal["raw", "base64"]] = None


@dataclass
class WatcherEvent:
    """File watcher change event."""

    event: Literal["create", "modify", "delete", "rename"]
    path: str
    content: Optional[str] = None


# ==================== Auth Types ====================


@dataclass
class SessionToken:
    """Session token for sandbox authentication."""

    id: str
    token: str
    expires_at: str
    expires_in: int
    description: Optional[str] = None


@dataclass
class MagicLink:
    """Magic link for web-based authentication."""

    magic_url: str
    expires_at: str
    redirect_url: Optional[str] = None


@dataclass
class AuthInfo:
    """Authentication status information."""

    authenticated: bool
    user_id: Optional[str] = None
    session_id: Optional[str] = None


# ==================== Signal Types ====================


@dataclass
class SignalStatus:
    """Signal service status."""

    status: Literal["active", "stopped"]
    channel: Optional[str] = None
    ws_url: Optional[str] = None


@dataclass
class PortEvent:
    """Port open/close event."""

    port: int
    type: Literal["open", "close"]
    url: str


# ==================== Options Types ====================


@dataclass
class CreateSandboxOptions:
    """Options for creating a sandbox."""

    timeout: Optional[int] = None
    template_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    envs: Optional[Dict[str, str]] = None
    name: Optional[str] = None
    namespace: Optional[str] = None


@dataclass
class RunCommandOptions:
    """Options for running a command."""

    shell: Optional[str] = None
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    background: bool = False
    stream: bool = False
    timeout: Optional[int] = None


@dataclass
class CreateTerminalOptions:
    """Options for creating a terminal."""

    shell: Optional[str] = None
    encoding: Optional[Literal["raw", "base64"]] = None
    pty: bool = False


@dataclass
class CreateWatcherOptions:
    """Options for creating a file watcher."""

    include_content: bool = False
    ignored: Optional[List[str]] = None
    encoding: Optional[Literal["raw", "base64"]] = None


@dataclass
class StartServerOptions:
    """Options for starting a server."""

    slug: str
    command: str
    path: Optional[str] = None
    env_file: Optional[str] = None


@dataclass
class CreateSessionTokenOptions:
    """Options for creating a session token."""

    description: Optional[str] = None
    expires_in: int = 604800  # 7 days in seconds


@dataclass
class CreateMagicLinkOptions:
    """Options for creating a magic link."""

    redirect_url: Optional[str] = None


@dataclass
class GetUrlOptions:
    """Options for getting a service URL."""

    port: int
    protocol: str = "https"


# ==================== Response Types ====================


@dataclass
class SandboxResponse:
    """Response from sandbox creation/retrieval."""

    sandbox_id: str
    url: str
    token: str
    provider: str
    metadata: Optional[Dict[str, Any]] = None
    name: Optional[str] = None
    namespace: Optional[str] = None


@dataclass
class HealthResponse:
    """Health check response."""

    status: str
    version: Optional[str] = None


# ==================== Child Sandbox Types ====================


@dataclass
class ChildSandboxInfo:
    """Child sandbox information."""

    subdomain: str
    url: str
    status: str
    created_at: Optional[datetime] = None
