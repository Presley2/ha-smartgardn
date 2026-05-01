#!/usr/bin/env python3
"""Install git hooks for development."""

import shutil
from pathlib import Path

def setup_hooks():
    """Copy hooks from .github/hooks to .git/hooks."""
    repo_root = Path(__file__).parent.parent
    hooks_src = repo_root / ".github" / "hooks"
    hooks_dst = repo_root / ".git" / "hooks"

    if not hooks_src.exists():
        print(f"❌ Hooks source directory not found: {hooks_src}")
        return False

    if not hooks_dst.exists():
        hooks_dst.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created hooks directory: {hooks_dst}")

    for hook_file in hooks_src.iterdir():
        if hook_file.is_file():
            dst_file = hooks_dst / hook_file.name
            shutil.copy2(hook_file, dst_file)
            # Make executable
            dst_file.chmod(0o755)
            print(f"✓ Installed: {hook_file.name}")

    print("✓ Git hooks installed successfully!")
    return True

if __name__ == "__main__":
    success = setup_hooks()
    exit(0 if success else 1)
