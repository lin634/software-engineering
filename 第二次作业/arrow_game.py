# -*- coding: utf-8 -*-
"""
一箭又一箭 —— 点击式箭头解谜小游戏
软件工程课程第二次个人作业

玩法：
  棋盘中分布着朝向 上/下/左/右 的箭头。点击一支箭头时，程序会检查它
  前进方向上（同一行或同一列、直到棋盘边界）是否还有其他箭头阻挡：
    · 没有阻挡 —— 箭头飞出棋盘并消失；
    · 有阻挡   —— 箭头不能消失，发生碰撞并消耗 1 次失误机会。
  清空本关全部箭头即过关；失误次数耗尽则失败。
  主菜单可选择「随机模式」：每关箭头随机分布、难度逐关递增，
  生成器在构造上保证关卡可通关（附加功能）。

操作：
  鼠标左键  点击箭头尝试射出
  R         重新开始当前关卡
  Z         撤销上一步（附加功能）
  H         提示当前可射出的箭头（附加功能）
  S         AI 自动求解当前关卡（附加功能）
  空格/回车 开始 / 下一关 / 重试
  ESC       返回菜单 / 退出
  F2        保存截图到 screenshots/
"""
import os
import sys
import math
import time
import random
import asyncio
from collections import deque
from dataclasses import dataclass, field

import pygame

# ============================== 基础配置 ==============================
WIN_W, WIN_H = 960, 720
FPS = 60
CELL = 76                     # 每格像素边长
ARROW_SCALE = 0.82            # 箭头相对格子的大小

# 配色
C_BG_TOP    = (22, 24, 40)
C_BG_BOT    = (32, 35, 56)
C_PANEL     = (36, 40, 60)
C_CELL      = (48, 54, 78)
C_CELL_LINE = (68, 76, 104)
C_ARROW     = (96, 204, 255)
C_ARROW_OUT = (16, 26, 44)
C_HIT       = (255, 96, 118)
C_HINT      = (120, 230, 150)
C_TEXT      = (236, 240, 248)
C_DIM       = (160, 168, 192)
C_ACCENT    = (255, 196, 87)
C_OK        = (120, 220, 140)
C_BAD       = (255, 96, 118)
C_BTN       = (58, 64, 90)
C_BTN_HOVER = (74, 82, 116)

# 方向向量 (dr, dc)：U 行减=上，D 行增=下，L 列减=左，R 列增=右
DIR_VEC = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}

# 关卡数据：'.' 为空地，U/D/L/R 为对应方向的箭头。
# 布局由 generate_random_level 以固定种子生成，箭头尽量随机分布，
# 且每关都经求解器验证可通关。
LEVELS = [
    {
        "name": "初识箭阵",
        "mistakes": 3,
        "grid": [
            ".....",
            ".....",
            "D....",
            "....R",
            ".R.D.",
        ],
    },
    {
        "name": "小试锋芒",
        "mistakes": 4,
        "grid": [
            ".L..U.",
            "...R..",
            "DU....",
            "R.....",
            ".....R",
            ".D....",
        ],
    },
    {
        "name": "渐入佳境",
        "mistakes": 4,
        "grid": [
            "..DR.U",
            ".L....",
            "...R..",
            "..D..R",
            ".U...D",
            ".D....",
        ],
    },
    {
        "name": "左右逢源",
        "mistakes": 5,
        "grid": [
            ".L.....",
            "R...U..",
            ".U.....",
            "U.L...L",
            ".LD..L.",
            "..R....",
            "....U..",
        ],
    },
    {
        "name": "密阵初现",
        "mistakes": 6,
        "grid": [
            "..U...U",
            "...L...",
            "D.....D",
            "L.U..L.",
            "D...DR.",
            "L...R..",
            "....D.L",
        ],
    },
    {
        "name": "迷雾重重",
        "mistakes": 7,
        "grid": [
            "...U...U",
            "R..R....",
            "....U.R.",
            "LR...U..",
            ".U.L...D",
            ".U..R...",
            "U....D..",
            "....LL..",
        ],
    },
    {
        "name": "箭雨滂沱",
        "mistakes": 8,
        "grid": [
            "L.R.....",
            ".....D.L",
            ".RDR....",
            "L...LRR.",
            "..L..DLD",
            "D....R..",
            ".......R",
            "..LL..DD",
        ],
    },
    {
        "name": "万箭归宗",
        "mistakes": 9,
        "grid": [
            "DU..U..L",
            "....UR..",
            ".LL..U..",
            ".R.R....",
            "...U..L.",
            "..U.LRU.",
            ".D.L.RR.",
            "L..UU.R.",
        ],
    },
]

