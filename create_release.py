#!/usr/bin/env python3
"""Create GitHub release using token from .env"""

import os
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load .env
load_dotenv()
token = os.getenv("GITHUB_TOKEN")

if not token:
    print("❌ GITHUB_TOKEN not found in .env")
    exit(1)

print(f"✓ Loaded token: {token[:20]}...")

# Get version from manifest
manifest_path = Path("custom_components/smartgardn_et0/manifest.json")
with open(manifest_path) as f:
    manifest = json.load(f)
    version = manifest["version"]

print(f"✓ Version: {version}")

# Build distribution
print("📦 Building distribution...")
os.system("rm -rf dist && mkdir -p dist")
os.system("cd custom_components/smartgardn_et0 && zip -r ../../dist/smartgardn_et0.zip . -x '*.pyc' '__pycache__/*' && cd ../..")
print("✓ Distribution built")

# GitHub API
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json",
}
repo = "Presley2/ha-smartgardn"
tag = f"v{version}"

# Check if release exists
print(f"🔍 Checking if release {tag} exists...")
check_url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
check_resp = requests.get(check_url, headers=headers)

if check_resp.status_code == 200:
    print(f"⚠️  Release {tag} already exists")
    exit(0)

# Create release
print(f"📤 Creating release {tag}...")
create_url = f"https://api.github.com/repos/{repo}/releases"
release_data = {
    "tag_name": tag,
    "name": f"Release {version}",
    "body": f"SmartGardn ET₀ v{version}\n\n- Scientific irrigation control based on FAO-56 ET₀\n- See CHANGELOG.md for details",
    "draft": False,
    "prerelease": False,
}

release_resp = requests.post(create_url, headers=headers, json=release_data)
if release_resp.status_code != 201:
    print(f"❌ Failed to create release: {release_resp.text}")
    exit(1)

release_json = release_resp.json()
upload_url = release_json["upload_url"]
print(f"✓ Release created: {release_json['html_url']}")

# Upload asset
print(f"📤 Uploading asset...")
zip_path = Path(f"dist/smartgardn_et0.zip")
with open(zip_path, "rb") as f:
    upload_headers = headers.copy()
    upload_headers["Content-Type"] = "application/zip"
    upload_url_clean = upload_url.split("{")[0]  # Remove {?name,label}
    asset_resp = requests.post(
        f"{upload_url_clean}?name=smartgardn_et0-{version}.zip",
        headers=upload_headers,
        data=f.read(),
    )

if asset_resp.status_code != 201:
    print(f"⚠️  Asset upload failed: {asset_resp.text}")
else:
    print(f"✓ Asset uploaded")

print(f"\n✅ Release {tag} created successfully!")
print(f"🔗 {release_json['html_url']}")
