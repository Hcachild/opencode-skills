#!/usr/bin/env python3
"""Decrypt WeCom (企业微信) encrypted databases on Windows.

Reads encrypted SQLite databases (message.db, session.db, user.db) and their
WAL files, decrypts using the AES-128 key, and writes plaintext snapshots.

Usage:
    python decrypt_wecom.py [--key <hex>] [--profile <id>]
"""

import argparse
import ctypes
import ctypes.wintypes as wintypes
import os
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from wecom_crypto import decrypt_database_bytes, PAGE_SIZE, database_format

PROFILES_DIR = Path(os.environ["USERPROFILE"]) / "Documents" / "WXWork"
OUTPUT_DIR = Path(os.environ["TEMP"]) / "opencode" / "wecom_decrypted"
KEY_FILE = Path(os.environ["TEMP"]) / "opencode" / "wecom_key.txt"

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
kernel32.CreateFileW.restype = wintypes.HANDLE
kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p
]
kernel32.ReadFile.restype = wintypes.BOOL
kernel32.ReadFile.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def read_locked_file(path):
    """Read entire file even if locked by another process (WeCom)."""
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3
    handle = kernel32.CreateFileW(
        wintypes.LPCWSTR(str(path)), GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None
    )
    if handle == ctypes.c_void_p(-1).value:
        return None
    try:
        result = bytearray()
        buf = (ctypes.c_ubyte * 65536)()
        bytes_read = wintypes.DWORD(0)
        while True:
            success = kernel32.ReadFile(
                handle, buf, 65536, ctypes.byref(bytes_read), None
            )
            if not success or bytes_read.value == 0:
                break
            result.extend(buf[:bytes_read.value])
        return bytes(result)
    finally:
        kernel32.CloseHandle(handle)


def decrypt_profile(profile_id, key):
    """Decrypt all databases for a profile."""
    data_dir = PROFILES_DIR / profile_id / "Data"
    out_dir = OUTPUT_DIR / profile_id
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for db_name in ["message.db", "session.db", "user.db", "message_lookup.db"]:
        db_path = data_dir / db_name
        if not db_path.exists():
            continue

        print(f"  Decrypting {db_name}...")
        db_bytes = read_locked_file(str(db_path))
        if not db_bytes:
            print(f"    Could not read {db_name}")
            continue

        fmt = database_format(db_bytes[:PAGE_SIZE])
        if fmt != "wecom-wxsqlite3-aes128":
            print(f"    Skipping {db_name}: format={fmt}")
            continue

        wal_path = Path(str(db_path) + "-wal")
        wal_bytes = None
        if wal_path.exists():
            wal_bytes = read_locked_file(str(wal_path))
            if wal_bytes:
                print(f"    WAL: {len(wal_bytes)} bytes")

        try:
            plaintext, details = decrypt_database_bytes(db_bytes, key, wal_bytes=wal_bytes)
            out_path = out_dir / db_name
            out_path.write_bytes(plaintext)
            print(f"    Decrypted: {details}")
            results[db_name] = out_path
        except Exception as e:
            print(f"    Error: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Decrypt WeCom databases")
    parser.add_argument("--key", help="Hex key string (default: read from wecom_key.txt)")
    parser.add_argument("--profile", help="Decrypt only this profile ID")
    args = parser.parse_args()

    print("=== WeCom Database Decryptor ===")

    # Get key
    if args.key:
        key = bytes.fromhex(args.key)
    elif KEY_FILE.exists():
        key = bytes.fromhex(KEY_FILE.read_text().strip())
    else:
        print(f"Error: No key provided. Run scan_key_win.py first or use --key.")
        return 1

    print(f"Key: {key.hex()}")

    # Find profiles
    profiles = []
    for d in PROFILES_DIR.iterdir():
        if d.is_dir() and d.name.isdigit():
            data_dir = d / "Data"
            if data_dir.exists() and (data_dir / "message.db").exists():
                profiles.append(d.name)

    if args.profile:
        profiles = [p for p in profiles if p == args.profile]

    print(f"\nFound {len(profiles)} profile(s): {profiles}")

    for profile_id in profiles:
        print(f"\nDecrypting profile {profile_id}...")
        db_paths = decrypt_profile(profile_id, key)
        if db_paths:
            print(f"  Successfully decrypted: {list(db_paths.keys())}")
        else:
            print(f"  No databases decrypted (key may not match this profile)")

    print(f"\nDecrypted databases saved to: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
