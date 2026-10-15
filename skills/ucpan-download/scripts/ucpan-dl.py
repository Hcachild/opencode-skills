#!/usr/bin/env python3
"""ucpan-dl — UC网盘分享链接多线程下载器（免登录可用）

特性:
  - 匿名解析分享链接（drive.uc.cn / fast.uc.cn），无需客户端、无需登录
  - 递归扫描目录树，保留原目录结构
  - 单文件多连接分块并发 + 多文件并行，突破单连接 ~100KB/s 限速
  - 断点续传（分块级）+ 直链过期自动刷新
  - 支持提取码分享；如匿名受限可传 --cookie

用法:
  python ucpan-dl.py <分享链接> [--out DIR] [--pwd 提取码] [--cookie "xx=yy"]
                       [--jobs 3] [--chunks 16] [--only 正则] [--list]

示例:
  python ucpan-dl.py "https://drive.uc.cn/s/ca97d20a92444?public=1#/list/share" --out .\out
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath

import requests

API = "https://pc-api.uc.cn/1/clouddrive"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
API_HEADERS = {
    "User-Agent": UA,
    "Content-Type": "application/json",
    "Origin": "https://drive.uc.cn",
    "Referer": "https://drive.uc.cn/",
    "x-biz-retry": "0",
}
DL_HEADERS = {"User-Agent": UA}
URL_SAFETY_MARGIN = 120
BATCH = 50
PAGE = 200
CHUNK_MIN = 512 * 1024


def log(msg: str) -> None:
    print(msg, flush=True)


def human(n: float) -> str:
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def parse_share_id(url: str) -> str:
    m = re.search(r"/s/([0-9a-zA-Z]+)", url)
    if not m:
        raise SystemExit(f"无法从链接中解析分享ID: {url}")
    return m.group(1)


class TokenExpired(Exception):
    pass


class UcPan:
    def __init__(self, share_id: str, passcode: str = "", cookie: str = ""):
        self.share_id = share_id
        self.passcode = passcode
        self.sess = requests.Session()
        self.sess.headers.update(API_HEADERS)
        self.sess.headers["Referer"] = f"https://drive.uc.cn/s/{share_id}"
        if cookie:
            self.sess.headers["Cookie"] = cookie
        self.stoken = ""
        self.title = ""

    def _post(self, path: str, body: dict, retry: int = 3) -> dict:
        url = f"{API}{path}?entry=ft&fr=pc&pr=UCBrowser"
        last_err = ""
        for i in range(retry):
            try:
                r = self.sess.post(url, data=json.dumps(body), timeout=20)
                data = r.json()
                if data.get("status") == 200:
                    return data
                if data.get("code") == 41020:
                    raise TokenExpired(data.get("message", ""))
                last_err = f"status={data.get('status')} code={data.get('code')} msg={data.get('message')}"
            except requests.RequestException as e:
                last_err = str(e)
            time.sleep(1 + i)
        raise SystemExit(f"API请求失败: {path} ({last_err})")

    def _get(self, path: str, params: dict, retry: int = 3) -> dict:
        url = f"{API}{path}"
        last_err = ""
        for i in range(retry):
            try:
                r = self.sess.get(url, params=params, timeout=20)
                data = r.json()
                if data.get("status") == 200:
                    return data
                last_err = f"status={data.get('status')} code={data.get('code')} msg={data.get('message')}"
            except requests.RequestException as e:
                last_err = str(e)
            time.sleep(1 + i)
        raise SystemExit(f"API请求失败: {path} ({last_err})")

    def token(self) -> None:
        data = self._post(
            "/share/sharepage/token",
            {"pwd_id": self.share_id, "passcode": self.passcode, "share_for_transfer": True},
        )
        self.stoken = data["data"]["stoken"]
        self.title = data["data"].get("title", "")
        log(f"[ok] token 获取成功 | 分享标题: {self.title}")

    def list_dir(self, pdir_fid: str) -> list[dict]:
        out: list[dict] = []
        page = 1
        while True:
            params = {
                "entry": "ft",
                "pwd_id": self.share_id,
                "pdir_fid": pdir_fid,
                "fetch_file_list": "1",
                "passcode": self.passcode,
                "_page": str(page),
                "_size": str(PAGE),
                "_fetch_total": "1",
                "_fetch_task": "1",
                "_fetch_share": "1",
                "_sort": "file_type:asc,file_name:asc",
                "stoken": self.stoken,
                "fr": "pc",
                "pr": "UCBrowser",
            }
            data = self._get("/transfer_share/detail", params)
            items = data["data"]["list"]
            out.extend(items)
            total = data["data"].get("total", 0)
            if len(out) >= total or len(items) < PAGE:
                break
            page += 1
        return out

    def walk(self) -> list[dict]:
        files: list[dict] = []

        def rec(fid: str, rel: str) -> None:
            for it in self.list_dir(fid):
                name = it["file_name"]
                if it.get("dir"):
                    rec(it["fid"], f"{rel}/{name}")
                else:
                    it["_rel"] = f"{rel}/{name}"
                    it["_pdir"] = fid
                    files.append(it)

        rec("0", ".")
        return files

    def refresh_single(self, meta: dict) -> tuple[str, int] | None:
        pdir = meta.get("_pdir")
        if not pdir:
            return None
        for it in self.list_dir(pdir):
            if it.get("fid") == meta["fid"] and it.get("file"):
                meta["share_fid_token"] = it["share_fid_token"]
                urls = self.download_urls([meta])
                return urls.get(meta["fid"])
        return None

    def download_urls(self, files: list[dict]) -> dict[str, tuple[str, int]]:
        res: dict[str, tuple[str, int]] = {}
        for i in range(0, len(files), BATCH):
            batch = files[i : i + BATCH]
            body = {
                "fids": [f["fid"] for f in batch],
                "fids_token": [f["share_fid_token"] for f in batch],
                "pwd_id": self.share_id,
                "stoken": self.stoken,
            }
            try:
                data = self._post("/file/download", body)
            except TokenExpired:
                log(f"  [warn] 批次 {i // BATCH + 1} token 过期，逐个刷新…")
                for f in batch:
                    fresh = self.refresh_single(f)
                    if fresh:
                        res[f["fid"]] = fresh
                continue
            got = set()
            for d in data["data"]:
                fid = d.get("fid")
                url = d.get("download_url", "")
                if not url:
                    continue
                m = re.search(r"[?&]Expires=(\d+)", url)
                exp = int(m.group(1)) if m else int(time.time()) + 3600
                res[fid] = (url, exp)
                got.add(fid)
            missing = [f for f in batch if f["fid"] not in got]
            if missing:
                log(
                    f"  [warn] {len(missing)} 个文件未返回直链（可能需登录Cookie）: "
                    + ", ".join(m["_rel"] for m in missing[:3])
                    + (" …" if len(missing) > 3 else "")
                )
        return res


class Progress:
    def __init__(self, total_files: int, total_bytes: int):
        self.total_files = total_files
        self.total_bytes = total_bytes
        self.done_files = 0
        self.done_bytes = 0
        self.lock = threading.Lock()
        self.t0 = time.time()
        self.t_print = 0.0

    def add_bytes(self, n: int) -> None:
        with self.lock:
            self.done_bytes += n
            now = time.time()
            if now - self.t_print >= 2:
                self.t_print = now
                self._print_locked()

    def file_done(self) -> None:
        with self.lock:
            self.done_files += 1
            self._print_locked()

    def _print_locked(self) -> None:
        speed = self.done_bytes / max(1e-6, time.time() - self.t0)
        pct = 100 * self.done_bytes / max(1, self.total_bytes)
        log(
            f"    >> [{self.done_files}/{self.total_files}] {pct:5.1f}% | "
            f"{human(self.done_bytes)}/{human(self.total_bytes)} @ {human(speed)}/s"
        )


def _refresh_url(pan: UcPan, meta: dict, refresh_lock: threading.Lock, url: str, expires: int):
    with refresh_lock:
        try:
            fresh = pan.download_urls([meta])
        except Exception:
            fresh = {}
        if meta["fid"] in fresh:
            return fresh[meta["fid"]]
        try:
            fresh2 = pan.refresh_single(meta)
        except Exception:
            fresh2 = None
        if fresh2:
            return fresh2
    return url, expires


def _download_chunk(pan, meta, url, expires, refresh_lock, start, end, part: Path) -> int | None:
    need = end - start + 1
    for attempt in range(6):
        if expires - time.time() < URL_SAFETY_MARGIN:
            url, expires = _refresh_url(pan, meta, refresh_lock, url, expires)
        hh = dict(DL_HEADERS)
        hh["Range"] = f"bytes={start}-{end}"
        try:
            r = requests.get(url, headers=hh, stream=True, timeout=(15, 120))
        except requests.RequestException:
            time.sleep(1 + attempt)
            continue
        if r.status_code == 403:
            r.close()
            url, expires = _refresh_url(pan, meta, refresh_lock, url, expires)
            continue
        if r.status_code not in (200, 206):
            r.close()
            time.sleep(1 + attempt)
            continue
        if r.status_code == 200:
            r.close()
            return -1
        got = 0
        try:
            with open(part, "wb") as fh:
                for c in r.iter_content(1024 * 256):
                    if c:
                        fh.write(c)
                        got += len(c)
        except requests.RequestException:
            pass
        finally:
            r.close()
        if got == need:
            return got
        if part.exists():
            part.unlink(missing_ok=True)
        time.sleep(1 + attempt)
    return None


def _download_single(pan, meta, url, expires, refresh_lock, part: Path, progress: Progress) -> bool:
    size = meta.get("size", 0)
    for attempt in range(6):
        if expires - time.time() < URL_SAFETY_MARGIN:
            url, expires = _refresh_url(pan, meta, refresh_lock, url, expires)
        pos = part.stat().st_size if part.exists() else 0
        hh = dict(DL_HEADERS)
        if pos:
            hh["Range"] = f"bytes={pos}-"
        try:
            r = requests.get(url, headers=hh, stream=True, timeout=(15, 120))
        except requests.RequestException:
            time.sleep(1 + attempt)
            continue
        if r.status_code == 403:
            r.close()
            url, expires = _refresh_url(pan, meta, refresh_lock, url, expires)
            continue
        if r.status_code not in (200, 206):
            r.close()
            time.sleep(1 + attempt)
            continue
        if pos and r.status_code == 200:
            pos = 0
            mode = "wb"
        else:
            mode = "ab"
        got = pos
        try:
            with open(part, mode) as fh:
                for c in r.iter_content(1024 * 256):
                    if c:
                        fh.write(c)
                        got += len(c)
        except requests.RequestException:
            pass
        finally:
            r.close()
        if size and got < size:
            time.sleep(1)
            continue
        return True
    return False


def fetch_one(
    pan: UcPan,
    meta: dict,
    url: str,
    expires: int,
    dest: Path,
    progress: Progress,
    refresh_lock: threading.Lock,
    chunks: int,
) -> bool:
    rel = meta["_rel"]
    size = int(meta.get("size", 0) or 0)
    dest.parent.mkdir(parents=True, exist_ok=True)
    counted = 0

    if dest.exists() and (size <= 0 or dest.stat().st_size == size):
        log(f"  [skip] {rel}")
        progress.add_bytes(size)
        progress.file_done()
        return True

    if size <= 0 or chunks <= 1:
        part = dest.with_name(dest.name + ".part")
        ok = _download_single(pan, meta, url, expires, refresh_lock, part, progress)
        if ok:
            part.replace(dest)
            log(f"  [done] {rel} {human(dest.stat().st_size)}")
            progress.add_bytes(dest.stat().st_size - counted)
            progress.file_done()
        return ok

    n = min(chunks, max(1, (size + CHUNK_MIN - 1) // CHUNK_MIN))
    bounds = [(size * i // n, size * (i + 1) // n - 1) for i in range(n)]
    parts = [dest.with_name(dest.name + f".part{i}") for i in range(n)]

    todo = []
    for i, (start, end) in enumerate(bounds):
        pf = parts[i]
        if pf.exists() and pf.stat().st_size == end - start + 1:
            counted += end - start + 1
        else:
            todo.append(i)
    progress.add_bytes(counted)

    fallback_single = False
    if todo:
        with ThreadPoolExecutor(max_workers=min(len(todo), chunks)) as pool:
            futs = {
                pool.submit(_download_chunk, pan, meta, url, expires, refresh_lock, bounds[i][0], bounds[i][1], parts[i]): i
                for i in todo
            }
            for fut in as_completed(futs):
                res = fut.result()
                if res == -1:
                    fallback_single = True
                elif res:
                    counted += res
                    progress.add_bytes(res)

    if fallback_single or any(not p.exists() or p.stat().st_size != bounds[i][1] - bounds[i][0] + 1 for i, p in enumerate(parts)):
        if fallback_single:
            for p in parts:
                p.unlink(missing_ok=True)
            part = dest.with_name(dest.name + ".part")
            ok = _download_single(pan, meta, url, expires, refresh_lock, part, progress)
            if ok:
                part.replace(dest)
                log(f"  [done] {rel} {human(dest.stat().st_size)}")
                progress.add_bytes(dest.stat().st_size - counted)
                progress.file_done()
                return True
        return False

    t0 = time.time()
    with open(dest, "wb") as out:
        for p in parts:
            with open(p, "rb") as fh:
                while True:
                    buf = fh.read(1024 * 1024)
                    if not buf:
                        break
                    out.write(buf)
    for p in parts:
        p.unlink(missing_ok=True)
    dt = max(1e-6, time.time() - t0)
    if size and dest.stat().st_size != size:
        log(f"  [fail] {rel} 合并后大小不符")
        return False
    log(f"  [done] {rel} {human(size)}")
    progress.file_done()
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="UC网盘分享链接多线程下载器")
    ap.add_argument("url", help="分享链接，如 https://drive.uc.cn/s/xxxx")
    ap.add_argument("--out", default="ucpan-out", help="保存目录 (默认 ./ucpan-out)")
    ap.add_argument("--pwd", default="", help="提取码（如有）")
    ap.add_argument("--cookie", default="", help="登录Cookie（可选）")
    ap.add_argument("--jobs", type=int, default=3, help="并发下载文件数 (默认3)")
    ap.add_argument("--chunks", type=int, default=16, help="单文件分块并发数 (默认16)")
    ap.add_argument("--only", default="", help="只下载路径匹配该正则的文件")
    ap.add_argument("--list", action="store_true", help="仅列出文件不下载")
    args = ap.parse_args()

    share_id = parse_share_id(args.url)
    pan = UcPan(share_id, args.pwd, args.cookie)
    pan.token()

    out_dir = Path(args.out)
    index_file = out_dir / ".ucpan_index.json"
    files: list[dict] = []
    if index_file.exists():
        try:
            files = json.loads(index_file.read_text(encoding="utf-8"))
            log(f"[ok] 复用索引缓存: {len(files)} 个文件")
        except Exception:
            files = []

    if not files:
        log("[..] 扫描目录树…")
        files = pan.walk()
        out_dir.mkdir(parents=True, exist_ok=True)
        index_file.write_text(json.dumps(files, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"[ok] 扫描完成: {len(files)} 个文件，索引已存 {index_file}")
    elif "_pdir" not in files[0] or not pan.download_urls(files[:1]):
        log("[..] 索引已过期或缺父目录信息，重新扫描…")
        files = pan.walk()
        index_file.write_text(json.dumps(files, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"[ok] 重新扫描完成: {len(files)} 个文件")

    if args.only:
        rx = re.compile(args.only)
        files = [f for f in files if rx.search(f["_rel"])]
        log(f"[ok] 过滤后: {len(files)} 个文件")

    total_bytes = sum(int(f.get("size", 0) or 0) for f in files)
    log(f"[ok] 共 {len(files)} 个文件, {human(total_bytes)}")

    if args.list:
        for f in files:
            print(f"{human(int(f.get('size', 0) or 0)):>10}  {f['_rel']}")
        return

    log("[..] 申请下载直链…")
    urls = pan.download_urls(files)
    log(f"[ok] 拿到 {len(urls)}/{len(files)} 条直链")

    todo = [f for f in files if f["fid"] in urls]
    progress = Progress(len(todo), sum(int(f.get("size", 0) or 0) for f in todo))
    refresh_lock = threading.Lock()
    failed: list[str] = []
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futs = {}
        for f in todo:
            url, exp = urls[f["fid"]]
            dest = out_dir / PurePosixPath(f["_rel"].lstrip("./"))
            futs[pool.submit(fetch_one, pan, f, url, exp, dest, progress, refresh_lock, args.chunks)] = f["_rel"]
        for fut in as_completed(futs):
            if not fut.result():
                failed.append(futs[fut])

    dt = time.time() - t0
    log(
        f"\n[完成] 成功 {len(todo) - len(failed)}/{len(todo)}，耗时 {dt:.0f}s，"
        f"平均 {human(progress.done_bytes / max(1, dt))}/s"
    )
    if failed:
        log("失败列表:")
        for x in failed:
            log(f"  - {x}")
        sys.exit(1)


if __name__ == "__main__":
    main()
