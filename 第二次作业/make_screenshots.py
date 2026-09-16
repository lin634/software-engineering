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


g = Game(screen)

# 1) 开始界面
g.state = Game.MENU
g.draw()
shot("01_menu.png")

# 2) 游戏界面（第 5 关 · 密阵初布，15 支箭）
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

# 4) 箭头飞出动画（第 1 关，射出一支）
g.load_level(0)
g.state = Game.PLAYING
g.click_cell(1, 2)   # (1,2)R 飞出
g.update(0.02, (0, 0))
g.draw()
shot("04_arrow_flyout.png")
flush(g, 0.8)

# 5) 通关界面（清空第 1 关剩余箭头：先 (3,2)U 再 (4,1)L）
g.click_cell(3, 2)    # (3,2)U 飞出
flush(g, 0.4)
g.click_cell(4, 1)    # (4,1)L 飞出 -> LEVEL_CLEAR
flush(g, 0.4)
g.draw()
shot("05_level_clear.png")

# 6) 失败界面（第 5 关，强行耗尽失误）
g.load_level(4)
g.state = Game.PLAYING
g.mistakes = 1        # 只剩 1 次，再失误即失败
g.click_cell(1, 0)    # (1,0)R 被 (1,1)R 阻挡 -> GAME_OVER
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
