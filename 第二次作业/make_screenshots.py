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


g = Game(screen)

# 1) 开始界面
g.state = Game.MENU
g.draw()
shot("01_menu.png")

# 2) 游戏界面（第 5 关）
g.load_level(4)
g.state = Game.PLAYING
g.draw()
shot("02_play_level1.png")

# 3) 提示功能（同关，高亮可射出箭头）
g.load_level(4)
g.state = Game.PLAYING
g.hint_t = 2.2
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

# 5) 通关界面（按可飞顺序清空第 1 关全部箭头）
guard = 0
while g.arrows_left() > 0 and g.state == Game.PLAYING and guard < 100:
    guard += 1
    cell = find_clearable(g)
    if cell is None:
        break
    g.click_cell(*cell)
    flush(g, 0.25)
flush(g, 0.3)
g.draw()
shot("05_level_clear.png")

# 6) 失败界面（第 5 关，强行耗尽失误）
g.load_level(4)
g.state = Game.PLAYING
g.mistakes = 1        # 只剩 1 次，再失误即失败
cell = find_blocked(g)
assert cell, "第 5 关应存在被阻挡的箭头"
g.click_cell(*cell)   # 被阻挡 -> GAME_OVER
g.draw()
shot("06_game_over.png")

# 7) 全部通关界面
g.state = Game.VICTORY
g.draw()
shot("07_victory.png")

# 8) 随机模式（每关箭头随机分布）
g.enter_random_mode()
g.draw()
shot("08_random_mode.png")

print("done")
