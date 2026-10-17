#!/usr/bin/env python3
"""ucpan-login — UC网盘扫码登录，一次性获取登录Cookie（供 ucpan-dl 使用）

特点:
  - 一次性运行：出二维码 → 手机扫码确认 → 保存Cookie → 自动退出，无任何常驻进程
  - 走官方 CAS 扫码登录接口，不需要 UC 客户端、不需要输密码
  - Cookie 默认保存到 ~/.ucpan_cookie，ucpan-dl.py 会自动检测并使用

用法:
  python ucpan-login.py [--save PATH] [--timeout 180] [--no-open]

扫码: 用手机 UC浏览器 / UC网盘 App 扫描弹出的二维码（终端也有字符版二维码）
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

import requests

UA = (
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/72.0.3626.81 Safari/537.36 SE 2.X MetaSr 1.0"
)
CLIENT_ID = "381"
CAS = "https://api.open.uc.cn/cas/ajax"
QR_TEMPLATE = (
    "https://su.uc.cn/1_n0ZCv?uc_param_str=dsdnfrpfbivesscpgimibtbmnijblauputogpintnwktprchmt"
    "&token={token}&client_id=" + CLIENT_ID + "&uc_biz_str=S%3Acustom%7CC%3Atitlebar_fix"
)
DEFAULT_COOKIE_FILE = Path.home() / ".ucpan_cookie"


def log(msg: str) -> None:
    print(msg, flush=True)


def collect_cookies(resp: requests.Response, jar: dict[str, str]) -> None:
    for sc in resp.raw.headers.getlist("Set-Cookie"):
        pair = sc.split(";", 1)[0].strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            jar[k.strip()] = v.strip()


def cookie_header(jar: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in jar.items())


def get_token(sess: requests.Session, jar: dict[str, str]) -> str:
    r = sess.get(
        f"{CAS}/getTokenForQrcodeLogin",
        params={"client_id": CLIENT_ID, "v": "1.2", "request_id": str(int(time.time() * 1000))},
        headers={"User-Agent": UA, "Referer": "https://drive.uc.cn"},
        timeout=20,
    )
    collect_cookies(r, jar)
    body = r.json()
    token = body.get("data", {}).get("members", {}).get("token")
    if not token:
        raise SystemExit(f"获取二维码token失败: {str(body)[:200]}")
    return token


def poll_ticket(sess: requests.Session, token: str, timeout_s: int) -> str | None:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        r = sess.get(
            f"{CAS}/getServiceTicketByQrcodeToken",
            params={
                "__t": int(time.time() * 1000),
                "token": token,
                "client_id": CLIENT_ID,
                "v": "1.2",
                "request_id": str(int(time.time() * 1000)),
            },
            headers={"User-Agent": UA, "Referer": "https://drive.uc.cn"},
            timeout=20,
        )
        body = r.json()
        st = body.get("status")
        if st == 2000000:
            return body.get("data", {}).get("members", {}).get("service_ticket")
        if st == 50004002:
            return None
        left = int(timeout_s - (time.time() - t0))
        log(f"  [等待] 尚未扫码/确认… 剩余 {left}s")
        time.sleep(2)
    return None


def get_full_cookie(sess: requests.Session, ticket: str, jar: dict[str, str]) -> str:
    r = sess.get(
        "https://drive.uc.cn/account/info",
        params={"st": ticket, "fr": "pc", "platform": "pc"},
        headers={"User-Agent": UA, "Cookie": cookie_header(jar), "Referer": "https://drive.uc.cn"},
        timeout=20,
    )
    collect_cookies(r, jar)
    r = sess.post(
        "https://pc-api.uc.cn/1/clouddrive/transfer/upload/pdir?pr=UCBrowser&fr=pc",
        data=b"{}",
        headers={
            "User-Agent": UA,
            "Cookie": cookie_header(jar),
            "Content-Type": "application/json",
            "Referer": "https://drive.uc.cn",
        },
        timeout=20,
    )
    collect_cookies(r, jar)
    return cookie_header(jar)


def whoami(cookie: str) -> str | None:
    try:
        r = requests.post(
            "https://fast.uc.cn/api/info?fr=pc&pr=UCBrowser",
            json={"st": ""},
            headers={
                "Cookie": cookie,
                "User-Agent": UA,
                "Content-Type": "application/json",
                "x-biz-retry": "0",
            },
            timeout=15,
        )
        d = r.json()
        if d.get("success") and (d.get("data") or {}).get("nickname"):
            return d["data"]["nickname"]
    except Exception:
        pass
    return None


def show_qr(url: str, open_png: bool) -> Path:
    import qrcode

    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    png_path = Path(tempfile.gettempdir()) / "ucpan_login_qr.png"
    qr.make_image().save(png_path)
    log(f"  [二维码图片] {png_path}")
    if open_png:
        try:
            os.startfile(png_path)  # type: ignore[attr-defined]
        except Exception:
            pass
    try:
        qr.print_ascii(invert=True)
    except Exception:
        pass
    return png_path


def main() -> None:
    ap = argparse.ArgumentParser(description="UC网盘扫码登录（一次性获取Cookie）")
    ap.add_argument("--save", default=str(DEFAULT_COOKIE_FILE), help="Cookie保存路径 (默认 ~/.ucpan_cookie)")
    ap.add_argument("--timeout", type=int, default=180, help="等待扫码的秒数 (默认180)")
    ap.add_argument("--no-open", action="store_true", help="不自动打开二维码图片")
    args = ap.parse_args()

    sess = requests.Session()
    jar: dict[str, str] = {}
    png_path: Path | None = None
    try:
        for round_no in range(1, 4):
            log(f"[1/3] 获取二维码 token (第{round_no}次)…")
            token = get_token(sess, jar)
            url = QR_TEMPLATE.format(token=token)
            log("[2/3] 请用手机 UC浏览器 或 UC网盘 App 扫码，并在手机上点确认：")
            png_path = show_qr(url, not args.no_open)

            log(f"[3/3] 等待扫码（最长 {args.timeout}s）…")
            ticket = poll_ticket(sess, token, args.timeout)
            if ticket:
                break
            log("  [warn] 二维码已过期，重新生成…")
        else:
            raise SystemExit("多次二维码均未扫码成功，已退出。")

        cookie = get_full_cookie(sess, ticket, jar)
        nick = whoami(cookie)
        if not nick:
            raise SystemExit("登录流程完成但凭证校验失败，请重试。")

        save_path = Path(args.save)
        save_path.write_text(cookie, encoding="utf-8")
        log("")
        log(f"[完成] 登录成功！账号昵称: {nick}")
        log(f"[完成] Cookie 已保存: {save_path}")
        log(f"       {cookie[:80]}…（共 {len(cookie)} 字符）")
        log("")
        log("有效期通常数周；失效后重新运行本脚本即可。现在可以：")
        log('  python ucpan-dl.py "<分享链接>" --out DIR')
    finally:
        if png_path and png_path.exists():
            png_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
