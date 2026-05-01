#!/usr/bin/env python3
"""
Test SmartGardn cards on a Live Home Assistant instance.
This script verifies that cards are properly registered and accessible.
"""

import asyncio
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError
import argparse


def check_static_files(ha_url: str, timeout: int = 5) -> dict:
    """Check if static card files are accessible."""
    results = {
        "static_path_ok": False,
        "files_checked": {},
    }

    cards = [
        "overview-card.js",
        "history-card.js",
        "settings-card.js",
        "ansaat-card.js",
    ]

    base_url = f"{ha_url}/smartgardn_et0_cards"

    print(f"🔍 Checking static files at {base_url}")

    for card in cards:
        url = f"{base_url}/{card}"
        try:
            with urlopen(url, timeout=timeout) as response:
                status = response.status
                size = len(response.read())
                results["files_checked"][card] = {
                    "status": status,
                    "size": size,
                    "ok": status == 200 and size > 0,
                }
                print(f"  {'✓' if status == 200 else '✗'} {card}: {status} ({size} bytes)")
        except URLError as e:
            results["files_checked"][card] = {
                "status": None,
                "size": 0,
                "ok": False,
                "error": str(e),
            }
            print(f"  ✗ {card}: {e}")
        except Exception as e:
            results["files_checked"][card] = {
                "status": None,
                "size": 0,
                "ok": False,
                "error": str(e),
            }
            print(f"  ✗ {card}: Unexpected error: {e}")

    results["static_path_ok"] = all(f["ok"] for f in results["files_checked"].values())
    return results


def check_manifest(ha_config_path: str) -> dict:
    """Check if manifest.json is correctly configured."""
    results = {
        "manifest_ok": False,
        "resources": [],
    }

    manifest_path = Path(ha_config_path) / "custom_components" / "smartgardn_et0" / "manifest.json"

    print(f"🔍 Checking manifest at {manifest_path}")

    if not manifest_path.exists():
        print(f"  ✗ Manifest not found at {manifest_path}")
        return results

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)

        if "lovelace" not in manifest:
            print(f"  ✗ 'lovelace' section missing in manifest")
            return results

        if "resources" not in manifest["lovelace"]:
            print(f"  ✗ 'resources' list missing in lovelace section")
            return results

        resources = manifest["lovelace"]["resources"]
        for resource in resources:
            if "url" in resource:
                results["resources"].append(resource["url"])
                print(f"  ✓ {resource['url']}")

        results["manifest_ok"] = len(resources) == 4
        return results

    except json.JSONDecodeError as e:
        print(f"  ✗ Invalid JSON: {e}")
        return results
    except Exception as e:
        print(f"  ✗ Error reading manifest: {e}")
        return results


async def check_lovelace_resources(ha_url: str, token: str) -> dict:
    """Check if Lovelace has resources registered (requires HA token)."""
    results = {
        "lovelace_ok": None,
        "resources": [],
        "message": "Requires Home Assistant token",
    }

    if not token:
        print("⚠️  Skipping Lovelace resource check (no token provided)")
        return results

    print("🔍 Checking Lovelace resources...")
    # This would require aiohttp and proper HA API integration
    # Skipping for now as it requires authentication
    print("  ℹ️  Requires Home Assistant API token")
    return results


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test SmartGardn ET₀ card registration on a Live Home Assistant instance"
    )
    parser.add_argument(
        "--ha-url",
        default="http://homeassistant.local:8123",
        help="Home Assistant URL (default: http://homeassistant.local:8123)",
    )
    parser.add_argument(
        "--ha-config",
        help="Path to Home Assistant config directory (for manifest checking)",
    )
    parser.add_argument(
        "--ha-token",
        help="Home Assistant API token (for advanced checks)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Request timeout in seconds (default: 5)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("SmartGardn ET₀ - Card Registration Test")
    print("=" * 60)

    all_ok = True

    # Test 1: Static files
    print()
    static_results = check_static_files(args.ha_url, args.timeout)
    if not static_results["static_path_ok"]:
        print("⚠️  Static files not accessible - integration may not be loaded yet")
        all_ok = False
    else:
        print("✓ All static files accessible")

    # Test 2: Manifest
    if args.ha_config:
        print()
        manifest_results = check_manifest(args.ha_config)
        if not manifest_results["manifest_ok"]:
            print("⚠️  Manifest configuration issues detected")
            all_ok = False
        else:
            print("✓ Manifest properly configured")

    # Test 3: Lovelace resources
    if args.ha_token:
        print()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(check_lovelace_resources(args.ha_url, args.ha_token))

    # Summary
    print()
    print("=" * 60)
    if all_ok:
        print("✓ All tests passed!")
        print()
        print("Next steps:")
        print("1. Go to Home Assistant Lovelace dashboard")
        print("2. Edit dashboard (pencil icon)")
        print("3. Add custom card: 'custom:irrigation-overview-card'")
        print("4. Set entry_id to your SmartGardn configuration ID")
        return 0
    else:
        print("⚠️  Some tests failed")
        print()
        print("Troubleshooting:")
        print("1. Ensure SmartGardn ET₀ integration is installed and loaded")
        print("2. Restart Home Assistant")
        print("3. Check HA logs for 'smartgardn_et0' errors")
        print("4. Verify Home Assistant URL is correct")
        return 1


if __name__ == "__main__":
    exit(main())
