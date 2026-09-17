# -*- coding: utf-8 -*-
"""一箭又一箭 —— 自动生成界面截图（headless）。

用 SDL dummy 驱动离屏渲染各界面并保存 PNG，供 README/博客使用。
运行： python make_screenshots.py
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_caption("一箭又一箭")
screen = pygame.display.set_mode((960, 720))

from arrow_game import Game

# 截图输出固定落在本脚本所在目录，与运行时的工作目录无关
os.chdir(os.path.dirname(os.path.abspath(__file__)))

OUT = "screenshots"
os.makedirs(OUT, exist_ok=True)


def shot(name):
    path = os.path.join(OUT, name)
    pygame.image.save(screen, path)
    print("saved", path)


def flush(game, seconds=0.6):
    """推进若干帧，让飞出动画等播完。"""
    frames = int(seconds * 60)
    for _ in range(frames):
        game.update(1 / 60, (0, 0))


def find_clearable(game):
    """找一支当前可以飞出的箭头。"""
    for r in range(game.rows):
        for c in range(game.cols):
            a = game.board[r][c]
            if a and game.is_clear(r, c, a.d):
                return (r, c)
    return None


def find_blocked(game):
    """找一支当前被阻挡的箭头。"""
    for r in range(game.rows):
        for c in range(game.cols):
            a = game.board[r][c]
            if a and not game.is_clear(r, c, a.d):
                return (r, c)
    return None


def quiet(game):
    """清掉残留的提示气泡，让静态截图更干净。"""
    game.feedback = ""
    game.feedback_t = 0.0


def clear_level(game, per_shot=0.25):
    """按可飞顺序清空当前关卡，直到弹出通关画面。

    最后一支箭要等飞出动画（0.8s）播完才进通关画面，所以末尾多刷 1 秒。
    """
    guard = 0
    while game.state == Game.PLAYING and game.arrows_left() > 0 and guard < 100:
        guard += 1
        cell = find_clearable(game)
        if cell is None:
            break
        game.click_cell(*cell)
        flush(game, per_shot)
    flush(game, 1.0)


g = Game(screen)

# 1) 开始界面
g.state = Game.MENU
g.draw()
shot("01_menu.png")

# 2) 游戏界面（第 5 关）
g.load_level(4)
g.state = Game.PLAYING
quiet(g)
g.draw()
shot("02_play_level1.png")

# 3) 提示功能（同关，高亮可射出箭头，本关提示机会只剩 0 次）
g.load_level(4)
g.state = Game.PLAYING
g.use_hint()
g.draw()
shot("03_hint.png")

# 4) 箭头飞出动画（第 1 关，射出一支可飞的箭头）
g.load_level(0)
g.state = Game.PLAYING
cell = find_clearable(g)
assert cell, "第 1 关应存在可飞出的箭头"
g.click_cell(*cell)
g.update(0.02, (0, 0))
g.draw()
shot("04_arrow_flyout.png")
flush(g, 0.8)

# 5) 通关界面（不借助任何辅助：满 3 星）
clear_level(g)
quiet(g)
g.draw()
shot("05_level_clear.png")

# 6) 失败界面（第 5 关，连点同一支被阻挡的箭头耗尽 3 次失误）
g.load_level(4)
g.state = Game.PLAYING
cell = find_blocked(g)
assert cell, "第 5 关应存在被阻挡的箭头"
for _ in range(g.mistakes_max):
    g.click_cell(*cell)          # 每次 -1 失误，耗尽即 GAME_OVER
assert g.state == Game.GAME_OVER, "3 次失误后应进入失败界面"
quiet(g)
g.draw()
shot("06_game_over.png")

# 7) 全部通关界面（真实连打 8 关，累计 24 星）
g.total_stars = 0
for i in range(8):
    g.load_level(i)
    g.state = Game.PLAYING
    clear_level(g, 0.12)
    assert g.state == Game.LEVEL_CLEAR, f"第 {i + 1} 关未能通关"
    g.advance_level()
g.state = Game.VICTORY
quiet(g)
g.draw()
shot("07_victory.png")

# 8) 随机模式（每关箭头随机分布）
g.enter_random_mode()
quiet(g)
g.draw()
shot("08_random_mode.png")

# 9) 用过一次撤销：本关只评 2 星
g.load_level(0)
g.state = Game.PLAYING
cell = find_clearable(g)
g.click_cell(*cell)              # 先射出一支
g.undo()                         # 撤销（-1 星，机会归零）
clear_level(g)
assert g.stars == 2, "用过撤销应为 2 星"
quiet(g)
g.draw()
shot("09_clear_2stars.png")

print("done")
