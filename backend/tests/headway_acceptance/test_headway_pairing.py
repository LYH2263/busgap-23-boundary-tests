"""场景脚本：只串联，不做任何判定。

纪律（验收硬性要求）：
- 脚本只把「造数器产出的场景」喂给「断言器」，并把断言器结果与钉死的期望对核对；
- 禁止在脚本里用分支写“应否串车”——所有状态是按验收规格钉死的声明式期望表，
  不允许由间隔大小临时计算；
- 断言器同时强制：同一组到站喂现网检测入口，逐对一致，否则整场失败。

期望表钉死的验收点：
1. 串车阈相等不串车（间隔 == bunch_threshold → normal）
2. 小一分钟必串车（间隔 == bunch_threshold - 1 → bunching）
3. 大间隔阈相等不大间隔（间隔 == large_threshold → normal）
4. 大一分钟必大间隔（间隔 == large_threshold + 1 → large_gap）
5. 自班次不配（同一 trip_no 的相邻到点 → 不出对）
6. 三班同站只相邻两对、禁首尾越配（只 T1→T2、T2→T3，不得 T1→T3）
7. 同一场景串车与大间隔并存时，按对分别给状态
"""
from __future__ import annotations

import pytest

from .gap_assertor import (
    BUNCHING,
    LARGE_GAP,
    NORMAL,
    assert_pairing_matches_production,
)
from .scenario_data import SCENARIOS, Scenario

STOP = "A站"

# 声明式期望表：场景名 -> 逐对 (站点, 前班次, 后班次, 状态)。
# 这里的状态是验收规格钉死的，不是按间隔现算的；脚本主体不含任何分支判定。
PINNED_EXPECTATIONS: dict[str, list[tuple[str, str, str, str]]] = {
    # 1) 间隔恰等于串车阈 3：不串车
    "two_trips_gap_3_min": [
        (STOP, "T1", "T2", NORMAL),
    ],
    # 2) 间隔 2 = 串车阈 3 - 1（小一分钟）：必串车
    "two_trips_gap_2_min": [
        (STOP, "T1", "T2", BUNCHING),
    ],
    # 3) 两段间隔恰好 3（串车阈相等）与恰好 15（大间隔阈相等）：都不触发
    "three_trips_gaps_3_and_15_min": [
        (STOP, "T1", "T2", NORMAL),
        (STOP, "T2", "T3", NORMAL),
    ],
    # 4) 后一段 16 = 大间隔阈 15 + 1（大一分钟）：必大间隔；前段 8 普通
    "three_trips_gaps_8_and_16_min": [
        (STOP, "T1", "T2", NORMAL),
        (STOP, "T2", "T3", LARGE_GAP),
    ],
    # 5) 三条全是同一班次 T1：自班次不配，一对都不出
    "three_arrivals_same_trip_no": [],
    # 6) 三班同站：只有相邻两对 T1→T2、T2→T3；首尾 T1→T3 禁越配
    "three_trips_offsets_0_1_21": [
        (STOP, "T1", "T2", BUNCHING),
        (STOP, "T2", "T3", LARGE_GAP),
    ],
    # 7) 同一场景三对分别为 串车 / 大间隔 / 串车，按对各自给状态
    "four_trips_offsets_0_1_21_22": [
        (STOP, "T1", "T2", BUNCHING),
        (STOP, "T2", "T3", LARGE_GAP),
        (STOP, "T3", "T4", BUNCHING),
    ],
    # 相等边界 3、15 与普通间隔 8 连排：全部不触发
    "four_trips_offsets_0_3_18_26": [
        (STOP, "T1", "T2", NORMAL),
        (STOP, "T2", "T3", NORMAL),
        (STOP, "T3", "T4", NORMAL),
    ],
    # 乱序输入：消费侧配对前必须先按时刻排序，结果与三班相邻场景一致
    "three_trips_offsets_given_out_of_order": [
        (STOP, "T1", "T2", BUNCHING),
        (STOP, "T2", "T3", LARGE_GAP),
    ],
    # 单条到站：无相邻，不成对
    "single_trip_one_arrival": [],
}

# 串联：每个造数场景配它钉死的期望（纯列表推导，无分支）。
_CASES = [(scenario, PINNED_EXPECTATIONS[scenario.name]) for scenario in SCENARIOS]


@pytest.mark.parametrize(
    "scenario, pinned_pairs",
    _CASES,
    ids=[scenario.name for scenario in SCENARIOS],
)
def test_headway_pairing(scenario: Scenario, pinned_pairs: list[tuple[str, str, str, str]]):
    # 断言器内部已把同一组到站喂给现网检测入口并逐对差分；不一致会在此整场失败。
    actual_pairs = assert_pairing_matches_production(scenario)

    # 再与钉死的规格期望逐对核对（前后班次号 + 状态），失败含场景名/期望/实际。
    assert pinned_pairs == actual_pairs, (
        "间隔配对与验收规格不符\n"
        f"  场景名: {scenario.name}\n"
        f"  期望: {pinned_pairs}\n"
        f"  实际: {actual_pairs}"
    )
