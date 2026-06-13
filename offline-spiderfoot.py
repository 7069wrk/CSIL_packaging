#!/usr/bin/env python3
import os
import sys
import shutil
import urllib.request
import tarfile
import subprocess
import json

# --- CONFIGURATION ---
TARGET_TOOL = "spiderfoot"
VERSION = "4.0"
DOWNLOAD_URL = f"https://github.com/smicallef/spiderfoot/archive/v{VERSION}.tar.gz"

# Directory Structure for Building the Payload Archive
BUILD_DIR = "./build_payload"
OUTPUT_DIR = "./dist_assets"
TOOL_DIR_NAME = f"{TARGET_TOOL}-{VERSION}"
WHEELS_DIR_NAME = f"{TARGET_TOOL}_wheels"

# Exact absolute paths inside the compilation sandbox
PATH_TO_TOOL = os.path.join(BUILD_DIR, TOOL_DIR_NAME)
PATH_TO_WHEELS = os.path.join(BUILD_DIR, WHEELS_DIR_NAME)
FINAL_ARCHIVE_PATH = os.path.join(OUTPUT_DIR, f"{TARGET_TOOL}_package.tar.gz")
METADATA_JSON_PATH = os.path.join(OUTPUT_DIR, f"{TARGET_TOOL}_metadata.json")

def setup_environment():
    """Cleans out old build directories and creates fresh staging areas."""
    print("[*] Initializing staging environments...")
    for directory in [BUILD_DIR, OUTPUT_DIR]:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory)

def fetch_source_code():
    """Downloads and extracts the clean release source code archive."""
    archive_target = os.path.join(BUILD_DIR, f"{TARGET_TOOL}.tar.gz")
    print(f"[*] Downloading {TARGET_TOOL} v{VERSION} source from GitHub...")
    try:
        urllib.request.urlretrieve(DOWNLOAD_URL, archive_target)
    except Exception as e:
        print(f"[-] Critical Error: Failed to fetch source archive: {e}")
        sys.exit(1)
        
    print("[*] Extracting source code archive...")
    with tarfile.open(archive_target, "r:gz") as tar:
        tar.extractall(path=BUILD_DIR)
    os.remove(archive_target) # Clean up the intermediate downloaded file

def gather_wheels():
    """Executes pip download targeting specific Linux deployment parameters."""
    requirements_path = os.path.join(PATH_TO_TOOL, "requirements.txt")
    if not os.path.exists(requirements_path):
        print("[-] Critical Error: requirements.txt not found in source payload.")
        sys.exit(1)
        
    os.makedirs(PATH_TO_WHEELS)
    print("[*] Fetching compiled Python wheels for target platform (Linux x86_64)...")
    
    # Construct the pip download command forcing compatibility constraints
    pip_cmd = [
        sys.executable, "-m", "pip", "download",
        "-r", requirements_path,
        "-d", PATH_TO_WHEELS,
        "--platform", "manylinux1_x86_64",
        "--only-binary=:all:"
    ]
    
    result = subprocess.run(pip_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("[-] Pip download failed! Standard Output / Error below:")
        print(result.stderr)
        sys.exit(1)
    print(f"[+] Successfully cached {len(os.listdir(PATH_TO_WHEELS))} dependencies locally.")

def package_assets():
    """Compresses the tool source and wheel dependencies into a single deployment tarball."""
    print(f"[*] Packaging assets into final system installer archive: {FINAL_ARCHIVE_PATH}")
    with tarfile.open(FINAL_ARCHIVE_PATH, "w:gz") as tar:
        # Add the extracted tool directories into the archive root
        tar.add(PATH_TO_TOOL, arcname=TOOL_DIR_NAME)
        tar.add(PATH_TO_WHEELS, arcname=WHEELS_DIR_NAME)

def generate_installer_metadata():
    """Generates the JSON metadata descriptor payload used by Phase 2/3 of the installer architecture."""
    print(f"[*] Emitting provisioning profile descriptor template to {METADATA_JSON_PATH}")
    
    metadata = {
        "asset_name": f"{TARGET_TOOL}_core",
        "expected_archive": f"{TARGET_TOOL}_package.tar.gz",
        "target_destination": f"/usr/share/{TARGET_TOOL}",
        "install_manifest": {
            "source_dir_name": TOOL_DIR_NAME,
            "wheels_dir_name": WHEELS_DIR_NAME,
            "requirements_file": f"/usr/share/{TARGET_TOOL}/{TOOL_DIR_NAME}/requirements.txt"
        },
        "profile_assignments": {
            "minimal": {
                "action": "purge",
                "reason": "Headless text mode preferred; scanning stack violates storage constraints."
            },
            "forensic": {
                "action": "install",
                "configuration": "headless_only"
            },
            "workstation": {
                "action": "install",
                "configuration": "full_webui"
            }
        }
    }
    
    with open(METADATA_JSON_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

def main():
    print("=== CSI LINUX ADAPTIVE FORENSIC SYSTEM: PRE-DEPLOYMENT COMPILER ===")
    setup_environment()
    fetch_source_code()
    gather_wheels()
    package_assets()
    generate_installer_metadata()
    
    # Cleanup intermediary raw build directory tree
    shutil.rmtree(BUILD_DIR)
    print("\n[+] Success! Target deployment files generated inside './dist_assets/' directory.")
    print("    - Move the package archive onto your provisioning image payload.")
    print("    - Inject the generated json schema block directly into your installer pipeline rules.")

if __name__ == "__main__":
    main()
