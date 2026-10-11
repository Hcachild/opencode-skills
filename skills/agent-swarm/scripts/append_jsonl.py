#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent-swarm 安全追加 JSONL（排他锁自旋，防并发写坏行）。

用法:
    python append_jsonl.py <path> '<json>'     # 追加一行（校验合法性）
    python append_jsonl.py --count <path>      # 打印现有行数（用于预算核对）

规则: 单行 JSON；失败（超时/非法 JSON）非零退出。
"""
from __future__ import annotations

import json
import os
import sys
import time


def append_line(path: str, obj: dict) -> None:
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False)
    lock = path + ".lock"
    for _ in range(1500):  # 最长 ~5 min
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock) > 120:
                    os.unlink(lock)
                    continue
            except OSError:
                pass
            time.sleep(0.2)
            continue
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        finally:
            os.close(fd)
            try:
                os.unlink(lock)
            except OSError:
                pass
        return
    sys.exit(f"append lock timeout: {lock}")


def count_lines(path: str) -> int:
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--count":
        print(count_lines(sys.argv[2]))
        return
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    obj = json.loads(sys.argv[2])  # 校验合法 JSON
    if not isinstance(obj, dict):
        sys.exit("json 必须是对象")
    append_line(sys.argv[1], obj)


if __name__ == "__main__":
    main()
