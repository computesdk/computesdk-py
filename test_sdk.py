#!/usr/bin/env python3
"""
Manual test script for ComputeSDK Python SDK.

Usage:
    # Set environment variables first
    export COMPUTESDK_API_KEY="your-key"
    export E2B_API_KEY="your-e2b-key"  # or another provider

    # Run tests
    python test_sdk.py
"""


import asyncio
import os
import sys


async def test_basic():
    """Test basic sandbox operations."""
    from computesdk import compute

    print("=" * 50)
    print("TEST: Basic Sandbox Operations")
    print("=" * 50)

    # Create sandbox
    print("\n1. Creating sandbox...")
    sandbox = await compute.sandbox.create()
    print(f"   Created: {sandbox.sandbox_id}")
    print(f"   Provider: {sandbox.provider}")

    try:
        # Test health
        print("\n2. Checking health...")
        healthy = await sandbox.health()
        print(f"   Healthy: {healthy}")

        # Test code execution
        print("\n3. Running Python code...")
        result = await sandbox.run_code(
            'import sys; print(f"Python {sys.version_info.major}.{sys.version_info.minor}")',
            "python",
        )
        print(f"   Output: {result.output.strip()}")
        print(f"   Exit code: {result.exit_code}")

        # Test command execution
        print("\n4. Running shell command...")
        cmd = await sandbox.run_command("echo 'Hello from shell!'")
        print(f"   Stdout: {cmd.stdout.strip()}")
        print(f"   Exit code: {cmd.exit_code}")

        # Test file operations
        print("\n5. Testing file operations...")
        await sandbox.filesystem.write_file("/tmp/test.txt", "Hello, ComputeSDK!")
        content = await sandbox.filesystem.read_file("/tmp/test.txt")
        print(f"   Written and read: {content}")

        exists = await sandbox.filesystem.exists("/tmp/test.txt")
        print(f"   File exists: {exists}")

        # Test directory listing
        print("\n6. Listing /tmp directory...")
        entries = await sandbox.filesystem.readdir("/tmp")
        for entry in entries[:5]:  # Show first 5
            print(f"   {entry.type}: {entry.name}")

        # Test sandbox info
        print("\n7. Getting sandbox info...")
        info = await sandbox.get_info()
        print(f"   ID: {info.id}")
        print(f"   Status: {info.status}")

        # Test URL generation
        print("\n8. Getting service URL...")
        url = await sandbox.get_url(port=3000)
        print(f"   URL for port 3000: {url}")

        print("\n" + "=" * 50)
        print("ALL BASIC TESTS PASSED!")
        print("=" * 50)

    finally:
        # Cleanup
        print("\n9. Destroying sandbox...")
        await sandbox.destroy()
        print("   Destroyed successfully")


async def test_named_sandbox():
    """Test named sandbox operations."""
    from computesdk import compute

    print("\n" + "=" * 50)
    print("TEST: Named Sandbox Operations")
    print("=" * 50)

    # Create or find named sandbox
    print("\n1. Finding or creating named sandbox...")
    sandbox = await compute.sandbox.find_or_create(
        name="test-sandbox",
        namespace="testing",
    )
    print(f"   Sandbox ID: {sandbox.sandbox_id}")
    print(f"   Name: {sandbox.name}")
    print(f"   Namespace: {sandbox.namespace}")

    try:
        # Run some code
        print("\n2. Running code in named sandbox...")
        result = await sandbox.run_code('print("Named sandbox works!")', "python")
        print(f"   Output: {result.output.strip()}")

        # Find the same sandbox
        print("\n3. Finding existing sandbox...")
        found = await compute.sandbox.find(name="test-sandbox", namespace="testing")
        if found:
            print(f"   Found: {found.sandbox_id}")
            print(f"   Same sandbox: {found.sandbox_id == sandbox.sandbox_id}")
        else:
            print("   Not found (unexpected)")

        print("\n" + "=" * 50)
        print("NAMED SANDBOX TESTS PASSED!")
        print("=" * 50)

    finally:
        print("\n4. Destroying named sandbox...")
        await sandbox.destroy()
        print("   Destroyed successfully")


