# -*- coding: utf-8 -*-
"""
一箭又一箭 —— 游戏流程测试（含界面冒烟测试）

这一份覆盖作业要求的 T04 / T05 / T06，另外顺带做界面的冒烟测试。

    T04  清除本关全部箭头      -> 显示通关并进入下一关
    T05  失误次数耗尽          -> 显示失败并允许重新开始
    T06  游戏进行中重新开始    -> 箭头布局和失误次数恢复

为什么界面也能自动测：
    给 SDL 设置 dummy 视频驱动，pygame 就会在「虚拟屏幕」上绘制，
    不需要真的弹出窗口，于是渲染代码也能被自动跑到，
    任何绘制时的报错都会当场暴露。
"""

import os
import sys
import time

# 关键：必须在 import pygame 之前设置，让它用虚拟显示驱动
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pygame
import unittest

from game import (Game, STATE_START, STATE_PLAYING, STATE_LEVEL_CLEAR,
                  STATE_FAILED, STATE_ALL_CLEAR, FLY_DURATION)
from solver import solve


class TestGameFlow(unittest.TestCase):
    """游戏流程：通关、失败、重新开始。"""

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.game = Game()
        self.game._enter_level(0)

    def _settle(self, ms=None):
        """等待动画播完并刷新状态。"""
        time.sleep((ms or FLY_DURATION + 60) / 1000.0)
        self.game._update_animations()

    def _draw_ok(self):
        """跑一次完整绘制，确认渲染代码不报错。"""
        self.game._draw()

    # ------------------------------------------------------------ T04

    def test_T04_清空全部箭头后进入通关界面(self):
        path = solve(self.game.board)
        self.assertIsNotNone(path)

        for (r, c) in path:
            self.game.on_click_arrow(r, c)

        self.assertEqual(self.game.board.count(), 0, "箭头应该全部被清除")
        self._settle()
        self._draw_ok()
        self.assertEqual(self.game.state, STATE_LEVEL_CLEAR,
                         "清空后应进入通关界面")

    def test_T04_通关后可以进入下一关(self):
        第1关 = 0
        path = solve(self.game.board)
        for (r, c) in path:
            self.game.on_click_arrow(r, c)
        self._settle()
        self.assertEqual(self.game.state, STATE_LEVEL_CLEAR)

        self.game._enter_level(self.game.level_index + 1)
        self.assertEqual(self.game.level_index, 1)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.level.name, "第 2 关 · 渐入佳境")
        self._draw_ok()

    def test_T04_三个关卡依次通关后进入全通关界面(self):
        for i in range(len(self.game.levels)):
            self.game._enter_level(i)
            path = solve(self.game.board)
            self.assertIsNotNone(path, f"第 {i+1} 关应当可以通关")
            for (r, c) in path:
                self.game.on_click_arrow(r, c)
            self._settle()

            if i < len(self.game.levels) - 1:
                self.assertEqual(self.game.state, STATE_LEVEL_CLEAR,
                                 f"第 {i+1} 关通关后应显示过关")
            else:
                self.assertEqual(self.game.state, STATE_ALL_CLEAR,
                                 "最后一关通关后应显示全部通关")
        self._draw_ok()

    # ------------------------------------------------------------ T05

    def test_T05_失误次数耗尽进入失败界面(self):
        # 找一个当前被挡住的箭头，反复点它直到机会用完
        blocked = None
        for (r, c) in sorted(self.game.board.arrows.keys()):
            can_fly, _ = self.game.board.check_path(r, c)
            if not can_fly:
                blocked = (r, c)
                break
        self.assertIsNotNone(blocked, "第 1 关里应该存在被挡住的箭头")

        allow = self.game.mistakes_left
        for _ in range(allow):
            self.game.on_click_arrow(*blocked)

        self.assertEqual(self.game.mistakes_left, 0)
        self.assertEqual(self.game.state, STATE_FAILED,
                         "失误次数用完后应进入失败界面")
        self._draw_ok()

    def test_T05_失败后可以重新开始本关(self):
        blocked = None
        for (r, c) in sorted(self.game.board.arrows.keys()):
            can_fly, _ = self.game.board.check_path(r, c)
            if not can_fly:
                blocked = (r, c)
                break
        for _ in range(self.game.mistakes_left):
            self.game.on_click_arrow(*blocked)
        self.assertEqual(self.game.state, STATE_FAILED)

        self.game._enter_level(self.game.level_index)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.assertEqual(self.game.mistakes_left, self.game.level.mistakes)

    # ------------------------------------------------------------ T06

    def test_T06_重新开始后棋盘和失误次数都恢复(self):
        before_arrows = dict(self.game.board.arrows)
        before_mistakes = self.game.mistakes_left

        # 先飞掉一个箭头、再制造一次失误
        flyable = self.game.board.flyable_arrows()
        self.assertTrue(flyable)
        self.game.on_click_arrow(*flyable[0])

        blocked = None
        for (r, c) in sorted(self.game.board.arrows.keys()):
            can_fly, _ = self.game.board.check_path(r, c)
            if not can_fly:
                blocked = (r, c)
                break
        if blocked:
            self.game.on_click_arrow(*blocked)

        self.assertNotEqual(dict(self.game.board.arrows), before_arrows)

        # 重新开始
        self.game._enter_level(self.game.level_index)
        self.assertEqual(dict(self.game.board.arrows), before_arrows,
                         "重新开始后箭头布局应完全恢复")
        self.assertEqual(self.game.mistakes_left, before_mistakes,
                         "重新开始后失误次数应恢复")

    # ------------------------------------------------------------ 倒计时

    def test_倒计时初始值等于关卡时限(self):
        for i, lv in enumerate(self.game.levels):
            self.game._enter_level(i)
            self.assertEqual(self.game.time_left_ms, lv.seconds * 1000,
                             f"{lv.name} 的初始倒计时应等于 {lv.seconds} 秒")

    def test_时间耗尽判定失败(self):
        self.game._enter_level(0)
        self.assertEqual(self.game.state, STATE_PLAYING)
        self.game.time_left_ms = 0
        self.game._check_timeout()
        self.assertEqual(self.game.state, STATE_FAILED, "时间到应该判定失败")
        self.assertEqual(self.game.fail_reason, "time")
        self._draw_ok()

    def test_棋盘清空后不再判超时(self):
        """已经清空只是还在播飞出动画时，倒计时归零不该算失败。"""
        path = solve(self.game.board)
        for (r, c) in path:
            self.game.on_click_arrow(r, c)
        self.assertEqual(self.game.board.count(), 0)
        # 此时飞出动画可能还在播，人为把时间清零
        self.game.time_left_ms = 0
        self.game._check_timeout()
        self.assertNotEqual(self.game.state, STATE_FAILED,
                            "已经清空棋盘就不该再判超时失败")

    def test_重新开始会重置倒计时(self):
        self.game._enter_level(0)
        self.game.time_left_ms = 1234
        self.game._enter_level(0)
        self.assertEqual(self.game.time_left_ms,
                         self.game.level.seconds * 1000)

    def test_每一关都有时间限制且逐关变长(self):
        secs = [lv.seconds for lv in self.game.levels]
        for s in secs:
            self.assertGreater(s, 0, "每关都必须有时间限制")
        for a, b in zip(secs, secs[1:]):
            self.assertGreaterEqual(b, a, "后面的关卡时间不应比前面短")

    def test_每关的爱心不超过两颗(self):
        """爱心是容错的额度，给多了就能乱点碰运气，统一收到 2 颗。"""
        for i, lv in enumerate(self.game.levels):
            with self.subTest(level=lv.name):
                self.game._enter_level(i)
                self.assertEqual(self.game.mistakes_left, 2)

    # ------------------------------------------------------------ 事件道具
    #
    # 这一组用例守的是新规则：道具**不能点**，只能靠箭头飞过时带走。
    # 之前是可点的，结果顺手一点就白得奖励，太便宜了。
    # 现在点上去应该和点空格子一样毫无反应。

    def _play_until_event(self, level_index):
        """按通关路径一路点下去，直到道具到手。返回是否吃到。"""
        self.game._enter_level(level_index)
        path = solve(self.game.board)
        for (r, c) in path:
            self.game.on_click_arrow(r, c)
            if all(e["triggered"] for e in self.game.events):
                return True
        return False

    def test_点道具格拿不到奖励(self):
        """点上去必须是没反应 —— 这是「不能再白拿」的核心保证。"""
        for i in range(len(self.game.levels)):
            with self.subTest(level=i + 1):
                self.game._enter_level(i)
                ev = self.game.events[0]
                before_time = self.game.time_left_ms
                before_hearts = self.game.mistakes_left
                self.game.on_click_arrow(ev["r"], ev["c"])
                self.assertFalse(ev["triggered"],
                                 f"第 {i+1} 关的道具被点出来了，规则失效")
                self.assertEqual(self.game.time_left_ms, before_time)
                self.assertEqual(self.game.mistakes_left, before_hearts)

    def test_每关只有一个加五秒的道具(self):
        for i, lv in enumerate(self.game.levels):
            with self.subTest(level=lv.name):
                self.game._enter_level(i)
                self.assertEqual(len(self.game.events), 1)
                ev = self.game.events[0]
                self.assertEqual(ev["kind"], "time")
                self.assertEqual(ev["amount"], 5)

    def test_第1关道具的正确吃法_先清挡路箭头再让箭头飞过(self):
        """第 1 关的道具在 (1,3)，只有 (1,0)R 的飞行路线会经过它。

        开局时 (1,0)R 被 (1,2)U 挡着飞不出去，
        所以必须先把 U 放走，R 才能一飞到底顺手带走道具。
        这条用例精确锁住这个两步解法。
        """
        self.game._enter_level(0)
        before = self.game.time_left_ms

        self.game.on_click_arrow(1, 2)      # 把挡路的 U 放走
        self.assertFalse(self.game.events[0]["triggered"],
                         "只飞走了挡路的箭头，这时还不该拿到道具")

        self.game.on_click_arrow(1, 0)      # R 现在能一路飞过 (1,3)
        self.assertTrue(self.game.events[0]["triggered"],
                        "(1,0)R 的飞行路线扫过 (1,3)，应该拿到道具")
        self.assertEqual(self.game.time_left_ms, before + 5000,
                         "拿到时间道具后应该正好多 5 秒")

    def test_三关的道具都能靠通关路径吃到(self):
        for i in range(len(self.game.levels)):
            with self.subTest(level=i + 1):
                self.assertTrue(self._play_until_event(i),
                                f"第 {i+1} 关的道具吃不到，可能被放到了死角")

    def test_拿到道具后倒计时真的变长了(self):
        """注意 _play_until_event 内部会重新进关，所以起始时间会被重置成
        本关的时限，断言要按「时限 + 5 秒」来算，而不是外面设的值。"""
        self.assertTrue(self._play_until_event(0))
        self.assertEqual(self.game.time_left_ms,
                         self.game.level.seconds * 1000 + 5000)
        self.assertEqual(len(self.game.taken_events), 1)

    def test_同一个道具不会被重复结算(self):
        """道具只有一份 —— 就算拿到之后再点同一条路线也不该重复给。"""
        self.game._enter_level(0)
        ev = self.game.events[0]
        self.game.collect_event(ev)
        after_first = self.game.time_left_ms
        self.game.collect_event(ev)
        self.assertEqual(self.game.time_left_ms, after_first,
                         "同一个道具不应重复发奖")
        self.assertEqual(len(self.game.taken_events), 1)

    def test_重新开始会重置道具(self):
        self.game._enter_level(0)
        self.game.collect_event(self.game.events[0])
        self.assertTrue(self.game.events[0]["triggered"])
        self.assertEqual(len(self.game.taken_events), 1)

        self.game._enter_level(0)
        self.assertFalse(self.game.events[0]["triggered"],
                         "重新开始后道具应该回到未触发状态")
        self.assertEqual(self.game.taken_events, [])

    def test_箭头飞过但不经过道具时拿不到(self):
        """反向验证：随便飞一个路线不经过道具的箭头，道具必须还在。"""
        self.game._enter_level(0)
        ev = self.game.events[0]
        target = (ev["r"], ev["c"])
        shooter = None
        for cell in self.game.board.flyable_arrows():
            if target not in self.game.board.path_cells(*cell):
                shooter = cell
                break
        self.assertIsNotNone(shooter, "第 1 关应该有路线不经道具的可飞箭头")
        before = self.game.time_left_ms
        self.game.on_click_arrow(*shooter)
        self.assertFalse(ev["triggered"])
        self.assertEqual(self.game.time_left_ms, before)

    # ------------------------------------------------------------ 结算表情图

    def test_三张结算图都能加载(self):
        for st in (STATE_LEVEL_CLEAR, STATE_FAILED, STATE_ALL_CLEAR):
            with self.subTest(state=st):
                img = self.game.result_images.get(st)
                self.assertIsNotNone(img, f"{st} 对应的表情图没加载出来")
                self.assertGreater(img.get_width(), 0)
                self.assertGreater(img.get_height(), 0)

    def test_结算图不会超出窗口(self):
        from game import WINDOW_W, WINDOW_H
        for st, img in self.game.result_images.items():
            if img is None:
                continue
            with self.subTest(state=st):
                self.assertLessEqual(img.get_width(), WINDOW_W)
                self.assertLessEqual(img.get_height(), WINDOW_H)

    def test_爱心绘制不报错(self):
        """爱心是程序化画的，各种数量都试一遍，确认不崩。"""
        from game import draw_hearts
        surf = pygame.Surface((400, 60))
        for total, remain in [(1, 1), (5, 5), (5, 0), (6, 3), (13, 7)]:
            with self.subTest(total=total, remain=remain):
                draw_hearts(surf, 0, 0, 20, total, remain)

    def test_结算界面在三种状态下都能绘制(self):
        for st in (STATE_LEVEL_CLEAR, STATE_FAILED, STATE_ALL_CLEAR):
            with self.subTest(state=st):
                self.game.state = st
                self.game.result_shown_at = pygame.time.get_ticks() - 500
                self.game._draw()
                # 弹入动画刚开始的一瞬间也要能画
                self.game.result_shown_at = pygame.time.get_ticks()
                self.game._draw()

    # ------------------------------------------------------------ 其他

    def test_点击空格子不扣机会(self):
        empty = None
        for r in range(self.game.board.rows):
            for c in range(self.game.board.cols):
                if not self.game.board.has_arrow(r, c):
                    empty = (r, c)
                    break
            if empty:
                break
        before = self.game.mistakes_left
        self.game.on_click_arrow(*empty)
        self.assertEqual(self.game.mistakes_left, before)

    def test_提示给出的是安全走法(self):
        from solver import next_hint, is_solvable
        cell = next_hint(self.game.board)
        self.assertIsNotNone(cell)
        # 按提示走一步之后，局面应该仍然可解
        nxt = self.game.board.copy()
        nxt.remove(*cell)
        self.assertTrue(is_solvable(nxt), "提示不应该把玩家带进死局")

    def test_每关界面都能正常绘制(self):
        for i in range(len(self.game.levels)):
            self.game._enter_level(i)
            self.game._draw()
        # 各个结算界面也各画一次
        for st, btn in ((STATE_LEVEL_CLEAR, self.game.btn_next),
                        (STATE_FAILED, self.game.btn_retry),
                        (STATE_ALL_CLEAR, self.game.btn_again)):
            self.game.state = st
            self.game._draw()
        self.game.state = STATE_START
        self.game._draw()

    def test_开始界面初始状态正确(self):
        g = Game()
        self.assertEqual(g.state, STATE_START)
        g._draw()


# ---------------------------------------------------------------- 运行

def run():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    import io
    buf = io.StringIO()
    result = unittest.TextTestRunner(verbosity=2, stream=buf).run(suite)

    lines = [buf.getvalue(), ""]
    lines.append("游戏流程测试汇总")
    lines.append("=" * 50)
    lines.append(f"运行用例数：{result.testsRun}")
    lines.append(f"通过：{result.testsRun - len(result.failures) - len(result.errors)}")
    lines.append(f"失败：{len(result.failures)}")
    lines.append(f"错误：{len(result.errors)}")
    if result.wasSuccessful():
        lines.append("结论：全部通过 OK")
    else:
        lines.append("结论：存在问题")
        for t, _ in result.failures + result.errors:
            lines.append(f"  - {t}")

    text = "\n".join(lines)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "test_game_report.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)
    print("done")


if __name__ == "__main__":
    run()
