"""场景脚本：只负责把造数器与断言器串联起来。

这里不写任何「这对该不该串车/算不算大间隔」的判断分支（无 if 分类逻辑），
逐对状态的期望由断言器按验收口径给出，再与现网检测入口的结果逐对核对。
每个场景是一条独立用例，对不上即整场失败。
"""
from __future__ import annotations

import pytest

from headway_assertions import assert_scenario_matches
from headway_fixtures import build_scenarios

_SCENARIOS = build_scenarios()


@pytest.mark.parametrize(
    "scenario",
    _SCENARIOS,
    ids=[s.name for s in _SCENARIOS],
)
def test_headway_scenario(scenario):
    assert_scenario_matches(scenario)
