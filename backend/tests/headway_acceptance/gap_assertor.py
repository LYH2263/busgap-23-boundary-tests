"""配对断言器：只吃造数结果，不碰库。

职责（验收硬性要求）：
- 从造数器产出的「到站序列 + 阈值」出发，独立按验收规格推出每一对
  (站点, 前班次, 后班次, 状态)，并给出前后班次号；
- 再把同一组到站原样喂给现网检测入口（可调用判定入口 detect_bunching），
  逐对差分：对数、每对的前后班次号、状态必须完全一致；
- 不允许为测例另写一套放宽判定——期望状态由规格直接钉死，实际状态只来自现网。
- 失败信息含：场景名、期望、实际。
"""
from __future__ import annotations

from app.services.bunch_engine import detect_bunching

from .scenario_data import Scenario, in_chronological_order

# 状态集合与现网一致：normal / bunching / large_gap。
NORMAL = "normal"
BUNCHING = "bunching"
LARGE_GAP = "large_gap"

PairStatus = tuple[str, str, str, str]  # (站点, 前班次, 后班次, 状态)


def _classify_by_spec(gap_min: float, bunch_threshold: float, large_threshold: float) -> str:
    """验收规格（钉死严格不等号）：

    - 间隔 == 串车阈：不串车；间隔 < 串车阈：串车（小一分钟必串车）；
    - 间隔 == 大间隔阈：不大间隔；间隔 > 大间隔阈：大间隔（大一分钟必大间隔）。
    """
    if gap_min < bunch_threshold:
        return BUNCHING
    if gap_min > large_threshold:
        return LARGE_GAP
    return NORMAL


def expected_pairs(scenario: Scenario) -> list[PairStatus]:
    """断言器独立推期望：同站按时刻排序，相邻配一对；自班次不配；首尾不越配。"""
    ordered = in_chronological_order(scenario.arrivals)
    pairs: list[PairStatus] = []
    for prev, cur in zip(ordered, ordered[1:]):
        if prev.trip_no == cur.trip_no:
            continue  # 自班次不配
        gap_min = round(cur.offset_min - prev.offset_min, 2)
        status = _classify_by_spec(gap_min, scenario.bunch_threshold_min, scenario.large_threshold_min)
        pairs.append((scenario.stop_name, prev.trip_no, cur.trip_no, status))
    return pairs


def actual_pairs_from_production(scenario: Scenario) -> list[PairStatus]:
    """把同一组到站喂给现网检测入口，取回每对状态（不放宽、不重判）。"""
    events = detect_bunching(
        scenario.arrivals_payload(),
        scenario.planned_headway_min,
        scenario.bunch_threshold_min,
        scenario.large_threshold_min,
    )
    return [(e.stop_name, e.earlier_trip, e.later_trip, e.status) for e in events]


def assert_pairing_matches_production(scenario: Scenario) -> list[PairStatus]:
    """逐对核对断言器期望与现网检测结果；任一不一致整场失败。

    返回期望对列表，供场景脚本做声明式钉死。
    """
    expected = expected_pairs(scenario)
    actual = actual_pairs_from_production(scenario)

    if expected != actual:
        raise AssertionError(
            "配对结果与现网检测不一致（整场失败）\n"
            f"  场景名: {scenario.name}\n"
            f"  期望对: {expected}\n"
            f"  实际对: {actual}"
        )
    return expected
