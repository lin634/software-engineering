# -*- coding: utf-8 -*-
"""关卡可解性验证工具。

用法： python verify_levels.py
直接导入 arrow_game.py 中的 LEVELS，对每一关执行 DFS 求解，
输出是否可通关以及一条通关顺序。仅用于开发期验证，游戏运行不需要本文件。
"""
from arrow_game import LEVELS, DIR_VEC

DIRS = DIR_VEC  # (dr, dc)


def parse(level):
    """把字符串关卡解析为 {(r, c): dir}。"""
    arrows = {}
    for r, row in enumerate(level["grid"]):
        for c, ch in enumerate(row):
            if ch in DIRS:
                arrows[(r, c)] = ch
    return arrows


def is_clear(arrows, r, c, d, rows, cols):
    """判断 (r,c) 朝方向 d 是否一路畅通到边界。"""
    dr, dc = DIRS[d]
    nr, nc = r + dr, c + dc
    while 0 <= nr < rows and 0 <= nc < cols:
        if (nr, nc) in arrows:
            return False
        nr += dr
        nc += dc
    return True


def solve(level):
    rows = len(level["grid"])
    cols = len(level["grid"][0])
    start = parse(level)
    start_key = frozenset(start.items())
    if not start_key:
        return True, []
    seen = {start_key}
    stack = [(start_key, [])]
    while stack:
        state, path = stack.pop()
        if not state:
            return True, path
        state_dict = dict(state)
        for (r, c), d in list(state_dict.items()):
            if is_clear(state_dict, r, c, d, rows, cols):
                nxt = dict(state_dict)
                del nxt[(r, c)]
                nk = frozenset(nxt.items())
                if nk not in seen:
                    seen.add(nk)
                    stack.append((nk, path + [(r, c, d)]))
    return False, []


def main():
    all_ok = True
    for i, lvl in enumerate(LEVELS, 1):
        grid = lvl["grid"]
        rows = len(grid)
        cols = len(grid[0])
        n = sum(1 for row in grid for ch in row if ch in DIR_VEC)
        ok, order = solve(lvl)
        status = "可通关 ✓" if ok else "不可通关 ✗"
        print(f"第 {i} 关 {lvl['name']} ({rows}x{cols}, {n} 支箭, 失误上限 {lvl['mistakes']}): {status}")
        if ok:
            print("  通关顺序:", " -> ".join(f"({r},{c}){d}" for r, c, d in order))
        else:
            all_ok = False
    print("\n全部可通关" if all_ok else "\n存在不可通关的关卡！")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
