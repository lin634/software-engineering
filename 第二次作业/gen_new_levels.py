# -*- coding: utf-8 -*-
"""一次性工具：为 20 关扩展生成 L9-L20 的 8x8 网格（固定种子、可通关）。

运行：python gen_new_levels.py
把输出粘贴进 arrow_game.py 的 LEVELS 末尾即可。
"""
from arrow_game import generate_random_level, DIR_VEC
from verify_levels import solve

# (序号, 名称, n_arrows, seed)
SPECS = [
    (9,  "阵云密布", 24, 9001),
    (10, "箭走游龙", 24, 9017),
    (11, "乱箭交错", 25, 9033),
    (12, "矢影重重", 25, 9049),
    (13, "箭阵连环", 25, 9065),
    (14, "矢海沉舟", 26, 9081),
    (15, "万矢齐发", 26, 9097),
    (16, "天罗地网", 26, 9113),
    (17, "群矢破空", 26, 9129),
    (18, "箭神之境", 26, 9145),
    (19, "万箭穿云", 26, 9161),
    (20, "箭阵终极", 26, 9177),
]

SIZE = 8
MISTAKES = 3


def make(n, seed):
    for off in range(2000):
        grid = generate_random_level(SIZE, SIZE, n, seed=seed + off)
        if grid and solve({"grid": grid, "mistakes": MISTAKES})[0]:
            return grid, seed + off
    raise RuntimeError(f"无法生成 n={n} seed={seed}")


def main():
    for idx, name, n, seed in SPECS:
        grid, used = make(n, seed)
        rows = len(grid)
        cols = len(grid[0])
        count = sum(ch in DIR_VEC for row in grid for ch in row)
        block = "    {\n"
        block += f'        "name": "{name}",\n'
        block += f'        "mistakes": {MISTAKES},\n'
        block += '        "grid": [\n'
        for row in grid:
            block += f'            "{row}",\n'
        block += "        ],\n"
        block += "    },"
        print(f"# 第 {idx} 关 {name}  {rows}x{cols}  {count} 支箭  seed={used}")
        print(block)
        print()


if __name__ == "__main__":
    main()
