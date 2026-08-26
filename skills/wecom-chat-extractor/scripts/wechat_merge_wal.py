#!/usr/bin/env python3
"""Merge encrypted SQLCipher WAL of WeChat 4.x into a decrypted main DB.

Frames are validated by (a) salt chain + cumulative checksum per SQLite WAL
recovery rules, then (b) page HMAC to pick the right cipher layout. Stale
frames from previous WAL generations (file reuse) are excluded.

Usage:
    python wechat_merge_wal.py --account <wxid_dir> [--keys all_keys.json]
                               [--db-dir <db_storage>] [--output <dir>]
                               [--targets message\\message_0.db ...]
"""

import argparse
import hashlib
import hmac as hmac_mod
import json
import shutil
import struct
from pathlib import Path

from Crypto.Cipher import AES

PAGE = 4096
RESERVE = 80
IV_SZ = 16
HMAC_SZ = 64
SALT_SZ = 16
SQLITE_HDR = b"SQLite format 3\x00"
FRAME_HDR = 24
WAL_HDR = 32


def wal_checksum(data: bytes, s0: int, s1: int, big: bool):
    fmt = (">" if big else "<") + f"{len(data) // 4}I"
    words = struct.unpack(fmt, data)
    for i in range(0, len(words), 2):
        s0 = (s0 + words[i] + s1) & 0xFFFFFFFF
        s1 = (s1 + words[i + 1] + s0) & 0xFFFFFFFF
    return s0, s1


def mac_key_for(enc_key: bytes, salt: bytes) -> bytes:
    mac_salt = bytes(b ^ 0x3A for b in salt)
    return hashlib.pbkdf2_hmac("sha512", enc_key, mac_salt, 2, 32)


def hmac_ok(mkey: bytes, data: bytes, pgno: int, stored: bytes) -> bool:
    hm = hmac_mod.new(mkey, data, hashlib.sha512)
    hm.update(struct.pack("<I", pgno))
    return hmac_mod.compare_digest(hm.digest(), stored)


def decrypt_frame(payload: bytes, enc_key: bytes, mkey: bytes, pgno: int):
    """Decrypt one WAL frame payload; HMAC decides between the two layouts."""
    layouts = [
        (b"", payload[: PAGE - RESERVE], payload[PAGE - RESERVE : PAGE - RESERVE + IV_SZ]),
        (payload[:SALT_SZ], payload[SALT_SZ : PAGE - RESERVE], payload[PAGE - RESERVE : PAGE - RESERVE + IV_SZ]),
    ]
    for prefix, ct, iv in layouts:
        hmac_data = (ct + iv)[: PAGE - RESERVE + IV_SZ - len(prefix)]
        if not hmac_ok(mkey, hmac_data, pgno, payload[PAGE - HMAC_SZ :]):
            continue
        body = AES.new(enc_key, AES.MODE_CBC, iv).decrypt(ct)
        # salt-prefix layout is page 1: first 16 plaintext bytes were replaced
        # by the file salt -> restore the SQLite header
        page = (SQLITE_HDR + body) if prefix else body
        page = page + payload[PAGE - RESERVE :]
        if len(page) == PAGE:
            return page
    return None


def valid_frames(wal: bytes):
    """Yield (pgno, commit, payload) for frames passing salt+checksum chain."""
    magic, _fmt, page_size, _ckpt, hsalt1, hsalt2, hck1, hck2 = struct.unpack(">8I", wal[:WAL_HDR])
    if magic not in (0x377F0682, 0x377F0683) or page_size != PAGE:
        return
    big = magic == 0x377F0683
    s0, s1 = wal_checksum(wal[:24], 0, 0, big)
    if (s0, s1) != (hck1, hck2):
        return
    off = WAL_HDR
    while off + FRAME_HDR + PAGE <= len(wal):
        pgno, commit, fs1, fs2, fck1, fck2 = struct.unpack(">6I", wal[off : off + FRAME_HDR])
        if fs1 != hsalt1 or fs2 != hsalt2:
            break
        s0, s1 = wal_checksum(wal[off : off + 8], s0, s1, big)
        s0, s1 = wal_checksum(wal[off + FRAME_HDR : off + FRAME_HDR + PAGE], s0, s1, big)
        if (s0, s1) != (fck1, fck2):
            break
        yield pgno, commit, wal[off + FRAME_HDR : off + FRAME_HDR + PAGE]
        off += FRAME_HDR + PAGE


