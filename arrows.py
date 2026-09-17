# -*- coding: utf-8 -*-
"""
一箭又一箭 —— 核心逻辑层（纯 Python，不依赖 pygame）

设计说明：
    本模块只负责「游戏怎么算」，不负责「游戏怎么画」。
    把它和界面代码分开有两个好处：
    1. 可以直接写自动测试（不用手点鼠标），测试结果能贴进博客；
    2. 写博客「实现思路」时，逻辑独立出来更好讲清楚。

游戏规则（对应作业要求）：
    棋盘上有若干带方向的箭头（上/下/左/右）。玩家点击一个箭头后，
    沿它指的方向一路检查到棋盘边界：
      - 路上一个箭头都没有  ->  该箭头飞出棋盘并被消除；
      - 路上碰到别的箭头    ->  该箭头不能消除，扣一次失误机会。
    清空全部箭头即通关；失误次数耗尽则失败。
"""

# ---------------------------------------------------------------- 方向定义

UP = "U"
DOWN = "D"
LEFT = "L"
RIGHT = "R"

# 四个方向对应的「行增量, 列增量」。
# 注意：行索引向下增长，所以 UP 是 -1。
DELTA = {
    UP: (-1, 0),
    DOWN: (1, 0),
    LEFT: (0, -1),
    RIGHT: (0, 1),
}

# 方向 -> 中文名（界面和日志里显示用）
DIR_NAME = {
    UP: "上",
    DOWN: "下",
    LEFT: "左",
    RIGHT: "右",
}

# 方向 -> 箭头字符（关卡文本里用）
DIR_CHAR = {
    UP: "U",
    DOWN: "D",
    LEFT: "L",
    RIGHT: "R",
}

# 字符 -> 方向（解析关卡用）
CHAR_DIR = {
    "U": UP,
    "D": DOWN,
    "L": LEFT,
    "R": RIGHT,
}

EMPTY_CHAR = "."  # 关卡文本里表示空格子的字符


