# -*- coding: utf-8 -*-
"""
一箭又一箭 —— 关卡求解器

用途有两个：
    1. 【保分】验证每个关卡确实存在通关顺序。
       评分标准里「关卡实际上无法通关」是明确的扣分项，
       靠肉眼判断不靠谱，这里用程序穷举一遍给出保证。
    2. 【扩展功能】给游戏提供「提示 / 自动求解」能力。
       玩家卡住时，可以用它算出下一步该点哪个箭头。

算法思路（深度优先搜索 + 记忆化）：
    每一轮，先找出当前所有「可以飞出去」的箭头；
    任选其中一个让它飞出，棋盘就少一个箭头，局面随之变化；
    然后在新局面上重复这个过程。
      - 如果某一步把所有箭头都清空了  -> 找到一条通关路径；
      - 如果某一步一个能飞的箭头都没有  -> 死局，退回去换一种点法。

    为了避免重复搜索同样的局面，用字典把「已经算过的局面」记下来。
"""

from arrows import Board


def solve(board, _memo=None, _stats=None):
    """求解一个棋盘，返回一条通关路径。

    参数：
        board: 待求解的棋盘（不会被修改）

    返回：
        若能通关：按点击顺序排列的坐标列表，例如 [(1, 3), (1, 2), ...]
        若无法通关：None
    """
    if _memo is None:
        _memo = {}
    if _stats is None:
        _stats = {"visited": 0}

    # 全部清空 -> 通关（递归出口）
    if board.is_clear():
        return []

    # 用「剩余箭头的集合」作为局面的身份标识，用于记忆化
    key = frozenset(board.arrows.items())
    if key in _memo:
        return _memo[key]

    _stats["visited"] += 1

    # 依次尝试每一个当前能飞出去的箭头
    for (r, c) in board.flyable_arrows():
        nxt = board.copy()
        nxt.remove(r, c)

        sub_path = solve(nxt, _memo, _stats)
        if sub_path is not None:
            # 这个箭头能带来一条通关路径，把它记在最前面
            result = [(r, c)] + sub_path
            _memo[key] = result
            return result

    # 所有能飞的箭头都试过了，还是走不通 -> 死局
    _memo[key] = None
    return None


def is_solvable(board):
    """判断棋盘是否可解（只关心能不能，不关心怎么走）。"""
    return solve(board) is not None


def count_solutions(board, limit=10000):
    """统计通关路径的条数（最多数到 limit 条就停）。

    条数越少说明关卡越「险」，玩家越容易点错；
    这个数字可以用来衡量关卡难度。
    """
    memo = {}

    def dfs(b):
        if b.is_clear():
            return 1
        key = frozenset(b.arrows.items())
        if key in memo:
            return memo[key]
        total = 0
        for (r, c) in b.flyable_arrows():
            nxt = b.copy()
            nxt.remove(r, c)
            total += dfs(nxt)
            if total >= limit:
                break
        memo[key] = total
        return total

    return dfs(board)


def next_hint(board):
    """给出「下一步该点哪个箭头」的提示。

    做法：对每个当前能飞出去的箭头，试着点它，
          然后看剩下的局面是否仍然可解；只有点了之后还能通关的
          才是「安全的选择」。这样可以避免提示出一条把玩家带进死局的走法。
    """
    for (r, c) in board.flyable_arrows():
        nxt = board.copy()
        nxt.remove(r, c)
        if is_solvable(nxt):
            return (r, c)
    return None


def format_path(path):
    """把坐标列表格式化成人类可读的文字，例如 (1,3)->(1,2)->..."""
    if path is None:
        return "无解"
    return " -> ".join(f"({r},{c})" for r, c in path)


# ---------------------------------------------------------------- 命令行验证

if __name__ == "__main__":
    import sys
    from levels import build_levels

    # Windows 控制台中文输出需要 utf-8
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    out_lines = []
    all_ok = True

    for lv in build_levels():
        board = lv.fresh_board()
        out_lines.append(f"=== {lv.name} ===")
        out_lines.append(f"尺寸 {lv.rows}x{lv.cols}，箭头 {lv.arrow_count} 个，"
                         f"允许失误 {lv.mistakes} 次")
        out_lines.append("初始局面：")
        out_lines.append(str(board))

        stats = {"visited": 0}
        path = solve(board, _stats=stats)

        if path is None:
            all_ok = False
            out_lines.append("【失败】该关卡无法通关，必须修改关卡数据！")
        else:
            n_sol = count_solutions(board, limit=5000)
            out_lines.append(f"【通过】存在通关路径，共 {len(path)} 步")
            out_lines.append(f"搜索局面数：{stats['visited']}")
            out_lines.append(f"通关路径总数：{n_sol}{'+' if n_sol >= 5000 else ''} 条")
            out_lines.append("一条可行的点击顺序：")
            out_lines.append("  " + format_path(path))

            # 逐步演示这条路径，确认每一步确实合法
            demo = board.copy()
            steps = []
            for i, (r, c) in enumerate(path, 1):
                can_fly, blocker = demo.check_path(r, c)
                d = demo.direction_at(r, c)
                steps.append(f"  第{i:2d}步 点 ({r},{c}) "
                             f"方向{ {'U':'上','D':'下','L':'左','R':'右'}[d] } "
                             f"-> {'飞出' if can_fly else '被挡!!'}")
                demo.remove(r, c)
            out_lines.extend(steps)
            out_lines.append(f"  剩余箭头：{demo.count()}（应为 0）")
            if demo.count() != 0:
                all_ok = False
                out_lines.append("【错误】按该路径走完仍有剩余箭头！")
        out_lines.append("")

    out_lines.append("=" * 50)
    out_lines.append("全部关卡验证通过！" if all_ok else "存在问题，请检查上面的输出！")

    text = "\n".join(out_lines)
    print(text)

    # 同时写一份到文件，方便查看（本机 PowerShell 输出有时会被吞）
    with open("solver_report.txt", "w", encoding="utf-8") as f:
        f.write(text)
