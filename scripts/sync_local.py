#!/usr/bin/env python3
"""
================================================================================
BMS LOCAL SYNCHRONIZATION & DEPLOYMENT UTILITY
================================================================================
Synchronizes the compiled native C++ core (bms_core.exe), all Python engine
modules, and the entire anti-slop modular web dashboard (web/) directly into
C:\\ProgramData\\BMS. Ensures zero discrepancies between the development repo
and the local runtime environment.
================================================================================
"""

import os
import sys
import shutil
import hashlib

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TARGET_DIR = r"C:\ProgramData\BMS"
_TARGET_WEB = os.path.join(_TARGET_DIR, "web")

FILES_TO_DEPLOY = [
    "bms_core.exe",
    "bms_core.cpp",
    "bms_engine.py",
    "bms_ui.py",
    "bms_storage.py",
    "bms_diagnostics.py",
    "bms_service.py",
    "bms_autostart.py",
    "bms.py",
]

def hash_file(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def sync_local():
    print("================================================================================")
    print("  BMS LOCAL SYNCHRONIZATION: REPO -> C:\\ProgramData\\BMS")
    print("================================================================================")

    os.makedirs(_TARGET_DIR, exist_ok=True)
    os.makedirs(_TARGET_WEB, exist_ok=True)

    synced_count = 0
    # 1. Sync Root Binaries and Python Scripts
    for fname in FILES_TO_DEPLOY:
        src = os.path.join(_REPO_ROOT, fname)
        dst = os.path.join(_TARGET_DIR, fname)
        if not os.path.isfile(src):
            print(f"  [WARN] Source file missing: {fname}")
            continue

        src_hash = hash_file(src)
        dst_hash = hash_file(dst)
        if src_hash != dst_hash:
            shutil.copy2(src, dst)
            print(f"  [SYNC] {fname} -> {dst}")
            synced_count += 1
        else:
            print(f"  [UP-TO-DATE] {fname}")

    # 2. Sync Full web/ Hierarchy
    repo_web = os.path.join(_REPO_ROOT, "web")
    if os.path.isdir(repo_web):
        for root, dirs, files in os.walk(repo_web):
            rel_dir = os.path.relpath(root, repo_web)
            target_sub = os.path.join(_TARGET_WEB, rel_dir) if rel_dir != "." else _TARGET_WEB
            os.makedirs(target_sub, exist_ok=True)

            for file in files:
                src_f = os.path.join(root, file)
                dst_f = os.path.join(target_sub, file)
                if hash_file(src_f) != hash_file(dst_f):
                    shutil.copy2(src_f, dst_f)
                    rel_p = os.path.relpath(dst_f, _TARGET_DIR)
                    print(f"  [SYNC] {rel_p}")
                    synced_count += 1

    # 3. Verify index.html match
    repo_index = os.path.join(repo_web, "index.html")
    installed_index = os.path.join(_TARGET_WEB, "index.html")
    if hash_file(repo_index) == hash_file(installed_index):
        print("\n  [VERIFIED] Web Dashboard index.html exact cryptographic match:")
        print(f"             SHA256: {hash_file(repo_index)}")
    else:
        print("\n  [ERROR] Web Dashboard index.html mismatch!")
        sys.exit(1)

    # 4. Eradicate any legacy VBS in ProgramData
    for f in os.listdir(_TARGET_DIR):
        if f.lower().endswith(".vbs"):
            p = os.path.join(_TARGET_DIR, f)
            try:
                os.remove(p)
                print(f"  [PURGED] Legacy VBS file: {p}")
            except Exception as e:
                print(f"  [WARN] Could not remove {p}: {e}")

    print("================================================================================")
    print(f"  SYNCHRONIZATION COMPLETE: {synced_count} items updated.")
    print("================================================================================\n")

if __name__ == "__main__":
    sync_local()
