r"""
小番茄图片混淆 - 还原脚本 (numpy 向量化加速版)
基于 Gilbert 空间填充曲线算法 (TomatoScramble)
源码参考: https://github.com/jiarandiana0307/PicEncrypt

用法:
  python fanqie_decrypt.py <图片路径或文件夹>
  python fanqie_decrypt.py D:\opencode-workspace\20260701
  python fanqie_decrypt.py D:\opencode-workspace\20260701\xxx.jpg

说明:
  - 默认使用 key=1 (网站/APP默认值) 进行解混淆
  - 如果图片经过多次混淆，需要运行多次解混淆 (-n)
  - 也支持块混淆/逐像素混淆/行像素混淆(需要密钥, -m -k)
  - 部分图片是被"解混淆"方向处理过的，需用 -e 混淆方向还原
"""

import os
import sys
import math
import hashlib
import argparse
import numpy as np
from PIL import Image


# ============================================================
# 1. Gilbert 曲线生成 (TomatoScramble 核心)
# ============================================================

def gilbert2d(width, height):
    """生成 Gilbert 空间填充曲线的位置数组"""
    positions = [0] * (width * height)
    pos = [0]  # 用列表模拟指针

    def generate2d(x, y, ax, ay, bx, by):
        w = abs(ax + ay)
        h = abs(bx + by)
        dax = (1 if ax > 0 else (-1 if ax < 0 else 0))
        day = (1 if ay > 0 else (-1 if ay < 0 else 0))
        dbx = (1 if bx > 0 else (-1 if bx < 0 else 0))
        dby = (1 if by > 0 else (-1 if by < 0 else 0))

        if h == 1:
            for i in range(w):
                positions[pos[0]] = x + y * width
                pos[0] += 1
                x += dax
                y += day
            return

        if w == 1:
            for i in range(h):
                positions[pos[0]] = x + y * width
                pos[0] += 1
                x += dbx
                y += dby
            return

        ax2 = ax // 2
        ay2 = ay // 2
        bx2 = bx // 2
        by2 = by // 2
        w2 = abs(ax2 + ay2)
        h2 = abs(bx2 + by2)

        if 2 * w > 3 * h:
            if (w2 & 1) == 1 and w > 2:
                ax2 += dax
                ay2 += day
            generate2d(x, y, ax2, ay2, bx, by)
            generate2d(x + ax2, y + ay2, ax - ax2, ay - ay2, bx, by)
        else:
            if (h2 & 1) == 1 and h > 2:
                bx2 += dbx
                by2 += dby
            generate2d(x, y, bx2, by2, ax2, ay2)
            generate2d(x + bx2, y + by2, ax, ay, bx - bx2, by - by2)
            generate2d(
                x + (ax - dax) + (bx2 - dbx),
                y + (ay - day) + (by2 - dby),
                -bx2, -by2, -(ax - ax2), -(ay - ay2)
            )

    if width >= height:
        generate2d(0, 0, width, 0, 0, height)
    else:
        generate2d(0, 0, 0, height, width, 0)

    return positions


# ============================================================
# 2. 小番茄算法 (TomatoScramble, 向量化)
# ============================================================

def tomato_process(pixels, width, height, key=1.0, encrypt=False):
    """
    小番茄混淆/解混淆
    encrypt=True  -> 混淆 (加密)
    encrypt=False -> 解混淆 (解密)
    """
    pixel_count = width * height
    offset = int(round((math.sqrt(5) - 1) / 2 * pixel_count * key))
    loop_position = pixel_count - offset

    pos = np.array(gilbert2d(width, height), dtype=np.intp)
    new_pixels = np.zeros(pixel_count, dtype=np.uint32)

    if encrypt:
        # newPixels[positions[i+offset]] = pixels[positions[i]]
        new_pixels[pos[offset:]] = pixels[pos[:loop_position]]
        new_pixels[pos[:offset]] = pixels[pos[loop_position:]]
    else:
        # newPixels[positions[i]] = pixels[positions[i+offset]]
        new_pixels[pos[:loop_position]] = pixels[pos[offset:]]
        new_pixels[pos[loop_position:]] = pixels[pos[:offset]]

    return new_pixels


# ============================================================
# 3. MD5 shuffle (BlockScramble / PerPixelScramble / RowPixelScramble)
# ============================================================

