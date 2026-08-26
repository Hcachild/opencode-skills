#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoxCode Image Generation Script
Calls gpt-image-2 via the FoxCode proxy API to generate images.
Always use this Python script instead of PowerShell to avoid UTF-8 encoding issues.

Usage:
  python generate_image.py --prompt "你的提示词" --output "output.png"
  python generate_image.py --prompt "描述..." --output "diagram.png" --size 1536x1024
  python generate_image.py --prompt "描述..." --output "poster.png" --size 1024x1536 --quality high
"""
import argparse
import base64
import json
import os
import sys
import requests

# ── FoxCode API Configuration ──
API_KEY = "YOUR_FOXCODE_API_KEY"
API_URL = "https://code.newcli.com/codex/v1/images/generations"
MODEL = "gpt-image-2"


def generate_image(prompt: str, output_path: str, size: str = "1024x1024", quality: str = "medium") -> bool:
    """Generate an image via the FoxCode gpt-image-2 API and save to output_path."""

    # If the prompt contains Chinese, append a clarity instruction
    has_chinese = any('\u4e00' <= ch <= '\u9fff' for ch in prompt)
    if has_chinese and "必须使用中文" not in prompt:
        prompt = prompt.rstrip() + "\n\n图中所有文字必须使用中文，文字必须清晰可读，不能有乱码。配色协调，留白充足，文字居中清晰。"

    body = {
        "model": MODEL,
        "prompt": prompt,
        "n": 1,
        "size": size,
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    print(f"Generating image: {output_path}", flush=True)
    print(f"  Size: {size}", flush=True)

    try:
        resp = requests.post(API_URL, headers=headers, json=body, timeout=120)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.HTTPError as e:
        print(f"  API Error: {e}", flush=True)
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Status: {e.response.status_code}", flush=True)
            print(f"  Body: {e.response.text[:500]}", flush=True)
        return False
    except Exception as e:
        print(f"  Request Error: {e}", flush=True)
        return False

    # Ensure output directory exists
    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # Download from URL
    if data.get("data") and data["data"][0].get("url"):
        img_url = data["data"][0]["url"]
        print(f"  Downloading from {img_url[:80]}...", flush=True)
        try:
            img_resp = requests.get(img_url, timeout=120)
            img_resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(img_resp.content)
        except Exception as e:
            print(f"  Download Error: {e}", flush=True)
            return False

    # Decode from base64
    elif data.get("data") and data["data"][0].get("b64_json"):
        try:
            img_bytes = base64.b64decode(data["data"][0]["b64_json"])
            with open(output_path, "wb") as f:
                f.write(img_bytes)
        except Exception as e:
            print(f"  Decode Error: {e}", flush=True)
            return False

    else:
        print(f"  WARNING: unexpected response format: {json.dumps(data)[:300]}", flush=True)
        return False

    size_kb = os.path.getsize(output_path) // 1024
    print(f"  OK: saved {output_path} ({size_kb} KB)", flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate images via FoxCode gpt-image-2 API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_image.py --prompt "画一只猫" --output cat.png
  python generate_image.py --prompt "架构图..." --output arch.png --size 1536x1024
  python generate_image.py --prompt "海报..." --output poster.png --size 1024x1536 --quality high
        """,
    )
    parser.add_argument("--prompt", "-p", required=True, help="Image generation prompt (Chinese or English)")
    parser.add_argument("--output", "-o", required=True, help="Output file path (e.g. output.png)")
    parser.add_argument("--size", "-s", default="1024x1024",
                        choices=["1024x1024", "1536x1024", "1024x1536"],
                        help="Image size (default: 1024x1024)")
    parser.add_argument("--quality", "-q", default="medium",
                        choices=["low", "medium", "high"],
                        help="Image quality (default: medium)")

    args = parser.parse_args()

    success = generate_image(args.prompt, args.output, args.size, args.quality)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
