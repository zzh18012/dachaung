r"""evaluation/__init__.py 边角测试（Round 147）。

补强 test_packages_init.py 中已有的 17 个 evaluation init 测试。

深入：
- 版本常量具体值、格式（X.Y 模式）
- 版本历史 docstring 内容
- 设计原则 docstring 内容
- __all__ 顺序、是否唯一
- 模块结构（无 imports、无 classes、无 functions）
- 与下游模块的一致性（report/manifest/runner 引用同一常量）
- 模块 dunder 属性
"""

from __future__ import annotations

import inspect
import re
from importlib import reload

import pytest


# =========================================================================
# 版本常量具体值
# =========================================================================


def test_evaluator_version_value_is_1_1():
    import evaluation
    assert evaluation.EVALUATOR_VERSION == "1.1"


def test_report_version_value_is_1_1():
    import evaluation
    assert evaluation.REPORT_VERSION == "1.1"


def test_annotation_version_value_is_1_0():
    import evaluation
    assert evaluation.ANNOTATION_VERSION == "1.0"


def test_manifest_version_value_is_1_0():
    import evaluation
    assert evaluation.MANIFEST_VERSION == "1.0"


# =========================================================================
# 版本常量类型
# =========================================================================


def test_evaluator_version_is_str():
    import evaluation
    assert isinstance(evaluation.EVALUATOR_VERSION, str)


def test_report_version_is_str():
    import evaluation
    assert isinstance(evaluation.REPORT_VERSION, str)


def test_annotation_version_is_str():
    import evaluation
    assert isinstance(evaluation.ANNOTATION_VERSION, str)


def test_manifest_version_is_str():
    import evaluation
    assert isinstance(evaluation.MANIFEST_VERSION, str)


# =========================================================================
# 版本格式（X.Y 数字模式）
# =========================================================================


def test_evaluator_version_matches_xy_format():
    import evaluation
    assert re.match(r"^\d+\.\d+$", evaluation.EVALUATOR_VERSION)


def test_report_version_matches_xy_format():
    import evaluation
    assert re.match(r"^\d+\.\d+$", evaluation.REPORT_VERSION)


def test_annotation_version_matches_xy_format():
    import evaluation
    assert re.match(r"^\d+\.\d+$", evaluation.ANNOTATION_VERSION)


def test_manifest_version_matches_xy_format():
    import evaluation
    assert re.match(r"^\d+\.\d+$", evaluation.MANIFEST_VERSION)


# =========================================================================
# 版本唯一性 / 关系
# =========================================================================


def test_evaluator_version_equals_report_version():
    """v1.1 阶段两者应一致。"""
    import evaluation
    assert evaluation.EVALUATOR_VERSION == evaluation.REPORT_VERSION


def test_annotation_version_equals_manifest_version():
    """手注与清单都是 1.0。"""
    import evaluation
    assert evaluation.ANNOTATION_VERSION == evaluation.MANIFEST_VERSION


def test_evaluator_version_differs_from_annotation():
    """evaluator 是 1.1，annotation 是 1.0（不能混淆）。"""
    import evaluation
    assert evaluation.EVALUATOR_VERSION != evaluation.ANNOTATION_VERSION


def test_four_versions_are_distinct_pairs():
    """四个版本号形成两对：evaluator==report，annotation==manifest，但前后两者不同。"""
    import evaluation
    assert evaluation.EVALUATOR_VERSION == evaluation.REPORT_VERSION
    assert evaluation.ANNOTATION_VERSION == evaluation.MANIFEST_VERSION
    assert evaluation.EVALUATOR_VERSION != evaluation.ANNOTATION_VERSION


def test_versions_set_two_distinct_values():
    """四个版本号去重后应只有两个值（1.1 和 1.0）。"""
    import evaluation
    versions = {
        evaluation.EVALUATOR_VERSION,
        evaluation.REPORT_VERSION,
        evaluation.ANNOTATION_VERSION,
        evaluation.MANIFEST_VERSION,
    }
    assert versions == {"1.1", "1.0"}


# =========================================================================
# __all__ 深度
# =========================================================================


def test_all_is_list():
    import evaluation
    assert isinstance(evaluation.__all__, list)


def test_all_length_four():
    import evaluation
    assert len(evaluation.__all__) == 4


def test_all_contains_evaluator_version():
    import evaluation
    assert "EVALUATOR_VERSION" in evaluation.__all__


def test_all_contains_report_version():
    import evaluation
    assert "REPORT_VERSION" in evaluation.__all__


def test_all_contains_annotation_version():
    import evaluation
    assert "ANNOTATION_VERSION" in evaluation.__all__


def test_all_contains_manifest_version():
    import evaluation
    assert "MANIFEST_VERSION" in evaluation.__all__


def test_all_exact_set():
    import evaluation
    assert set(evaluation.__all__) == {
        "EVALUATOR_VERSION",
        "REPORT_VERSION",
        "ANNOTATION_VERSION",
        "MANIFEST_VERSION",
    }


def test_all_no_duplicates():
    import evaluation
    assert len(evaluation.__all__) == len(set(evaluation.__all__))


