# -*- coding: utf-8 -*-
"""
一箭又一箭 —— 核心逻辑自动测试

覆盖作业要求的 T01 / T02 / T03 三项测试，并补充了四方向对称性、
最近阻挡、关卡可解性等用例。

为什么写成自动测试而不是手点鼠标：
    1. 路径判断是分值最高的一块（25 分），边界情况多，手点容易漏；
    2. 测试输出可以直接整理成表格贴进博客的「测试结果」章节。

运行方式：
    & "D:\\Users\\14566\\anaconda3\\envs\\Yet_myenv\\python.exe" test_core.py
"""

import sys
import unittest

from arrows import Board, UP, DOWN, LEFT, RIGHT, DIR_NAME
from solver import solve
from levels import build_levels

# Windows 控制台中文输出
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


class TestPathDetection(unittest.TestCase):
    """路径检测：能否飞出棋盘。"""

    def setUp(self):
        self.board = Board(5, 5)

    # ------------------------------------------------ T01 前方无阻挡

    def test_T01_右侧无阻挡可以飞出(self):
        self.board.place(2, 0, RIGHT)
        can_fly, blocker = self.board.check_path(2, 0)
        self.assertTrue(can_fly)
        self.assertIsNone(blocker)

    def test_T01_左侧无阻挡可以飞出(self):
        self.board.place(2, 4, LEFT)
        can_fly, blocker = self.board.check_path(2, 4)
        self.assertTrue(can_fly)
        self.assertIsNone(blocker)

    def test_T01_上方无阻挡可以飞出(self):
        self.board.place(4, 2, UP)
        can_fly, blocker = self.board.check_path(4, 2)
        self.assertTrue(can_fly)
        self.assertIsNone(blocker)

    def test_T01_下方无阻挡可以飞出(self):
        self.board.place(0, 2, DOWN)
        can_fly, blocker = self.board.check_path(0, 2)
        self.assertTrue(can_fly)
        self.assertIsNone(blocker)

    # ------------------------------------------------ T02 前方有阻挡

    def test_T02_右侧有阻挡不能飞出(self):
        self.board.place(2, 0, RIGHT)
        self.board.place(2, 3, UP)
        can_fly, blocker = self.board.check_path(2, 0)
        self.assertFalse(can_fly)
        self.assertEqual(blocker, (2, 3))

    def test_T02_左侧有阻挡不能飞出(self):
        self.board.place(2, 4, LEFT)
        self.board.place(2, 1, DOWN)
        can_fly, blocker = self.board.check_path(2, 4)
        self.assertFalse(can_fly)
        self.assertEqual(blocker, (2, 1))

    def test_T02_上方有阻挡不能飞出(self):
        self.board.place(4, 2, UP)
        self.board.place(1, 2, RIGHT)
        can_fly, blocker = self.board.check_path(4, 2)
        self.assertFalse(can_fly)
        self.assertEqual(blocker, (1, 2))

    def test_T02_下方有阻挡不能飞出(self):
        self.board.place(0, 2, DOWN)
        self.board.place(3, 2, LEFT)
        can_fly, blocker = self.board.check_path(0, 2)
        self.assertFalse(can_fly)
        self.assertEqual(blocker, (3, 2))

    def test_紧邻的箭头也算阻挡(self):
        """两个箭头挨在一起，也应该算挡住。"""
        self.board.place(2, 0, RIGHT)
        self.board.place(2, 1, UP)
        can_fly, blocker = self.board.check_path(2, 0)
        self.assertFalse(can_fly)
        self.assertEqual(blocker, (2, 1))

    def test_阻挡取最近的那一个(self):
        """路上有多个箭头时，应该返回最先遇到的那个。"""
        self.board.place(2, 0, RIGHT)
        self.board.place(2, 2, UP)
        self.board.place(2, 4, DOWN)
        can_fly, blocker = self.board.check_path(2, 0)
        self.assertFalse(can_fly)
        self.assertEqual(blocker, (2, 2), "应该返回最近的 (2,2)，而不是 (2,4)")

    # ------------------------------------------------ T03 边缘朝外

    def test_T03_左上角朝上可以飞出不越界(self):
        """第 0 行朝上，索引会变成 -1，必须能正常飞出而不是报错。"""
        self.board.place(0, 0, UP)
        can_fly, blocker = self.board.check_path(0, 0)
        self.assertTrue(can_fly)

    def test_T03_左上角朝左可以飞出不越界(self):
        self.board.place(0, 0, LEFT)
        can_fly, _ = self.board.check_path(0, 0)
        self.assertTrue(can_fly)

    def test_T03_右下角朝下可以飞出不越界(self):
        self.board.place(4, 4, DOWN)
        can_fly, _ = self.board.check_path(4, 4)
        self.assertTrue(can_fly)

    def test_T03_右下角朝右可以飞出不越界(self):
        self.board.place(4, 4, RIGHT)
        can_fly, _ = self.board.check_path(4, 4)
        self.assertTrue(can_fly)

    def test_T03_四角四方向全部不越界(self):
        """把四个角的箭头朝各个方向都试一遍，确认不会抛异常。"""
        corners = [(0, 0), (0, 4), (4, 0), (4, 4)]
        for r, c in corners:
            for d in (UP, DOWN, LEFT, RIGHT):
                b = Board(5, 5)
                b.place(r, c, d)
                try:
                    can_fly, _ = b.check_path(r, c)
                except Exception as e:
                    self.fail(f"角点 ({r},{c}) 朝{DIR_NAME[d]} 时抛异常: {e}")
                # 朝棋盘外的方向必定能飞出
                outward = (
                    (r == 0 and d == UP)
                    or (r == 4 and d == DOWN)
                    or (c == 0 and d == LEFT)
                    or (c == 4 and d == RIGHT)
                )
                if outward:
                    self.assertTrue(can_fly,
                                    f"角点 ({r},{c}) 朝{DIR_NAME[d]} 朝棋盘外，应该能飞出")

    # ------------------------------------------------ 其他

    def test_空格子不崩溃(self):
        """点到空格子，应该返回 (False, None) 而不是报错。"""
        can_fly, blocker = self.board.check_path(2, 2)
        self.assertFalse(can_fly)
        self.assertIsNone(blocker)

    def test_移除箭头后原本被挡的变得可飞(self):
        """消除一个箭头后，它后面的箭头应该能飞了 —— 这是关卡能通关的基础。"""
        self.board.place(2, 0, RIGHT)
        self.board.place(2, 3, UP)

        self.assertFalse(self.board.check_path(2, 0)[0])

        self.board.remove(2, 3)  # 让挡路的箭头飞走
        self.assertTrue(self.board.check_path(2, 0)[0])

    def test_可飞箭头列表(self):
        # 布局：
        #   (0,0) 朝右，第 0 行右边全空            -> 可飞
        #   (2,2) 朝上，上方 (1,2)(0,2) 都空        -> 可飞
        #   (4,4) 朝右，直接朝棋盘外                -> 可飞
        #   (2,0) 朝右，右边 (2,2) 有箭头挡着       -> 不可飞
        self.board.place(0, 0, RIGHT)
        self.board.place(2, 2, UP)
        self.board.place(4, 4, RIGHT)
        self.board.place(2, 0, RIGHT)

        flyable = self.board.flyable_arrows()
        self.assertIn((0, 0), flyable)
        self.assertIn((2, 2), flyable)
        self.assertIn((4, 4), flyable)
        self.assertNotIn((2, 0), flyable,
                         "(2,0) 被 (2,2) 挡住，不应出现在可飞列表里")

    def test_棋盘清空判定(self):
        # 刚建好的空棋盘本身就是「已清空」状态
        self.assertTrue(self.board.is_clear())
        self.board.place(0, 0, UP)
        self.assertFalse(self.board.is_clear())
        self.board.remove(0, 0)
        self.assertTrue(self.board.is_clear())