def _pick_direction(arrows, rows, cols, r, c, rng):
    """随机选一个可行方向，避免与已有箭头形成“同线相对”的必死死局。

    例如新箭头朝右时，若其右侧已存在朝左的箭头，二者相对互挡必死，
    该方向不可取；但允许被垂直方向或同向箭头“挡路”（那是正常依赖）。
    """
    dirs = list(DIR_VEC)
    rng.shuffle(dirs)
    facing = {"R": "L", "L": "R", "D": "U", "U": "D"}
    for d in dirs:
        dr, dc = DIR_VEC[d]
        nr, nc = r + dr, c + dc
        ok = True
        while 0 <= nr < rows and 0 <= nc < cols:
            if (nr, nc) in arrows and arrows[(nr, nc)] == facing[d]:
                ok = False
                break
            nr += dr
            nc += dc
        if ok:
            return d
    return None


def _arrows_to_grid(arrows, rows, cols):
    return ["".join(arrows.get((r, c), ".") for c in range(cols)) for r in range(rows)]


def _is_solvable(arrows, rows, cols):
    """依赖图无环 ⇔ 存在合法消除顺序（与 verify_levels 的 DFS 等价但更快）。

    边 X -> Y 表示 X 位于 Y 的前进射线上、必须先于 Y 消除。
    """
    adj = {p: [] for p in arrows}
    for (r, c), d in arrows.items():
        dr, dc = DIR_VEC[d]
        nr, nc = r + dr, c + dc
        while 0 <= nr < rows and 0 <= nc < cols:
            if (nr, nc) in arrows:
                adj[(nr, nc)].append((r, c))
            nr += dr
            nc += dc
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {p: WHITE for p in arrows}

    def dfs(u):
        color[u] = GRAY
        for v in adj[u]:
            if color[v] == GRAY:
                return False
            if color[v] == WHITE and not dfs(v):
                return False
        color[u] = BLACK
        return True

    return all(color[u] != WHITE or dfs(u) for u in arrows)


def _random_ok(arrows, rows, cols):
    """分布“尽量随机”的约束：杜绝整行/整列同向、连续同向过长、箭头过度扎堆。"""
    def line_ok(items, limit):
        if not items:
            return True
        if len(items) > limit:
            return False
        dirs = [d for _, d in items]
        if len(dirs) >= 3 and len(set(dirs)) == 1:
            return False                        # 整行/整列全是同一方向
        run = 1
        for i in range(1, len(items)):
            run = run + 1 if items[i][1] == items[i - 1][1] else 1
            if run > 2:
                return False                    # 连续 3 支以上同向
        return True

    for r in range(rows):
        items = sorted((c, arrows[(r, c)]) for c in range(cols) if (r, c) in arrows)
        if not line_ok(items, max(1, int(cols * 0.6))):
            return False
    for c in range(cols):
        items = sorted((r, arrows[(r, c)]) for r in range(rows) if (r, c) in arrows)
        if not line_ok(items, max(1, int(rows * 0.6))):
            return False
    return True


def _random_place(rng, rows, cols, n_arrows):
    """随机撒 n_arrows 支箭头（位置均匀随机、方向避免相对死局）。"""
    cells = [(r, c) for r in range(rows) for c in range(cols)]
    rng.shuffle(cells)
    arrows = {}
    for r, c in cells[:n_arrows]:
        d = _pick_direction(arrows, rows, cols, r, c, rng)
        if d is None:
            return None
        arrows[(r, c)] = d
    return arrows


def generate_random_level(rows, cols, n_arrows, seed=None):
    """生成一个箭头尽量随机分布、且保证可通关的关卡（返回字符串列表）。

    随机撒点 + 依赖图无环判定 + “尽量随机”分布约束，未通过则换种子重试；
    若始终无法同时满足（极端情况），放宽为“仅保证可通关”，保证游戏不卡死。
    """
    rng = random.Random(seed)
    for _ in range(3000):
        arrows = _random_place(rng, rows, cols, n_arrows)
        if arrows is None:
            continue
        if _is_solvable(arrows, rows, cols) and _random_ok(arrows, rows, cols):
            return _arrows_to_grid(arrows, rows, cols)
    for _ in range(3000):                        # 放宽：仅保证可通关
        arrows = _random_place(rng, rows, cols, n_arrows)
        if arrows is None:
            continue
        if _is_solvable(arrows, rows, cols):
            return _arrows_to_grid(arrows, rows, cols)
    return None


