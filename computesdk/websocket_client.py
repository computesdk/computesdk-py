"""
WebSocket client for real-time sandbox features.

Provides WebSocket connectivity for terminals, file watchers,
and signal services.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable, Dict, Optional, Set

try:
    import websockets
    from websockets.client import WebSocketClientProtocol

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketClientProtocol = Any  # type: ignore

from .exceptions import WebSocketError
from .protocol import BinaryProtocol


# Type alias for event handlers
EventHandler = Callable[[Dict[str, Any]], Awaitable[None]]


class WebSocketClient:
    """
    WebSocket client for real-time sandbox events.

    Supports both binary and JSON protocols, with automatic
    reconnection and event handling.

    Example:
        client = WebSocketClient(
            url="wss://sandbox.computesdk.com/ws",
            token="your-token",
        )

        async def on_output(data):
            print(data["output"])

        client.on("terminal:output", on_output)

        await client.connect()
        await client.subscribe("terminal:abc123")

        # ... do work ...

        await client.disconnect()
    """

    def __init__(
        self,
        url: str,
        token: str,
        protocol: str = "binary",
        auto_reconnect: bool = True,
        reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 30.0,
    ):
        """
        Initialize the WebSocket client.

        Args:
            url: WebSocket URL (wss://...)
            token: Authentication token
            protocol: Protocol to use ('binary' or 'json')
            auto_reconnect: Whether to automatically reconnect on disconnect
            reconnect_delay: Initial reconnect delay in seconds
            max_reconnect_delay: Maximum reconnect delay in seconds
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets package is required for WebSocket support. "
                "Install it with: pip install websockets"
            )

        # Build URL with query params
        separator = "&" if "?" in url else "?"
        self._url = f"{url}{separator}token={token}&protocol={protocol}"
        self._protocol_name = protocol
        self._auto_reconnect = auto_reconnect
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_delay = max_reconnect_delay

        # State
        self._ws: Optional[WebSocketClientProtocol] = None
        self._running = False
        self._handlers: Dict[str, EventHandler] = {}
        self._subscriptions: Set[str] = set()
        self._receive_task: Optional[asyncio.Task[None]] = None
        self._current_reconnect_delay = reconnect_delay

        # Protocol encoder/decoder
        self._encoder = BinaryProtocol() if protocol == "binary" else None

    @property
    def connected(self) -> bool:
        """Check if the WebSocket is connected."""
        return self._ws is not None and self._ws.open

    async def connect(self) -> None:
        """
        Establish WebSocket connection.

        Raises:
            WebSocketError: If connection fails.
        """
        try:
            self._ws = await websockets.connect(self._url)
            self._running = True
            self._current_reconnect_delay = self._reconnect_delay

            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())

            # Re-subscribe to any previous subscriptions
            for channel in self._subscriptions.copy():
                await self._send_subscribe(channel)

        except Exception as e:
            raise WebSocketError(f"Failed to connect: {e}") from e

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._running = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._ws:
            await self._ws.close()
            self._ws = None

    async def subscribe(self, channel: str) -> None:
        """
        Subscribe to a channel for events.

        Args:
            channel: Channel identifier to subscribe to
        """
        self._subscriptions.add(channel)
        if self.connected:
            await self._send_subscribe(channel)

    async def unsubscribe(self, channel: str) -> None:
        """
        Unsubscribe from a channel.

        Args:
            channel: Channel identifier to unsubscribe from
        """
        self._subscriptions.discard(channel)
        if self.connected:
            await self._send_unsubscribe(channel)

    def on(self, event_type: str, handler: EventHandler) -> None:
        """
        Register an event handler.

        Args:
            event_type: Event type to handle (e.g., 'terminal:output')
            handler: Async function to call when event is received

        Example:
            async def handle_output(data):
                print(data["output"])

            client.on("terminal:output", handle_output)
        """
        self._handlers[event_type] = handler

    def off(self, event_type: str) -> None:
        """
        Remove an event handler.

        Args:
            event_type: Event type to stop handling
        """
        self._handlers.pop(event_type, None)

    async def send_terminal_input(self, terminal_id: str, input_text: str) -> None:
        """
        Send input to a terminal.

        Args:
            terminal_id: Terminal identifier
            input_text: Text to send to the terminal
        """
        await self._send_message({
            "type": "terminal:input",
            "data": {"terminal_id": terminal_id, "input": input_text},
        })

    async def resize_terminal(self, terminal_id: str, cols: int, rows: int) -> None:
        """
        Resize a terminal window.

        Args:
            terminal_id: Terminal identifier
            cols: Number of columns
            rows: Number of rows
        """
        await self._send_message({
            "type": "terminal:resize",
            "data": {"terminal_id": terminal_id, "cols": cols, "rows": rows},
        })

    async def start_command(self, cmd_id: str) -> None:
        """
        Start a pending streaming command.

        Args:
            cmd_id: Command identifier
        """
        await self._send_message({
            "type": "command:start",
            "data": {"cmd_id": cmd_id},
        })

    async def _send_subscribe(self, channel: str) -> None:
        """Send a subscribe message."""
        await self._send_message({"type": "subscribe", "channel": channel})

    async def _send_unsubscribe(self, channel: str) -> None:
        """Send an unsubscribe message."""
        await self._send_message({"type": "unsubscribe", "channel": channel})

    async def _send_message(self, message: Dict[str, Any]) -> None:
        """Send a message through the WebSocket."""
        if not self._ws or not self._ws.open:
            raise WebSocketError("WebSocket is not connected")

        try:
            if self._encoder:
                await self._ws.send(self._encoder.encode(message))
            else:
                await self._ws.send(json.dumps(message))
        except Exception as e:
            raise WebSocketError(f"Failed to send message: {e}") from e

    async def _receive_loop(self) -> None:
        """Main receive loop for WebSocket messages."""
        while self._running:
            try:
                if not self._ws or not self._ws.open:
                    if self._auto_reconnect:
                        await self._reconnect()
                    else:
                        break
                    continue

                message = await self._ws.recv()

                # Decode message
                if self._encoder and isinstance(message, bytes):
                    data = self._encoder.decode(message)
                else:
                    data = json.loads(message)

                # Dispatch to handler
                event_type = data.get("type", "")
                handler = self._handlers.get(event_type)
                if handler:
                    try:
                        await handler(data)
                    except Exception:
                        # Don't let handler errors crash the receive loop
                        pass

                # Also dispatch to wildcard handler if present
                wildcard_handler = self._handlers.get("*")
                if wildcard_handler:
                    try:
                        await wildcard_handler(data)
                    except Exception:
                        pass

            except websockets.ConnectionClosed:
                if self._auto_reconnect and self._running:
                    await self._reconnect()
                else:
                    break

            except asyncio.CancelledError:
                break

            except Exception:
                # Log error and continue
                if self._auto_reconnect and self._running:
                    await asyncio.sleep(0.1)
                else:
                    break

    async def _reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        # Wait before reconnecting
        await asyncio.sleep(self._current_reconnect_delay)

        # Increase delay for next attempt (exponential backoff)
        self._current_reconnect_delay = min(
            self._current_reconnect_delay * 2,
            self._max_reconnect_delay,
        )

        try:
            self._ws = await websockets.connect(self._url)
            self._current_reconnect_delay = self._reconnect_delay

            # Re-subscribe to channels
            for channel in self._subscriptions:
                await self._send_subscribe(channel)

        except Exception:
            # Will retry on next loop iteration
            pass

    async def __aenter__(self) -> "WebSocketClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        await self.disconnect()


