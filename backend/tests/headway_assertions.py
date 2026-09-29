"""配对断言器：只吃造数结果，吐出每对状态与前后班次号；严禁碰库。

输入是造数器产出的 HeadwayScenario（到站序列 + 阈值），不读数据库、
不构造任何数据。它做两件事：

1. expected_pairs：按验收口径独立给出「相邻配对 + 每对状态」的期望，
   口径钉死为严格边界——间隔严格小于串车阈值才算 bunching，
   严格大于大间隔阈值才算 large_gap，相等一律 normal；同班次不配；
   只在同站内按到站时刻相邻配对，不做首尾越配。
2. actual_pairs：把同一组到站原样喂给现网检测入口 detect_bunching，
   取回生产判定结果。

assert_scenario_matches 逐对比对（站点、前班次、后班次、状态），
任何一对对不上即整场失败，失败信息含场景名、期望、实际。

注意：这里的期望口径是验收标准本身，独立于生产实现推导，
不为让测例通过而放宽或改写成另一套判定。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.bunch_engine import detect_bunching

from headway_fixtures import HeadwayScenario

_STATUS_BUNCHING = "bunching"
_STATUS_LARGE = "large_gap"
_STATUS_NORMAL = "normal"


@dataclass(frozen=True)
class PairVerdict:
    stop_name: str
    earlier_trip: str
    later_trip: str
    gap_min: float
    status: str

    def key(self) -> tuple[str, str, str]:
        return (self.stop_name, self.earlier_trip, self.later_trip)


def _verdict_status(gap_min: float, bunch_threshold: float, large_threshold: float) -> str:
    """验收口径：严格小于才串车，严格大于才大间隔，相等均为正常。"""
    if gap_min < bunch_threshold:
        return _STATUS_BUNCHING
    if gap_min > large_threshold:
        return _STATUS_LARGE
    return _STATUS_NORMAL


def expected_pairs(scenario: HeadwayScenario) -> list[PairVerdict]:
    """依据造数结果独立推导期望：同站、按时刻排序、相邻配对、同班次跳过。"""
    by_stop: dict[str, list[dict]] = {}
    for a in scenario.arrivals:
        by_stop.setdefault(a["stop_name"], []).append(a)

    pairs: list[PairVerdict] = []
    for stop_name in sorted(by_stop):
        items = sorted(by_stop[stop_name], key=lambda x: x["actual_arrive"])
        for i in range(1, len(items)):
            prev, cur = items[i - 1], items[i]
            if prev["trip_no"] == cur["trip_no"]:
                # 自班次不配
                continue
            gap_min = (cur["actual_arrive"] - prev["actual_arrive"]).total_seconds() / 60.0
            pairs.append(
                PairVerdict(
                    stop_name=stop_name,
                    earlier_trip=prev["trip_no"],
                    later_trip=cur["trip_no"],
                    gap_min=round(gap_min, 2),
                    status=_verdict_status(
                        gap_min, scenario.bunch_threshold, scenario.large_threshold
                    ),
                )
            )
    return pairs


def actual_pairs(scenario: HeadwayScenario) -> list[PairVerdict]:
    """把造数器的同一组到站原样喂给现网检测入口，取回逐对结果。"""
    events = detect_bunching(
        scenario.arrivals,
        scenario.planned_headway_min,
        scenario.bunch_threshold,
        scenario.large_threshold,
    )
    return [
        PairVerdict(
            stop_name=e.stop_name,
            earlier_trip=e.earlier_trip,
            later_trip=e.later_trip,
            gap_min=e.gap_min,
            status=e.status,
        )
        for e in events
    ]


def _render(pairs: list[PairVerdict]) -> list[str]:
    return [
        f"{p.stop_name}:{p.earlier_trip}->{p.later_trip} gap={p.gap_min} 状态={p.status}"
        for p in pairs
    ]


def assert_scenario_matches(scenario: HeadwayScenario) -> None:
    """逐对比对期望与现网检测结果；对不上则整场失败。

    以 (站点, 前班次, 后班次) 为键键控比对，不依赖生产侧的遍历顺序，
    同时钉死配对集合本身（缺失/越配/重复都会暴露）。
    """
    expected = expected_pairs(scenario)
    actual = actual_pairs(scenario)

    expected_map = {p.key(): p for p in expected}
    actual_map = {p.key(): p for p in actual}

    if len(expected_map) != len(expected) or len(actual_map) != len(actual):
        raise AssertionError(
            f"场景「{scenario.name}」存在重复配对：\n"
            f"期望: {_render(expected)}\n实际: {_render(actual)}"
        )

    if set(expected_map) != set(actual_map):
        missing = [expected_map[k] for k in expected_map.keys() - actual_map.keys()]
        extra = [actual_map[k] for k in actual_map.keys() - expected_map.keys()]
        raise AssertionError(
            f"场景「{scenario.name}」配对集合不一致：\n"
            f"缺失的对: {_render(missing)}\n越配的对: {_render(extra)}\n"
            f"期望: {_render(expected)}\n实际: {_render(actual)}"
        )

    for key in expected_map:
        exp, act = expected_map[key], actual_map[key]
        if exp.status != act.status:
            raise AssertionError(
                f"场景「{scenario.name}」配对 {key[0]}:{key[1]}->{key[2]} 状态不一致：\n"
                f"期望: 状态={exp.status} (gap={exp.gap_min})\n"
                f"实际: 状态={act.status} (gap={act.gap_min})"
            )