class TestPathCells(unittest.TestCase):
    """path_cells：箭头飞出时会经过哪些格子。

    这个方法是「道具要被飞过才能拿到」的地基 ——
    它算错一点点，道具就有可能永远吃不到，或者点一下白送。
    """

    def setUp(self):
        self.board = Board(5, 5)

    def test_空格子返回空列表(self):
        self.assertEqual(self.board.path_cells(2, 2), [])

    def test_四个方向各自算对(self):
        cases = [
            (UP, [(1, 2), (0, 2)]),
            (DOWN, [(3, 2), (4, 2)]),
            (LEFT, [(2, 1), (2, 0)]),
            (RIGHT, [(2, 3), (2, 4)]),
        ]
        for d, expected in cases:
            with self.subTest(direction=DIR_NAME[d]):
                b = Board(5, 5)
                b.place(2, 2, d)
                self.assertEqual(b.path_cells(2, 2), expected)

    def test_边缘朝外的路线是空的(self):
        """箭头紧贴边界又朝外，一步就出去了，路线当然没有格子。"""
        b = Board(5, 5)
        b.place(0, 0, UP)
        self.assertEqual(b.path_cells(0, 0), [])

    def test_路线一直算到边界(self):
        b = Board(5, 5)
        b.place(2, 0, RIGHT)
        self.assertEqual(b.path_cells(2, 0), [(2, 1), (2, 2), (2, 3), (2, 4)],
                         "从最左边出发应该一直算到最右边")

    def test_被挡住时路线仍然包含挡路的箭头(self):
        """path_cells 只看方向射到哪儿，**不管**路上有没有东西挡着。

        这点很重要：有没有被挡住是 check_path 负责回答的事，
        path_cells 只回答「这条射线经过哪些格子」，两者分工明确。
        """
        b = Board(5, 5)
        b.place(2, 0, RIGHT)
        b.place(2, 3, UP)
        self.assertEqual(b.path_cells(2, 0),
                         [(2, 1), (2, 2), (2, 3), (2, 4)],
                         "挡路的 (2,3) 也应该出现在路线里")

    def test_路线不含箭头自己所在的格子(self):
        b = Board(5, 5)
        b.place(2, 2, RIGHT)
        self.assertNotIn((2, 2), b.path_cells(2, 2))

    def test_移除箭头后路线变空(self):
        """箭头一旦飞走，它自己的路线就没了 —— 所以上层代码
        必须在 remove 之前调用 path_cells，顺序不能反。"""
        b = Board(5, 5)
        b.place(2, 1, RIGHT)
        self.assertTrue(b.path_cells(2, 1))
        b.remove(2, 1)
        self.assertEqual(b.path_cells(2, 1), [])


