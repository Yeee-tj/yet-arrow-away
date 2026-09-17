# -*- coding: utf-8 -*-
"""
一箭又一箭 —— 关卡生成器

为什么要写这个：
    手工设计关卡有两个麻烦：
      1. 容易不小心造出「互相挡死」的死锁，整关直接无解；
      2. 容易做出「一整排同方向箭头」这种结构 —— 虽然可解，
         但玩起来就是从一头到另一头挨个点，纯机械劳动。

设计铁律（都是踩坑踩出来的）：
    【铁律一】同一行或同一列上，不能出现两个箭头「面对面」互相指向对方
              （例如一行里的 R ...... L）。这样两个箭头互相挡死，整关无解。

    【铁律二】同一行或同一列上，相邻位置连续同方向的箭头不能超过 2 个。
              否则会出现「一整排都朝右」的情况，玩家从最右边开始
              一路点过去就行，毫无思考乐趣。这一条是试玩反馈后补上的。

难度怎么衡量：
    这个游戏里「移除箭头只会让路更通，不会新增阻挡」，
    所以玩家不可能把局面点死 —— 任何当前能飞的箭头，点了都是安全的。
    因此衡量难度不该看通关路径有多少条，而应该看：
      - 箭头总数：越多，需要观察的信息量越大；
      - 开局可飞箭头数：越少，越难下手；
      - 是否有「一路点过去」的单调段落。
"""

import random
import sys

from arrows import Board, UP, DOWN, LEFT, RIGHT
from solver import solve

# Windows 控制台中文输出
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DIRECTIONS = [UP, DOWN, LEFT, RIGHT]


# ---------------------------------------------------------------- 质量检查

def max_same_dir_line(board, limit=2):
    """统计一整行/一整列里，相邻位置连续同方向箭头的最长长度。

    注意这里要求「相邻」，也就是格子挨在一起。
    返回最长的一段有多少个箭头。
    """
    best = 1

    for r in range(board.rows):
        run = 1
        prev_pos = None
        prev_dir = None
        for c in range(board.cols):
            if board.has_arrow(r, c):
                d = board.direction_at(r, c)
                if prev_dir == d and prev_pos == c - 1:
                    run += 1
                    best = max(best, run)
                else:
                    run = 1
                prev_pos, prev_dir = c, d

    for c in range(board.cols):
        run = 1
        prev_pos = None
        prev_dir = None
        for r in range(board.rows):
            if board.has_arrow(r, c):
                d = board.direction_at(r, c)
                if prev_dir == d and prev_pos == r - 1:
                    run += 1
                    best = max(best, run)
                else:
                    run = 1
                prev_pos, prev_dir = r, d

    return best


def max_same_dir_streak(board, limit=3):
    """看通关过程中会不会出现连续好几步都在点同一方向的箭头。

    返回某条通关路径上，连续同方向点击的最长段。
    """
    initial = dict(board.arrows)   # 保存初始方向，后面箭头会被移掉
    b = board.copy()
    prev_dir = None
    streak = 1
    best = 1

    while not b.is_clear():
        flyable = b.flyable_arrows()
        if not flyable:
            break
        # 挑一个方向尽可能和上次不同的，模拟玩家不会一路点同类
        pick = None
        for cell in flyable:
            if initial[cell] != prev_dir:
                pick = cell
                break
        if pick is None:
            pick = flyable[0]

        d = initial[pick]
        if d == prev_dir:
            streak += 1
            best = max(best, streak)
        else:
            streak = 1
            prev_dir = d
        b.remove(*pick)

    return best


def random_board(rows, cols, n_arrows, rng):
    """在棋盘上随机撒 n_arrows 个随机方向的箭头。"""
    cells = [(r, c) for r in range(rows) for c in range(cols)]
    chosen = rng.sample(cells, n_arrows)
    board = Board(rows, cols)
    for (r, c) in chosen:
        board.place(r, c, rng.choice(DIRECTIONS))
    return board


def generate(rows, cols, n_arrows,
             max_opening=None,
             max_line_run=2,
             max_streak=3,
             seed=None, max_try=60000):
    """生成一个合格的关卡。

    参数：
        rows, cols    : 棋盘尺寸
        n_arrows      : 箭头数量
        max_opening   : 开局可飞箭头数上限（不填则按箭头数的四分之一算）
        max_line_run  : 直线上相邻连续同方向箭头最多允许几个
        max_streak    : 通关过程中连续点同方向最多允许几步
        seed          : 随机种子，填了就能复现
        max_try       : 最多尝试多少次
    """
    rng = random.Random(seed)
    if max_opening is None:
        max_opening = max(2, n_arrows // 4)

    # 检查顺序：便宜的放前面，贵的放最后
    for _ in range(max_try):
        board = random_board(rows, cols, n_arrows, rng)

        # 1) 四个方向都得出现
        if len(set(board.arrows.values())) < 4:
            continue

        # 2) 开局可飞不能太多
        opening = len(board.flyable_arrows())
        if opening > max_opening:
            continue

        # 3) 不能有「一整排同方向」的死板结构
        if max_same_dir_line(board) > max_line_run:
            continue

        # 4) 必须能通关（较贵）
        if solve(board) is None:
            continue

        # 5) 通关过程不能一路点同一个方向
        if max_same_dir_streak(board) > max_streak:
            continue

        return board, {"opening": opening}

    return None, None


def board_to_grid_lines(board):
    """把棋盘转成 levels.py 里那种字符网格写法。"""
    return [" ".join(row) for row in board.to_grid()]


# ---------------------------------------------------------------- 命令行

if __name__ == "__main__":
    # 棋盘更大、箭头更多，同时消掉「一路点过去」的单调结构
    specs = [
        ("第 1 关", 6, 6, 9, 4, 2, 2, 101),
        ("第 2 关", 7, 7, 14, 4, 2, 3, 202),
        ("第 3 关", 8, 8, 20, 5, 2, 3, 303),
    ]

    out = []
    try:
        for name, rows, cols, n, mo, mlr, ms, seed in specs:
            out.append(f"=== {name} ===")
            out.append(f"尺寸 {rows}x{cols}，箭头 {n} 个，"
                       f"要求：开局可飞<={mo}，直线同方向连续<={mlr}，"
                       f"通关时连续同方向<={ms}")
            board, info = generate(rows, cols, n,
                                   max_opening=mo,
                                   max_line_run=mlr,
                                   max_streak=ms,
                                   seed=seed)
            if board is None:
                out.append("没有找到符合条件的关卡，请放宽条件。")
            else:
                out.append(f"找到：开局可飞 {info['opening']} 个")
                out.append(f"      直线最长同方向连续：{max_same_dir_line(board)}")
                out.append(f"      通关时最长同方向连续：{max_same_dir_streak(board)}")
                out.append("关卡数据（可直接粘进 levels.py）：")
                out.append('        "grid": [')
                for line in board_to_grid_lines(board):
                    out.append(f'            "{line}",')
                out.append('        ],')
                out.append("")
                out.append("初始局面：")
                out.append(str(board))
                path = solve(board)
                out.append(f"一条通关顺序（共 {len(path)} 步）：")
                out.append("  " + " -> ".join(f"({r},{c})" for r, c in path))
            out.append("")
    except Exception:
        import traceback
        out.append("出错了：")
        out.append(traceback.format_exc())

    text = "\n".join(out)
    with open("level_gen_report.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("done")
