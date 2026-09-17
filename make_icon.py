# -*- coding: utf-8 -*-
"""
打包用的图标生成脚本。

把结算表情图裁成正方形、缩放成 .ico，给 exe 当图标 ——
不然打包出来的文件是 PyInstaller 的默认图标，一眼看不出是个游戏。

注意：.ico 需要多尺寸（16/32/48/64/128/256），
Windows 在任务栏、桌面、文件列表里用的尺寸都不一样，
只塞一张大图的话小尺寸会糊。

运行：
    & "D:\\Users\\14566\\anaconda3\\envs\\Yet_myenv\\python.exe" make_icon.py
"""

import os
import sys

# 用虚拟显示驱动跑，这样能弹出隐藏的显示模式而不真的开窗口。
# 注意 convert() 需要一个已创建的显示模式，否则报 "No video mode has been set"，
# 所以下面必须 set_mode 一个小窗口（dummy 驱动下不会显示出来）。
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "resources", "单关通过图.jpg")
DST = os.path.join(HERE, "game_icon.ico")

# Windows 会用到的各个尺寸，从小到大都得备着
SIZES = [16, 24, 32, 48, 64, 128, 256]


def main():
    if not os.path.exists(SRC):
        print(f"找不到源图：{SRC}")
        return 1

    pygame.init()
    pygame.display.set_mode((64, 64))       # convert() 需要先有显示模式
    img = pygame.image.load(SRC).convert()

    # 裁成正方形（居中取最大的正方形区域），避免缩放出比例失真
    w, h = img.get_size()
    side = min(w, h)
    square = pygame.Surface((side, side))
    square.blit(img, ((side - w) // 2, (side - h) // 2))

    # pygame 没有直接导出 ico 的能力，这里手写 ICO 文件格式。
    # ICO 就是「一个头 + 各尺寸的 PNG 数据」，现代 Windows 都支持 PNG 压缩的条目。
    images = []
    for s in SIZES:
        scaled = pygame.transform.smoothscale(square, (s, s))
        # 用 pygame 把 Surface 存成 PNG 到内存
        png_path = os.path.join(HERE, f"_icon_{s}.png")
        pygame.image.save(scaled, png_path)
        with open(png_path, "rb") as f:
            images.append((s, f.read()))
        os.remove(png_path)

    # ---- 组装 ICO ----
    import struct
    header = struct.pack("<HHH", 0, 1, len(images))     # 保留位, 类型=图标, 数量
    offset = 6 + 16 * len(images)                        # 数据区起始偏移
    entries, blobs = b"", b""
    for s, data in images:
        # 每项 16 字节：宽 高 色数 保留 平面数 位深 数据大小 数据偏移
        # 宽高为 256 时用 0 表示（一个字节放不下 256）
        dim = 0 if s >= 256 else s
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32,
                               len(data), offset)
        blobs += data
        offset += len(data)

    with open(DST, "wb") as f:
        f.write(header + entries + blobs)

    pygame.quit()
    print(f"图标已生成：{DST}（{os.path.getsize(DST)} 字节，{len(images)} 个尺寸）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
