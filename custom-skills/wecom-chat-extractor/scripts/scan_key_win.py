#!/usr/bin/env python3
"""Scan WeCom (Windows) process memory for the 16-byte AES database key.

Uses Windows ReadProcessMemory API directly (no admin rights needed).
Finds WXWork.exe PID, enumerates RW memory regions, validates 16-byte
candidates against page 1 of the largest encrypted database.

Usage:
    python scan_key_win.py [--duration <seconds>]

Output:
    Prints the key hex string and saves it to %TEMP%/opencode/wecom_key.txt
"""

import argparse
import ctypes
import ctypes.wintypes as wintypes
import hashlib
import os
import struct
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

from wecom_crypto import PAGE_SIZE, verify_key, database_format
from Crypto.Cipher import AES

PROFILES_DIR = Path(os.environ["USERPROFILE"]) / "Documents" / "WXWork"
KEY_FILE = Path(os.environ["TEMP"]) / "opencode" / "wecom_key.txt"

# Windows API constants
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MEM_COMMIT = 0x00001000
PAGE_READWRITE = 0x00000004
PAGE_EXECUTE_READWRITE = 0x00000040
PAGE_WRITECOPY = 0x00000008

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t
kernel32.VirtualQueryEx.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t
]
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


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


def read_first_page(path, max_bytes=PAGE_SIZE):
    """Read the first page of a file, even if locked by another process."""
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3
    handle = kernel32.CreateFileW(
        wintypes.LPCWSTR(path), GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None
    )
    if handle == ctypes.c_void_p(-1).value:
        return None
    try:
        buf = (ctypes.c_ubyte * max_bytes)()
        bytes_read = wintypes.DWORD(0)
        success = kernel32.ReadFile(
            handle, buf, max_bytes, ctypes.byref(bytes_read), None
        )
        if not success:
            return None
        return bytes(buf[:bytes_read.value])
    finally:
        kernel32.CloseHandle(handle)


def find_wecom_pid():
    """Find WeCom process PID via tasklist."""
    result = subprocess.run(
        ['tasklist', '/FI', 'IMAGENAME eq WXWork.exe', '/FO', 'CSV', '/NH'],
        capture_output=True, text=True
    )
    for line in result.stdout.strip().split('\n'):
        parts = line.strip().strip('"').split('","')
        if len(parts) >= 2:
            try:
                return int(parts[1])
            except ValueError:
                continue
    raise SystemExit("WXWork.exe not found. Is WeCom running?")


def find_best_database():
    """Find the largest encrypted WeCom database for key validation."""
    candidates = []
    if not PROFILES_DIR.exists():
        raise SystemExit(f"WeCom data directory not found: {PROFILES_DIR}")
    for profile_dir in PROFILES_DIR.iterdir():
        if not profile_dir.is_dir() or not profile_dir.name.isdigit():
            continue
        data_dir = profile_dir / "Data"
        if not data_dir.exists():
            continue
        for db_name in ["message.db", "session.db", "user.db"]:
            db_path = data_dir / db_name
            if db_path.exists():
                size = db_path.stat().st_size
                page1 = read_first_page(str(db_path))
                if page1 and len(page1) >= PAGE_SIZE:
                    fmt = database_format(page1[:PAGE_SIZE])
                    if fmt == "wecom-wxsqlite3-aes128":
                        candidates.append((size, db_path, page1[:PAGE_SIZE]))
                        print(f"  Found: {db_path} ({size} bytes)")
    if not candidates:
        raise SystemExit("No encrypted WeCom databases found")
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0]


