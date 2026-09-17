# -*- coding: utf-8 -*-
"""
生成「路径检测」对比示意图，给博客的「实现思路」章节用。

左边：箭头前方一路畅通 -> 可以飞出
右边：箭头前方被另一个箭头挡住 -> 飞不出去

用 PIL 直接画，不依赖游戏代码，配色参照游戏本体。

运行：
    & "D:\\Users\\14566\\anaconda3\\envs\\Yet_myenv\\python.exe" make_diagram.py
"""

import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "preview", "fig_路径检测示意.png")

FONT = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"

CELL = 56
COLS, ROWS = 5, 4
BOARD_W, BOARD_H = COLS * CELL, ROWS * CELL
GAP = 62                       # 两个棋盘之间的间距
MARGIN = 44
TOP = 140                      # 标题区高度：要留得下大标题 + 各棋盘上方的小标题

W = MARGIN * 2 + BOARD_W * 2 + GAP
H = TOP + BOARD_H + 150

C_BG = (255, 255, 255)
C_CELL = (244, 246, 250)
C_GRID = (206, 214, 228)
C_ARROW = (214, 160, 42)       # 金黄色箭头（和游戏里一致）
C_OTHER = (140, 148, 165)      # 灰：挡路的那个箭头
C_OK = (34, 150, 94)           # 绿：路通
C_BAD = (200, 60, 60)          # 红：被挡
C_TEXT = (38, 44, 58)
C_DIM = (120, 128, 145)

img = Image.new("RGB", (W, H), C_BG)
d = ImageDraw.Draw(img)


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def draw_arrow(cx, cy, size, direction, color):
    """画一个箭头。direction 取 'U' 'D' 'L' 'R'。"""
    s = size / 2.0
    # 朝右的基准形状：箭尖在右
    base = [(1.0, 0.0), (-0.35, -0.78), (-0.05, 0.0), (-0.35, 0.78)]
    if direction == "R":
        pts = base
    elif direction == "L":
        pts = [(-x, y) for (x, y) in base]
    elif direction == "D":                    # 屏幕上 y 轴向下
        pts = [(y, x) for (x, y) in base]
    else:                                     # U
        pts = [(-y, -x) for (x, y) in base]
    d.polygon([(cx + x * s, cy + y * s) for (x, y) in pts], fill=color)


def draw_board(ox, oy):
    for r in range(ROWS):
        for c in range(COLS):
            x, y = ox + c * CELL, oy + r * CELL
            d.rectangle([x, y, x + CELL, y + CELL], fill=C_CELL,
                        outline=C_GRID, width=1)


def cell_center(ox, oy, r, c):
    return ox + c * CELL + CELL // 2, oy + r * CELL + CELL // 2


def dashed_line(p0, p1, color, dash=9, gap=7, width=3):
    """画虚线，用来表示箭头的飞行路线。"""
    (x0, y0), (x1, y1) = p0, p1
    total = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    if total == 0:
        return
    ux, uy = (x1 - x0) / total, (y1 - y0) / total
    pos = 0.0
    while pos < total:
        end = min(pos + dash, total)
        d.line([(x0 + ux * pos, y0 + uy * pos),
                (x0 + ux * end, y0 + uy * end)], fill=color, width=width)
        pos = end + gap


# ---------------- 标题 ----------------
title = "路径检测：箭头前方到底有没有东西挡着"
tw = d.textlength(title, font=font(27, True))
d.text(((W - tw) / 2, 26), title, font=font(27, True), fill=C_TEXT)

# ---------------- 左：可以飞出 ----------------
lx, ly = MARGIN, TOP
draw_board(lx, ly)

# (1,0) 朝右，前方 (1,1)(1,2)(1,3)(1,4) 全空
cx, cy = cell_center(lx, ly, 1, 0)
draw_arrow(cx, cy, CELL * 0.62, "R", C_ARROW)
# 路线一路画到棋盘外
dashed_line((cx + CELL * 0.34, cy), (lx + BOARD_W + 46, cy), C_OK)

d.text((lx + 2, ly - 42), "前方没有其他箭头", font=font(20, True), fill=C_OK)
d.text((lx + 2, ly + BOARD_H + 18),
       "沿着方向一路查到棋盘边界，中间是空的",
       font=font(18), fill=C_DIM)
d.text((lx + 2, ly + BOARD_H + 48),
       "→ 箭头飞出棋盘，被消除", font=font(20, True), fill=C_TEXT)

# ---------------- 右：被挡住 ----------------
rx, ry = MARGIN + BOARD_W + GAP, TOP
draw_board(rx, ry)

cx, cy = cell_center(rx, ry, 1, 0)
draw_arrow(cx, cy, CELL * 0.62, "R", C_ARROW)

# (1,3) 放一个挡路的箭头（灰色表示"别人"）
bx, by = cell_center(rx, ry, 1, 3)
draw_arrow(bx, by, CELL * 0.62, "U", C_OTHER)

# 路线只画到阻挡格前面
dashed_line((cx + CELL * 0.34, cy), (bx - CELL * 0.36, cy), C_BAD)
# 圈出冲突点
d.ellipse([bx - CELL * 0.46, by - CELL * 0.46,
           bx + CELL * 0.46, by + CELL * 0.46], outline=C_BAD, width=3)

d.text((rx + 2, ry - 42), "前方被另一个箭头挡住", font=font(20, True), fill=C_BAD)
d.text((rx + 2, ry + BOARD_H + 18),
       "查到 (1,3) 时碰到箭头，中途停下", font=font(18), fill=C_DIM)
d.text((rx + 2, ry + BOARD_H + 48),
       "→ 箭头不消除，扣一次失误机会", font=font(20, True), fill=C_TEXT)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT)
print(f"已生成：{OUT}（{os.path.getsize(OUT) / 1024:.0f} KB，{W}x{H}）")
