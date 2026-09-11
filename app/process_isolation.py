"""原生崩溃隔离：一次性 subprocess 子进程执行高风险解析（Stage 10 批次 2 首项）。

背景（docs/BACKLOG.md §5，批次 16 已知限制）：pdfplumber 底层 C 库的
原生崩溃（segfault / access violation）会直接杀死所在进程。在
multiprocessing.Pool 场景（app.cli batch-parse 与 evaluation --workers）
一个 worker 的原生崩溃使整个进程池失效——剩余任务全部失败或永久挂起。
Python 异常自批次 16 起已在 worker 内全隔离，本模块补的是原生崩溃层：
每个高风险任务在一次性子进程内执行，崩溃由父侧经退出码捕获并转为
结构化错误，进程池与批次继续。

实现选型：subprocess 而非 multiprocessing.Process——Pool worker 是
daemonic 进程，而 daemonic 进程禁止再派生 multiprocessing 子进程
（Process.start() 直接 AssertionError），mp 方案恰在要保护的并行路径上
不可用；subprocess 无此限制，主进程 / 顺序路径 / Pool worker 内行为一致。

裁决约束（十六/十八轮）：隔离崩溃与显式失败，禁静默重试、禁换解析
策略悄悄改结果——成功路径输出与隔离前逐字节一致；崩溃仅新增错误码
``parser_process_crashed``（无 traceback，exitcode 入 message）。

任务传递：stdin 两段 pickle（父 sys.path 列表 + (fn, args)）。先恢复
sys.path 再 unpickle 函数引用，使测试模块级函数与插件模块在子进程内
可解析；结果经 stdout 单段 pickle 回传。

已知边界：
- 只按输入后缀隔离 ``.pdf``（pdfplumber 是唯一有原生崩溃记录的库；
  md/html/text/ipynb 为纯 Python 路径，不付每文件一次解释器启动的
  import 代价）；插件声明 .pdf 扩展名时同被隔离（过近似，无语义影响）
- 等待无超时：C 库死循环（挂起而非崩溃）行为与既有实现一致，不属
  本项范围
- 单文件 ``app.cli parse`` 仍为进程内执行（崩溃 = CLI 进程死亡，
  既有语义不变）
- 子进程内 Python 异常同样结构化回传（与批次 16 worker 错误隔离
  语义对齐），不外泄原始 traceback 到进程边界外
- 子进程 stderr 丢弃（DEVNULL）：崩溃诊断信息只有结构化错误码 +
  exitcode，stdout 是唯一结果通道
"""

from __future__ import annotations

import pickle
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

CRASH_ERROR_CODE = "parser_process_crashed"

_CHILD_SCRIPT = Path(__file__).resolve().parent / "_isolated_child.py"


def run_in_isolated_process(
    fn: Callable, args: tuple
) -> tuple[str, Any]:
    """在一次性子进程内执行 ``fn(*args)``。

    返回 ``(status, payload)``：

    - ``("ok", value)``：fn 正常返回；
    - ``("exc", {"type", "message", "traceback"})``：fn 抛出 Python 异常
      （调用方按既有错误隔离语义归类，不算崩溃）；
    - ``("crashed", {"code", "message", "exitcode"})``：子进程异常终止
      （原生崩溃 / os._exit 等，exitcode≠0 或结果管道 EOF）。
    """
    task = pickle.dumps(list(sys.path)) + pickle.dumps((fn, args))
    proc = subprocess.Popen(
        [sys.executable, str(_CHILD_SCRIPT)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        out, _ = proc.communicate(input=task)
    finally:
        # communicate 正常完成后无残留；防御性确保句柄不泄漏
        if proc.stdin is not None and not proc.stdin.closed:
            proc.stdin.close()
    if proc.returncode != 0:
        return (
            "crashed",
            {
                "code": CRASH_ERROR_CODE,
                "exitcode": proc.returncode,
                "message": (
                    f"解析子进程异常终止（exitcode={proc.returncode}，"
                    f"疑似 pdfplumber 底层 C 库原生崩溃），已隔离，"
                    f"批处理继续"
                ),
            },
        )
    try:
        status, *rest = pickle.loads(out)
    except Exception:  # noqa: BLE001 — 空输出/坏数据均按崩溃防御处理
        # exitcode==0 但无可解析结果：防御路径（send 失败被吞/结果损坏）
        return (
            "crashed",
            {
                "code": CRASH_ERROR_CODE,
                "exitcode": proc.returncode,
                "message": "解析子进程正常退出但未回传结果（结果管道 EOF）",
            },
        )
    if status == "ok":
        return ("ok", rest[0])
    return (
        "exc",
        {
            "type": rest[0],
            "message": rest[1],
            "traceback": rest[2],
        },
    )


__all__ = ["CRASH_ERROR_CODE", "run_in_isolated_process"]
