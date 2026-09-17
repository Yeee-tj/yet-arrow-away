# -*- coding: utf-8 -*-
"""
一箭又一箭 —— 离屏渲染预览

用 pygame 的虚拟显示驱动把各个界面画出来存成 PNG，
这样不用真的弹出窗口，也能检查布局对不对：
文字有没有重叠、棋盘有没有超出边界、箭头方向画对没有、颜色是否正常。

运行后图片输出到 preview/ 目录，需要**打开看一眼**确认，
不能只看「没报错」就算过。
"""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pygame

from game import (Game, STATE_START, STATE_PLAYING, STATE_LEVEL_CLEAR,
                  STATE_FAILED, STATE_ALL_CLEAR, FLY_DURATION, SHAKE_DURATION)
from solver import solve

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "preview")
os.makedirs(OUT_DIR, exist_ok=True)

log = []


def save(game, name):
    path = os.path.join(OUT_DIR, f"{name}.png")
    pygame.image.save(game.screen, path)
    log.append(f"{name}.png")
    return path


def main():
    pygame.init()
    game = Game()
    now = pygame.time.get_ticks()

    # 1) 开始界面
    game.state = STATE_START
    game._draw()
    save(game, "01_开始界面")

    # 2) 第 1 关初始局面
    game._enter_level(0)
    game._draw()
    save(game, "02_第1关初始")

    # 3) 最大的第 3 关（7x7），检查布局会不会超出窗口
    game._enter_level(2)
    game._draw()
    save(game, "03_第3关初始_最大棋盘")

    # 4) 提示高亮 + 顶部信息
    game.use_hint()
    game._draw()
    save(game, "04_提示高亮")

    # 5) 飞出动画进行到一半
    game._enter_level(2)
    r, c = game.board.flyable_arrows()[0]
    direction = game.board.direction_at(r, c)
    fx, fy = game._cell_center(r, c)
    game.board.remove(r, c)
    game.flying.append({
        "r": r, "c": c, "direction": direction,
        "start": now - int(FLY_DURATION * 0.45),
        "from_x": fx, "from_y": fy,
    })
    game._draw()
    save(game, "05_飞出动画中途")

    # 6) 碰撞晃动（点了一个被挡住的箭头）
    game._enter_level(2)
    blocked = None
    for (rr, cc) in sorted(game.board.arrows.keys()):
        can_fly, _ = game.board.check_path(rr, cc)
        if not can_fly:
            blocked = (rr, cc)
            break
    if blocked:
        game.mistakes_left -= 1
        game.shaking[blocked] = now - int(SHAKE_DURATION * 0.25)
        game._show_message("被挡住了！", (224, 92, 92))
        game._draw()
        save(game, "06_碰撞晃动")

    # 7) 通关界面（带表情图）
    game._enter_level(0)
    for (rr, cc) in solve(game.board):
        game.on_click_arrow(rr, cc)
    game.flying.clear()
    game._check_result()
    game.result_shown_at = pygame.time.get_ticks() - 500  # 让弹入动画播完
    game._draw()
    save(game, "07_通关界面")

    # 8) 失败界面 —— 失误用完
    game._enter_level(0)
    blocked = None
    for (rr, cc) in sorted(game.board.arrows.keys()):
        can_fly, _ = game.board.check_path(rr, cc)
        if not can_fly:
            blocked = (rr, cc)
            break
    if blocked:
        for _ in range(game.mistakes_left):
            game.on_click_arrow(*blocked)
        game.flying.clear()
        game._check_result()
        game.result_shown_at = pygame.time.get_ticks() - 500
        game._draw()
        save(game, "08_失败界面_机会用完")

    # 8b) 失败界面 —— 时间到
    game._enter_level(0)
    game.time_left_ms = 0
    game._check_timeout()
    game.result_shown_at = pygame.time.get_ticks() - 500
    game._draw()
    save(game, "08b_失败界面_时间到")

    # 9) 全部通关界面
    game.state = STATE_ALL_CLEAR
    game.result_shown_at = pygame.time.get_ticks() - 500
    game._draw()
    save(game, "09_全部通关")

    # 10) 道具静止在棋盘上的样子（第 3 关，道具落在正中间最好看）
    game._enter_level(2)
    game._draw()
    save(game, "10_道具静止在棋盘上")

    # 11) 箭头飞过时吃到道具的那一瞬间（顶部会冒出提示文字）
    #     第 1 关的吃法：先放走挡路的 (1,2)U，(1,0)R 才能一飞到底扫过 (1,3)
    game._enter_level(0)
    game.on_click_arrow(1, 2)
    game.on_click_arrow(1, 0)
    game._draw()
    save(game, "11_道具被飞过时拿到")

    pygame.quit()

    with open(os.path.join(OUT_DIR, "_预览清单.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log))
    print("done")


if __name__ == "__main__":
    main()
