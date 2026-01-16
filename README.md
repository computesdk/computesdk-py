# ComputeSDK Python

Official Python SDK for the ComputeSDK gateway — run code in remote sandboxes across multiple cloud providers.

ComputeSDK provides a unified interface for executing code, running commands, and managing files in isolated sandbox environments. Connect to providers like E2B, Modal, Railway, Daytona, and more through a single, consistent API.

## Installation

```bash
pip install git+https://github.com/computesdk/computesdk-py.git
```

## Quick Start

```python
import asyncio
from computesdk import compute

async def main():
    # Create a sandbox (auto-configured from environment variables)
    sandbox = await compute.sandbox.create()

    try:
        # Execute Python code
        result = await sandbox.run_code('print("Hello, World!")', 'python')
        print(result.output)  # Hello, World!

        # Execute shell commands
        cmd = await sandbox.run_command('ls -la')
        print(cmd.stdout)

    finally:
        await sandbox.destroy()

asyncio.run(main())
```

## Configuration

### Environment Variables (Recommended)

Set your API keys as environment variables:

```bash
# Required: ComputeSDK API key
export COMPUTESDK_API_KEY="your-computesdk-api-key"

# Provider credentials (set one of these based on your provider)
export E2B_API_KEY="your-e2b-key"
# OR
export MODAL_TOKEN_ID="your-modal-token-id"
export MODAL_TOKEN_SECRET="your-modal-token-secret"
# OR
export RAILWAY_API_KEY="your-railway-key"
export RAILWAY_PROJECT_ID="your-project-id"
export RAILWAY_ENVIRONMENT_ID="your-env-id"
# etc.
```

The SDK will automatically detect your provider based on which credentials are set.

### Explicit Configuration

```python
from computesdk import Compute, GatewayConfig

config = GatewayConfig(
    api_key="your-computesdk-api-key",
    provider="e2b",
    provider_headers={"X-E2B-API-Key": "your-e2b-key"},
)

compute = Compute(config=config)
sandbox = await compute.sandbox.create()
```

## Features

### Code Execution

```python
# Python
result = await sandbox.run_code('''
import sys
print(f"Python {sys.version}")
''', 'python')

# Node.js
result = await sandbox.run_code('console.log("Hello from Node!")', 'node')
```

### Command Execution

```python
from computesdk import RunCommandOptions

# Simple command
result = await sandbox.run_command('echo "Hello"')
print(result.stdout)

# With options
result = await sandbox.run_command(
    'npm install',
    RunCommandOptions(cwd='/app', timeout=60000)
)
```

### File System Operations

```python
# Write files
await sandbox.filesystem.write_file('/app/main.py', 'print("Hello")')

# Read files
content = await sandbox.filesystem.read_file('/app/main.py')

# List directory
entries = await sandbox.filesystem.readdir('/app')
for entry in entries:
    print(f"{entry.type}: {entry.name}")

# Check existence
exists = await sandbox.filesystem.exists('/app/main.py')

# Delete files
await sandbox.filesystem.remove('/app/main.py')

# Batch write
await sandbox.filesystem.batch_write([
    {"path": "/app/a.py", "content": "# file a"},
    {"path": "/app/b.py", "content": "# file b"},
])
```

### Named Sandboxes

Named sandboxes persist across sessions:

```python
# Find or create a named sandbox
sandbox = await compute.sandbox.find_or_create(
    name="my-dev-sandbox",
    namespace="development",
)

# Find an existing sandbox
sandbox = await compute.sandbox.find(
    name="my-dev-sandbox",
    namespace="development",
)
```

### Terminal Sessions

```python
from computesdk import CreateTerminalOptions

# Create a terminal
terminal = await sandbox.create_terminal(
    CreateTerminalOptions(shell="/bin/bash", pty=True)
)

# Execute commands
result = await sandbox.execute_in_terminal(
    terminal.id,
    "npm test",
    background=False
)

# List terminals
terminals = await sandbox.list_terminals()

# Destroy terminal
await sandbox.destroy_terminal(terminal.id)
```

