# -*- coding: utf-8 -*-
"""
一箭又一箭 —— 游戏主程序（pygame 界面层）

这一层只管「怎么画」和「怎么响应鼠标键盘」，
所有游戏规则都交给 arrows.py / levels.py / solver.py 去算，
界面层自己不重复实现任何判定逻辑。

界面流程：
    开始界面 -> 游戏界面 -> （通关界面 -> 下一关）或（失败界面 -> 重来）
    -> 最后一关通关后进入全部通关界面

    每关都有时间限制，倒计时归零还没清空也算失败。
    结算界面会弹出对应的表情图。

    棋盘上的时间道具**不是点了就能拿的按钮**：
    只有当箭头沿着自己的方向飞出棋盘、路线正好穿过道具格时才算拿到。
    所以它考验的是路线规划 —— 把哪个箭头留到什么时候放飞。

操作：
    鼠标左键  点击箭头 / 点击按钮
    H 键      提示（高亮一个「点了不会走进死路」的箭头）
    R 键      重新开始本关
    ESC       退出
"""

import os
import sys
import math

# 自检模式（--smoke）：用虚拟显示驱动跑，不弹窗，把界面渲染成 PNG 存下来。
# 必须在 import pygame 之前设置，所以放在这里。
if "--smoke" in sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from arrows import UP, DOWN, LEFT, RIGHT, DELTA
from levels import build_levels
from solver import next_hint

# Windows 控制台中文输出（本机 PowerShell 有时吞输出，日志统一写文件）
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---------------------------------------------------------------- 显示常量

# 窗口留够地方给 8x8 的最大棋盘
WINDOW_W = 880
WINDOW_H = 800
FPS = 60

# 配色（深色背景 + 亮色箭头，对比清楚）
C_BG = (26, 30, 42)
C_PANEL = (34, 39, 54)
C_CELL_A = (42, 48, 66)
C_CELL_B = (37, 43, 59)
C_GRID = (58, 66, 88)
C_ARROW = (242, 193, 78)        # 金黄：普通箭头
C_ARROW_FLY = (126, 214, 126)   # 绿色：正在飞出
C_ARROW_BLOCK = (224, 92, 92)   # 红色：被挡住
C_HINT = (110, 190, 255)        # 蓝色：提示高亮
C_TEXT = (232, 236, 244)
C_TEXT_DIM = (150, 158, 178)
C_ACCENT = (242, 193, 78)
C_BTN = (52, 60, 82)
C_BTN_HOVER = (68, 78, 105)

# 爱心（表示剩余机会）
C_HEART = (240, 78, 104)        # 亮红：还剩的机会
C_HEART_LOST = (92, 66, 78)     # 暗红：已经失去的机会

# 时间条
C_TIME_OK = (108, 200, 158)     # 时间充裕：绿
C_TIME_WARN = (242, 193, 78)    # 时间过半：黄
C_TIME_DANGER = (224, 92, 92)   # 最后 10 秒：红

# 事件（加分道具）配色
C_PLUS_SLOT = (86, 96, 122)     # 未触发的道具槽
C_PLUS_ICON = (150, 240, 180)   # +N 道具图标

# 布局（加高信息栏，腾出放爱心和时间条的地方）
TOP_BAR_H = 132
BOTTOM_BAR_H = 96
CELL_MAX = 84
CELL_GAP = 4

# 动画时长（毫秒）
FLY_DURATION = 380
SHAKE_DURATION = 340

# ---------------------------------------------------------------- 界面状态

STATE_START = "start"
STATE_PLAYING = "playing"
STATE_LEVEL_CLEAR = "level_clear"
STATE_FAILED = "failed"
STATE_ALL_CLEAR = "all_clear"


# ---------------------------------------------------------------- 资源路径
#
# 这里有个打包才会暴露的坑：
#   直接跑源码时，__file__ 就是 game.py 所在的目录，资源就在旁边；
#   但用 PyInstaller 打成单个 exe 之后，程序会先把所有东西解压到
#   一个临时目录（sys._MEIPASS）再运行，__file__ 指向的是那个临时目录。
#   两种运行方式都得能找到表情图，所以统一走下面这个函数。
def app_path(*parts):
    """返回一个随程序一起分发的文件的绝对路径。"""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS              # 打包后：临时解压目录
    else:
        base = os.path.dirname(os.path.abspath(__file__))   # 源码运行：本文件所在目录
    return os.path.join(base, *parts)


# 中文字体候选，按顺序试。
# 游戏要拿到别人的机器上跑，不能假设对方系统一定装了微软雅黑，
# 所以多列几个 Windows 常见的中文字体，全都没有再退回默认字体。
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",     # 微软雅黑（Win10/11 自带）
    r"C:\Windows\Fonts\msyhbd.ttc",   # 微软雅黑粗体
    r"C:\Windows\Fonts\simhei.ttf",   # 黑体
    r"C:\Windows\Fonts\simsun.ttc",   # 宋体
    r"C:\Windows\Fonts\Deng.ttf",     # 等线
]
FONT_BOLD_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
] + FONT_CANDIDATES

# 资源目录：结算时弹出的表情图放在这里
HERE = os.path.dirname(os.path.abspath(__file__))
RES_DIR = app_path("resources")

# 三种结算场面各自对应的图
IMAGE_FILES = {
    STATE_LEVEL_CLEAR: "单关通过图.jpg",
    STATE_FAILED: "单关失败图.jpg",
    STATE_ALL_CLEAR: "全部通过图.jpg",
}


