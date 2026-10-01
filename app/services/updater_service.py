# app/services/updater_service.py
"""
Auto-Updater & Release Inspector Service.
Queries GitHub releases for Carxofa3/notes, compares semver, and automatically identifies
the correct binary asset for the user's platform (Windows Portable/Setup, Android APK, Linux AppImage/Deb).
"""

import os
import re
import sys
import time
import json
import shutil
import urllib.request
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from app.version import __version__, GITHUB_REPO, REPO_OWNER, REPO_NAME


def parse_semver(version_str: str) -> Tuple[int, ...]:
    """Parse string like 'v2.1.3' or '2.0.0-beta' into integer tuple for accurate comparison."""
    if not version_str:
        return (0, 0, 0)
    cleaned = version_str.strip().lstrip("vV")
    # Extract numeric digits separated by dots
    match = re.findall(r"\d+", cleaned)
    if match:
        return tuple(int(x) for x in match[:4])
    return (0, 0, 0)


class UpdaterService:
    def __init__(self):
        self._cached_release: Optional[Dict[str, Any]] = None
        self._last_checked = 0
        self._cache_ttl = 300  # Cache for 5 minutes

    def get_current_version(self) -> str:
        return f"v{__version__}"

    def check_for_updates(self, client_platform: Optional[str] = None) -> Dict[str, Any]:
        """
        Check GitHub for the latest release.
        Detects user's platform (or uses client_platform) to pinpoint the exact right asset.
        """
        now = time.time()
        raw_release = None

        if self._cached_release is not None and (now - self._last_checked < self._cache_ttl):
            raw_release = self._cached_release
        else:
            raw_release = self._fetch_latest_release()
            if raw_release:
                self._cached_release = raw_release
                self._last_checked = now

        if not raw_release:
            # Could not reach GitHub API (offline or rate-limited)
            return {
                "update_available": False,
                "current_version": self.get_current_version(),
                "latest_version": self.get_current_version(),
                "error": "Could not check for updates. GitHub releases unreachable or offline.",
                "recommended_asset": None,
                "platform_assets": {},
                "all_assets": []
            }

        latest_tag = raw_release.get("tagName") or raw_release.get("tag_name") or ""
        current_ver = self.get_current_version()

        current_tuple = parse_semver(current_ver)
        latest_tuple = parse_semver(latest_tag)

        update_available = latest_tuple > current_tuple

        # Parse and group all release assets
        raw_assets = raw_release.get("assets", [])
        parsed_assets = []
        for a in raw_assets:
            name = a.get("name", "")
            size_bytes = a.get("size", 0)
            size_mb = round(size_bytes / (1024 * 1024), 1) if size_bytes else 0.0
            dl_url = a.get("url") or a.get("browser_download_url") or ""
            # If GitHub API gave apiUrl instead of direct browser download url
            if not dl_url.startswith("http") and a.get("apiUrl"):
                dl_url = f"https://github.com/{GITHUB_REPO}/releases/download/{latest_tag}/{name}"

            parsed_assets.append({
                "name": name,
                "size_mb": size_mb,
                "size_bytes": size_bytes,
                "download_url": dl_url,
                "content_type": a.get("contentType") or a.get("content_type") or ""
            })

        platform_assets = self._group_assets_by_platform(parsed_assets)

        # Detect target platform
        target_plat = (client_platform or self._detect_host_platform()).lower()
        recommended = self._pick_recommended_asset(platform_assets, target_plat)

        return {
            "update_available": update_available,
            "current_version": current_ver,
            "latest_version": latest_tag if latest_tag.startswith("v") else f"v{latest_tag}",
            "release_title": raw_release.get("name", f"Release {latest_tag}"),
            "published_at": raw_release.get("publishedAt") or raw_release.get("published_at"),
            "changelog": raw_release.get("body", ""),
            "html_url": f"https://github.com/{GITHUB_REPO}/releases/tag/{latest_tag}",
            "target_platform": target_plat,
            "recommended_asset": recommended,
            "platform_assets": platform_assets,
            "all_assets": parsed_assets
        }

    def _detect_host_platform(self) -> str:
        if sys.platform == "win32":
            return "windows"
        elif sys.platform.startswith("linux"):
            return "linux"
        elif sys.platform == "darwin":
            return "macos"
        return "windows"

    def _group_assets_by_platform(self, assets: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {
            "windows": [],
            "android": [],
            "linux": [],
            "macos": [],
            "other": []
        }

        for a in assets:
            name_lower = a["name"].lower()
            if ".apk" in name_lower or "android" in name_lower:
                grouped["android"].append(a)
            elif ".exe" in name_lower or ".msi" in name_lower or "windows.ps1" in name_lower:
                grouped["windows"].append(a)
            elif ".appimage" in name_lower or ".deb" in name_lower or "linux.sh" in name_lower:
                grouped["linux"].append(a)
            elif ".dmg" in name_lower or "darwin" in name_lower or "mac" in name_lower:
                grouped["macos"].append(a)
            else:
                grouped["other"].append(a)

        return grouped

    def _pick_recommended_asset(self, grouped: Dict[str, List[Dict[str, Any]]], platform: str) -> Optional[Dict[str, Any]]:
        """Find the single most appropriate file to download for the given platform."""
        candidates = grouped.get(platform, [])
        if not candidates:
            return None

        if platform == "android":
            # Prefer Universal APK, then any APK
            for c in candidates:
                if "universal" in c["name"].lower() and c["name"].endswith(".apk"):
                    return c
            for c in candidates:
                if c["name"].endswith(".apk"):
                    return c

        elif platform == "windows":
            # Prefer official setup wizard installer (Notes-Workstation-Setup.exe)
            for c in candidates:
                if "setup.exe" in c["name"].lower():
                    return c
            # Then portable standalone EXE (Notes-Workstation-Windows.exe)
            for c in candidates:
                if "windows.exe" in c["name"].lower():
                    return c
            # Any EXE
            for c in candidates:
                if c["name"].endswith(".exe"):
                    return c

        elif platform == "linux":
            # Prefer AppImage, then deb
            for c in candidates:
                if c["name"].endswith(".AppImage"):
                    return c
            for c in candidates:
                if c["name"].endswith(".deb"):
                    return c

        return candidates[0] if candidates else None

    def _fetch_latest_release(self) -> Optional[Dict[str, Any]]:
        """Fetch release info using gh CLI or GitHub API."""
        # 1. Try GitHub CLI (handles private repos and tokens automatically)
        if shutil.which("gh"):
            try:
                out = subprocess.check_output(
                    ["gh", "release", "view", "--json", "tagName,name,body,publishedAt,assets"],
                    timeout=5.0,
                    text=True,
                    stderr=subprocess.DEVNULL
                ).strip()
                if out:
                    return json.loads(out)
            except Exception:
                pass

            # Fallback to viewing latest by list
            try:
                out = subprocess.check_output(
                    ["gh", "release", "list", "--json", "tagName,name,isLatest,publishedAt", "-L", "1"],
                    timeout=4.0,
                    text=True,
                    stderr=subprocess.DEVNULL
                ).strip()
                if out:
                    data = json.loads(out)
                    if data:
                        tag = data[0].get("tagName")
                        view_out = subprocess.check_output(
                            ["gh", "release", "view", tag, "--json", "tagName,name,body,publishedAt,assets"],
                            timeout=5.0,
                            text=True,
                            stderr=subprocess.DEVNULL
                        ).strip()
                        if view_out:
                            return json.loads(view_out)
            except Exception:
                pass

        # 2. Try direct GitHub API with env GITHUB_TOKEN or Setting
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            try:
                from app.models.models import Setting
                s = Setting.query.filter_by(key="github_token").first()
                if s and s.value:
                    token = s.value
            except Exception:
                pass

        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        headers = {
            "User-Agent": "NotesWorkstation-AutoUpdater",
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception:
            pass

        return None


updater_service = UpdaterService()