class TerminalSession:
    """
    High-level terminal session wrapper.

    Provides a convenient interface for interactive terminal sessions.

    Example:
        async with TerminalSession(sandbox, terminal_info) as term:
            term.on_output(lambda data: print(data))
            await term.write("ls -la\\n")
            await asyncio.sleep(1)
    """

    def __init__(
        self,
        sandbox_url: str,
        token: str,
        terminal_id: str,
        channel: str,
    ):
        """
        Initialize a terminal session.

        Args:
            sandbox_url: Sandbox base URL
            token: Authentication token
            terminal_id: Terminal identifier
            channel: WebSocket channel for this terminal
        """
        # Convert HTTP URL to WebSocket URL
        ws_url = sandbox_url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_url}/ws"

        self._terminal_id = terminal_id
        self._channel = channel
        self._client = WebSocketClient(ws_url, token)
        self._output_handler: Optional[Callable[[str], None]] = None

    @property
    def terminal_id(self) -> str:
        """Terminal identifier."""
        return self._terminal_id

    def on_output(self, handler: Callable[[str], None]) -> None:
        """
        Set output handler.

        Args:
            handler: Function to call with output text
        """
        self._output_handler = handler

    async def write(self, text: str) -> None:
        """
        Write text to the terminal.

        Args:
            text: Text to write (include \\n for newlines)
        """
        await self._client.send_terminal_input(self._terminal_id, text)

    async def resize(self, cols: int, rows: int) -> None:
        """
        Resize the terminal window.

        Args:
            cols: Number of columns
            rows: Number of rows
        """
        await self._client.resize_terminal(self._terminal_id, cols, rows)

    async def _handle_output(self, data: Dict[str, Any]) -> None:
        """Handle terminal output event."""
        if self._output_handler:
            output = data.get("data", {}).get("output", "")
            self._output_handler(output)

    async def __aenter__(self) -> "TerminalSession":
        """Async context manager entry."""
        # Register output handler
        self._client.on("terminal:output", self._handle_output)

        # Connect and subscribe
        await self._client.connect()
        await self._client.subscribe(self._channel)

        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        await self._client.disconnect()
