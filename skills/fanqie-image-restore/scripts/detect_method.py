r"""
混淆方法自动检测脚本

用法:
  python detect_method.py <图片路径或文件夹>
  python detect_method.py D:\opencode-workspace\20260718

原理:
  用 local std (32x32块的局部标准差均值) 作为清晰度启发式指标。
  解混淆正确时，图像局部平滑度增加 -> local std 显著下降(通常降 2 以上)。
  检测器遍历 番茄/块/逐像素/行像素 各方法与方向、次数，输出降幅排名。

输出:
  候选列表(按 local std 降幅排序)，并给出推荐命令。
"""

import os
import sys
import argparse
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fanqie_decrypt import (
    tomato_process, block_scramble, per_pixel_scramble,
    row_pixel_scramble, picencrypt_row_scramble,
)

COMMON_KEYS = ['', '1', '123', '123456', 'fanqie', 'tomato', 'fqt', 'xiaofanqie', 'password', 'admin']
BLOCK = 32


def image_to_pixels(path):
    img = Image.open(path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    w, h = img.size
    arr = np.array(img, dtype=np.uint32)
    px = (0xFF000000 | (arr[:, :, 0] << 16) | (arr[:, :, 1] << 8) | arr[:, :, 2]).reshape(-1)
    return px, w, h


def local_std(px, w, h):
    """平均 32x32 块局部标准差 (用 R 通道)，越小越平滑"""
    H = (h // BLOCK) * BLOCK
    W = (w // BLOCK) * BLOCK
    if H == 0 or W == 0:
        return 999.0
    r = ((px >> 16) & 0xFF).astype(np.float32).reshape(h, w)[:H, :W]
    blocks = r.reshape(H // BLOCK, BLOCK, W // BLOCK, BLOCK).transpose(0, 2, 1, 3)
    blocks = blocks.reshape(-1, BLOCK * BLOCK)
    return float(blocks.std(axis=1).mean())


def pick_image(path):
    if os.path.isfile(path):
        return path
    exts = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
    files = [f for f in sorted(os.listdir(path))
             if f.lower().endswith(exts) and '_restored' not in f]
    if not files:
        print(f'未找到图片: {path}')
        sys.exit(1)
    return os.path.join(path, files[0])


def main():
    parser = argparse.ArgumentParser(description='混淆方法自动检测')
    parser.add_argument('input', help='图片路径或文件夹(取第一张检测)')
    parser.add_argument('--keys', nargs='*', default=None, help='额外尝试的字符串密钥')
    args = parser.parse_args()

    path = pick_image(args.input)
    px0, w, h = image_to_pixels(path)
    orig_std = local_std(px0, w, h)

    print(f'检测图片: {path}')
    print(f'尺寸: {w}x{h}, 原始 local std: {orig_std:.2f}')
    print()

    results = []  # (drop, label, method, key, encrypt, iterations, size)

    def add(label, method, key, encrypt, iterations, px, ww, hh):
        std = local_std(px, ww, hh)
        results.append((orig_std - std, label, method, key, encrypt, iterations, (ww, hh), std))

    # 1. 小番茄多次(两个方向)
    for direction, dname in [(False, 'decrypt'), (True, 'encrypt')]:
        p = px0.copy()
        for i in range(1, 6):
            p = tomato_process(p, w, h, 1.0, encrypt=direction)
            add(f'tomato key=1 {dname} x{i}', 'tomato', None,
                direction, i, p, w, h)

    # 2. 块/逐像素/行像素 (常见密钥，两个方向)
    keys = list(COMMON_KEYS) + [k for k in (args.keys or []) if k not in COMMON_KEYS]
    for key in keys:
        r, nw, nh = block_scramble(px0.copy(), w, h, key, encrypt=False)
        add(f'block key={key!r} decrypt', 'block', key, False, 1, r, nw, nh)
        r, nw, nh = block_scramble(px0.copy(), w, h, key, encrypt=True)
        add(f'block key={key!r} encrypt', 'block', key, True, 1, r, nw, nh)
        add(f'perpixel key={key!r} decrypt', 'perpixel', key, False, 1,
            per_pixel_scramble(px0.copy(), w, h, key, encrypt=False), w, h)
        add(f'rowpixel key={key!r} decrypt', 'rowpixel', key, False, 1,
            row_pixel_scramble(px0.copy(), w, h, key, encrypt=False), w, h)

    # 3. 输出排名
    results.sort(key=lambda r: -r[0])
    print(f'{"排名":<4}{"降幅":<8}{"结果std":<9}{"方法":<40}{"尺寸":<12}')
    print('-' * 80)
    for idx, (drop, label, method, key, encrypt, iters, size, std) in enumerate(results[:15], 1):
        mark = '  <<< 推荐' if idx == 1 and drop > 1.5 else ''
        print(f'{idx:<6}{drop:<10.2f}{std:<11.2f}{label:<42}{size[0]}x{size[1]}{mark}')

    best = results[0]
    print()
    if best[0] > 1.5:
        drop, label, method, key, encrypt, iters, size, std = best
        cmd = f'python fanqie_decrypt.py <文件夹> -o <文件夹>_restored'
        if method != 'tomato':
            cmd += f' -m {method} -k "{key}"'
        if encrypt:
            cmd += ' -e'
        if iters > 1:
            cmd += f' -n {iters}'
        print(f'推荐: {label}')
        print(f'命令: {cmd}')
    else:
        print('未发现显著改善的候选(降幅 <= 1.5)。')
        print('可能原因: 密钥不在常见列表(用 --keys 指定)、需要多次混合操作、或图片未混淆。')
        print('建议: 查看排名前几的候选输出图, 人工确认; 或向用户询问密钥。')


if __name__ == '__main__':
    main()