class Board:
    """棋盘：保存所有箭头的位置和方向。

    坐标采用 (行, 列)，左上角为 (0, 0)。
    内部用字典 self.arrows 存储，键是 (行, 列)，值是方向常量；
    不存空格子，所以「某个位置有没有箭头」就是「这个键在不在字典里」。
    """

    def __init__(self, rows, cols, arrows=None):
        self.rows = rows
        self.cols = cols
        self.arrows = dict(arrows) if arrows else {}

    # ------------------------------------------------------------ 基础查询

    def in_bounds(self, r, c):
        """判断 (r, c) 是否在棋盘范围内。"""
        return 0 <= r < self.rows and 0 <= c < self.cols

    def has_arrow(self, r, c):
        """判断 (r, c) 上是否有箭头。越界位置一律视为没有。"""
        return (r, c) in self.arrows

    def direction_at(self, r, c):
        """返回 (r, c) 上箭头的方向；该位置没有箭头则返回 None。"""
        return self.arrows.get((r, c))

    def count(self):
        """当前剩余箭头数量。"""
        return len(self.arrows)

    def is_clear(self):
        """棋盘是否已清空（即本关通关）。"""
        return len(self.arrows) == 0

    # ------------------------------------------------------------ 增删箭头

    def place(self, r, c, direction):
        """在 (r, c) 放一个 direction 方向的箭头。会做合法性检查。"""
        if not self.in_bounds(r, c):
            raise IndexError(f"位置 ({r}, {c}) 超出棋盘范围 {self.rows}x{self.cols}")
        if direction not in DELTA:
            raise ValueError(f"非法方向: {direction}")
        self.arrows[(r, c)] = direction

    def remove(self, r, c):
        """移除 (r, c) 上的箭头（箭头飞出棋盘时调用）。"""
        self.arrows.pop((r, c), None)

    def copy(self):
        """复制一份棋盘。搜索/求解时要用到，避免改动原始关卡数据。"""
        return Board(self.rows, self.cols, self.arrows)

    # ------------------------------------------------------------ 核心算法

    def check_path(self, r, c):
        """检查 (r, c) 上的箭头能否飞出棋盘 —— 本程序最核心的一个方法。

        做法：从箭头的**下一格**开始，沿着它指的方向一格一格往外走，
              一直走到走出棋盘边界为止。

              - 中途只要碰到任何一个箭头  -> 被挡住，不能飞出去；
              - 一路走到棋盘外都还没碰到   -> 畅通，可以飞出去。

        【易错点提示】这里是整个作业最容易写错的地方：
        「走出边界」和「被挡住」是两件完全不同的事。
        朝棋盘外飞的箭头**必须能正常飞出去**，不能因为索引变成 -1 或
        超出列数就抛异常。下面的循环用 in_bounds 作为条件，
        索引越界时循环自然结束并返回「可以飞出」，就天然避开了这个坑。

        参数：
            r, c: 待检查箭头所在的行、列

        返回：
            (can_fly, blocker)
              can_fly : bool          True 表示可以飞出棋盘
              blocker : tuple|None    挡路的那个箭头坐标 (行, 列)；
                                      如果可以飞出则为 None
        """
        if not self.has_arrow(r, c):
            # 点到空格子：既不能飞也没人挡，交给调用方去处理（通常忽略）
            return False, None

        direction = self.arrows[(r, c)]
        dr, dc = DELTA[direction]

        # 从箭头的相邻格开始往外走
        nr, nc = r + dr, c + dc

        while self.in_bounds(nr, nc):
            if self.has_arrow(nr, nc):
                # 前方有别的箭头挡着 -> 飞不出去
                return False, (nr, nc)
            # 这一格是空的，继续往外走一格
            nr += dr
            nc += dc

        # 能走到这里，说明一路畅通走到了棋盘外面 -> 可以飞出
        return True, None

    def flyable_arrows(self):
        """列出当前所有「可以飞出去」的箭头坐标，按 (行, 列) 排序。

        这个方法既给界面用（高亮提示），也给求解器用（搜索下一步）。
        """
        result = []
        for (r, c) in sorted(self.arrows.keys()):
            can_fly, _ = self.check_path(r, c)
            if can_fly:
                result.append((r, c))
        return result

    def path_cells(self, r, c):
        """返回箭头飞出时会经过的所有格子（从相邻格一直到棋盘外，不含自身）。

        这个方法有两个用处：
          1. 判断箭头的飞行路线上有没有事件道具 —— 有就顺路拿到；
          2. 画飞行轨迹时表示飞过了哪些格子。

        注意它只看「棋盘范围内」的格子，走到边界就停，
        和 check_path 里的越界处理保持一致的思路。
        """
        if not self.has_arrow(r, c):
            return []

        direction = self.arrows[(r, c)]
        dr, dc = DELTA[direction]

        nr, nc = r + dr, c + dc
        cells = []
        while self.in_bounds(nr, nc):
            cells.append((nr, nc))
            nr += dr
            nc += dc
        return cells

    # ------------------------------------------------------------ 文本表示

    def to_grid(self):
        """把棋盘转成二维字符列表，方便打印和调试。"""
        grid = [[EMPTY_CHAR for _ in range(self.cols)] for _ in range(self.rows)]
        for (r, c), d in self.arrows.items():
            grid[r][c] = DIR_CHAR[d]
        return grid

    @classmethod
    def from_grid(cls, grid):
        """从二维字符列表构造棋盘（'.' 表示空格子）。"""
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        board = cls(rows, cols)
        for r in range(rows):
            for c in range(cols):
                ch = grid[r][c]
                if ch != EMPTY_CHAR:
                    board.place(r, c, CHAR_DIR[ch])
        return board

    def __str__(self):
        return "\n".join(" ".join(row) for row in self.to_grid())


def parse_level(grid_lines):
    """把关卡文本（字符串列表）解析成 Board。

    允许写成 ['..R.', '.LR.', ...] 或者带空格的 ['.. R .', ...]，
    后者写起来更清楚，解析时会自动去掉空格。
    """
    cleaned = []
    for line in grid_lines:
        line = line.strip()
        if not line:
            continue
        cleaned.append([ch for ch in line if ch != " "])
    return Board.from_grid(cleaned)
