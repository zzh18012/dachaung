r"""套件健康元测试（f 优先级首轮，Round 1885，R52 协议 v2）。

三个守卫（R1885 实测基线：1857 文件 / 94464 test 函数 /
87558 唯一体 → 2619 重复组 / 6906 冗余实例）：
- **重复体天花板**：跨文件 AST 体重复组 ≤ 2619、冗余实例
  ≤ 6906——只许降不许升（防新增机械重复；历史存量的清理
  属指示线裁决，不在自跑线单方面动）
- **无空测试文件**：每个 test_*.py 至少一个 test 函数
- **无文件内重名**：同名 def 后者遮蔽前者（R1885 已修 10 组
  ——7 组复活重命名 + 3 组纯冗余删除，全过）
"""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
from pathlib import Path

TESTS_DIR = Path(__file__).parent
MAX_DUPLICATE_GROUPS = 2619
MAX_REDUNDANT_FUNCTIONS = 6906


def _scan() -> tuple[defaultdict, list[str], list[str]]:
    bodies: defaultdict = defaultdict(int)
    empty_files: list[str] = []
    dup_names: list[str] = []
    for p in sorted(TESTS_DIR.glob("test_*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        names = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) \
                    and node.name.startswith("test_"):
                bodies[ast.dump(node)] += 1
                names.append(node.name)
        if not names:
            empty_files.append(p.name)
        for name, k in Counter(names).items():
            if k > 1:
                dup_names.append(f"{p.name}::{name}")
    return bodies, empty_files, dup_names


def test_duplicate_test_bodies_below_ceiling():
    bodies, _, _ = _scan()
    groups = sum(1 for c in bodies.values() if c > 1)
    redundant = sum(c - 1 for c in bodies.values() if c > 1)
    assert groups <= MAX_DUPLICATE_GROUPS, \
        f"duplicate groups grew: {groups} > {MAX_DUPLICATE_GROUPS}"
    assert redundant <= MAX_REDUNDANT_FUNCTIONS, \
        f"redundant functions grew: {redundant} > {MAX_REDUNDANT_FUNCTIONS}"


def test_every_test_file_has_tests():
    _, empty_files, _ = _scan()
    assert empty_files == []


def test_no_within_file_duplicate_test_names():
    _, _, dup_names = _scan()
    assert dup_names == []


def test_no_private_user_paths_in_tests():
    """私有数据路径审计（f 队列，R1886）：测试源码不得含
    用户名 / 中文私人目录字面量（R1886 修复 edges57 一处
    硬编码用户名路径；C 盘符串不禁止——66 处为良性负向守卫
    断言"源码不含绝对路径"）。模式运行时拼接，防自匹配。"""
    user = "zzh" + "n2"
    private_dir = "大" + "创"
    banned = (user, private_dir)
    offenders = []
    for p in sorted(TESTS_DIR.glob("test_*.py")):
        src = p.read_text(encoding="utf-8")
        for token in banned:
            if token in src:
                offenders.append(f"{p.name} contains private token")
                break
    assert offenders == []
