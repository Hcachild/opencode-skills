#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent-swarm 重任务物理槽（默认 heavy_01..NN，防重计算并发过载）。

acquire: 依次尝试独占创建 <locks-dir>/heavy_XX.lock（内容 `agent|iso|eta_min`）；
         全部被占则等待重试（--wait-min，默认 30 分钟）；超过 --stale-min（默认 150）
         的锁视为死代理残留，自动改名 .stale 后重抢。
release: 删除自己持有的锁。
status : 打印当前槽占用。

用法:
    python heavy_lock.py acquire --agent <agent_id> --locks-dir <swarm_dir>/locks [--slots 16] [--eta 180] [--wait-min 30]
    python heavy_lock.py release --agent <agent_id> --locks-dir <swarm_dir>/locks [--slots 16]
    python heavy_lock.py status  --locks-dir <swarm_dir>/locks [--slots 16]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone

STALE_MIN_DEFAULT = 150.0
SLOTS_DEFAULT = 8


def now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def lock_paths(locks_dir: str, slots: int) -> list[str]:
    return [os.path.join(locks_dir, f"heavy_{i:02d}.lock") for i in range(1, slots + 1)]


def sweep_stale(locks_dir: str, slots: int, stale_min: float) -> None:
    for f in lock_paths(locks_dir, slots):
        if not os.path.exists(f):
            continue
        try:
            age_min = (time.time() - os.path.getmtime(f)) / 60.0
        except OSError:
            continue
        if age_min > stale_min:
            stale = f + f".stale-{int(time.time())}"
            try:
                os.replace(f, stale)
                print(f"  stale swept: {os.path.basename(f)} (age {age_min:.0f} min)")
            except OSError:
                pass


def cmd_acquire(a: argparse.Namespace) -> int:
    os.makedirs(a.locks_dir, exist_ok=True)
    deadline = time.time() + a.wait_min * 60.0
    start = time.time()
    while True:
        sweep_stale(a.locks_dir, a.slots, a.stale_min)
        for f in lock_paths(a.locks_dir, a.slots):
            try:
                fd = os.open(f, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                continue
            os.write(fd, f"{a.agent}|{now_iso()}|{a.eta}".encode("utf-8"))
            os.close(fd)
            waited = (time.time() - start) / 60.0
            print(f"ACQUIRED {os.path.basename(f)} (waited {waited:.1f} min)")
            return 0
        if time.time() >= deadline:
            print(f"BUSY: all {a.slots} heavy slots occupied after {a.wait_min} min; "
                  f"retry later or do light work first（不训练/不筛查）")
            return 2
        time.sleep(30)
        print("  all busy, waiting 30s ...", flush=True)


def cmd_release(a: argparse.Namespace) -> int:
    released = 0
    for f in lock_paths(a.locks_dir, a.slots):
        if not os.path.exists(f):
            continue
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read().strip()
        except OSError:
            continue
        if content.split("|")[0] == a.agent:
            try:
                os.unlink(f)
                print(f"RELEASED {os.path.basename(f)}")
                released += 1
            except OSError as e:
                print(f"  failed to release {f}: {e}")
    if released == 0:
        print(f"no lock held by {a.agent}")
    return 0


def cmd_status(a: argparse.Namespace) -> int:
    for f in lock_paths(a.locks_dir, a.slots):
        state = "free"
        content = ""
        if os.path.exists(f):
            try:
                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read().strip()
            except OSError:
                pass
            state = "HELD"
        print(f"{os.path.basename(f)}: {state} {content}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["acquire", "release", "status"])
    ap.add_argument("--agent", default="")
    ap.add_argument("--eta", type=int, default=180, help="预计占用分钟数（仅供参考）")
    ap.add_argument("--wait-min", type=float, default=30.0, help="无槽时最长等待分钟数")
    ap.add_argument("--slots", type=int, default=SLOTS_DEFAULT, help="物理槽总数（按机器核数定）")
    ap.add_argument("--stale-min", type=float, default=STALE_MIN_DEFAULT,
                    help="锁超过该分钟数视为死代理残留")
    ap.add_argument("--locks-dir", required=True, help="如 <swarm_dir>/locks")
    a = ap.parse_args()
    if a.cmd in ("acquire", "release") and not a.agent:
        sys.exit("--agent 必填")
    if a.slots < 1:
        sys.exit("--slots 必须 >=1")
    sys.exit({"acquire": cmd_acquire, "release": cmd_release, "status": cmd_status}[a.cmd](a))


if __name__ == "__main__":
    main()