def md5_shuffle(length, key):
    """基于 MD5 的 Fisher-Yates shuffle，与 Java BasePixelScramble.shuffle 一致"""
    arr = list(range(length))
    for i in range(length - 1, 0, -1):
        md5 = hashlib.md5((key + str(i)).encode()).digest()
        hex_str = md5.hex()
        # Java: Integer.parseInt(hex.substring(0,7), 16) % (i+1)
        rand = int(hex_str[:7], 16) % (i + 1)
        arr[rand], arr[i] = arr[i], arr[rand]
    return arr


# ============================================================
# 4. 块混淆 (BlockScramble, 向量化)
# ============================================================

def block_scramble(pixels, width, height, key, x_block=32, y_block=32, encrypt=False):
    xa = np.array(md5_shuffle(x_block, key), dtype=np.intp)
    ya = np.array(md5_shuffle(y_block, key), dtype=np.intp)

    new_width = width if width % x_block == 0 else width + x_block - width % x_block
    new_height = height if height % y_block == 0 else height + y_block - height % y_block
    bw = new_width // x_block
    bh = new_height // y_block

    i2 = np.arange(new_width, dtype=np.intp)[None, :]
    j2 = np.arange(new_height, dtype=np.intp)[:, None]

    n1 = j2
    m1 = (xa[(n1 // bh) % x_block] * bw + i2) % new_width
    m2 = xa[m1 // bw] * bw + m1 % bw
    n2 = (ya[(m2 // bw) % y_block] * bh + n1) % new_height
    n3 = ya[n2 // bh] * bh + n2 % bh

    new_pixels = np.zeros(new_width * new_height, dtype=np.uint32)
    if encrypt:
        srcid = (m2 % width) + (n3 % height) * width
        return pixels[srcid.flatten()], new_width, new_height
    else:
        id_arr = (m2 + n3 * new_width).flatten()
        srcv = pixels[(i2 % width) + (j2 % height) * width]
        new_pixels[id_arr] = srcv.flatten()
        return new_pixels, new_width, new_height


# ============================================================
# 5. 逐像素混淆 (PerPixelScramble, 向量化)
# ============================================================

def per_pixel_scramble(pixels, width, height, key, encrypt=False):
    xa = np.array(md5_shuffle(width, key), dtype=np.intp)
    ya = np.array(md5_shuffle(height, key), dtype=np.intp)

    i2 = np.arange(width, dtype=np.intp)[None, :]
    j2 = np.arange(height, dtype=np.intp)[:, None]
    M = xa[(xa[j2 % width] + i2) % width]
    N = ya[(ya[M % height] + j2) % height]
    S2 = (N * width + M).flatten()

    new_pixels = np.zeros(width * height, dtype=np.uint32)
    if encrypt:
        return pixels[S2]
    else:
        new_pixels[S2] = pixels
        return new_pixels


# ============================================================
# 6. 行像素混淆 (RowPixelScramble, 向量化)
# ============================================================

def row_pixel_scramble(pixels, width, height, key, encrypt=False):
    xa = np.array(md5_shuffle(width, key), dtype=np.intp)

    i2 = np.arange(width, dtype=np.intp)[None, :]
    j2 = np.arange(height, dtype=np.intp)[:, None]
    M = xa[(xa[j2 % width] + i2) % width]
    id_arr = (j2 * width + M).flatten()

    new_pixels = np.zeros(width * height, dtype=np.uint32)
    if encrypt:
        return pixels[id_arr]
    else:
        new_pixels[id_arr] = pixels
        return new_pixels


# ============================================================
# 7. Logistic Map (PicEncrypt 兼容模式)
# ============================================================

def generate_logistic(x1, n):
    arr = []
    x = x1
    arr.append((x, 0))
    for i in range(1, n):
        x = 3.9999999 * x * (1 - x)
        arr.append((x, i))
    return arr


def get_sorted_positions(logistic_map):
    sorted_map = sorted(logistic_map, key=lambda a: a[0])
    return [int(item[1]) for item in sorted_map]


def picencrypt_row_scramble(pixels, width, height, key, encrypt=False):
    logistic_map = generate_logistic(key, width)
    positions = get_sorted_positions(logistic_map)
    new_pixels = np.zeros(width * height, dtype=np.uint32)
    offset = (height - 1) * width

    for i in range(width):
        m = positions[i]
        for j in range(offset, -1, -width):
            if encrypt:
                new_pixels[i + j] = pixels[m + j]
            else:
                new_pixels[m + j] = pixels[i + j]

    return new_pixels


# ============================================================
# 8. 主处理函数
# ============================================================

def process_image(input_path, output_path, method='tomato', key=None, decrypt=True, iterations=1):
    """
    处理单张图片
    method: tomato / block / perpixel / rowpixel / picencrypt_row
    key: tomato -> float(默认1.0), 其他 -> str
    decrypt: True=解混淆, False=混淆
    iterations: 重复次数
    """
    img = Image.open(input_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    width, height = img.size
    # PIL pixels -> flattened uint32 array (0xAARRGGBB)
    arr = np.array(img, dtype=np.uint32)
    pixels_u32 = (0xFF000000 | (arr[:,:,0] << 16) | (arr[:,:,1] << 8) | arr[:,:,2]).reshape(-1)

    print(f'  图片: {os.path.basename(input_path)} ({width}x{height})')
    print(f'  方法: {method}, 密钥: {key}, 操作: {"解混淆" if decrypt else "混淆"}, 次数: {iterations}')

    for it in range(iterations):
        op = '解混淆' if decrypt else '混淆'
        print(f'  第 {it+1}/{iterations} 次 {op}...')

        if method == 'tomato':
            k = float(key) if key else 1.0
            pixels_u32 = tomato_process(pixels_u32, width, height, k, encrypt=not decrypt)
        elif method == 'block':
            pixels_u32, width, height = block_scramble(pixels_u32, width, height, str(key), encrypt=not decrypt)
        elif method == 'perpixel':
            pixels_u32 = per_pixel_scramble(pixels_u32, width, height, str(key), encrypt=not decrypt)
        elif method == 'rowpixel':
            pixels_u32 = row_pixel_scramble(pixels_u32, width, height, str(key), encrypt=not decrypt)
        elif method == 'picencrypt_row':
            k = float(key) if key else 0.5
            pixels_u32 = picencrypt_row_scramble(pixels_u32, width, height, k, encrypt=not decrypt)
        else:
            print(f'  未知方法: {method}')
            return False

    # uint32 -> RGB
    result = np.zeros((height * width, 3), dtype=np.uint8)
    result[:, 0] = (pixels_u32 >> 16) & 0xFF
    result[:, 1] = (pixels_u32 >> 8) & 0xFF
    result[:, 2] = pixels_u32 & 0xFF
    result = result.reshape((height, width, 3))

    out_img = Image.fromarray(result, 'RGB')
    out_img.save(output_path, 'JPEG', quality=95)
    print(f'  已保存: {output_path}')
    return True


def main():
    parser = argparse.ArgumentParser(description='小番茄图片混淆还原工具')
    parser.add_argument('input', help='输入图片路径或文件夹')
    parser.add_argument('-o', '--output', help='输出路径(默认在输入旁加后缀)')
    parser.add_argument('-m', '--method', default='tomato',
                        choices=['tomato', 'block', 'perpixel', 'rowpixel', 'picencrypt_row'],
                        help='混淆方法 (默认: tomato)')
    parser.add_argument('-k', '--key', default=None,
                        help='密钥 (tomato: 浮点数默认1.0, 其他: 字符串)')
    parser.add_argument('-e', '--encrypt', action='store_true',
                        help='混淆(加密)而非解混淆')
    parser.add_argument('-n', '--iterations', type=int, default=1,
                        help='重复次数 (默认1)')
    args = parser.parse_args()

    input_path = args.input

    if os.path.isdir(input_path):
        # 处理文件夹中所有图片
        out_dir = args.output or (input_path + '_restored')
        os.makedirs(out_dir, exist_ok=True)

        exts = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
        files = [f for f in sorted(os.listdir(input_path))
                 if f.lower().endswith(exts)
                 and not f.lower().endswith('_restored.jpg')
                 and not f.lower().endswith('_restored.png')
                 and not f.lower().endswith('_encrypted.jpg')]

        if not files:
            print(f'未找到图片文件: {input_path}')
            return

        print(f'找到 {len(files)} 张图片')
        for f in files:
            inp = os.path.join(input_path, f)
            name, _ = os.path.splitext(f)
            outp = os.path.join(out_dir, name + '_restored.jpg')
            print(f'\n处理: {f}')
            try:
                process_image(inp, outp, args.method, args.key, not args.encrypt, args.iterations)
            except Exception as e:
                print(f'  错误: {e}')
    else:
        # 处理单个文件
        if not os.path.isfile(input_path):
            print(f'文件不存在: {input_path}')
            return

        if args.output:
            outp = args.output
        else:
            d, name = os.path.split(input_path)
            base, _ = os.path.splitext(name)
            suffix = 'encrypted' if args.encrypt else 'restored'
            outp = os.path.join(d, f'{base}_{suffix}.jpg')

        process_image(input_path, outp, args.method, args.key, not args.encrypt, args.iterations)


if __name__ == '__main__':
    main()