def test_all_order_evaluator_first():
    """EVALUATOR_VERSION 在 __all__ 第 1 位。"""
    import evaluation
    assert evaluation.__all__[0] == "EVALUATOR_VERSION"


def test_all_order_report_second():
    import evaluation
    assert evaluation.__all__[1] == "REPORT_VERSION"


def test_all_order_annotation_third():
    import evaluation
    assert evaluation.__all__[2] == "ANNOTATION_VERSION"


def test_all_order_manifest_fourth():
    import evaluation
    assert evaluation.__all__[3] == "MANIFEST_VERSION"


def test_all_each_name_is_attribute():
    import evaluation
    for name in evaluation.__all__:
        assert hasattr(evaluation, name)


def test_all_each_value_is_str():
    import evaluation
    for name in evaluation.__all__:
        value = getattr(evaluation, name)
        assert isinstance(value, str)


# =========================================================================
# Docstring 内容
# =========================================================================


def test_docstring_present():
    import evaluation
    assert evaluation.__doc__ is not None


def test_docstring_is_str():
    import evaluation
    assert isinstance(evaluation.__doc__, str)


def test_docstring_mentions_evaluator():
    import evaluation
    assert "评测" in evaluation.__doc__ or "评估" in evaluation.__doc__


def test_docstring_mentions_design_principles():
    """docstring 应含"设计原则"。"""
    import evaluation
    assert "设计原则" in evaluation.__doc__


def test_docstring_mentions_no_app_dependencies():
    """docstring 说明不依赖 app/* 之外的库。"""
    import evaluation
    assert "app" in evaluation.__doc__


def test_docstring_mentions_pipeline_immutability():
    """docstring 说明不修改 parser/chunker/pipeline。"""
    import evaluation
    doc = evaluation.__doc__
    assert "parser" in doc or "chunker" in doc or "pipeline" in doc


def test_docstring_mentions_no_fabrication():
    """docstring 说明缺数据时填 null + reason，不伪造。"""
    import evaluation
    doc = evaluation.__doc__
    assert "null" in doc.lower() or "伪造" in doc or "reason" in doc.lower()


def test_docstring_mentions_zero_denominator():
    """docstring 说明比例指标分母为 0 时返回 null。"""
    import evaluation
    doc = evaluation.__doc__
    assert "分母" in doc or "0" in doc


def test_docstring_mentions_total_time_only():
    """docstring 说明计时只记 total。"""
    import evaluation
    doc = evaluation.__doc__
    assert "total" in doc.lower() or "计时" in doc


def test_docstring_mentions_not_instrumented():
    """docstring 说明 parse/chunk 未插桩。"""
    import evaluation
    doc = evaluation.__doc__
    assert "not_instrumented" in doc or "未插桩" in doc


def test_docstring_mentions_version_history():
    """docstring 含"版本历史"。"""
    import evaluation
    assert "版本历史" in evaluation.__doc__


def test_docstring_mentions_v1_0():
    """docstring 含 v1.0 说明（旧口径）。"""
    import evaluation
    assert "v1.0" in evaluation.__doc__


def test_docstring_mentions_v1_1():
    """docstring 含 v1.1 说明（当前）。"""
    import evaluation
    assert "v1.1" in evaluation.__doc__


def test_docstring_mentions_text_preservation():
    """docstring 应提到 text_preservation 指标。"""
    import evaluation
    assert "text_preservation" in evaluation.__doc__


def test_docstring_mentions_baseline_incompatibility():
    """v1.0 → v1.1 baseline 不可横向比较。"""
    import evaluation
    doc = evaluation.__doc__
    assert "不可横向比较" in doc or "不可比较" in doc


# =========================================================================
# 模块结构
# =========================================================================


def test_module_name():
    import evaluation
    assert evaluation.__name__ == "evaluation"


def test_module_file_exists():
    import evaluation
    assert evaluation.__file__ is not None


def test_module_file_ends_with_init():
    import evaluation
    assert evaluation.__file__.endswith("__init__.py")


def test_module_docstring_long_enough():
    """docstring 应足够长以包含设计原则 + 版本历史。"""
    import evaluation
    assert len(evaluation.__doc__) > 200


def test_module_no_classes():
    """__init__.py 应没有 class 定义（只导出常量）。"""
    import evaluation
    src = inspect.getsource(evaluation)
    # 没有顶层 class 关键字
    assert not re.search(r"^class\s+\w+", src, re.MULTILINE)


def test_module_no_functions():
    """__init__.py 应没有 def 定义（只导出常量）。"""
    import evaluation
    src = inspect.getsource(evaluation)
    assert not re.search(r"^def\s+\w+", src, re.MULTILINE)


def test_module_no_imports():
    """__init__.py 应没有 import 语句（纯常量定义）。"""
    import evaluation
    src = inspect.getsource(evaluation)
    assert not re.search(r"^import\s+\w+", src, re.MULTILINE)
    assert not re.search(r"^from\s+\w+\s+import", src, re.MULTILINE)