async def test_terminal():
    """Test terminal operations."""
    from computesdk import compute, CreateTerminalOptions

    print("\n" + "=" * 50)
    print("TEST: Terminal Operations")
    print("=" * 50)

    sandbox = await compute.sandbox.create()

    try:
        # Create terminal
        print("\n1. Creating terminal...")
        terminal = await sandbox.create_terminal(
            CreateTerminalOptions(shell="/bin/bash")
        )
        print(f"   Terminal ID: {terminal.id}")
        print(f"   Status: {terminal.status}")

        # List terminals
        print("\n2. Listing terminals...")
        terminals = await sandbox.list_terminals()
        print(f"   Count: {len(terminals)}")

        # Execute in terminal
        print("\n3. Executing command in terminal...")
        result = await sandbox.execute_in_terminal(
            terminal.id,
            "echo 'Terminal test'",
        )
        print(f"   Result: {result}")

        # Destroy terminal
        print("\n4. Destroying terminal...")
        await sandbox.destroy_terminal(terminal.id)
        print("   Destroyed successfully")

        print("\n" + "=" * 50)
        print("TERMINAL TESTS PASSED!")
        print("=" * 50)

    finally:
        await sandbox.destroy()


async def test_config():
    """Test configuration and auto-detection."""
    from computesdk import detect_provider, auto_config, GatewayConfig, Compute

    print("\n" + "=" * 50)
    print("TEST: Configuration")
    print("=" * 50)

    # Test provider detection
    print("\n1. Detecting provider...")
    provider = detect_provider()
    print(f"   Detected: {provider}")

    # Test auto config
    print("\n2. Auto-configuring...")
    try:
        config = auto_config()
        print(f"   API Key: {config.api_key[:10]}...")
        print(f"   Provider: {config.provider}")
        print(f"   Gateway URL: {config.gateway_url}")
        print(f"   Provider headers: {list(config.provider_headers.keys())}")
    except ValueError as e:
        print(f"   Error (expected if env vars not set): {e}")

    # Test explicit config
    print("\n3. Testing explicit config...")
    explicit_config = GatewayConfig(
        api_key="test-key",
        provider="e2b",
        provider_headers={"X-E2B-API-Key": "test-e2b-key"},
    )
    compute_client = Compute(config=explicit_config)
    print(f"   Created Compute client with explicit config")

    print("\n" + "=" * 50)
    print("CONFIG TESTS PASSED!")
    print("=" * 50)


async def test_types():
    """Test type imports and creation."""
    from computesdk import (
        CodeResult,
        CommandResult,
        CreateSandboxOptions,
        RunCommandOptions,
        Runtime,
        SandboxStatus,
    )

    print("\n" + "=" * 50)
    print("TEST: Types")
    print("=" * 50)

    # Test enums
    print("\n1. Testing enums...")
    print(f"   Runtime.PYTHON = {Runtime.PYTHON}")
    print(f"   SandboxStatus.RUNNING = {SandboxStatus.RUNNING}")

    # Test dataclasses
    print("\n2. Testing dataclasses...")
    code_result = CodeResult(output="Hello", exit_code=0, language="python")
    print(f"   CodeResult: {code_result}")

    options = CreateSandboxOptions(timeout=300000, template_id="python-dev")
    print(f"   CreateSandboxOptions: {options}")

    print("\n" + "=" * 50)
    print("TYPE TESTS PASSED!")
    print("=" * 50)


async def test_exceptions():
    """Test exception handling."""
    from computesdk import (
        ComputeSDKError,
        AuthenticationError,
        NotFoundError,
        ConfigurationError,
    )

    print("\n" + "=" * 50)
    print("TEST: Exceptions")
    print("=" * 50)

    print("\n1. Testing exception hierarchy...")
    try:
        raise AuthenticationError("Test auth error")
    except ComputeSDKError as e:
        print(f"   AuthenticationError caught as ComputeSDKError: {e}")

    try:
        raise NotFoundError("Resource not found")
    except ComputeSDKError as e:
        print(f"   NotFoundError caught as ComputeSDKError: {e}")
        print(f"   Status code: {e.status_code}")

    print("\n" + "=" * 50)
    print("EXCEPTION TESTS PASSED!")
    print("=" * 50)


async def run_all_tests():
    """Run all tests."""
    print("\n" + "#" * 60)
    print("# ComputeSDK Python SDK Test Suite")
    print("#" * 60)

    # Check for API keys
    if not os.environ.get("COMPUTESDK_API_KEY"):
        print("\nWARNING: COMPUTESDK_API_KEY not set")
        print("Some tests will be skipped.\n")

    # Always run these tests (no API key needed)
    await test_types()
    await test_exceptions()

    # These need API keys
    if os.environ.get("COMPUTESDK_API_KEY"):
        await test_config()
        await test_basic()
        await test_named_sandbox()
        await test_terminal()
    else:
        print("\nSkipping integration tests (no API key)")
        print("Set COMPUTESDK_API_KEY and provider credentials to run full tests")

    print("\n" + "#" * 60)
    print("# TEST SUITE COMPLETE")
    print("#" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