def merge(db_enc_main: Path, db_plain: bytes, enc_key: bytes, salt: bytes, wal_path: Path):
    """Returns (merged_bytes, frames, applied, failed, note)."""
    mkey = mac_key_for(enc_key, salt)
    note = ""
    wal = None
    if wal_path.exists():
        try:
            wal = wal_path.read_bytes()
        except OSError as e:
            note = f"WAL read failed: {e}"
    if not wal or len(wal) < WAL_HDR:
        return db_plain, 0, 0, 0, note or "no WAL"

    frames = list(valid_frames(wal))
    last_commit = -1
    for i, (_pgno, commit, _pl) in enumerate(frames):
        if commit:
            last_commit = i
    if not frames or last_commit < 0:
        # WAL likely checkpointed & reset; main DB snapshot may be stale.
        return db_plain, len(frames), 0, 0, "0 valid committed frames (WAL reset? re-decrypt main DB)"

    buf = bytearray(db_plain)
    applied = failed = 0
    for pgno, _commit, payload in frames[: last_commit + 1]:
        page = decrypt_frame(payload, enc_key, mkey, pgno)
        if page is None:
            failed += 1
            continue
        start = (pgno - 1) * PAGE
        if len(buf) < start + PAGE:
            buf.extend(b"\x00" * (start + PAGE - len(buf)))
        buf[start : start + PAGE] = page
        applied += 1
    return bytes(buf), len(frames), applied, failed, note


def find_account_dirs(root: Path):
    return [d for d in root.iterdir() if d.is_dir() and (d / "db_storage").exists()]


def main():
    ap = argparse.ArgumentParser(description="Merge WeChat 4.x SQLCipher WAL into decrypted DB")
    ap.add_argument("--root", default=str(Path.home() / "Documents" / "xwechat_files"))
    ap.add_argument("--account", help="wxid directory name (default: most recently modified)")
    ap.add_argument("--keys", default="all_keys.json")
    ap.add_argument("--decrypted", default="decrypted", help="dir with tool-decrypted main DBs")
    ap.add_argument("--output", default="merged")
    ap.add_argument("--targets", nargs="*", help="relative db paths (default: all keys entries)")
    args = ap.parse_args()

    root = Path(args.root)
    accounts = find_account_dirs(root)
    if not accounts:
        raise SystemExit(f"No account dirs with db_storage under {root}")
    if args.account:
        acct = root / args.account
        if not acct.exists():
            raise SystemExit(f"Account dir not found: {acct}")
    else:
        acct = max(accounts, key=lambda d: (d / "db_storage").stat().st_mtime)
    print(f"Account: {acct.name}")

    keys_path = Path(args.keys)
    keys = json.loads(keys_path.read_text())
    enc_root = acct / "db_storage"
    dec_root = Path(args.decrypted)
    out_root = Path(args.output)
    tmp = Path("wal_snap")
    tmp.mkdir(exist_ok=True)

    targets = args.targets or [k for k in keys if k.replace("\\", "/").endswith(".db")]
    for rel in targets:
        info = keys.get(rel) or keys.get(rel.replace("/", "\\"))
        if not info:
            print(f"  [skip] no key for {rel}")
            continue
        enc_key = bytes.fromhex(info["enc_key"])
        salt = bytes.fromhex(info["salt"])
        rel_norm = rel.replace("\\", "/")
        src_wal = enc_root / f"{rel_norm}-wal"
        snap = tmp / (rel_norm.replace("/", "_") + "-wal")
        try:
            shutil.copyfile(src_wal, snap)
        except OSError as e:
            print(f"  {rel}: WAL copy failed ({e}); using main DB only")
            snap = src_wal
        plain_rel = dec_root / rel_norm
        if not plain_rel.exists():
            print(f"  [skip] decrypted main DB missing: {plain_rel}")
            continue
        merged, nfr, applied, failed, note = merge(
            enc_root / rel_norm, plain_rel.read_bytes(), enc_key, salt, snap
        )
        out_path = out_root / rel_norm
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(merged)
        status = "OK" if failed == 0 else f"{failed} FAILED"
        print(f"  {rel}: {nfr} valid frames, {applied} applied, {status} {('- ' + note) if note else ''}")


if __name__ == "__main__":
    main()