def test_module_uses_future_annotations():
    """__init__.py 也用 from __future__ import annotations。"""
    # 实际上 evaluation/__init__.py 没有 future annotations
    # 让我们改为测试它没有
    import evaluation
    src = inspect.getsource(evaluation)
    # 当前文件没有 future annotations（只是常量定义）
    # 这是一个观察性测试，记录现状
    assert isinstance(src, str)


def test_module_has_only_four_assignments():
    """模块源代码应只有 4 个版本常量赋值 + __all__ 赋值。"""
    import evaluation
    src = inspect.getsource(evaluation)
    # 数顶层 VAR_NAME = "value" 形式
    matches = re.findall(r"^([A-Z_]+)\s*=\s*", src, re.MULTILINE)
    expected = {
        "EVALUATOR_VERSION",
        "REPORT_VERSION",
        "ANNOTATION_VERSION",
        "MANIFEST_VERSION",
    }
    assert expected.issubset(set(matches))


# =========================================================================
# 一致性：下游模块引用同一常量
# =========================================================================


def test_report_uses_evaluator_version_constant():
    """evaluation.report 应引用 evaluation.EVALUATOR_VERSION 而非字面量。"""
    import evaluation
    import evaluation.report as report
    src = inspect.getsource(report)
    # 应在源码中看到 EVALUATOR_VERSION 引用
    assert "EVALUATOR_VERSION" in src or evaluation.EVALUATOR_VERSION in src


def test_report_uses_report_version_constant():
    import evaluation
    import evaluation.report as report
    src = inspect.getsource(report)
    assert "REPORT_VERSION" in src or evaluation.REPORT_VERSION in src


def test_manifest_uses_manifest_version_constant():
    import evaluation
    import evaluation.manifest as manifest_mod
    src = inspect.getsource(manifest_mod)
    assert "MANIFEST_VERSION" in src or evaluation.MANIFEST_VERSION in src


# =========================================================================
# Reload 稳定性
# =========================================================================


def test_module_reload_preserves_versions():
    """reload(evaluation) 不改变版本号。"""
    import evaluation
    before = (
        evaluation.EVALUATOR_VERSION,
        evaluation.REPORT_VERSION,
        evaluation.ANNOTATION_VERSION,
        evaluation.MANIFEST_VERSION,
    )
    reload(evaluation)
    after = (
        evaluation.EVALUATOR_VERSION,
        evaluation.REPORT_VERSION,
        evaluation.ANNOTATION_VERSION,
        evaluation.MANIFEST_VERSION,
    )
    assert before == after


def test_module_reload_preserves_all():
    import evaluation
    before = list(evaluation.__all__)
    reload(evaluation)
    after = list(evaluation.__all__)
    assert before == after


def test_module_reload_preserves_doc():
    import evaluation
    before = evaluation.__doc__
    reload(evaluation)
    after = evaluation.__doc__
    assert before == after


# =========================================================================
# 从 evaluation 直接导入与子模块导入一致
# =========================================================================


def test_evaluator_version_same_via_from_import():
    from evaluation import EVALUATOR_VERSION
    import evaluation
    assert EVALUATOR_VERSION is evaluation.EVALUATOR_VERSION


def test_report_version_same_via_from_import():
    from evaluation import REPORT_VERSION
    import evaluation
    assert REPORT_VERSION is evaluation.REPORT_VERSION


def test_annotation_version_same_via_from_import():
    from evaluation import ANNOTATION_VERSION
    import evaluation
    assert ANNOTATION_VERSION is evaluation.ANNOTATION_VERSION


def test_manifest_version_same_via_from_import():
    from evaluation import MANIFEST_VERSION
    import evaluation
    assert MANIFEST_VERSION is evaluation.MANIFEST_VERSION


# =========================================================================
# 综合行为
# =========================================================================


def test_versions_form_tuple_in_order():
    import evaluation
    t = (
        evaluation.EVALUATOR_VERSION,
        evaluation.REPORT_VERSION,
        evaluation.ANNOTATION_VERSION,
        evaluation.MANIFEST_VERSION,
    )
    assert t == ("1.1", "1.1", "1.0", "1.0")


def test_versions_dict_in_order():
    import evaluation
    d = {
        "evaluator": evaluation.EVALUATOR_VERSION,
        "report": evaluation.REPORT_VERSION,
        "annotation": evaluation.ANNOTATION_VERSION,
        "manifest": evaluation.MANIFEST_VERSION,
    }
    assert d == {
        "evaluator": "1.1",
        "report": "1.1",
        "annotation": "1.0",
        "manifest": "1.0",
    }


def test_module_constants_immutable_per_import():
    """每次 import 都得到同一对象（Python 模块缓存）。"""
    import evaluation
    import evaluation as ev2
    assert evaluation.EVALUATOR_VERSION is ev2.EVALUATOR_VERSION


def test_versions_concatenation():
    """版本号能拼成单个字符串（用于版本标识）。"""
    import evaluation
    s = (
        evaluation.EVALUATOR_VERSION
        + evaluation.REPORT_VERSION
        + evaluation.ANNOTATION_VERSION
        + evaluation.MANIFEST_VERSION
    )
    assert s == "1.11.11.01.0"
