"""时刻造数器：只产出「到站序列 + 阈值」，严禁夹带任何期望分类。

本模块的唯一职责是按场景构造喂给判定入口的数据：
- 每个场景给出名称、到站记录序列（stop_name / trip_no / actual_arrive）
- 以及该线的计划间隔、串车阈值、大间隔阈值

禁止在此声明某对应为 bunching / normal / large_gap，
期望状态一律由配对断言器依据验收口径独立给出。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class HeadwayScenario:
    name: str
    arrivals: list[dict]
    planned_headway_min: float
    bunch_threshold: float
    large_threshold: float


_BASE = datetime(2026, 1, 1, 8, 0, 0)

# 全线统一阈值：串车 3 分钟（严格小于才算），大间隔 15 分钟（严格大于才算）
_BUNCH_T = 3.0
_LARGE_T = 15.0
_PLANNED = 8.0


def _arrivals(spec: list[tuple[str, str, int]]) -> list[dict]:
    """spec: (站点, 班次号, 距基准时刻的分钟偏移)。"""
    return [
        {
            "stop_name": stop,
            "trip_no": trip,
            "actual_arrive": _BASE + timedelta(minutes=offset),
        }
        for stop, trip, offset in spec
    ]


def _scenario(name: str, spec: list[tuple[str, str, int]]) -> HeadwayScenario:
    return HeadwayScenario(
        name=name,
        arrivals=_arrivals(spec),
        planned_headway_min=_PLANNED,
        bunch_threshold=_BUNCH_T,
        large_threshold=_LARGE_T,
    )


def build_scenarios() -> list[HeadwayScenario]:
    """构造全部验收场景。间隔与阈值的边界关系由时刻偏移钉死，此处不写结论。"""
    return [
        # 间隔 == 串车阈值：不串车
        _scenario(
            "串车阈值相等不串车",
            [("A", "T1", 0), ("A", "T2", 3)],
        ),
        # 间隔比串车阈值小一分钟：必串车
        _scenario(
            "小一分钟必串车",
            [("A", "T1", 0), ("A", "T2", 2)],
        ),
        # 间隔 == 大间隔阈值：不算大间隔
        _scenario(
            "大间隔阈值相等不算大间隔",
            [("A", "T1", 0), ("A", "T2", 15)],
        ),
        # 间隔比大间隔阈值大一分钟：必大间隔
        _scenario(
            "大一分钟必大间隔",
            [("A", "T1", 0), ("A", "T2", 16)],
        ),
        # 同一班次的两条到站记录：自班次不配
        _scenario(
            "自班次不配",
            [("A", "T1", 0), ("A", "T1", 2)],
        ),
        # 三班同站：只允许相邻两对，禁止首尾越配
        _scenario(
            "三班同站只相邻两对禁首尾越配",
            [("A", "T1", 0), ("A", "T2", 5), ("A", "T3", 10)],
        ),
        # 同一场景串车与大间隔并存：按对分别给状态
        _scenario(
            "串车与大间隔并存按对分别判定",
            [("A", "T1", 0), ("A", "T2", 2), ("A", "T3", 22)],
        ),
        # 配对不得跨站：两站各自成对对同一组时刻分别判定
        _scenario(
            "配对限定在同站之内",
            [
                ("A", "T1", 0),
                ("A", "T2", 2),
                ("B", "T1", 0),
                ("B", "T2", 16),
            ],
        ),
    ]