def make_font(size, bold=False):
    """加载中文字体。

    注意：pygame 3.13 环境下 SysFont() 会抛 TypeError，
    所以这里一律用字体文件路径直接加载（详见项目说明）。

    字体按候选列表依次尝试 —— 拿到别人机器上运行时，
    对方系统不一定有微软雅黑，多备几个就不会变成方块。
    万一全都没有，退回 pygame 默认字体（中文会显示成方块，但至少不崩）。
    """
    for path in (FONT_BOLD_CANDIDATES if bold else FONT_CANDIDATES):
        if not os.path.exists(path):
            continue
        try:
            return pygame.font.Font(path, size)
        except Exception:
            continue                      # 这个字体打不开，换下一个
    return pygame.font.Font(None, size)


def load_result_image(filename, max_w, max_h):
    """加载结算表情图，并按比例缩放到不超过 (max_w, max_h)。

    图片可能不是正方形，所以用等比缩放，免得被拉变形。
    加载失败时返回 None，调用方会跳过绘制 —— 图片缺失不该让游戏崩掉。
    """
    path = os.path.join(RES_DIR, filename)
    if not os.path.exists(path):
        return None
    try:
        img = pygame.image.load(path).convert()
    except Exception:
        return None

    w, h = img.get_size()
    scale = min(max_w / w, max_h / h, 1.0)
    if scale < 1.0:
        img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))
    return img


# ---------------------------------------------------------------- 心形绘制
#
# 用经典的心形参数方程画：
#     x = 16·sin³t
#     y = 13·cos t − 5·cos 2t − 2·cos 3t − cos 4t
# 好处是不依赖字体里有没有「♥」这个字符，颜色和大小都能精确控制。
# 采样出来的点会自动归一化到指定尺寸，所以换大小不用改一堆数字。

_HEART_SAMPLES = 60
_HEART_PTS = None


def _heart_unit_points():
    """采样并归一化好的单位心形轮廓（范围约 [-0.5, 0.5]，屏幕上 y 向下）。"""
    global _HEART_PTS
    if _HEART_PTS is not None:
        return _HEART_PTS

    raw = []
    for i in range(_HEART_SAMPLES):
        t = 2 * math.pi * i / _HEART_SAMPLES
        x = 16 * (math.sin(t) ** 3)
        # 参数方程里 y 轴向上，屏幕 y 轴向下，所以取负号翻转
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t)
              - 2 * math.cos(3 * t) - math.cos(4 * t))
        raw.append((x, y))

    xs = [p[0] for p in raw]
    ys = [p[1] for p in raw]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span = max(max_x - min_x, max_y - min_y)
    cx0 = (min_x + max_x) / 2
    cy0 = (min_y + max_y) / 2

    _HEART_PTS = [((x - cx0) / span, (y - cy0) / span) for (x, y) in raw]
    return _HEART_PTS


def draw_heart(surface, cx, cy, size, color, filled=True, outline=None):
    """在 (cx, cy) 处画一颗大小为 size 的心。

    filled=False 时画成空心（用来表示已经失去的机会）。
    """
    pts = [(cx + ux * size, cy + uy * size)
           for (ux, uy) in _heart_unit_points()]
    if filled:
        pygame.draw.polygon(surface, color, pts)
    else:
        pygame.draw.polygon(surface, color, pts, max(2, int(size * 0.09)))
    if outline:
        pygame.draw.polygon(surface, outline, pts, 1)


def draw_hearts(surface, x, y, size, total, remain, gap=6):
    """画一串爱心表示剩余机会，返回这串爱心占用的总宽度。

    remain 颗亮红实心，其余画成暗色空心 —— 一眼能看出还剩几条命。
    """
    for i in range(total):
        hx = x + i * (size + gap) + size // 2
        hy = y + size // 2
        if i < remain:
            draw_heart(surface, hx, hy, size, C_HEART, filled=True)
        else:
            draw_heart(surface, hx, hy, size, C_HEART_LOST, filled=False)
    return total * size + (total - 1) * gap


class Button:
    """一个简单的矩形按钮。"""

    def __init__(self, text, rect, font):
        self.text = text
        self.rect = pygame.Rect(rect)
        self.font = font

    def draw(self, surface, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        color = C_BTN_HOVER if hovered else C_BTN
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, C_GRID, self.rect, 2, border_radius=8)
        label = self.font.render(self.text, True, C_TEXT)
        lx = self.rect.x + (self.rect.width - label.get_width()) // 2
        ly = self.rect.y + (self.rect.height - label.get_height()) // 2
        surface.blit(label, (lx, ly))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


# ---------------------------------------------------------------- 箭头绘制

# 朝上的箭头轮廓（单位坐标，中心在原点，尺寸约 1x1）
# 绘制其他方向时，把这个轮廓旋转到对应角度即可。
_ARROW_SHAPE = [
    (0.00, -0.50),   # 箭尖
    (0.34, 0.02),    # 右翼
    (0.15, 0.02),    # 右翼内收
    (0.15, 0.48),    # 右下
    (-0.15, 0.48),   # 左下
    (-0.15, 0.02),   # 左翼内收
    (-0.34, 0.02),   # 左翼
]

# 每个方向对应的旋转角（度）。屏幕上 y 轴向下，顺时针为正。
_DIR_ANGLE = {
    UP: 0,
    RIGHT: 90,
    DOWN: 180,
    LEFT: 270,
}


