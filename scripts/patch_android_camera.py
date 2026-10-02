#!/usr/bin/env python3
"""
Patch the generated Android project for release permissions and signing-key rotation:
1. Adds CAMERA permission and features to AndroidManifest.xml.
2. Allows the app to connect to its HTTP LAN/Tailscale peer from Android release builds.
3. Requires Android API 28+ so releases use only the rotated signing key.
"""

import os
import re

MINIMUM_ANDROID_SDK = 28

def patch_manifest():
    manifest_path = os.path.join('src-tauri', 'gen', 'android', 'app', 'src', 'main', 'AndroidManifest.xml')
    if not os.path.exists(manifest_path):
        print(f"[Patch] Manifest not found at {manifest_path}, skipping.")
        return False

    with open(manifest_path, 'r', encoding='utf-8') as f:
        content = f.read()

    camera_perms = (
        '    <uses-permission android:name="android.permission.CAMERA" />\n'
        '    <uses-feature android:name="android.hardware.camera" android:required="false" />\n'
        '    <uses-feature android:name="android.hardware.camera.autofocus" android:required="false" />\n'
    )

    if 'android.permission.CAMERA' not in content:
        content = content.replace('<application', camera_perms + '    <application')
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[Patch] Successfully injected CAMERA permissions into {manifest_path}")
    else:
        print(f"[Patch] CAMERA permission already present in {manifest_path}")
    return True


def patch_minimum_android_sdk():
    gradle_path = os.path.join('src-tauri', 'gen', 'android', 'app', 'build.gradle.kts')
    if not os.path.exists(gradle_path):
        raise FileNotFoundError(f'Generated Android Gradle file not found: {gradle_path}')

    with open(gradle_path, 'r', encoding='utf-8') as f:
        content = f.read()

    updated, replacements = re.subn(
        r'(?m)^([ \t]*minSdk[ \t]*=[ \t]*)\d+[ \t]*$',
        rf'\g<1>{MINIMUM_ANDROID_SDK}',
        content,
        count=1,
    )
    if replacements != 1:
        raise RuntimeError(f'Could not set Android minSdk to {MINIMUM_ANDROID_SDK} in {gradle_path}')

    with open(gradle_path, 'w', encoding='utf-8') as f:
        f.write(updated)
    print(f'[Patch] Set minimum Android version to API {MINIMUM_ANDROID_SDK} (Android 9).')
    return True


def patch_release_cleartext_traffic():
    """Permit HTTP peer URLs in release builds; Tauri defaults this placeholder to false."""
    gradle_path = os.path.join('src-tauri', 'gen', 'android', 'app', 'build.gradle.kts')
    if not os.path.exists(gradle_path):
        raise FileNotFoundError(f'Generated Android Gradle file not found: {gradle_path}')

    with open(gradle_path, 'r', encoding='utf-8') as f:
        content = f.read()

    release = re.search(r'(?m)^([ \t]*)getByName\("release"\)[ \t]*\{[ \t]*$', content)
    if not release:
        raise RuntimeError(f'Could not find release build type in {gradle_path}')

    indent = release.group(1)
    closing = re.search(rf'(?m)^{re.escape(indent)}\}}[ \t]*$', content[release.end():])
    if not closing:
        raise RuntimeError(f'Could not find end of release build type in {gradle_path}')

    block_start = release.end()
    block_end = block_start + closing.start()
    block = content[block_start:block_end]
    placeholder = re.compile(r'manifestPlaceholders\["usesCleartextTraffic"\][ \t]*=[ \t]*"(?:true|false)"')
    if placeholder.search(block):
        updated_block, count = placeholder.subn('manifestPlaceholders["usesCleartextTraffic"] = "true"', block, count=1)
        if count != 1:
            raise RuntimeError(f'Could not update release HTTP policy in {gradle_path}')
    else:
        updated_block = f'\n{indent}    manifestPlaceholders["usesCleartextTraffic"] = "true"' + block

    updated = content[:block_start] + updated_block + content[block_end:]
    with open(gradle_path, 'w', encoding='utf-8') as f:
        f.write(updated)
    print('[Patch] Enabled HTTP connections for the Android release build.')
    return True


if __name__ == '__main__':
    print("[Patch] Applying Android camera permissions to AndroidManifest.xml...")
    p1 = patch_manifest()
    p2 = patch_minimum_android_sdk()
    p3 = patch_release_cleartext_traffic()
    print(f"[Patch] Done: manifest={p1}, min_sdk={p2}, release_http={p3}")
