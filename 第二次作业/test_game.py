# -*- coding: utf-8 -*-
"""一箭又一箭 —— 自动化逻辑测试（headless，不依赖显示器）。

覆盖作业要求的 T01–T06：
  T01 点击前方无阻挡的箭头 -> 飞出并消失
  T02 点击前方有阻挡的箭头 -> 不消失，失误 -1
  T03 点击边缘且朝向棋盘外的箭头 -> 正常消失，无越界
  T04 消除本关全部箭头 -> 通关并进入下一关
  T05 失误次数耗尽 -> 失败，且可重新开始
  T06 游戏进行中重新开始 -> 布局与失误次数恢复

运行： python test_game.py
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((960, 720))

from arrow_game import Game, Arrow, LEVELS, generate_random_level, random_level_spec
from verify_levels import solve


def setup(game, grid, mistakes=3):
    """用自定义网格直接构造一关（不影响 LEVELS）。"""
    game.current_level = {"name": "test", "mistakes": mistakes, "grid": grid}
    game.rows = len(grid)
    game.cols = len(grid[0])
    game.board = [[Arrow(grid[r][c]) if grid[r][c] in "UDLR" else None
                   for c in range(game.cols)] for r in range(game.rows)]
    game.mistakes_max = mistakes
    game.mistakes = mistakes
    game.projectiles = []
    game.history = []
    game.state = Game.PLAYING
    gw = game.cols * 76
    gh = game.rows * 76
    game.grid_x = (960 - gw) // 2
    game.grid_y = 120 + (720 - 120 - 40 - gh) // 2


def dirs(game):
    return [[a.d if a else None for a in row] for row in game.board]


def run():
    g = Game(pygame.display.get_surface())
    passed = 0
    failed = 0

    def check(name, cond):
        nonlocal passed, failed
        if cond:
            print(f"  {name}  通过")
            passed += 1
        else:
            print(f"  {name}  失败")
            failed += 1

    # ---- T01 ----
    print("T01 点击前方无阻挡的箭头")
    setup(g, ["....", "..R.", "....", "L..."])   # (1,2)R 朝右畅通；另留一支 L
    g.click_cell(1, 2)
    check("T01", g.board[1][2] is None and len(g.projectiles) == 1 and g.state == Game.PLAYING)

    # ---- T02 ----
    print("T02 点击前方有阻挡的箭头")
    setup(g, [".RR.", "....", "....", "...."])
    g.click_cell(0, 1)  # (0,1)R 被 (0,2)R 阻挡
    a = g.board[0][1]
    check("T02", a is not None and g.mistakes == 2 and (a.shake > 0 or a.flash > 0))

    # ---- T03 ----
    print("T03 点击边缘且朝向棋盘外的箭头")
    setup(g, ["L...", "....", "....", "...."])   # 左边缘朝左（朝外）
    g.click_cell(0, 0)
    c1 = g.board[0][0] is None
    setup(g, ["U...", "....", "....", "...."])   # 上边缘朝上（朝外）
    g.click_cell(0, 0)
    c2 = g.board[0][0] is None
    setup(g, ["....", "....", "....", "...D"])   # 下边缘朝下（朝外）
    g.click_cell(3, 3)
    c3 = g.board[3][3] is None
    check("T03", c1 and c2 and c3)

    # ---- T04 ----
    print("T04 消除本关全部箭头")
    setup(g, ["R...", "...L"])   # (0,0)R 与 (1,3)L 都畅通
    g.click_cell(0, 0)
    g.click_cell(1, 3)
    cleared = g.arrows_left() == 0 and g.state == Game.LEVEL_CLEAR
    g.advance_level()
    check("T04", cleared and g.level_index == 1 and g.state == Game.PLAYING)

    # ---- T05 ----
    print("T05 失误次数耗尽")
    setup(g, [".RR.", "....", "....", "...."], mistakes=1)
    g.click_cell(0, 1)            # 阻挡 -> 失误 -> GAME_OVER
    over = g.mistakes == 0 and g.state == Game.GAME_OVER
    g._activate()                 # 失败后重试 -> 重新开始（恢复测试网格满失误 1）
    check("T05", over and g.state == Game.PLAYING and g.mistakes == 1)

    # ---- T06 ----
    print("T06 游戏进行中重新开始")
    setup(g, [".RR.", "....", "....", "...."])   # (0,1)R 被 (0,2)R 阻挡
    init = dirs(g)
    g.click_cell(0, 1)            # 失误一次
    mid_ok = g.mistakes == 2 and g.board[0][1] is not None
    g.restart_level()             # 模拟按 R 重新开始
    check("T06", mid_ok and dirs(g) == init and g.mistakes == 3)

    # ---- T07（附加）随机模式：生成关卡均保证可通关 ----
    print("T07 随机模式：随机分布且保证可通关")
    random_ok = True
    for i in range(40):
        rows, cols, n, m = random_level_spec(1 + i % 12)
        grid = None
        for _ in range(100):
            grid = generate_random_level(rows, cols, n)
            if grid:
                break
        if grid is None or not solve({"grid": grid, "mistakes": m})[0]:
            random_ok = False
            print(f"  随机生成失败或不可通关: {rows}x{cols} n={n}")
    check("T07", random_ok)

    print(f"\n结果：{passed} 通过，{failed} 失败")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run())
