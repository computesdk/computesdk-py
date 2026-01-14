#!/usr/bin/env python3
"""
Simple sandbox test that creates a sandbox, displays info, waits 60 seconds, then destroys it.
"""

import asyncio
import json
import os

from dotenv import load_dotenv

load_dotenv()

from computesdk import compute, auto_config, CreateSandboxOptions


async def main():
    # Debug: show config
    print("Configuration:")
    print(f"  COMPUTESDK_API_KEY: {'set' if os.environ.get('COMPUTESDK_API_KEY') else 'NOT SET'}")
    print(f"  COMPUTESDK_GATEWAY_URL: {os.environ.get('COMPUTESDK_GATEWAY_URL', 'default')}")
    print(f"  E2B_API_KEY: {'set' if os.environ.get('E2B_API_KEY') else 'NOT SET'}")

    try:
        config = auto_config()
        print(f"  Detected provider: {config.provider}")
        print(f"  Gateway URL: {config.gateway_url}")
    except ValueError as e:
        print(f"  Config error: {e}")
        return

    print("\nCreating sandbox...")
    sandbox = await compute.sandbox.create(
        CreateSandboxOptions(
            name="test-sandbox-2",
            namespace="development",
        )
    )

    print("\n" + "=" * 50)
    print("SUCCESS: Sandbox created!")
    print("=" * 50)
    print(f"  Sandbox ID: {sandbox.sandbox_id}")
    print(f"  Provider:   {sandbox.provider}")
    print(f"  Name:       {sandbox.name}")
    print(f"  Namespace:  {sandbox.namespace}")

    # Get detailed info
    info = await sandbox.get_info()
    print(f"  Status:     {info.status.value}")
    print(f"  Timeout:    {info.timeout}")

    # Check health
    healthy = await sandbox.health()
    print(f"  Healthy:    {healthy}")
    print("=" * 50)

    # Test run_command
    print("\nRunning command: ls -la /")
    cmd_result = await sandbox.run_command("ls -la /")
    print(f"  Exit code: {cmd_result.exit_code}")
    print(f"  Duration:  {cmd_result.duration_ms}ms")
    print(f"  Output:\n{cmd_result.stdout}")
    if cmd_result.stderr:
        print(f"  Stderr: {cmd_result.stderr}")

    # Test run_code
    print("\nRunning Python code:")
    code = """
import sys
import platform

print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")
print("Hello from the sandbox!")
"""
    code_result = await sandbox.run_code(code, "python")
    print(f"  Exit code: {code_result.exit_code}")
    print(f"  Output:\n{code_result.output}")

    # Test filesystem operations
    print("\n" + "=" * 50)
    print("FILESYSTEM TESTS")
    print("=" * 50)

    # write_file
    print("\n1. Writing file /hello.txt...")
    await sandbox.filesystem.write_file("/hello.txt", "Hello from ComputeSDK!")
    print("   File written!")

    # read_file
    print("\n2. Reading file /hello.txt...")
    content = await sandbox.filesystem.read_file("/hello.txt")
    print(f"   Content: {content}")

    # exists (file that exists)
    print("\n3. Checking if /hello.txt exists...")
    exists = await sandbox.filesystem.exists("/hello.txt")
    print(f"   Exists: {exists}")

    # exists (file that doesn't exist)
    print("\n4. Checking if /nonexistent.txt exists...")
    exists = await sandbox.filesystem.exists("/nonexistent.txt")
    print(f"   Exists: {exists}")

    # readdir
    print("\n5. Listing root directory...")
    entries = await sandbox.filesystem.readdir("/")
    print(f"   Found {len(entries)} entries:")
    for entry in entries:
        print(f"     - {entry.name} (type: {entry.type})")

    # Test get_url
    print("\n" + "=" * 50)
    print("URL TESTS")
    print("=" * 50)

    print("\n1. Getting URL for port 3000...")
    url = await sandbox.get_url(port=3000)
    print(f"   URL: {url}")

    print("\n2. Getting URL for port 8080 with https...")
    url_https = await sandbox.get_url(port=8080, protocol="https")
    print(f"   URL: {url_https}")

    print("\n" + "=" * 50)
    print("INFO TESTS")
    print("=" * 50)

    # Test get_info
    print("\n3. Getting sandbox info...")
    info = await sandbox.get_info()
    info_dict = {
        "sandbox_id": info.id,
        "status": info.status.value,
        "timeout": info.timeout,
        "provider": info.provider,
        "name": info.name,
        "namespace": info.namespace,
    }
    print(f"   Info:\n{json.dumps(info_dict, indent=4)}")

    print("\n" + "=" * 50)
    print("All tests completed!")
    print("=" * 50)

    print("\nWaiting 60 seconds...")
    await asyncio.sleep(60)

    print("\nDestroying sandbox...")
    await sandbox.destroy()
    print("Sandbox destroyed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