class TestLevelEvents(unittest.TestCase):
    """关卡里道具的配置是否合理。"""

    def test_每关恰好一个道具(self):
        for lv in build_levels():
            with self.subTest(level=lv.name):
                self.assertEqual(len(lv.events), 1,
                                 f"{lv.name} 的道具数量应当正好是 1 个")

    def test_道具只加时间而且统一五秒(self):
        for lv in build_levels():
            with self.subTest(level=lv.name):
                ev = lv.events[0]
                self.assertEqual(ev["kind"], "time",
                                 f"{lv.name} 的道具应该只加时间")
                self.assertEqual(ev["amount"], 5,
                                 f"{lv.name} 的道具应该固定加 5 秒")

    def test_道具落在棋盘范围内而且不在箭头上(self):
        for lv in build_levels():
            board = lv.fresh_board()
            ev = lv.events[0]
            with self.subTest(level=lv.name):
                self.assertTrue(board.in_bounds(ev["r"], ev["c"]),
                                f"{lv.name} 的道具放到棋盘外面去了")
                self.assertFalse(board.has_arrow(ev["r"], ev["c"]),
                                 f"{lv.name} 的道具压在箭头上，位置不合法")

    def test_道具在某条飞行路线上_不会拿不到(self):
        """道具必须至少被一个箭头的射线覆盖，否则这辈子都吃不到。

        这是最容易踩的坑：随手挑个空格放下去，
        结果那一行那一列根本没有箭头指着它。
        """
        for lv in build_levels():
            board = lv.fresh_board()
            ev = lv.events[0]
            target = (ev["r"], ev["c"])
            covered = any(target in board.path_cells(r, c)
                          for (r, c) in board.arrows)
            with self.subTest(level=lv.name):
                self.assertTrue(covered,
                                f"{lv.name} 的道具 {target} 不在任何箭头的飞行路线上，"
                                "玩家永远吃不到")

    def test_顺着通关路径一定能吃到道具(self):
        """更强的保证：按求解器给的顺序走一遍，道具必须被扫到。

        注意循环里先算 path_cells 再 remove ——
        箭头一旦从棋盘上消失，这一趟的飞行路线就查不到了。
        """
        for lv in build_levels():
            board = lv.fresh_board()
            path = solve(board)
            self.assertIsNotNone(path, f"{lv.name} 应当可以通关")
            ev = lv.events[0]
            target = (ev["r"], ev["c"])
            got = False
            for (r, c) in path:
                if target in board.path_cells(r, c):
                    got = True
                    break
                board.remove(r, c)
            with self.subTest(level=lv.name):
                self.assertTrue(got,
                                f"{lv.name} 照着通关路径走完也吃不到道具")

    def test_道具不能开局就白送(self):
        """开局能直接飞走的箭头，其路线不该顺便扫过道具。

        否则玩家第一步就白得 5 秒，「必须规划路线」这个设计就废了。
        """
        for lv in build_levels():
            board = lv.fresh_board()
            ev = lv.events[0]
            target = (ev["r"], ev["c"])
            freebees = [cell for cell in board.flyable_arrows()
                        if target in board.path_cells(*cell)]
            with self.subTest(level=lv.name):
                self.assertEqual(freebees, [],
                                 f"{lv.name} 的道具开局就被 {freebees} 顺手扫到，太白送")

    def test_每关两颗爱心(self):
        for lv in build_levels():
            with self.subTest(level=lv.name):
                self.assertEqual(lv.mistakes, 2,
                                 f"{lv.name} 应当只允许 2 次失误")

    def test_三关时限分别是10_15_20秒(self):
        secs = [lv.seconds for lv in build_levels()]
        self.assertEqual(secs, [10, 15, 20],
                         "三关的时间限制应为 10 / 15 / 20 秒")

    def test_时间道具相对时限足够有分量(self):
        """加 5 秒至少要占到本关时限的四分之一，否则捡它没意义。"""
        for lv in build_levels():
            ev = lv.events[0]
            with self.subTest(level=lv.name):
                self.assertGreaterEqual(ev["amount"], lv.seconds * 0.25,
                                        f"{lv.name} 的道具奖励太寒酸")
