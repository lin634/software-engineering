# -*- coding: utf-8 -*-
"""一箭又一箭 —— 自动化逻辑测试（headless，不依赖显示器）。

覆盖作业要求的 T01–T06：
  T01 点击前方无阻挡的箭头 -> 飞出并消失
  T02 点击前方有阻挡的箭头 -> 不消失，失误 -1
  T03 点击边缘且朝向棋盘外的箭头 -> 正常消失，无越界
  T04 消除本关全部箭头 -> 通关并进入下一关
  T05 失误次数耗尽 -> 失败，且可重新开始
  T06 游戏进行中重新开始 -> 布局与失误次数恢复
附加 T07–T09：随机关可通关、AI 求解、星级计分规则

运行： python test_game.py
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((960, 720))

from arrow_game import (Game, Arrow, LEVELS, CELL, WIN_W, WIN_H,
                        generate_random_level, random_level_spec)
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
    game.pending_clear = False
    # 星级计分相关状态一并重置，保证各用例互相独立
    game.undos_left = 1
    game.hints_left = 1
    game.used_undos = False
    game.used_hints = False
    game.used_ai = False
    game.stars = 0
    gw = game.cols * CELL
    gh = game.rows * CELL
    game.grid_x = (WIN_W - gw) // 2
    game.grid_y = 120 + (WIN_H - 120 - 80 - gh) // 2


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
    # 最后一支箭点掉后：不立即通关，先等它飞出动画结束
    waiting = g.arrows_left() == 0 and g.state == Game.PLAYING and g.pending_clear
    g.update(1.0, (0, 0))        # 模拟动画播完（0.8s）-> 进入通关画面
    cleared = waiting and g.state == Game.LEVEL_CLEAR and not g.projectiles
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

    # ---- T08（附加）AI 自动求解：拓扑序可清空当前关卡 ----
    print("T08 AI 自动求解当前关卡")
    g.load_level(3)                       # 任意固定关卡
    g.state = Game.PLAYING
    order = g._solve_order()
    n0 = g.arrows_left()
    order_ok = len(order) == n0
    for (r, c) in order:                  # 按求解顺序逐一点击
        if g.board[r][c] is not None:
            g.click_cell(r, c)
    g.update(1.0, (0, 0))                 # 等最后一支箭飞完 -> 通关画面
    check("T08", order_ok and g.arrows_left() == 0 and g.state == Game.LEVEL_CLEAR)

    # ---- T09（附加）星级规则 ----
    print("T09 星级规则：满 3 星；撤销/提示各 1 次扣 1 星；AI 只给 1 星；失误上限统一 3")

    def clear_all(game):
        """按依赖顺序点掉剩余全部箭头，直到触发通关。"""
        for _ in range(100):
            hit = False
            for r in range(game.rows):
                for c in range(game.cols):
                    a = game.board[r][c]
                    if a and game.is_clear(r, c, a.d):
                        game.click_cell(r, c)
                        hit = True
                        break
                if hit:
                    break
            if not hit:
                return

    def fresh():
        g.load_level(0)
        g.state = Game.PLAYING
        g.total_stars = 0

    # 1) 不用任何辅助 -> 3 星
    fresh()
    clear_all(g)
    c1 = g.stars == 3 and g.total_stars == 3

    # 2) 用了 1 次撤销 -> 2 星；第 2 次撤销被拒绝且棋盘不变
    fresh()
    g.click_cell(2, 0)          # 飞出 -> 压栈
    g.undo()                    # 撤销 -> 机会归零，棋盘恢复
    restored = g.board[2][0] is not None and g.undos_left == 0
    g.click_cell(2, 0)          # 再射一次，让撤销栈非空
    before = dirs(g)
    g.undo()                    # 机会已用完：必须拒绝
    refused = g.undos_left == 0 and dirs(g) == before
    clear_all(g)
    c2 = restored and refused and g.stars == 2

    # 3) 用了 1 次提示 -> 2 星；第 2 次提示被拒绝
    fresh()
    g.use_hint()
    once_hint = g.hints_left == 0 and g.used_hints
    g.use_hint()
    clear_all(g)
    c3 = once_hint and g.hints_left == 0 and g.stars == 2

    # 4) 撤销 + 提示都用 -> 1 星
    fresh()
    g.click_cell(2, 0)
    g.undo()
    g.use_hint()
    clear_all(g)
    c4 = g.stars == 1

    # 5) 用 AI 自动求解 -> 只给 1 星
    fresh()
    g.start_auto_solve()
    ai_on = g.used_ai and g.auto_solving
    g.stop_auto_solve()
    clear_all(g)
    c5 = ai_on and g.stars == 1

    # 6) AI 与撤销叠加 -> 仍只给 1 星（不叠加为负）
    fresh()
    g.click_cell(2, 0)
    g.undo()
    g.use_hint()
    g.start_auto_solve()
    g.stop_auto_solve()
    clear_all(g)
    c6 = g.calc_stars() == 1 and g.stars == 1

    # 7) 失误上限统一为 3（8 关固定 + 随机模式各档）
    c7 = all(lv["mistakes"] == 3 for lv in LEVELS) and all(
        random_level_spec(1 + i)[3] == 3 for i in range(12))

    # 8) 重开本关要退回已计入的星数，避免重复计分
    fresh()
    clear_all(g)
    acc = g.total_stars
    g.restart_level()
    c8 = acc == 3 and g.total_stars == 0 and g.arrows_left() == 4

    check("T09", c1 and c2 and c3 and c4 and c5 and c6 and c7 and c8)

    print(f"\n结果：{passed} 通过，{failed} 失败")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run())