def random_level_spec(level_num):
    """随随机模式关卡序号递增难度：棋盘尺寸与箭头数量逐步加大。"""
    size = min(8, 5 + (level_num - 1) // 3)           # 5 -> 6 -> 7 -> 8
    cells = size * size
    n_arrows = min(int(cells * 0.42), 2 + 2 * level_num)  # 4, 6, 8, 10, ...
    mistakes = max(3, n_arrows // 3)
    return size, size, n_arrows, mistakes


# 指向“右”的基础多边形（归一化到 [-0.5, 0.5]），绘制时按方向旋转
RIGHT_POLY = [
    (-0.40, -0.13),
    ( 0.10, -0.13),
    ( 0.10, -0.30),
    ( 0.42,  0.00),
    ( 0.10,  0.30),
    ( 0.10,  0.13),
    (-0.40,  0.13),
]


def rotate_point(p, d):
    """把指向右的基础点按方向 d 旋转。屏幕坐标系 y 向下。"""
    x, y = p
    if d == "R":
        return (x, y)
    if d == "D":                       # 顺时针 90°
        return (-y, x)
    if d == "L":                       # 180°
        return (-x, -y)
    if d == "U":                       # 逆时针 90°（向上）
        return (y, -x)
    raise ValueError(d)


def lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


# ============================== 字体缓存 ==============================
# 直接用 TTF/TTC 文件路径构造字体，避免 pygame.font.SysFont 在部分
# Windows 环境下枚举系统字体时崩溃（initsysfonts_win32 报错）。
_FONT_PATH = None
_FONT_PATH_BOLD = None


def _resolve_fonts():
    global _FONT_PATH, _FONT_PATH_BOLD
    # 优先使用随包分发的开源中文字体（网页版必需；桌面版若无则回退系统字体）
    here = os.path.dirname(os.path.abspath(__file__))
    bundled = [os.path.join(here, "fonts", "NotoSansSC-VF.ttf"),
               os.path.join(here, "NotoSansSC-VF.ttf"),
               "fonts/NotoSansSC-VF.ttf"]
    for p in bundled:
        if os.path.exists(p):
            _FONT_PATH = p
            _FONT_PATH_BOLD = p
            return
    base = os.environ.get("WINDIR", r"C:\Windows") + r"\Fonts"
    cands_regular = [os.path.join(base, "msyh.ttc"),
                     os.path.join(base, "simhei.ttf")]
    cands_bold = [os.path.join(base, "msyhbd.ttc"),
                  os.path.join(base, "simhei.ttf")]
    for p in cands_regular:
        if os.path.exists(p):
            _FONT_PATH = p
            break
    for p in cands_bold:
        if os.path.exists(p):
            _FONT_PATH_BOLD = p
            break


_resolve_fonts()
_font_cache = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        path = _FONT_PATH_BOLD if (bold and _FONT_PATH_BOLD) else _FONT_PATH
        if path:
            f = pygame.font.Font(path, size)
            if bold:
                f.set_bold(True)           # 同一字体文件时用伪粗体
        else:                              # 极端回退：默认字体（可能不支持中文）
            f = pygame.font.Font(None, size)
            if bold:
                f.set_bold(True)
        _font_cache[key] = f
    return _font_cache[key]


# ============================== 箭头贴图缓存 ==============================
_arrow_surf_cache = {}


def arrow_surface(d, color, scale=1.0):
    """生成/缓存一张带方向的箭头 Surface（用于需要透明度渐变的飞出动画）。"""
    key = (d, color, round(scale, 2))
    if key not in _arrow_surf_cache:
        s = CELL * ARROW_SCALE * scale
        pad = int(s + 8)
        surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        pts = [(pad + px * s, pad + py * s)
               for px, py in (rotate_point(p, d) for p in RIGHT_POLY)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, C_ARROW_OUT, pts, 2)
        _arrow_surf_cache[key] = surf
    return _arrow_surf_cache[key]


# ============================== 数据结构 ==============================
@dataclass
class Arrow:
    d: str                      # 方向 'U'/'D'/'L'/'R'
    shake: float = 0.0          # 剩余抖动时间（秒）
    flash: float = 0.0          # 碰撞红色高亮剩余时间（秒）


@dataclass
class Projectile:
    x: float
    y: float
    d: str
    color: tuple
    t: float = 0.0
    life: float = 0.8


# ============================== 按钮 ==============================
class Button:
    def __init__(self, rect, text, color=C_BTN, text_color=C_ACCENT):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.hover = False

    def update(self, mpos):
        self.hover = self.rect.collidepoint(mpos)

    def draw(self, surf):
        col = C_BTN_HOVER if self.hover else self.color
        pygame.draw.rect(surf, col, self.rect, border_radius=10)
        pygame.draw.rect(surf, C_ACCENT if self.hover else (90, 98, 130),
                         self.rect, 2, border_radius=10)
        t = font(22, True).render(self.text, True,
                                  self.text_color if self.hover else C_TEXT)
        surf.blit(t, t.get_rect(center=self.rect.center))

    def clicked(self, mpos):
        return self.rect.collidepoint(mpos)


# ============================== 主游戏 ==============================
class Game:
    # ---- 状态常量 ----
    MENU = "MENU"
    PLAYING = "PLAYING"
    LEVEL_CLEAR = "LEVEL_CLEAR"
    GAME_OVER = "GAME_OVER"
    VICTORY = "VICTORY"

    def __init__(self, screen):
        self.screen = screen
        self.bg = self._make_bg()
        self.state = self.MENU
        self.level_index = 0
        self.random_mode = False       # True 时玩随机关卡（无尽模式）
        self.random_num = 0            # 随机模式下已过的关卡数
        self.current_level = LEVELS[0]  # 当前加载的关卡数据（固定或随机）

        # 各界面按钮
        self.menu_btn = Button((WIN_W // 2 - 120, 425, 240, 58), "开始游戏")
        self.random_btn = Button((WIN_W // 2 - 120, 505, 240, 54),
                                 "随机模式", text_color=C_OK)
        self.next_btn = Button((WIN_W // 2 - 120, WIN_H // 2 + 30, 240, 54), "下一关")
        self.retry_btn = Button((WIN_W // 2 - 120, WIN_H // 2 + 30, 240, 54), "重新开始")
        self.menu_return_btn = Button((WIN_W // 2 - 110, WIN_H // 2 + 98, 220, 44),
                                      "返回菜单", text_color=C_DIM)
        self.hud_restart = Button((WIN_W - 150, 28, 120, 44), "重新开始")

        self.feedback = ""
        self.feedback_t = 0.0
        self.title_t = 0.0
        self.hint_t = 0.0
        self.stars = 0
        self.load_level(0)

    # ---------- 背景与关卡 ----------
    def _make_bg(self):
        surf = pygame.Surface((WIN_W, WIN_H))
        for y in range(WIN_H):
            t = y / WIN_H
            surf.fill(lerp_color(C_BG_TOP, C_BG_BOT, t), (0, y, WIN_W, 1))
        return surf

    def _load_dict(self, lvl):
        """按关卡数据 dict 装载棋盘并居中。"""
        self.current_level = lvl
        self.rows = len(lvl["grid"])
        self.cols = len(lvl["grid"][0])
        self.board = [[Arrow(lvl["grid"][r][c]) if lvl["grid"][r][c] in DIR_VEC else None
                       for c in range(self.cols)] for r in range(self.rows)]
        self.mistakes_max = lvl["mistakes"]
        self.mistakes = self.mistakes_max
        self.projectiles = []
        self.history = []          # 撤销栈：[(board 快照, mistakes), ...]
        self.feedback = ""
        self.feedback_t = 0.0
        self.hint_t = 0.0
        self.auto_solving = False  # AI 自动求解中
        self.auto_steps = []       # 待执行的消除顺序 [(r, c), ...]
        self.auto_timer = 0.0      # 到下一次自动点击的倒计时
        # 棋盘居中
        gw = self.cols * CELL
        gh = self.rows * CELL
        self.grid_x = (WIN_W - gw) // 2
        self.grid_y = 120 + (WIN_H - 120 - 40 - gh) // 2

    def load_level(self, i):
        """加载固定关卡 i（关卡/画廊模式）。"""
        self.random_mode = False
        self.level_index = i
        self._load_dict(LEVELS[i])

    def load_random_level(self):
        """生成并加载一个随机分布且保证可通关的关卡。"""
        self.random_num += 1
        self.random_mode = True
        rows, cols, n, mistakes = random_level_spec(self.random_num)
        grid = None
        for _ in range(300):                       # 换种子重试，几乎不可能全失败
            grid = generate_random_level(rows, cols, n)
            if grid:
                break
        if grid is None:                           # 极端兜底：退回固定第 8 关
            grid = LEVELS[-1]["grid"]
            mistakes = LEVELS[-1]["mistakes"]
        self._load_dict({"name": f"随机箭阵（{n} 支）", "mistakes": mistakes,
                         "grid": grid})

    def restart_level(self):
        """重新开始当前关卡（随机模式也恢复为同一布局）。"""
        self._load_dict(self.current_level)
        self.set_feedback("已重新开始本关")

    def enter_random_mode(self):
        self.random_num = 0
        self.load_random_level()
        self.state = self.PLAYING

    # ---------- 棋盘逻辑 ----------
    def arrows_left(self):
        return sum(1 for r in range(self.rows)
                   for c in range(self.cols) if self.board[r][c])

    def is_clear(self, r, c, d):
        """箭头 (r,c) 朝方向 d 到边界之间是否没有其他箭头阻挡。"""
        dr, dc = DIR_VEC[d]
        nr, nc = r + dr, c + dc
        while 0 <= nr < self.rows and 0 <= nc < self.cols:
            if self.board[nr][nc] is not None:
                return False
            nr += dr
            nc += dc
        return True

    def cell_center(self, r, c):
        return (self.grid_x + c * CELL + CELL // 2,
                self.grid_y + r * CELL + CELL // 2)

    def pixel_to_cell(self, mx, my):
        if not (self.grid_x <= mx < self.grid_x + self.cols * CELL and
                self.grid_y <= my < self.grid_y + self.rows * CELL):
            return None
        return (my - self.grid_y) // CELL, (mx - self.grid_x) // CELL

    # ---------- AI 自动求解 ----------
    def _solve_order(self):
        """用依赖图拓扑排序求一条合法消除顺序 [(r, c), ...]。

        规则：箭头 X 位于 Y 的前进射线上时，X 必须先于 Y 消除（边 X->Y）。
        任一拓扑序都是合法消除序；返回空表示存在环（不可通关）。
        """
        arrows = {(r, c): self.board[r][c].d
                  for r in range(self.rows) for c in range(self.cols)
                  if self.board[r][c]}
        adj = {p: [] for p in arrows}
        indeg = {p: 0 for p in arrows}
        for (r, c), d in arrows.items():
            dr, dc = DIR_VEC[d]
            nr, nc = r + dr, c + dc
            while 0 <= nr < self.rows and 0 <= nc < self.cols:
                if (nr, nc) in arrows:            # (nr,nc) 在 (r,c) 射线上 -> 先消除
                    adj[(nr, nc)].append((r, c))
                    indeg[(r, c)] += 1
                nr += dr
                nc += dc
        q = deque(sorted(p for p in arrows if indeg[p] == 0))
        order = []
        while q:
            p = q.popleft()
            order.append(p)
            nxt = []
            for m in adj[p]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    nxt.append(m)
            for m in sorted(nxt):
                q.append(m)
        return order if len(order) == len(arrows) else []

    def start_auto_solve(self):
        if self.state != self.PLAYING:
            return
        order = self._solve_order()
        if not order:
            self.set_feedback("当前局面无法自动求解")
            return
        self.auto_solving = True
        self.auto_steps = order
        self.auto_timer = 0.3
        self.set_feedback("AI 求解中…（再按 S 停止）", 2.0)

    def stop_auto_solve(self):
        self.auto_solving = False
        self.auto_steps = []

    # ---------- 历史/撤销 ----------
    def push_history(self):
        snap = ([[Arrow(a.d) if a else None for a in row] for row in self.board],
                self.mistakes)
        self.history.append(snap)
        if len(self.history) > 80:
            self.history.pop(0)

    def undo(self):
        if not self.history:
            self.set_feedback("没有可撤销的操作")
            return
        snap, m = self.history.pop()
        self.board = snap
        self.mistakes = m
        self.hint_t = 0.0
        self.set_feedback("已撤销上一步")

    # ---------- 反馈 ----------
    def set_feedback(self, msg, t=1.4):
        self.feedback = msg
        self.feedback_t = t

    # ---------- 点击箭头 ----------
    def click_cell(self, r, c):
        if self.state != self.PLAYING:
            return
        cell = self.board[r][c]
        if cell is None:
            return
        if self.is_clear(r, c, cell.d):
            # 前方畅通 —— 飞出
            self.push_history()
            cx, cy = self.cell_center(r, c)
            self.projectiles.append(Projectile(cx, cy, cell.d, C_ARROW))
            self.board[r][c] = None
            self.set_feedback("箭头飞出！")
            self.hint_t = 0.0
            if self.arrows_left() == 0:
                used = self.mistakes_max - self.mistakes
                self.stars = 3 if used == 0 else (2 if used <= self.mistakes_max / 2 else 1)
                self.state = self.LEVEL_CLEAR
                self.stop_auto_solve()
        else:
            # 前方阻挡 —— 碰撞
            self.push_history()
            cell.shake = 0.5
            cell.flash = 0.5
            self.mistakes -= 1
            self.set_feedback("前方有阻挡！失误 -1")
            self.hint_t = 0.0
            if self.mistakes <= 0:
                self.state = self.GAME_OVER
                self.stop_auto_solve()

    # ---------- 关卡推进 ----------
    def advance_level(self):
        if self.random_mode:                       # 随机模式：一直有下一关
            self.load_random_level()
            self.state = self.PLAYING
        elif self.level_index < len(LEVELS) - 1:
            self.load_level(self.level_index + 1)
            self.state = self.PLAYING
        else:
            self.state = self.VICTORY

    # ---------- 截图 ----------
    def save_screenshot(self):
        name = f"shot_{int(time.time())}.png"
        try:
            os.makedirs("screenshots", exist_ok=True)
            pygame.image.save(self.screen, os.path.join("screenshots", name))
            self.set_feedback("已保存截图：screenshots/" + name, 1.6)
        except Exception as e:
            self.set_feedback("截图失败：" + str(e), 1.6)

    # ---------- 事件 ----------
    def handle_event(self, e):
        if e.type == pygame.QUIT:
            return False
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if self.state == self.MENU:
                    return False
                self.state = self.MENU
            elif e.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._activate()
            elif e.key == pygame.K_r and self.state == self.PLAYING:
                self.stop_auto_solve()
                self.restart_level()
            elif e.key == pygame.K_z and self.state == self.PLAYING:
                self.stop_auto_solve()
                self.undo()
            elif e.key == pygame.K_h and self.state == self.PLAYING:
                self.stop_auto_solve()
                self.hint_t = 2.2
                n = sum(1 for r in range(self.rows) for c in range(self.cols)
                        if self.board[r][c] and self.is_clear(r, c, self.board[r][c].d))
                self.set_feedback(f"提示：当前有 {n} 支箭头可射出")
            elif e.key == pygame.K_s and self.state == self.PLAYING:
                if self.auto_solving:
                    self.stop_auto_solve()
                    self.set_feedback("已停止 AI 求解")
                else:
                    self.start_auto_solve()
            elif e.key == pygame.K_F2:
                self.save_screenshot()
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self._click_mouse(e.pos)
        return True

    def _activate(self):
        """空格/回车在不同状态下的通用动作。"""
        if self.state == self.MENU:
            self.load_level(0)
            self.state = self.PLAYING
        elif self.state == self.LEVEL_CLEAR:
            self.advance_level()
        elif self.state == self.GAME_OVER:
            self.restart_level()
            self.state = self.PLAYING
        elif self.state == self.VICTORY:
            self.state = self.MENU

    def _click_mouse(self, mpos):
        if self.state == self.MENU:
            if self.menu_btn.clicked(mpos):
                self.load_level(0)
                self.state = self.PLAYING
            elif self.random_btn.clicked(mpos):
                self.enter_random_mode()
        elif self.state == self.PLAYING:
            if self.hud_restart.clicked(mpos):
                self.stop_auto_solve()
                self.restart_level()
            else:
                cell = self.pixel_to_cell(*mpos)
                if cell:
                    self.stop_auto_solve()       # 玩家手动操作，接管控制
                    self.click_cell(*cell)
        elif self.state == self.LEVEL_CLEAR:
            if self.next_btn.clicked(mpos):
                self.advance_level()
        elif self.state == self.GAME_OVER:
            if self.retry_btn.clicked(mpos):
                self.restart_level()
                self.state = self.PLAYING
            elif self.menu_return_btn.clicked(mpos):
                self.state = self.MENU
        elif self.state == self.VICTORY:
            if self.menu_return_btn.clicked(mpos):
                self.state = self.MENU

    # ---------- 更新 ----------
    def update(self, dt, mpos):
        self.menu_btn.update(mpos)
        self.random_btn.update(mpos)
        self.next_btn.update(mpos)
        self.retry_btn.update(mpos)
        self.menu_return_btn.update(mpos)
        self.hud_restart.update(mpos)
        self.title_t += dt
        if self.feedback_t > 0:
            self.feedback_t -= dt
        if self.hint_t > 0:
            self.hint_t -= dt
        # 箭头动画计时衰减
        if self.state == self.PLAYING:
            for r in range(self.rows):
                for c in range(self.cols):
                    a = self.board[r][c]
                    if a:
                        if a.shake > 0:
                            a.shake = max(0.0, a.shake - dt)
                        if a.flash > 0:
                            a.flash = max(0.0, a.flash - dt)
        # 飞出弹丸
        for p in self.projectiles:
            p.t += dt
            dr, dc = DIR_VEC[p.d]
            p.x += dc * 900 * dt
            p.y += dr * 900 * dt
        self.projectiles = [p for p in self.projectiles if p.t < p.life]
        # AI 自动求解：按拓扑序逐步点击
        if self.auto_solving and self.state == self.PLAYING and self.auto_steps:
            self.auto_timer -= dt
            if self.auto_timer <= 0:
                r, c = self.auto_steps.pop(0)
                if self.board[r][c] is not None:        # 理论上必为可飞出
                    self.click_cell(r, c)
                self.auto_timer = 0.32
                if not self.auto_steps:
                    self.auto_solving = False

    # ---------- 绘制 ----------
    def draw(self):
        self.screen.blit(self.bg, (0, 0))
        if self.state == self.MENU:
            self.draw_menu()
        elif self.state == self.VICTORY:
            self.draw_victory()
        else:  # PLAYING / LEVEL_CLEAR / GAME_OVER
            self.draw_play()
            if self.state == self.LEVEL_CLEAR:
                if self.random_mode:
                    sub = f"随机关卡 {self.random_num} · {self.current_level['name']}"
                    self.draw_overlay("通关！", sub, "下一关", self.next_btn,
                                      stars=self.stars)
                else:
                    last = self.level_index == len(LEVELS) - 1
                    self.draw_overlay("通关！",
                                      f"第 {self.level_index + 1} 关 · {self.current_level['name']}",
                                      "下一关" if not last else "完成全部", self.next_btn,
                                      stars=self.stars)
            elif self.state == self.GAME_OVER:
                self.draw_overlay("挑战失败", "剩余失误次数已耗尽，再来一次！",
                                  "重新开始", self.retry_btn, bad=True,
                                  extra=self.menu_return_btn)
        self.draw_feedback()

    def draw_menu(self):
        title = font(66, True).render("一  箭  又  一  箭", True, C_ACCENT)
        self.screen.blit(title, title.get_rect(center=(WIN_W // 2, 180)))
        sub = font(22).render("点击箭头，按正确顺序让所有箭头飞出棋盘", True, C_DIM)
        self.screen.blit(sub, sub.get_rect(center=(WIN_W // 2, 238)))
        # 装饰箭头
        for i, d in enumerate(["U", "D", "L", "R"]):
            cx = WIN_W // 2 - 180 + i * 120
            cy = 340 + int(8 * math.sin(self.title_t * 2 + i))
            self.draw_arrow(cx, cy, d, C_ARROW, scale=1.15)
        self.menu_btn.draw(self.screen)
        self.random_btn.draw(self.screen)
        foot = font(16).render("软件工程第二次个人作业 · 学号 102401129 · 空格/回车 开始",
                               True, C_DIM)
        self.screen.blit(foot, foot.get_rect(center=(WIN_W // 2, WIN_H - 40)))

    def draw_play(self):
        self.draw_hud()
        self.draw_grid()
        self.draw_projectiles()
        hint_txt = "鼠标点击箭头尝试射出  ·  R 重新开始  ·  Z 撤销  ·  H 提示  ·  S AI求解  ·  ESC 菜单  ·  F2 截图"
        t = font(16).render(hint_txt, True, C_DIM)
        self.screen.blit(t, t.get_rect(midbottom=(WIN_W // 2, WIN_H - 8)))

    def draw_hud(self):
        bar = pygame.Rect(0, 0, WIN_W, 100)
        pygame.draw.rect(self.screen, C_PANEL, bar)
        pygame.draw.line(self.screen, C_CELL_LINE, (0, 100), (WIN_W, 100), 2)
        lvl = self.current_level
        if self.random_mode:
            label = f"随机关卡 {self.random_num} · {lvl['name']}"
        else:
            label = f"第 {self.level_index + 1}/{len(LEVELS)} 关 · {lvl['name']}"
        t1 = font(26, True).render(label, True, C_TEXT)
        self.screen.blit(t1, (30, 20))
        t2 = font(22).render(f"剩余箭头：{self.arrows_left()}", True, C_DIM)
        self.screen.blit(t2, (30, 58))
        # 失误次数以圆点显示
        mt = font(22).render("失误：", True, C_DIM)
        self.screen.blit(mt, (300, 58))
        for i in range(self.mistakes_max):
            px = 300 + 64 + i * 24
            py = 70
            col = C_OK if i < self.mistakes else (70, 76, 100)
            pygame.draw.circle(self.screen, col, (px, py), 8)
            pygame.draw.circle(self.screen, C_CELL_LINE, (px, py), 8, 1)
        remain = font(16).render(f"{self.mistakes}/{self.mistakes_max}", True, C_DIM)
        self.screen.blit(remain, (300 + 64 + self.mistakes_max * 24 + 6, 64))
        self.hud_restart.draw(self.screen)

    def draw_grid(self):
        pad = 14
        pr = pygame.Rect(self.grid_x - pad, self.grid_y - pad,
                         self.cols * CELL + pad * 2, self.rows * CELL + pad * 2)
        pygame.draw.rect(self.screen, C_PANEL, pr, border_radius=14)
        pygame.draw.rect(self.screen, C_CELL_LINE, pr, 2, border_radius=14)
        for r in range(self.rows):
            for c in range(self.cols):
                rx = self.grid_x + c * CELL
                ry = self.grid_y + r * CELL
                crect = pygame.Rect(rx + 3, ry + 3, CELL - 6, CELL - 6)
                pygame.draw.rect(self.screen, C_CELL, crect, border_radius=8)
                a = self.board[r][c]
                if a:
                    cx, cy = self.cell_center(r, c)
                    if a.shake > 0:                       # 碰撞抖动
                        amp = 7.0 * (a.shake / 0.5)
                        cx += math.sin(a.shake * 70.0) * amp
                    col = C_ARROW
                    if a.flash > 0:                        # 碰撞变红
                        col = lerp_color(C_ARROW, C_HIT, a.flash / 0.5)
                    self.draw_arrow(cx, cy, a.d, col)
                elif self.hint_t > 0:                      # 空格不提示
                    pass
        # 提示：高亮当前可射出的箭头
        if self.hint_t > 0:
            for r in range(self.rows):
                for c in range(self.cols):
                    a = self.board[r][c]
                    if a and self.is_clear(r, c, a.d):
                        rx = self.grid_x + c * CELL
                        ry = self.grid_y + r * CELL
                        ring = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
                        pygame.draw.rect(ring, (*C_HINT, 70), ring.get_rect(),
                                         border_radius=8)
                        pygame.draw.rect(ring, C_HINT, ring.get_rect(), 3,
                                         border_radius=8)
                        self.screen.blit(ring, (rx, ry))

    def draw_projectiles(self):
        for p in self.projectiles:
            prog = p.t / p.life
            alpha = int(255 * (1 - prog))
            if alpha <= 0:
                continue
            surf = arrow_surface(p.d, p.color)
            surf.set_alpha(alpha)
            rect = surf.get_rect(center=(int(p.x), int(p.y)))
            self.screen.blit(surf, rect)

    def draw_arrow(self, cx, cy, d, color, scale=1.0, outline=C_ARROW_OUT):
        s = CELL * ARROW_SCALE * scale
        pts = [(cx + px * s, cy + py * s)
               for px, py in (rotate_point(p, d) for p in RIGHT_POLY)]
        pygame.draw.polygon(self.screen, color, pts)
        pygame.draw.polygon(self.screen, outline, pts, 2)

    def draw_overlay(self, title, sub, btn_label, btn, bad=False, stars=0, extra=None):
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        pw, ph = 500, 300
        pr = pygame.Rect((WIN_W - pw) // 2, (WIN_H - ph) // 2, pw, ph)
        pygame.draw.rect(self.screen, C_PANEL, pr, border_radius=16)
        col = C_BAD if bad else C_OK
        pygame.draw.rect(self.screen, col, pr, 3, border_radius=16)
        t = font(50, True).render(title, True, col)
        self.screen.blit(t, t.get_rect(center=(WIN_W // 2, pr.top + 65)))
        s = font(22).render(sub, True, C_TEXT)
        self.screen.blit(s, s.get_rect(center=(WIN_W // 2, pr.top + 115)))
        if stars:
            st = "★" * stars + "☆" * (3 - stars)
            ss = font(34, True).render(st, True, C_ACCENT)
            self.screen.blit(ss, ss.get_rect(center=(WIN_W // 2, pr.top + 165)))
        btn.text = btn_label
        btn.draw(self.screen)
        if extra:
            extra.draw(self.screen)

    def draw_victory(self):
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        t = font(58, True).render("全部通关！", True, C_ACCENT)
        self.screen.blit(t, t.get_rect(center=(WIN_W // 2, WIN_H // 2 - 60)))
        s = font(24).render("你成功射出了所有关卡的全部箭头！", True, C_TEXT)
        self.screen.blit(s, s.get_rect(center=(WIN_W // 2, WIN_H // 2)))
        self.menu_return_btn.text = "返回菜单"
        self.menu_return_btn.draw(self.screen)

    def draw_feedback(self):
        if self.feedback_t > 0 and self.feedback:
            alpha = 1.0 if self.feedback_t > 0.3 else max(0.0, self.feedback_t / 0.3)
            t = font(24, True).render(self.feedback, True, C_ACCENT)
            t.set_alpha(int(255 * alpha))
            self.screen.blit(t, t.get_rect(midbottom=(WIN_W // 2, WIN_H - 34)))


# ============================== 入口 ==============================
async def main():
    pygame.init()
    pygame.display.set_caption("一箭又一箭")
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    game = Game(screen)
    clock = pygame.time.Clock()
    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 1 / 30)
        mpos = pygame.mouse.get_pos()
        for e in pygame.event.get():
            if not game.handle_event(e):
                running = False
        game.update(dt, mpos)
        game.draw()
        pygame.display.flip()
        await asyncio.sleep(0)          # 让出事件循环（桌面与网页版通用）


if __name__ == "__main__":
    asyncio.run(main())
