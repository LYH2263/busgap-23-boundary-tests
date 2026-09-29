"""时刻造数器：只产出到站序列与阈值。

纪律（验收硬性要求）：
- 只描述“谁、在哪个站、相对基准晚到多少分钟”，以及三个阈值参数
  （计划间隔、串车阈 bunch_threshold、大间隔阈 large_threshold）；
- 绝不夹带任何期望分类：场景名与注释只描述“输入数据的形状/数值”，
  不声明某一对最终算什么状态；
- 不知道断言器的存在，也不碰数据库。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

# 所有场景共用的时刻基准，仅用于把分钟偏移换算成 datetime。
_BASE = datetime(2026, 9, 29, 8, 0)


@dataclass(frozen=True)
class ArrivalSeed:
    """一条到站记录：班次号 + 相对基准的分钟偏移（无任何判定信息）。"""

    trip_no: str
    offset_min: float


@dataclass(frozen=True)
class Scenario:
    """一个验收场景：名称 + 到站序列 + 三个阈值参数。"""

    name: str
    stop_name: str
    planned_headway_min: float
    bunch_threshold_min: float
    large_threshold_min: float
    arrivals: tuple[ArrivalSeed, ...] = field(default_factory=tuple)

    def arrivals_payload(self) -> list[dict]:
        """转成现网检测入口所吃的到站字典（同一组到站，原样喂给现网）。"""
        return [
            {
                "stop_name": self.stop_name,
                "trip_no": a.trip_no,
                "actual_arrive": _BASE + timedelta(minutes=a.offset_min),
            }
            for a in in_chronological_order(self.arrivals)
        ]


def in_chronological_order(arrivals: tuple[ArrivalSeed, ...]) -> list[ArrivalSeed]:
    """按偏移排序后输出；造数时允许故意写乱序，确保消费侧都靠时刻排序配对。"""
    return sorted(arrivals, key=lambda a: a.offset_min)


def a(trip_no: str, offset_min: float) -> ArrivalSeed:
    """快捷构造一条到站：a('T1', 0)。"""
    return ArrivalSeed(trip_no=trip_no, offset_min=offset_min)


# ---------------------------------------------------------------------------
# 以下全是“造数”：只给定班次于某站的到步时刻偏移与三个阈值参数。
# 场景名只写数据形状/数值（间隔几分钟、几个班次、是否乱序），不写任何结果。
# ---------------------------------------------------------------------------

# 通用阈值参数：计划 8 分钟，串车阈 3，大间隔阈 15（与现网默认值一致）。
_PLANNED, _BUNCH, _LARGE = 8.0, 3.0, 15.0

SCENARIOS = [
    Scenario(
        name="two_trips_gap_3_min",
        stop_name="A站",
        planned_headway_min=_PLANNED,
        bunch_threshold_min=_BUNCH,
        large_threshold_min=_LARGE,
        arrivals=(a("T1", 0), a("T2", 3.0)),
    ),
    Scenario(
        name="two_trips_gap_2_min",
        stop_name="A站",
        planned_headway_min=_PLANNED,
        bunch_threshold_min=_BUNCH,
        large_threshold_min=_LARGE,
        arrivals=(a("T1", 0), a("T2", 2.0)),
    ),
    Scenario(
        name="three_trips_gaps_3_and_15_min",
        stop_name="A站",
        planned_headway_min=_PLANNED,
        bunch_threshold_min=_BUNCH,
        large_threshold_min=_LARGE,
        arrivals=(a("T1", 0), a("T2", 3.0), a("T3", 18.0)),
    ),
    Scenario(
        name="three_trips_gaps_8_and_16_min",
        stop_name="A站",
        planned_headway_min=_PLANNED,
        bunch_threshold_min=_BUNCH,
        large_threshold_min=_LARGE,
        arrivals=(a("T1", 0), a("T2", 8.0), a("T3", 24.0)),
    ),
    Scenario(
        name="three_arrivals_same_trip_no",
        stop_name="A站",
        planned_headway_min=_PLANNED,
        bunch_threshold_min=_BUNCH,
        large_threshold_min=_LARGE,
        arrivals=(a("T1", 0), a("T1", 1.0), a("T1", 20.0)),
    ),
    Scenario(
        name="three_trips_offsets_0_1_21",
        stop_name="A站",
        planned_headway_min=_PLANNED,
        bunch_threshold_min=_BUNCH,
        large_threshold_min=_LARGE,
        arrivals=(a("T1", 0), a("T2", 1.0), a("T3", 21.0)),
    ),
    Scenario(
        name="four_trips_offsets_0_1_21_22",
        stop_name="A站",
        planned_headway_min=_PLANNED,
        bunch_threshold_min=_BUNCH,
        large_threshold_min=_LARGE,
        arrivals=(a("T1", 0), a("T2", 1.0), a("T3", 21.0), a("T4", 22.0)),
    ),
    Scenario(
        name="four_trips_offsets_0_3_18_26",
        stop_name="A站",
        planned_headway_min=_PLANNED,
        bunch_threshold_min=_BUNCH,
        large_threshold_min=_LARGE,
        arrivals=(a("T1", 0), a("T2", 3.0), a("T3", 18.0), a("T4", 26.0)),
    ),
    Scenario(
        name="three_trips_offsets_given_out_of_order",
        stop_name="A站",
        planned_headway_min=_PLANNED,
        bunch_threshold_min=_BUNCH,
        large_threshold_min=_LARGE,
        arrivals=(a("T3", 21.0), a("T1", 0), a("T2", 1.0)),
    ),
    Scenario(
        name="single_trip_one_arrival",
        stop_name="A站",
        planned_headway_min=_PLANNED,
        bunch_threshold_min=_BUNCH,
        large_threshold_min=_LARGE,
        arrivals=(a("T1", 0),),
    ),
]
