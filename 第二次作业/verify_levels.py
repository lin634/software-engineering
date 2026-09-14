# -*- coding: utf-8 -*-
"""关卡可解性验证工具。

用法： python verify_levels.py
对 arrow_game.py 中定义的每一关执行 DFS 求解，输出是否可通关以及一条通关顺序。
仅用于开发期验证，游戏运行时不需要本文件。
"""
from collections import deque

DIRS = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}

# 关卡定义（与 arrow_game.py 中的 LEVELS 保持一致）
LEVELS = [
    # 第 1 关：入门，两个互不阻挡的箭头
    [
        ".....",
        "..R..",
        ".....",
        "...L.",
        ".....",
    ],
    # 第 2 关：链式阻挡，必须按顺序
    [
        ".RD..",
        "..D..",
        ".....",
        ".....",
        ".....",
    ],
    # 第 3 关：横向链 + 纵向阻挡交叉
    [
        "......",
        ".RRRR.",
        "......",
        ".D..U.",
        "......",
        "......",
    ],
    # 第 4 关（附加）：横链与纵链相互牵制
    [
        ".RRRR.",
        "......",
        ".D..U.",
        ".D..U.",
        "......",
        "......",
    ],
]


def parse(level):
    """把字符串关卡解析为 {(r, c): dir}。"""
    arrows = {}
    for r, row in enumerate(level):
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
    rows = len(level)
    cols = len(level[0])
    start = parse(level)
    # 状态：当前剩余箭头集合的 frozenset
    start_key = frozenset(start.items())
    if not start_key:
        return True, []

    seen = {start_key}
    # stack 里存 (状态, 已走顺序)
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
        rows = len(lvl)
        cols = len(lvl[0])
        ok, order = solve(lvl)
        status = "可通关 ✓" if ok else "不可通关 ✗"
        print(f"第 {i} 关 ({rows}x{cols}, {len(''.join(lvl).replace('.', ''))} 支箭): {status}")
        if ok:
            print("  通关顺序:", " -> ".join(f"({r},{c}){d}" for r, c, d in order))
        else:
            all_ok = False
    print("\n全部可通关" if all_ok else "\n存在不可通关的关卡！")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