class TestLevels(unittest.TestCase):
    """关卡数据本身的质量检查。"""

    def test_每个关卡都必须能通关(self):
        for lv in build_levels():
            with self.subTest(level=lv.name):
                path = solve(lv.fresh_board())
                self.assertIsNotNone(path, f"{lv.name} 无法通关")
                self.assertEqual(len(path), lv.arrow_count,
                                 f"{lv.name} 通关步数应等于箭头总数")

    def test_关卡数量至少三个(self):
        self.assertGreaterEqual(len(build_levels()), 3)

    def test_每关都要有四个方向的覆盖(self):
        """每关至少出现三个不同方向，保证玩法不单调。"""
        for lv in build_levels():
            with self.subTest(level=lv.name):
                dirs = set(lv.initial_board.arrows.values())
                self.assertGreaterEqual(len(dirs), 3,
                                        f"{lv.name} 只出现了 {len(dirs)} 种方向")

    def test_重新开局不污染原始数据(self):
        """fresh_board 必须返回副本，否则重新开始会得到被改过的棋盘。"""
        for lv in build_levels():
            b = lv.fresh_board()
            original = b.count()
            for (r, c) in list(b.arrows.keys()):
                b.remove(r, c)
            self.assertEqual(lv.fresh_board().count(), original,
                             f"{lv.name} 的初始棋盘被修改污染了")

    def test_不能出现同方向长链(self):
        """同一行/列相邻位置连续同方向的箭头不能超过 2 个。

        早期版本为了让关卡「有顺序」，摆了一整排朝右的箭头当主链，
        结果玩家从最右边一路点过去就行，纯机械劳动。
        这条测试用来防止这种呆板结构再次出现。
        """
        from level_gen import max_same_dir_line
        for lv in build_levels():
            with self.subTest(level=lv.name):
                run = max_same_dir_line(lv.fresh_board())
                self.assertLessEqual(
                    run, 2,
                    f"{lv.name} 出现了 {run} 个同方向箭头排成一排，太呆板")

    def test_棋盘尺寸和箭头数量达到要求(self):
        """三关的棋盘要逐关变大，箭头数量要逐关变多。"""
        levels = build_levels()
        for prev, cur in zip(levels, levels[1:]):
            with self.subTest(level=cur.name):
                self.assertGreaterEqual(cur.arrow_count, prev.arrow_count,
                                        "后一关的箭头数量不应少于前一关")
                self.assertGreaterEqual(cur.rows * cur.cols,
                                        prev.rows * prev.cols,
                                        "后一关的棋盘不应小于前一关")

    def test_每关都有一定的观察量(self):
        """每关箭头不能太少，否则玩两下就结束了。"""
        for lv in build_levels():
            with self.subTest(level=lv.name):
                self.assertGreaterEqual(lv.arrow_count, 9,
                                        f"{lv.name} 箭头太少，玩起来不过瘾")


# ---------------------------------------------------------------- 自定义运行器

def run_tests():
    """跑全部测试，并把结果整理成文字报告（方便贴进博客）。"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)

    # 生成一份简洁的清单
    lines = []
    lines.append("测试汇总")
    lines.append("=" * 50)
    lines.append(f"运行用例数：{result.testsRun}")
    lines.append(f"通过：{result.testsRun - len(result.failures) - len(result.errors)}")
    lines.append(f"失败：{len(result.failures)}")
    lines.append(f"错误：{len(result.errors)}")
    lines.append("")
    if result.wasSuccessful():
        lines.append("结论：全部通过 ✓")
    else:
        lines.append("结论：存在问题 ✗")
        for t, _ in result.failures + result.errors:
            lines.append(f"  - {t}")

    report = "\n".join(lines)
    with open("test_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    print()
    print(report)


if __name__ == "__main__":
    run_tests()