### WIP - Server Management

```python
from computesdk import StartServerOptions

# Start a server
server = await sandbox.start_server(StartServerOptions(
    slug="api",
    command="node server.js",
    path="/app",
))

# Get public URL
url = await sandbox.get_url(port=3000)
print(f"Server available at: {url}")

# List servers
servers = await sandbox.list_servers()

# Stop server
await sandbox.stop_server("api")
```

### File Watchers

```python
from computesdk import CreateWatcherOptions

# Create a file watcher
watcher = await sandbox.create_watcher(
    "/app",
    CreateWatcherOptions(
        include_content=True,
        ignored=["node_modules", ".git"],
    )
)

# Use WebSocket to receive events
# watcher.ws_url and watcher.channel for real-time updates

# Destroy watcher
await sandbox.destroy_watcher(watcher.id)
```

### WIP - Session Tokens

```python
from computesdk import CreateSessionTokenOptions

# Create a session token
token = await sandbox.create_session_token(
    CreateSessionTokenOptions(
        description="My App Token",
        expires_in=604800,  # 7 days
    )
)
print(f"Token: {token.token}")

# Use the token
sandbox.set_token(token.token)

# List and revoke tokens
tokens = await sandbox.list_session_tokens()
await sandbox.revoke_session_token(token.id)
```


## Supported Providers

| Provider | Environment Variables |
|----------|----------------------|
| E2B | `E2B_API_KEY` |
| Modal | `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET` |
| Railway | `RAILWAY_API_KEY`, `RAILWAY_PROJECT_ID`, `RAILWAY_ENVIRONMENT_ID` |
| Daytona | `DAYTONA_API_KEY` |
| Vercel | `VERCEL_TOKEN`, `VERCEL_TEAM_ID`, `VERCEL_PROJECT_ID` |


## Error Handling

```python
from computesdk import (
    ComputeSDKError,
    AuthenticationError,
    NotFoundError,
    TimeoutError,
)

try:
    sandbox = await compute.sandbox.create()
    result = await sandbox.run_code('print("Hello")', 'python')
except AuthenticationError:
    print("Invalid API key")
except NotFoundError:
    print("Sandbox not found")
except TimeoutError:
    print("Request timed out")
except ComputeSDKError as e:
    print(f"Error: {e}")
```

## API Reference

### Sandbox Methods

| Method | Description |
|--------|-------------|
| `run_code(code, language)` | Execute code in the sandbox |
| `run_command(command, options)` | Execute a shell command |
| `get_info()` | Get sandbox information |
| `get_url(port, protocol)` | Get public URL for a service |
| `destroy()` | Destroy the sandbox |
| `extend(duration)` | WIP Extend sandbox timeout |
| `health()` | Check sandbox health |

### FileSystem Methods

| Method | Description |
|--------|-------------|
| `read_file(path)` | Read file contents |
| `write_file(path, content)` | Write to a file |
| `readdir(path)` | List directory contents |
| `mkdir(path)` | Create a directory |
| `exists(path)` | Check if path exists |
| `remove(path)` | Delete file or directory |
| `batch_write(files)` | Write multiple files |

### Terminal Methods

| Method | Description |
|--------|-------------|
| `create_terminal(options)` | Create a terminal session |
| `list_terminals()` | List all terminals |
| `get_terminal(id)` | Get terminal by ID |
| `destroy_terminal(id)` | Destroy a terminal |
| `execute_in_terminal(id, cmd)` | Execute command in terminal |

### WIP Server Methods

| Method | Description |
|--------|-------------|
| `start_server(options)` | Start a server process |
| `list_servers()` | List all servers |
| `get_server(slug)` | Get server by slug |
| `stop_server(slug)` | Stop a server |
| `restart_server(slug)` | Restart a server |

## Requirements

- Python >= 3.9
- httpx >= 0.25.0
- websockets >= 12.0 (optional, for real-time features)

## Development

```bash
# Clone the repository
git clone https://github.com/computesdk/computesdk
cd sdk/computesdk-py

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

MIT