def draw_arrow(surface, cx, cy, size, direction, color, alpha=255):
    """在 (cx, cy) 处画一个指定方向、颜色和透明度的箭头。"""
    angle = math.radians(_DIR_ANGLE[direction])
    cos_t = math.cos(angle)
    sin_t = math.sin(angle)

    pts = []
    for (x, y) in _ARROW_SHAPE:
        # 旋转
        rx = x * cos_t - y * sin_t
        ry = x * sin_t + y * cos_t
        # 缩放并平移到中心
        pts.append((cx + rx * size, cy + ry * size))

    if alpha >= 255:
        pygame.draw.polygon(surface, color, pts)
    else:
        # 半透明需要单独画到一个临时 surface 上
        tmp_size = int(size * 1.2) + 4
        tmp = pygame.Surface((tmp_size * 2, tmp_size * 2), pygame.SRCALPHA)
        local = [(tmp_size + (px - cx), tmp_size + (py - cy)) for (px, py) in pts]
        pygame.draw.polygon(tmp, color + (alpha,), local)
        surface.blit(tmp, (cx - tmp_size, cy - tmp_size))


# ---------------------------------------------------------------- 游戏主体

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("一箭又一箭")
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock = pygame.time.Clock()

        self.font_title = make_font(40, bold=True)
        self.font_big = make_font(30, bold=True)
        self.font_normal = make_font(22)
        self.font_small = make_font(17)

        self.levels = build_levels()
        self.state = STATE_START
        self.level_index = 0
        self.board = None
        self.mistakes_left = 0
        self.steps = 0

        # 倒计时（毫秒）。剩余时间归零则本关失败。
        self.time_left_ms = 0
        # 失败原因："time" 表示超时，"mistake" 表示机会用完
        self.fail_reason = ""

        # 事件道具（棋盘上可点的加分格）
        self.events = []
        self.taken_events = []    # 已触发的: [(r, c, kind, amount, 触发时刻)]

        # 结算表情图，启动时一次性加载好，避免每帧读盘
        self.result_images = {
            st: load_result_image(fn, int(WINDOW_W * 0.42), int(WINDOW_H * 0.40))
            for st, fn in IMAGE_FILES.items()
        }
        # 结算图出现的时刻（用于闪出动画）
        self.result_shown_at = 0

        # 动画：飞出中的箭头单独保存（已从棋盘移除，只做视觉表现）
        self.flying = []          # 每项: dict(r, c, direction, start, size, from_x, from_y)
        # 碰撞晃动：{ (r,c): start_time }
        self.shaking = {}
        self.hint_cell = None
        self.hint_until = 0
        self.message = ""
        self.message_until = 0
        # 超时提醒：只在第一次进入「最后 10 秒」时提示一次
        self.low_time_warned = False

        self._build_buttons()
        self._enter_level(0)
        # _enter_level 会把状态设成「游戏中」，但刚启动时应该先显示开始界面，
        # 等玩家点了「开始游戏」再真正进入第 1 关。
        self.state = STATE_START

    # ------------------------------------------------------------ 按钮

    def _build_buttons(self):
        """底部按钮。位置固定，不同状态下靠可见性控制。"""
        bw, bh = 140, 46
        # 底部区域从上往下排：按钮 -> 提示文字，都留出余量
        y = WINDOW_H - BOTTOM_BAR_H + 14
        cx = WINDOW_W // 2

        self.btn_restart = Button("重新开始", (cx - bw - 12, y, bw, bh), self.font_normal)
        self.btn_hint = Button("提示 (H)", (cx + 12, y, bw, bh), self.font_normal)

        # 开始界面 / 结算界面的大按钮，按窗口高度取位置，别写死
        self.btn_start = Button("开始游戏", (cx - 100, int(WINDOW_H * 0.70), 200, 56),
                                self.font_big)
        self.btn_next = Button("下一关", (cx - 100, int(WINDOW_H * 0.70), 200, 56),
                               self.font_big)
        self.btn_retry = Button("再来一次", (cx - 100, int(WINDOW_H * 0.70), 200, 56),
                                self.font_big)
        self.btn_again = Button("再玩一次", (cx - 100, int(WINDOW_H * 0.70), 200, 56),
                                self.font_big)

    # ------------------------------------------------------------ 关卡流程

    def _enter_level(self, index):
        """进入指定关卡，重置棋盘、失误次数、倒计时和动画。"""
        self.level_index = index
        level = self.levels[index]
        self.board = level.fresh_board()
        self.mistakes_left = level.mistakes
        self.steps = 0
        self.time_left_ms = level.seconds * 1000
        self.fail_reason = ""
        self.low_time_warned = False
        self.events = level.fresh_events()
        self.taken_events = []
        self.flying.clear()
        self.shaking.clear()
        self.hint_cell = None
        self.message = ""
        self.result_shown_at = pygame.time.get_ticks()
        self.state = STATE_PLAYING

    @property
    def level(self):
        return self.levels[self.level_index]

    # ------------------------------------------------------------ 棋盘布局

    def _board_rect(self):
        """计算棋盘在屏幕上的位置和格子大小（按当前关卡自适应）。

        注意这里的尺寸口径：整块棋盘宽度 = 列数 * 格子边长 + (列数 - 1) * 间距，
        也就是「格子之间的间距」比「格子数量」少一个。
        之前把间距按列数算，导致估算宽度偏大、棋盘没有真正居中。
        """
        margin_x = 50
        margin_y = 24
        avail_w = WINDOW_W - margin_x * 2
        avail_h = WINDOW_H - TOP_BAR_H - BOTTOM_BAR_H - margin_y * 2
        rows, cols = self.board.rows, self.board.cols

        # 先按可用空间推算格子边长（含间距的等效尺寸），再拆出边长
        cell_with_gap = min(avail_w // cols, avail_h // rows, CELL_MAX + CELL_GAP)
        cell = max(cell_with_gap - CELL_GAP, 20)

        w = cols * cell + (cols - 1) * CELL_GAP
        h = rows * cell + (rows - 1) * CELL_GAP
        x = (WINDOW_W - w) // 2
        y = TOP_BAR_H + margin_y + max(0, (avail_h - h) // 2)
        return x, y, cell

    def _cell_center(self, r, c):
        """格子中心在屏幕上的坐标。"""
        x, y, cell = self._board_rect()
        cx = x + c * (cell + CELL_GAP) + cell // 2
        cy = y + r * (cell + CELL_GAP) + cell // 2
        return cx, cy

    def _hit_cell(self, pos):
        """把鼠标坐标换算成格子坐标；不在棋盘内则返回 None。"""
        x, y, cell = self._board_rect()
        mx, my = pos
        c = (mx - x) // (cell + CELL_GAP)
        r = (my - y) // (cell + CELL_GAP)
        if 0 <= r < self.board.rows and 0 <= c < self.board.cols:
            # 还要确认没有点在格子的间隙上
            left = x + c * (cell + CELL_GAP)
            top = y + r * (cell + CELL_GAP)
            if left <= mx < left + cell and top <= my < top + cell:
                return (r, c)
        return None

    # ------------------------------------------------------------ 玩家操作

    def collect_event(self, ev):
        """结算一个已经拿到的事件道具，发放奖励。

        注意这个函数**不做「凭什么拿到」的判定** —— 那是调用方的活。
        现在的规则是「箭头飞过时顺手带走」，判定在
        _collect_events_on_path() 里做，本函数只负责发奖。
        好处是：将来要是想改回「点一下就能拿」，只需要换判定那一段。

        这里必须先判断 triggered —— 尽管调用方也会过滤，
        但发奖属于「有副作用」的操作，自己也要挡住重复触发，
        否则一旦别处漏了检查就会无限刷奖励。
        """
        if ev.get("triggered"):
            return

        ev["triggered"] = True
        kind = ev["kind"]
        amount = ev["amount"]

        if kind == "time":
            self.time_left_ms += amount * 1000
            self._show_message(f"箭头扫过时间道具，+{amount} 秒！", C_PLUS_ICON)
        elif kind == "mistake":
            self.mistakes_left += amount
            self._show_message(f"箭头扫过爱心道具，机会 +{amount}！", C_HEART)
        else:  # both
            self.time_left_ms += amount * 1000
            self.mistakes_left += amount
            self._show_message(f"扫到道具！时间 +{amount} 秒、机会 +{amount}！",
                               C_PLUS_ICON)

        self.taken_events.append((ev["r"], ev["c"], kind, amount,
                                  pygame.time.get_ticks()))

    def _collect_events_on_path(self, r, c):
        """箭头从 (r, c) 飞出时，把飞行路线上的道具一并收走。

        这是「道具不能白拿」的关键：只有箭头真的从道具格上飞过去才算数，
        点一下是拿不到的。

        【为什么必须在 board.remove 之前调用】
        path_cells(r, c) 的第一步就是 has_arrow(r, c)，
        箭头一旦从棋盘上移除，这个方法直接返回空列表，
        就再也拿不到飞行路线了。所以顺序不能反。

        返回本次拿到的道具列表，方便调用方和测试确认结果。
        """
        cells = self.board.path_cells(r, c)
        if not cells:
            return []

        got = []
        for e in self.events:
            if e["triggered"]:
                continue
            if (e["r"], e["c"]) in cells:
                got.append(e)
        for e in got:
            self.collect_event(e)
        return got

    def on_click_arrow(self, r, c):
        """玩家点了棋盘上的 (r, c)。"""
        if self.state != STATE_PLAYING:
            return
        if not self.board.has_arrow(r, c):
            return  # 点到空格子，忽略

        can_fly, blocker = self.board.check_path(r, c)

        if can_fly:
            # 先看这趟飞行会扫到哪些道具 —— 必须在 remove 之前，
            # 否则 path_cells 拿不到箭头，路线就没了。
            got = self._collect_events_on_path(r, c)

            # 逻辑上立刻移除，视觉上交给飞出动画慢慢飘走。
            # 这样做的好处：动画播放期间逻辑状态已经是「没了」，
            # 不会影响后续箭头的判定。
            direction = self.board.direction_at(r, c)
            self.board.remove(r, c)
            fx, fy = self._cell_center(r, c)
            self.flying.append({
                "r": r, "c": c,
                "direction": direction,
                "start": pygame.time.get_ticks(),
                "from_x": fx, "from_y": fy,
            })
            self.steps += 1
            self.hint_cell = None
            # 拿到道具时优先播道具提示，它比「飞出去了」更值得看一眼
            if not got:
                self._show_message("飞出去了！", C_ARROW_FLY)
        else:
            # 被挡住：扣一次失误，箭头晃动 + 变红
            self.mistakes_left -= 1
            self.shaking[(r, c)] = pygame.time.get_ticks()
            if blocker is not None:
                self._show_message(f"被 ({blocker[0]},{blocker[1]}) 挡住了，还剩 "
                                   f"{self.mistakes_left} 次机会", C_ARROW_BLOCK)
            else:
                self._show_message("这里没有箭头", C_TEXT_DIM)

        self._check_result()

    def _check_result(self):
        """每次操作后检查是否通关或失败。"""
        if self.board.is_clear():
            # 等飞出动画播完再切界面，观感更连贯
            if not self.flying:
                self._enter_result()
        elif self.mistakes_left <= 0:
            self.fail_reason = "mistake"
            self._enter_result()

    def _enter_result(self):
        """切换到结算界面，并记录表情图开始闪出的时刻。"""
        if self.board.is_clear():
            if self.level_index >= len(self.levels) - 1:
                self.state = STATE_ALL_CLEAR
            else:
                self.state = STATE_LEVEL_CLEAR
        else:
            self.state = STATE_FAILED
        self.result_shown_at = pygame.time.get_ticks()

    def _check_timeout(self):
        """倒计时归零 -> 本关失败。由主循环每帧调用。"""
        if self.state != STATE_PLAYING:
            return
        # 棋盘已清空时不再判超时（正在播飞出动画，属于已经完成）
        if self.board.is_clear():
            return
        if self.time_left_ms <= 0:
            self.time_left_ms = 0
            self.fail_reason = "time"
            self._enter_result()

    def _show_message(self, text, color):
        self.message = text
        self.message_color = color
        self.message_until = pygame.time.get_ticks() + 1600

    def use_hint(self):
        """提示：高亮一个「点了之后仍然能通关」的箭头。"""
        if self.state != STATE_PLAYING:
            return
        cell = next_hint(self.board)
        if cell is None:
            self._show_message("这个局面已经没有安全走法了", C_ARROW_BLOCK)
            return
        self.hint_cell = cell
        self.hint_until = pygame.time.get_ticks() + 2500
        self._show_message(f"试试 ({cell[0]},{cell[1]})", C_HINT)

    # ------------------------------------------------------------ 主循环

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)

            # 倒计时：只在游戏进行中走表
            if self.state == STATE_PLAYING:
                self.time_left_ms -= dt
                self._check_timeout()
                # 最后 10 秒给一次提示
                if (not self.low_time_warned
                        and 0 < self.time_left_ms <= 10000):
                    self.low_time_warned = True
                    self._show_message("最后 10 秒！", C_ARROW_BLOCK)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_h:
                        self.use_hint()
                    elif event.key == pygame.K_r and self.state in (
                            STATE_PLAYING, STATE_FAILED):
                        self._enter_level(self.level_index)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)

            self._update_animations()
            self._draw()

        pygame.quit()

    def _handle_click(self, pos):
        if self.state == STATE_START:
            if self.btn_start.is_clicked(pos):
                self._enter_level(0)
        elif self.state == STATE_PLAYING:
            if self.btn_restart.is_clicked(pos):
                self._enter_level(self.level_index)
            elif self.btn_hint.is_clicked(pos):
                self.use_hint()
            else:
                cell = self._hit_cell(pos)
                if cell is not None:
                    # 道具不再是「点一下就拿到」的按钮了，只能靠箭头飞过时带走，
                    # 所以这里不需要也不能判断事件格 —— 点到道具格就是点到空格子。
                    self.on_click_arrow(*cell)
        elif self.state == STATE_LEVEL_CLEAR:
            if self.btn_next.is_clicked(pos):
                self._enter_level(self.level_index + 1)
        elif self.state == STATE_FAILED:
            if self.btn_retry.is_clicked(pos):
                self._enter_level(self.level_index)
        elif self.state == STATE_ALL_CLEAR:
            if self.btn_again.is_clicked(pos):
                self._enter_level(0)

    def _update_animations(self):
        """清理已经播完的动画。"""
        now = pygame.time.get_ticks()

        self.flying = [f for f in self.flying
                       if now - f["start"] < FLY_DURATION]
        self.shaking = {k: v for k, v in self.shaking.items()
                        if now - v < SHAKE_DURATION}

        # 飞出动画播完后，如果棋盘已空，补一次结果检查
        if self.state == STATE_PLAYING and self.board.is_clear() and not self.flying:
            self._check_result()

        if self.hint_cell and now > self.hint_until:
            self.hint_cell = None

    # ------------------------------------------------------------ 绘制

    def _draw(self):
        self.screen.fill(C_BG)
        mouse = pygame.mouse.get_pos()

        if self.state == STATE_START:
            self._draw_start(mouse)
        else:
            self._draw_top_bar()
            self._draw_board()
            # 结算时底部按钮没有意义（有遮罩盖着也点不到），不画更清爽
            if self.state == STATE_PLAYING:
                self._draw_bottom_bar(mouse)
            else:
                pygame.draw.rect(self.screen, C_PANEL,
                                 (0, WINDOW_H - BOTTOM_BAR_H, WINDOW_W, BOTTOM_BAR_H))

            if self.state != STATE_PLAYING:
                self._draw_overlay(mouse)

            # 操作反馈文字最后画，保证盖在遮罩之上，不会被压暗
            self._draw_message()

        pygame.display.flip()

    def _draw_result_summary(self):
        """结算界面的标题和副标题文字。"""
        if self.state == STATE_LEVEL_CLEAR:
            return "过关！", f"用了 {self.steps} 步 · 剩余 {self.clock_text()}"
        if self.state == STATE_ALL_CLEAR:
            return "全部通关！", f"共 {len(self.levels)} 关 · 最后一关用了 {self.steps} 步"
        # 失败分两种原因，文案要区分开
        if self.fail_reason == "time":
            return "时间到！", f"还剩 {self.board.count()} 个箭头没清完"
        return "失败", "失误机会用完了"

    def clock_text(self):
        """把剩余毫秒格式化成 mm:ss。"""
        total = max(0, self.time_left_ms) // 1000
        return f"{total // 60:02d}:{total % 60:02d}"

    def _draw_start(self, mouse):
        title = self.font_title.render("一箭又一箭", True, C_ACCENT)
        self.screen.blit(title, ((WINDOW_W - title.get_width()) // 2,
                                 int(WINDOW_H * 0.16)))

        rules = [
            "点击箭头，让它沿着自己指的方向飞出棋盘。",
            "路上有别的东西挡着就飞不出去，还会扣掉一颗爱心。",
            "每关都有倒计时，清空全部箭头过关，爱心用完或时间到就失败。",
            "棋盘上发光的表盘是时间道具 —— 点它没用，",
            "　要让箭头飞出去时从它上面穿过去，才能 +5 秒。",
            "",
            "操作：鼠标点击箭头　H 提示　R 重开　ESC 退出",
        ]
        y = int(WINDOW_H * 0.28)
        for line in rules:
            surf = self.font_normal.render(line, True, C_TEXT)
            self.screen.blit(surf, ((WINDOW_W - surf.get_width()) // 2, y))
            y += 40

        self.btn_start.draw(self.screen, mouse)

    def _draw_top_bar(self):
        """顶部信息栏：关卡名 / 剩余箭头和步数 / 爱心（剩余机会）/ 倒计时。"""
        pygame.draw.rect(self.screen, C_PANEL, (0, 0, WINDOW_W, TOP_BAR_H))

        level = self.level
        # 第一行：关卡名 + 关卡进度
        name_surf = self.font_big.render(level.name, True, C_ACCENT)
        self.screen.blit(name_surf, (24, 10))
        prog = self.font_small.render(
            f"第 {self.level_index + 1} / {len(self.levels)} 关", True, C_TEXT_DIM)
        self.screen.blit(prog, (24 + name_surf.get_width() + 16,
                                10 + name_surf.get_height() - prog.get_height() - 4))

        # 第二行：剩余箭头、步数
        info = self.font_normal.render(
            f"剩余箭头 {self.board.count()}　　步数 {self.steps}", True, C_TEXT)
        self.screen.blit(info, (24, 52))

        # 第三行左：爱心表示剩余机会
        heart_size = 20
        label = self.font_small.render("机会", True, C_TEXT_DIM)
        self.screen.blit(label, (24, 90))
        max_hearts = max(self.level.mistakes, self.mistakes_left)
        draw_hearts(self.screen, 24 + label.get_width() + 10, 88,
                    heart_size, max_hearts, self.mistakes_left)

        # 第三行右：倒计时条 + 数字
        self._draw_time_bar()

    def _draw_time_bar(self):
        """右上角的倒计时：一根进度条 + 剩余秒数。

        颜色随时间变：绿 -> 黄 -> 红，最后 10 秒还会闪。
        """
        bar_w, bar_h = 260, 20
        x = WINDOW_W - bar_w - 30
        y = 88

        level = self.level
        total = max(1, level.seconds * 1000)
        ratio = max(0.0, min(1.0, self.time_left_ms / total))

        label = self.font_small.render("剩余时间", True, C_TEXT_DIM)
        self.screen.blit(label, (x, y - 24))

        # 底槽
        pygame.draw.rect(self.screen, (46, 52, 70),
                         (x, y, bar_w, bar_h), border_radius=6)

        # 进度条本身
        if ratio > 0.5:
            color = C_TIME_OK
        elif ratio > 0.18:
            color = C_TIME_WARN
        else:
            color = C_TIME_DANGER
            # 最后阶段闪烁提醒
            blink = (pygame.time.get_ticks() // 220) % 2 == 0
            if blink:
                color = (255, 140, 140)

        fill_w = int(bar_w * ratio)
        if fill_w > 0:
            pygame.draw.rect(self.screen, color,
                             (x, y, fill_w, bar_h), border_radius=6)
        pygame.draw.rect(self.screen, C_GRID,
                         (x, y, bar_w, bar_h), 2, border_radius=6)

        # 剩余秒数（贴在条上）
        secs = max(0, self.time_left_ms) // 1000
        num = self.font_normal.render(f"{secs} 秒", True, C_TEXT)
        self.screen.blit(num, (x + bar_w - num.get_width(), y - 26))

    def _draw_event_icon(self, cx, cy, cell, event, now):
        """画一个事件道具图标。

        - kind == time    : 画一个表盘
        - kind == mistake : 画一颗爱心
        - kind == both    : 外面套一圈光环，表示两种奖励都给
        图标会缓慢呼吸，提示玩家「这里有个道具」。
        注意它现在**不可点**，只能等箭头飞过时带着走 ——
        所以这里不会画 hover 效果，免得误导玩家去点。
        """
        # 呼吸效果
        pulse = 1 + 0.08 * math.sin(now / 260)
        r = int(cell * 0.34 * pulse)
        kind = event["kind"]

        # 底圈
        pygame.draw.circle(self.screen, C_PLUS_SLOT, (cx, cy), r + 4)
        pygame.draw.circle(self.screen, C_PLUS_ICON, (cx, cy), r + 4, 2)

        if kind == "time":
            # 表盘：一个圆 + 指向 12 点的指针
            pygame.draw.circle(self.screen, C_PLUS_ICON, (cx, cy), r, 2)
            pygame.draw.line(self.screen, C_PLUS_ICON,
                             (cx, cy), (cx, cy - r + 3), 3)
            pygame.draw.line(self.screen, C_PLUS_ICON,
                             (cx, cy), (cx + int(r * 0.62), cy), 3)
        elif kind == "mistake":
            draw_heart(self.screen, cx, cy, int(r * 1.5), C_HEART, filled=True)
        else:
            # both：心形 + 外圈，一眼看出是双份奖励
            draw_heart(self.screen, cx, cy, int(r * 1.4), C_HEART, filled=True)
            pygame.draw.circle(self.screen, C_ACCENT, (cx, cy), r + 8, 2)

        # 数字标注：告诉玩家奖励多少
        amount = event["amount"]
        label = self.font_small.render(f"+{amount}", True, C_PLUS_ICON)
        self.screen.blit(label, (cx - label.get_width() // 2,
                                 cy + r + 6))

    def _draw_board(self):
        x, y, cell = self._board_rect()
        now = pygame.time.get_ticks()

        # 棋盘底格
        for r in range(self.board.rows):
            for c in range(self.board.cols):
                gx = x + c * (cell + CELL_GAP)
                gy = y + r * (cell + CELL_GAP)
                color = C_CELL_A if (r + c) % 2 == 0 else C_CELL_B
                pygame.draw.rect(self.screen, color,
                                 (gx, gy, cell, cell), border_radius=6)
                pygame.draw.rect(self.screen, C_GRID,
                                 (gx, gy, cell, cell), 1, border_radius=6)

        # 事件道具格：还没被捡走的画成发光的图标
        for e in self.events:
            if e["triggered"]:
                continue
            cx, cy = self._cell_center(e["r"], e["c"])
            self._draw_event_icon(cx, cy, cell, e, now)

        # 棋盘上的箭头
        for (r, c), direction in sorted(self.board.arrows.items()):
            cx, cy = self._cell_center(r, c)

            color = C_ARROW
            offset_x = offset_y = 0

            # 碰撞晃动：左右小幅摆动，幅度随时间衰减
            if (r, c) in self.shaking:
                t = (now - self.shaking[(r, c)]) / SHAKE_DURATION
                color = C_ARROW_BLOCK
                amp = (1 - t) * cell * 0.12
                offset_x = math.sin(t * 40) * amp

            # 提示高亮：闪一闪
            if self.hint_cell == (r, c):
                color = C_HINT
                pulse = 1 + 0.12 * math.sin(now / 90)
                cx_extra = 0
                size = cell * 0.62 * pulse
                # 画一个高亮圈
                pygame.draw.circle(self.screen, C_HINT,
                                   (cx + offset_x, cy + offset_y),
                                   int(cell * 0.46), 2)
            else:
                size = cell * 0.62

            draw_arrow(self.screen, cx + offset_x, cy + offset_y,
                       size, direction, color)

        # 正在飞出的箭头：沿方向平移 + 淡出
        for f in self.flying:
            t = (now - f["start"]) / FLY_DURATION
            if t > 1:
                continue
            dr, dc = DELTA[f["direction"]]
            # 用平方曲线，飞出去有个加速的感觉
            dist = (cell + CELL_GAP) * 3.2 * (t ** 1.6)
            fx = f["from_x"] + dc * dist
            fy = f["from_y"] + dr * dist
            alpha = int(255 * (1 - t))
            draw_arrow(self.screen, fx, fy, cell * 0.62,
                       f["direction"], C_ARROW_FLY, alpha)

    def _draw_bottom_bar(self, mouse):
        y = WINDOW_H - BOTTOM_BAR_H
        pygame.draw.rect(self.screen, C_PANEL, (0, y, WINDOW_W, BOTTOM_BAR_H))
        self.btn_restart.draw(self.screen, mouse)
        self.btn_hint.draw(self.screen, mouse)

        tip = "提示：先看哪几个箭头前方是空的　|　发光表盘要箭头飞过才生效"
        surf = self.font_small.render(tip, True, C_TEXT_DIM)
        # 贴着底边往上留一点余量，避免被窗口边缘切掉
        self.screen.blit(surf, ((WINDOW_W - surf.get_width()) // 2,
                                WINDOW_H - surf.get_height() - 8))

    def _draw_message(self):
        """操作反馈文字。

        游戏中显示在顶部信息栏下方；结算界面时挪到窗口最底部，
        免得和表情图、结算标题挤在一起。
        """
        if not self.message or pygame.time.get_ticks() > self.message_until:
            return
        color = getattr(self, "message_color", C_TEXT)
        surf = self.font_normal.render(self.message, True, color)
        x = (WINDOW_W - surf.get_width()) // 2
        if self.state == STATE_PLAYING:
            y = TOP_BAR_H + 10
        else:
            y = WINDOW_H - surf.get_height() - 12
        self.screen.blit(surf, (x, y))

    def _draw_overlay(self, mouse):
        """结算界面：半透明遮罩 + 表情图 + 文字 + 按钮。

        表情图会有一个「弹一下」的出场效果：从略小放大到正常，
        比直接出现更有精神，也更像「闪」出来。
        """
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill((10, 12, 18, 232))
        self.screen.blit(overlay, (0, 0))

        title, subtitle = self._draw_result_summary()
        btn = {
            STATE_LEVEL_CLEAR: self.btn_next,
            STATE_FAILED: self.btn_retry,
            STATE_ALL_CLEAR: self.btn_again,
        }[self.state]

        # ---- 表情图：带弹入动画 ----
        img = self.result_images.get(self.state)
        # 纵向排布：图 -> 标题 -> 副标题 -> 按钮，整体在窗口里居中。
        # 图片高度按实际尺寸算，不能写死，否则大图会顶出窗口。
        title_h, sub_h, btn_h = 52, 36, 56
        block_gap = 20
        if img is not None:
            w, h = img.get_size()
            content_h = h + block_gap + title_h + sub_h + 34 + btn_h
            top = max(24, (WINDOW_H - content_h) // 2)
            img_bottom = top + h

            elapsed = pygame.time.get_ticks() - self.result_shown_at
            t = min(1.0, elapsed / 260.0)
            overshoot = 1.70158
            s = 1 + (overshoot + 1) * ((t - 1) ** 3) + overshoot * ((t - 1) ** 2)
            sw, sh = max(1, int(w * s)), max(1, int(h * s))
            scaled = pygame.transform.smoothscale(img, (sw, sh))
            ix = (WINDOW_W - sw) // 2
            iy = img_bottom - sh

            # 图后面垫一层浅色圆角底，避免深色图糊在深色背景上看不清
            pad = 8
            pygame.draw.rect(self.screen, (238, 240, 246),
                             (ix - pad, iy - pad, sw + pad * 2, sh + pad * 2),
                             border_radius=14)
            self.screen.blit(scaled, (ix, iy))
        else:
            img_bottom = 250

        # ---- 文字 ----
        t_surf = self.font_title.render(title, True, C_ACCENT)
        self.screen.blit(t_surf, ((WINDOW_W - t_surf.get_width()) // 2,
                                  img_bottom + block_gap))

        s_surf = self.font_normal.render(subtitle, True, C_TEXT)
        self.screen.blit(s_surf, ((WINDOW_W - s_surf.get_width()) // 2,
                                  img_bottom + block_gap + title_h))

        # 按钮放在文字下方固定间距处，跟着整体位置走
        btn.rect.y = img_bottom + block_gap + title_h + sub_h + 34
        btn.draw(self.screen, mouse)


# ---------------------------------------------------------------- 入口

def run_smoke_test(out_dir=None):
    """打包后的自检：渲染几个界面存成 PNG，用来确认「拿到别人机器上也能正常显示」。

    用法：
        yet-arrow-away.exe --smoke [输出目录]

    为什么需要它：打成 exe 之后是看不到控制台的，资源路径、中文字体
    这类问题在开发者机器上根本暴露不出来（因为源码目录下一切正常），
    但到了别人机器上就可能是黑框或者方块字。跑一次自检看截图就知道了。
    """
    game = Game()

    if out_dir is None:
        base = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
                else HERE)
        out_dir = os.path.join(base, "自检截图")
    os.makedirs(out_dir, exist_ok=True)

    lines = ["一箭又一箭 —— 运行自检", "=" * 40, ""]

    def snap(name):
        game._draw()
        path = os.path.join(out_dir, f"{name}.png")
        pygame.image.save(game.screen, path)
        lines.append(f"  [OK] {name}.png")

    # 各个界面各画一张，任何绘制异常都会当场冒出来
    game.state = STATE_START
    snap("01_开始界面")

    game._enter_level(0)
    snap("02_第1关")

    game._enter_level(2)
    snap("03_第3关_最大棋盘")

    # 吃道具那一瞬间（顺便验证资源路径和字体）
    game._enter_level(0)
    game.on_click_arrow(1, 2)
    game.on_click_arrow(1, 0)
    snap("04_吃到时间道具")

    # 结算界面：这里会用到 resources 里的表情图，最能验证打包有没有带全
    game.state = STATE_LEVEL_CLEAR
    game.result_shown_at = pygame.time.get_ticks() - 500
    snap("05_通关界面")

    # 检查表情图到底有没有被打包进去
    lines.append("")
    lines.append("表情图：")
    for st, fn in IMAGE_FILES.items():
        ok = game.result_images.get(st) is not None
        lines.append(f"  [{'OK' if ok else '缺失'}] {fn}")

    # 检查中文字体：默认字体的话中文会渲染得很窄，用宽度粗测一下
    probe = game.font_normal.render("中文测试", True, (255, 255, 255))
    font_ok = probe.get_width() >= 60      # 正常中文字体每个字约 22px，4 字约 88px
    lines.append("")
    lines.append(f"中文字体：[{'正常' if font_ok else '可能显示成方块'}]"
                 f"（「中文测试」渲染宽度 {probe.get_width()}px）")

    lines.append("")
    lines.append("全部截图已保存到：" + out_dir)

    text = "\n".join(lines)
    with open(os.path.join(out_dir, "自检结果.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    pygame.quit()
    return out_dir


def main():
    if "--smoke" in sys.argv:
        # 支持 --smoke <目录> 指定输出位置
        rest = [a for a in sys.argv[1:] if a != "--smoke"]
        run_smoke_test(rest[0] if rest else None)
        return
    game = Game()
    game.run()


def _write_crash_log():
    """把异常写进 exe 同目录的日志文件。

    打包成 exe 后是没有控制台窗口的，一旦出异常就是「双击之后闪一下就没了」，
    对方没法告诉你哪里错了。写一份日志，出问题时让他发回来就行。
    """
    import traceback
    # 打包后 exe 所在目录；源码运行时则写到代码目录
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = HERE
    path = os.path.join(base, "错误日志.txt")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("一箭又一箭 运行出错\n")
            f.write("=" * 40 + "\n\n")
            f.write(traceback.format_exc())
            f.write("\n\n系统信息：\n")
            f.write(f"  Python: {sys.version}\n")
            f.write(f"  pygame: {pygame.version.ver}\n")
    except Exception:
        pass
    return path


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _write_crash_log()
        raise
