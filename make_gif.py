# -*- coding: utf-8 -*-
"""
录制游戏演示动图（GIF），给博客用。

思路：
    用虚拟显示驱动把游戏跑起来，一边推进游戏状态、一边按固定帧率把画面抓成图片，
    最后用 PIL 合成 GIF。因为是「边跑边抓」，飞出、晃动、弹图这些动画
    都是照着真实速度录下来的，不是摆拍。

    录制过程中会真的 sleep，所以整个脚本要跑十几秒，属正常。

运行：
    & "D:\\Users\\14566\\anaconda3\\envs\\Yet_myenv\\python.exe" make_gif.py
"""

import os
import sys

# 虚拟显示驱动，录制过程不弹窗
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from game import Game
from solver import solve

OUT_DIR = os.path.join(HERE, "preview")
FPS = 15          # 抓帧帧率，15 帧够看出动画，再高体积吃不消
TARGET_W = 520    # 输出宽度。博客页面宽度有限，520 足够清晰又能压住体积


def to_image(surface):
    """pygame 的 Surface 直接转成 PIL 图片，不落盘中转。"""
    data = pygame.image.tobytes(surface, "RGB")
    return Image.frombytes("RGB", surface.get_size(), data)


class Recorder:
    """按固定帧率抓帧的小工具。"""

    def __init__(self, game):
        self.game = game
        self.frames = []

    def record(self, ms):
        """在 ms 毫秒里持续抓帧，真实等待让动画自然播放。"""
        n = max(1, int(ms / 1000.0 * FPS))
        step = int(1000.0 / FPS)
        for i in range(n):
            self.game._update_animations()
            self.game._draw()
            self.frames.append(to_image(self.game.screen))
            if i < n - 1:
                pygame.time.delay(step)      # 真实等待，动画才会往前走

    def save(self, name, colors=128):
        """缩放 + 转调色板 + 存成 GIF。

        转调色板（减少颜色数）是压体积的关键：游戏画面本来就是纯色块，
        降到 128 色肉眼几乎看不出差别，体积却能少一大截。
        """
        if not self.frames:
            print(f"  [跳过] {name}：没有抓到帧")
            return None

        w, h = self.frames[0].size
        size = (TARGET_W, int(round(h * TARGET_W / w)))
        scaled = [f.resize(size, Image.LANCZOS) for f in self.frames]
        pal = [f.quantize(colors=colors, method=Image.MEDIANCUT) for f in scaled]

        path = os.path.join(OUT_DIR, name)
        pal[0].save(path, save_all=True, append_images=pal[1:],
                    duration=int(1000 / FPS), loop=0, optimize=True)
        kb = os.path.getsize(path) / 1024
        print(f"  [完成] {name}  帧数 {len(pal)}  体积 {kb:.0f} KB")
        return path, len(pal), kb


def find_blocked(game):
    """找一个当前飞不出去的箭头，用来演示碰撞。"""
    for cell in sorted(game.board.arrows.keys()):
        can_fly, _ = game.board.check_path(*cell)
        if not can_fly:
            return cell
    return None


def demo_play(game, rec):
    """演示一：正常游玩。

    按第 1 关的正确解法点前几步，特别安排「先清挡路的箭头、
    再让 (1,0) 的箭头一路飞过 (1,3) 吃到时间道具」这个桥段 ——
    正好把新做的道具机制演示出来。
    """
    game._enter_level(0)
    rec.record(650)                  # 开局画面，让眼睛有个底

    game.on_click_arrow(1, 2)        # 先把挡路的 U 放走
    rec.record(650)

    game.on_click_arrow(1, 0)        # R 一路飞出，从道具上穿过去
    rec.record(1000)                 # 多留一会儿，能看清 +5 秒的提示

    game.on_click_arrow(2, 2)
    rec.record(650)

    game.on_click_arrow(3, 3)
    rec.record(650)


def demo_hit(game, rec):
    """演示二：碰撞反馈（点被挡住的箭头）。"""
    game._enter_level(0)
    rec.record(500)

    cell = find_blocked(game)
    if cell:
        game.on_click_arrow(*cell)   # 扣一颗爱心 + 箭头晃动变红
        rec.record(1100)


def demo_clear(game, rec):
    """演示三：清空棋盘 → 结算界面弹出表情图。"""
    game._enter_level(0)

    # 前面几步直接快进（不录），最后一步才录像
    path = solve(game.board)
    for cell in path[:-1]:
        game.on_click_arrow(*cell)
    game.flying.clear()              # 快进阶段不保留飞出动画

    rec.record(400)
    game.on_click_arrow(*path[-1])   # 最后一个箭头飞出
    rec.record(1600)                 # 清空 → 切结算 → 表情图弹入


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    pygame.init()
    game = Game()

    results = []

    print("录制演示一：正常游玩 ...")
    rec = Recorder(game)
    demo_play(game, rec)
    results.append(rec.save("demo_1_游玩.gif"))

    print("录制演示二：碰撞反馈 ...")
    rec = Recorder(game)
    demo_hit(game, rec)
    results.append(rec.save("demo_2_碰撞.gif"))

    print("录制演示三：通关结算 ...")
    rec = Recorder(game)
    demo_clear(game, rec)
    results.append(rec.save("demo_3_结算.gif"))

    pygame.quit()

    total = sum(r[2] for r in results if r)
    print()
    print("=" * 46)
    print(f"共 {len([r for r in results if r])} 个 GIF，合计 {total:.0f} KB")
    print(f"输出目录：{OUT_DIR}")
    print("=" * 46)


if __name__ == "__main__":
    main()
