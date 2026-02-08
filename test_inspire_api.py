#!/usr/bin/env python3
"""Test script for Inspire API client.

Usage:
    python test_inspire_api.py --api-key YOUR_KEY --username YOUR_USER --password YOUR_PASS

This script tests the Inspire API client outside of Home Assistant:
- Connects and obtains session key
- Lists all devices
- Gets detailed information for each device
- Checks device connection status
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add custom_components to path so we can import the api module directly
sys.path.insert(0, str(Path(__file__).parent / "custom_components" / "inspire_home_automation"))

from api import InspireAPIClient

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

_LOGGER = logging.getLogger(__name__)


async def test_api(api_key: str, username: str, password: str) -> None:
    """Test the Inspire API client.
    
    Args:
        api_key: Inspire API key
        username: Account username
        password: Account password
    """
    client = InspireAPIClient(api_key, username, password)
    
    try:
        # Test 1: Connect
        print("\n" + "="*60)
        print("TEST 1: Connecting to Inspire API")
        print("="*60)
        session_key = await client.connect()
        print(f"✓ Connected successfully!")
        print(f"  Session key: {session_key[:20]}..." if len(session_key) > 20 else f"  Session key: {session_key}")
        
        # Test 2: Get devices
        print("\n" + "="*60)
        print("TEST 2: Getting device list")
        print("="*60)
        devices = await client.get_devices()
        print(f"✓ Found {len(devices)} device(s)")
        
        for i, device in enumerate(devices, 1):
            print(f"\n  Device #{i}:")
            for key, value in device.items():
                print(f"    {key}: {value}")
        
        # Test 3: Get detailed info for each device
        if devices:
            print("\n" + "="*60)
            print("TEST 3: Getting detailed device information")
            print("="*60)
            
            for device in devices:
                device_id = device.get("id") or device.get("device_id")
                device_name = device.get("name") or device.get("device_name", "Unknown")
                
                if not device_id:
                    print(f"⚠ Skipping device '{device_name}' - no ID found")
                    continue
                    
                print(f"\n  Device: {device_name} (ID: {device_id})")
                
                try:
                    info = await client.get_device_information(device_id)
                    print(f"  ✓ Got device information:")
                    for key, value in info.items():
                        print(f"      {key}: {value}")
                        
                    # Test 4: Check connection
                    is_connected = await client.check_connection(device_id)
                    print(f"  ✓ Connection status: {'Connected' if is_connected else 'Disconnected'}")
                    
                except Exception as err:
                    print(f"  ✗ Error getting device info: {err}")
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"✓ Connection: OK")
        print(f"✓ Devices found: {len(devices)}")
        print(f"✓ All tests completed successfully!")
        
    except Exception as err:
        print(f"\n✗ Error: {err}")
        _LOGGER.exception("Test failed")
        sys.exit(1)
        
    finally:
        await client.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Inspire API client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_inspire_api.py --api-key abc123 --username user@example.com --password mypass
  
  # Use environment variables
  export INSPIRE_API_KEY=abc123
  export INSPIRE_USERNAME=user@example.com
  export INSPIRE_PASSWORD=mypass
  python test_inspire_api.py
        """,
    )
    
    parser.add_argument(
        "--api-key",
        help="Inspire API key (or set INSPIRE_API_KEY env var)",
        default=None,
    )
    parser.add_argument(
        "--username",
        help="Account username (or set INSPIRE_USERNAME env var)",
        default=None,
    )
    parser.add_argument(
        "--password",
        help="Account password (or set INSPIRE_PASSWORD env var)",
        default=None,
    )
    
    args = parser.parse_args()
    
    # Get credentials from args or environment
    import os
    api_key = args.api_key or os.getenv("INSPIRE_API_KEY")
    username = args.username or os.getenv("INSPIRE_USERNAME")
    password = args.password or os.getenv("INSPIRE_PASSWORD")
    
    if not all([api_key, username, password]):
        parser.error(
            "API credentials required. Provide via arguments or environment variables:\n"
            "  --api-key or INSPIRE_API_KEY\n"
            "  --username or INSPIRE_USERNAME\n"
            "  --password or INSPIRE_PASSWORD"
        )
    
    print("Inspire API Test Script")
    print("="*60)
    print(f"API Key: {api_key[:10]}..." if len(api_key) > 10 else f"API Key: {api_key}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    
    asyncio.run(test_api(api_key, username, password))


if __name__ == "__main__":
    main()