def scan_memory_for_key(pid, page1, duration=300):
    """Scan WeCom process memory for the 16-byte AES key."""
    handle = kernel32.OpenProcess(
        PROCESS_VM_READ | PROCESS_QUERY_INFORMATION | PROCESS_QUERY_LIMITED_INFORMATION,
        False, pid
    )
    if not handle:
        err = ctypes.get_last_error()
        raise SystemExit(f"OpenProcess failed (error={err}). Try running as Administrator.")

    print(f"  Process handle opened (PID={pid})")

    # Pre-compute validation materials for fast check
    header_fragment = page1[16:24]
    ciphertext = page1[8:16] + page1[24:]
    KEY_MATERIAL_TAG = b"sAlT"

    def lcg_step(value):
        quotient = value // 52774
        value = 40692 * (value - 52774 * quotient) - 3791 * quotient
        return value if value >= 0 else value + 2147483399

    def page_iv_bytes(page_number):
        value = page_number + 1
        output = bytearray()
        for _ in range(4):
            value = lcg_step(value)
            output.extend(struct.pack("<I", value & 0xFFFFFFFF))
        return hashlib.md5(output).digest()

    iv = page_iv_bytes(1)

    def validate_key_fast(raw_key):
        try:
            material = raw_key + struct.pack("<I", 1) + KEY_MATERIAL_TAG
            pkey = hashlib.md5(material).digest()
            cipher = AES.new(pkey, AES.MODE_CBC, iv)
            plain = cipher.decrypt(ciphertext)
            if plain[:8] == header_fragment:
                return verify_key(raw_key, page1)
            return False
        except Exception:
            return False

    mbi = MEMORY_BASIC_INFORMATION()
    address = 0
    max_addr = 0x7FFFFFFFFFFF

    regions_scanned = 0
    bytes_scanned = 0
    candidates_checked = 0
    seen_keys = set()
    found_key = None
    start_time = time.time()
    last_report = 0

    print(f"  Starting memory scan...")

    while address < max_addr:
        if time.time() - start_time > duration:
            print(f"  Timeout after {duration}s")
            break

        result = kernel32.VirtualQueryEx(
            handle, ctypes.c_void_p(address),
            ctypes.byref(mbi), ctypes.sizeof(mbi)
        )
        if result == 0:
            address += 0x1000
            continue

        region_size = mbi.RegionSize
        region_base = mbi.BaseAddress or 0
        region_prot = mbi.Protect
        region_state = mbi.State

        next_address = region_base + region_size
        if next_address <= address:
            address += 0x1000
            continue
        address = next_address

        if region_state != MEM_COMMIT:
            continue
        if region_prot not in (PAGE_READWRITE, PAGE_EXECUTE_READWRITE, PAGE_WRITECOPY):
            continue
        if region_size > 256 * 1024 * 1024:
            continue

        # Read the region in chunks
        chunk_size = min(region_size, 64 * 1024 * 1024)
        offset = 0
        while offset < region_size:
            read_size = min(chunk_size, region_size - offset)
            buf = (ctypes.c_ubyte * read_size)()
            bytes_read = ctypes.c_size_t(0)

            success = kernel32.ReadProcessMemory(
                handle,
                ctypes.c_void_p(region_base + offset),
                buf, read_size, ctypes.byref(bytes_read)
            )

            if not success or bytes_read.value == 0:
                offset += read_size
                continue

            data = bytes(buf[:bytes_read.value])
            bytes_scanned += len(data)

            for i in range(0, len(data) - 16, 8):
                candidate = data[i:i + 16]
                key_hex = candidate.hex()

                if key_hex in seen_keys:
                    continue
                seen_keys.add(key_hex)
                candidates_checked += 1

                if validate_key_fast(candidate):
                    found_key = key_hex
                    elapsed = time.time() - start_time
                    print(f"\n*** KEY FOUND: {found_key} ***")
                    print(f"    Candidates checked: {candidates_checked}")
                    print(f"    Memory scanned: {bytes_scanned // 1024 // 1024}MB")
                    print(f"    Time: {elapsed:.1f}s")
                    kernel32.CloseHandle(handle)
                    return found_key

            if bytes_scanned - last_report > 32 * 1024 * 1024:
                last_report = bytes_scanned
                elapsed = time.time() - start_time
                mb = bytes_scanned // 1024 // 1024
                print(f"    Scanned {mb}MB, {candidates_checked} candidates ({elapsed:.0f}s)")

            offset += read_size

        regions_scanned += 1

    kernel32.CloseHandle(handle)

    elapsed = time.time() - start_time
    print(f"\nScan complete: {regions_scanned} regions, "
          f"{bytes_scanned // 1024 // 1024}MB scanned, "
          f"{candidates_checked} candidates, {elapsed:.1f}s")
    return found_key


def main():
    parser = argparse.ArgumentParser(description="Scan WeCom memory for the database key")
    parser.add_argument("--duration", type=int, default=300, help="Max scan duration in seconds")
    args = parser.parse_args()

    print("=== WeCom Database Key Scanner (Windows) ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n[1] Finding encrypted databases...")
    db_size, db_path, page1 = find_best_database()
    print(f"    Using: {db_path} ({db_size} bytes)")

    print("\n[2] Finding WeCom process...")
    pid = find_wecom_pid()
    print(f"    PID: {pid}")

    print("\n[3] Scanning process memory...")
    key = scan_memory_for_key(pid, page1, args.duration)

    if key:
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        KEY_FILE.write_text(key)
        print(f"\nKey saved to: {KEY_FILE}")
        return 0
    else:
        print("\nNo key found. Try sending/receiving a message in WeCom first.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
