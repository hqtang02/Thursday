"""SmartWater Optimizer 核心引擎的 pytest 单元测试套件。

运行方式（在项目根目录）：
    pytest -q
"""

from __future__ import annotations

import itertools
from typing import Any, Dict, List

import pytest

from water_engine import (
    analyze_usage_breakdown,
    calculate_tiered_bill,
    check_drought_status,
    generate_conservation_plan,
    load_config,
)


@pytest.fixture(scope="module")
def hk_brackets() -> List[Dict[str, Any]]:
    """香港 4 个月账单周期的阶梯定义。"""
    return load_config()["tariffs"]["hong_kong"]["brackets"]


@pytest.fixture(scope="module")
def family_usage() -> Dict[str, Any]:
    """典型三口之家的每日用水参数。"""
    return {
        "people": 3,
        "shower_minutes_per_day": 8.0,
        "laundry_loads_per_week": 5.0,
        "dishwashing_habit": "dishwasher",
    }


# ---------------------------------------------------------------------------
# 1. 阶梯水价临界点
# ---------------------------------------------------------------------------


class TestTieredBill:
    """验证分段累进计价在临界点处完全准确。"""

    @pytest.mark.parametrize(
        ("usage", "expected_bill", "expected_tier"),
        [
            (0.0, 0.0, 1),
            (12.0, 0.0, 1),        # 免费上限，仍属第一档
            (12.1, 0.416, 2),      # 刚进入第二档：0.1 * 4.16
            (43.0, 128.96, 2),     # 31 * 4.16
            (62.0, 251.51, 3),     # 128.96 + 19 * 6.45
            (62.5, 256.035, 4),    # 251.51 + 0.5 * 9.05
        ],
    )
    def test_exact_boundaries(
        self,
        hk_brackets: List[Dict[str, Any]],
        usage: float,
        expected_bill: float,
        expected_tier: int,
    ) -> None:
        result = calculate_tiered_bill(usage, hk_brackets)
        assert result["total_bill"] == pytest.approx(expected_bill, abs=1e-9)
        assert result["current_tier"] == expected_tier
        assert result["total_m3"] == pytest.approx(usage)

    def test_tier_transition_distances(self, hk_brackets: List[Dict[str, Any]]) -> None:
        """检查距离下一档涨价临界点的剩余立方米数。"""
        assert calculate_tiered_bill(10.0, hk_brackets)["m3_to_next_tier"] == pytest.approx(2.0)
        assert calculate_tiered_bill(12.0, hk_brackets)["m3_to_next_tier"] == pytest.approx(0.0)
        assert calculate_tiered_bill(12.1, hk_brackets)["m3_to_next_tier"] == pytest.approx(30.9)
        last = calculate_tiered_bill(62.5, hk_brackets)
        assert last["next_tier_threshold_m3"] is None
        assert last["m3_to_next_tier"] is None

    def test_marginal_rate_at_each_tier(self, hk_brackets: List[Dict[str, Any]]) -> None:
        rates = {
            5.0: 0.0,
            20.0: 4.16,
            50.0: 6.45,
            70.0: 9.05,
        }
        for usage, rate in rates.items():
            assert calculate_tiered_bill(usage, hk_brackets)["marginal_rate"] == pytest.approx(rate)

    def test_bill_is_monotonic(self, hk_brackets: List[Dict[str, Any]]) -> None:
        bills = [calculate_tiered_bill(v, hk_brackets)["total_bill"] for v in range(0, 81)]
        assert all(later >= earlier for earlier, later in zip(bills, bills[1:]))

    def test_breakdown_sums_to_total(self, hk_brackets: List[Dict[str, Any]]) -> None:
        result = calculate_tiered_bill(70.0, hk_brackets)
        assert sum(item["charge"] for item in result["breakdown"]) == pytest.approx(
            result["total_bill"]
        )
        assert sum(item["billable_m3"] for item in result["breakdown"]) == pytest.approx(70.0)


# ---------------------------------------------------------------------------
# 2. 用水拆解
# ---------------------------------------------------------------------------


class TestUsageBreakdown:
    """验证分类用水定额、占比与费水刺客识别。"""

    def test_totals_and_shares(self, family_usage: Dict[str, Any]) -> None:
        result = analyze_usage_breakdown(family_usage)
        categories = result["categories"]

        assert set(categories) == {
            "shower", "laundry", "dishwashing", "toilet", "drinking_cooking"
        }
        assert result["cycle_days"] == 120
        assert result["total_m3"] == pytest.approx(result["total_liters"] / 1000.0)
        assert sum(item["cycle_liters"] for item in categories.values()) == pytest.approx(
            result["total_liters"]
        )
        assert sum(item["share_pct"] for item in categories.values()) == pytest.approx(100.0)

    def test_shower_is_top_consumer(self) -> None:
        result = analyze_usage_breakdown(
            {
                "people": 1,
                "shower_minutes_per_day": 20.0,
                "laundry_loads_per_week": 0.0,
                "dishwashing_habit": "basin_soak",
                "drinking_cooking_liters_per_person_per_day": 0.0,
            }
        )
        assert result["top_consumer"] == "shower"
        assert result["top_consumer_share_pct"] == pytest.approx(180.0 / 214.0 * 100.0)

    def test_shower_scales_with_people(self) -> None:
        one = analyze_usage_breakdown(
            {
                "people": 1,
                "shower_minutes_per_day": 10.0,
                "laundry_loads_per_week": 0.0,
                "dishwashing_habit": "basin_soak",
                "drinking_cooking_liters_per_person_per_day": 0.0,
                "toilet_flushes_per_person_per_day": 0.0,
            }
        )
        two = analyze_usage_breakdown(
            {
                "people": 2,
                "shower_minutes_per_day": 10.0,
                "laundry_loads_per_week": 0.0,
                "dishwashing_habit": "basin_soak",
                "drinking_cooking_liters_per_person_per_day": 0.0,
                "toilet_flushes_per_person_per_day": 0.0,
            }
        )
        assert two["categories"]["shower"]["daily_liters"] == pytest.approx(
            2 * one["categories"]["shower"]["daily_liters"]
        )

    def test_laundry_rate_is_applied(self) -> None:
        baseline = analyze_usage_breakdown(
            {
                "people": 1,
                "shower_minutes_per_day": 0.0,
                "laundry_loads_per_week": 0.0,
                "dishwashing_habit": "basin_soak",
                "drinking_cooking_liters_per_person_per_day": 0.0,
            }
        )
        extra = analyze_usage_breakdown(
            {
                "people": 1,
                "shower_minutes_per_day": 0.0,
                "laundry_loads_per_week": 7.0,
                "dishwashing_habit": "basin_soak",
                "drinking_cooking_liters_per_person_per_day": 0.0,
            }
        )
        laundry_extra = extra["categories"]["laundry"]["cycle_liters"]
        laundry_base = baseline["categories"]["laundry"]["cycle_liters"]
        added = laundry_extra - laundry_base
        assert added == pytest.approx(7.0 * 60.0 / 7.0 * 120.0)


# ---------------------------------------------------------------------------
# 3. 干旱检测
# ---------------------------------------------------------------------------


class TestDroughtStatus:
    """验证多雨/少雨月份的预警与配额收紧。"""

    def test_wet_month_has_no_alert(self) -> None:
        status = check_drought_status("hong_kong", 8)
        assert status["is_drought"] is False
        assert status["alert_level"] == "normal"
        assert status["quota_reduction_pct"] == pytest.approx(0.0)
        assert status["safe_daily_quota_l_per_person"] == pytest.approx(140.0)

    def test_dry_month_triggers_warning(self) -> None:
        status = check_drought_status("hong_kong", 11)  # 40 mm < 60 mm
        assert status["is_drought"] is True
        assert status["alert_level"] == "warning"
        assert status["quota_reduction_pct"] == pytest.approx(20.0)
        assert status["safe_daily_quota_l_per_person"] == pytest.approx(112.0)

    def test_critical_month_tightens_quota(self) -> None:
        status = check_drought_status("hong_kong", 1)  # 25 mm < 30 mm
        assert status["is_drought"] is True
        assert status["alert_level"] == "critical"
        assert status["quota_reduction_pct"] == pytest.approx(35.0)
        assert status["safe_daily_quota_l_per_person"] == pytest.approx(91.0)
        assert "预警" in status["message_zh"]

    def test_beijing_seasonality(self) -> None:
        assert check_drought_status("beijing", 1)["alert_level"] == "critical"
        assert check_drought_status("beijing", 7)["alert_level"] == "normal"

    @pytest.mark.parametrize("alias", ["香港", "hong kong", "HK", "hong_kong"])
    def test_city_aliases_resolve(self, alias: str) -> None:
        assert check_drought_status(alias, 1)["city"] == "hong_kong"

    def test_drought_message_has_both_languages(self) -> None:
        status = check_drought_status("hong_kong", 1)
        assert "预警" in status["message_zh"]
        assert "warning" in status["message_en"].lower()

    def test_top_consumer_has_both_language_labels(self, family_usage: Dict[str, Any]) -> None:
        result = analyze_usage_breakdown(family_usage)
        assert result["top_consumer_label_zh"]
        assert result["top_consumer_label_en"]

    def test_quota_is_monotonic_across_alert_levels(self) -> None:
        critical = check_drought_status("hong_kong", 1)
        warning = check_drought_status("hong_kong", 11)
        normal = check_drought_status("hong_kong", 8)
        assert critical["safe_daily_quota_l_per_person"] < warning["safe_daily_quota_l_per_person"]
        assert warning["safe_daily_quota_l_per_person"] < normal["safe_daily_quota_l_per_person"]


# ---------------------------------------------------------------------------
# 4. 节水组合优化
# ---------------------------------------------------------------------------


def _brute_force_min_penalty(
    usage: float, target: float, drought: bool, brackets: List[Dict[str, Any]]
) -> int:
    """独立实现穷举，用于交叉验证优化器确实取到最小折损。"""
    config = load_config()
    days = config["meta"]["billing_cycle_days"]
    measures = config["conservation_measures"]
    effective = target
    current_bill = calculate_tiered_bill(usage, brackets)["total_bill"]

    feasible_penalties = []
    for size in range(len(measures) + 1):
        for indices in itertools.combinations(range(len(measures)), size):
            saved_lpd = sum(measures[i]["water_saved_liters_per_day"] for i in indices)
            projected = max(0.0, usage - saved_lpd * days / 1000.0)
            savings = current_bill - calculate_tiered_bill(projected, brackets)["total_bill"]
            if savings + 1e-9 >= effective:
                feasible_penalties.append(
                    sum(measures[i]["comfort_penalty_score"] for i in indices)
                )
    return min(feasible_penalties) if feasible_penalties else -1


class TestConservationPlan:
    """验证省钱目标、舒适度最优性与不可达目标的降级处理。"""

    def test_plan_meets_target(
        self, family_usage: Dict[str, Any], hk_brackets: List[Dict[str, Any]]
    ) -> None:
        usage = analyze_usage_breakdown(family_usage)["total_m3"]
        plan = generate_conservation_plan(usage, 30.0, False)
        assert plan["target_achievable"] is True
        assert plan["projected_savings"] >= 30.0
        assert plan["projected_bill"] == pytest.approx(
            plan["current_bill"] - plan["projected_savings"]
        )
        assert plan["projected_usage_m3"] <= usage

    def test_plan_minimises_comfort_penalty(
        self, family_usage: Dict[str, Any], hk_brackets: List[Dict[str, Any]]
    ) -> None:
        usage = analyze_usage_breakdown(family_usage)["total_m3"]
        target = 35.0
        plan = generate_conservation_plan(usage, target, False)
        expected = _brute_force_min_penalty(usage, target, False, hk_brackets)
        assert expected >= 0
        assert plan["total_comfort_penalty"] == expected

    def test_measures_sorted_by_penalty(self, family_usage: Dict[str, Any]) -> None:
        usage = analyze_usage_breakdown(family_usage)["total_m3"]
        plan = generate_conservation_plan(usage, 25.0, False)
        scores = [item["comfort_penalty_score"] for item in plan["selected_measures"]]
        assert scores == sorted(scores)

    def test_savings_attribution_sums_exactly(self, family_usage: Dict[str, Any]) -> None:
        usage = analyze_usage_breakdown(family_usage)["total_m3"]
        plan = generate_conservation_plan(usage, 20.0, False)
        total = sum(item["savings"] for item in plan["selected_measures"])
        assert total == pytest.approx(plan["projected_savings"], abs=1e-9)

    def test_drought_mode_adds_safety_margin(self, family_usage: Dict[str, Any]) -> None:
        usage = analyze_usage_breakdown(family_usage)["total_m3"]
        plan = generate_conservation_plan(usage, 20.0, True)
        assert plan["drought_mode"] is True
        assert plan["effective_target"] == pytest.approx(22.0)
        assert plan["projected_savings"] >= plan["effective_target"]

    def test_unachievable_target_is_flagged(self, family_usage: Dict[str, Any]) -> None:
        usage = analyze_usage_breakdown(family_usage)["total_m3"]
        plan = generate_conservation_plan(usage, 100_000.0, False)
        assert plan["target_achievable"] is False
        assert plan["shortfall"] > 0.0
        assert len(plan["selected_measures"]) == len(load_config()["conservation_measures"])

    def test_plan_respects_category_usage(self) -> None:
        usage = analyze_usage_breakdown(
            {
                "people": 1,
                "shower_minutes_per_day": 0.0,
                "laundry_loads_per_week": 0.0,
                "dishwashing_habit": "basin_soak",
                "drinking_cooking_liters_per_person_per_day": 0.0,
                "toilet_flushes_per_person_per_day": 0.0,
            }
        )
        categories = {
            key: item["daily_liters"]
            for key, item in usage["categories"].items()
        }
        plan = generate_conservation_plan(
            usage["total_m3"],
            1_000.0,
            False,
            "hong_kong",
            usage_categories=categories,
        )
        assert plan["water_saved_liters_per_day"] <= usage["daily_total_liters"]
        shower_measures = [
            measure for measure in plan["selected_measures"]
            if measure.get("category") == "shower"
        ]
        assert all(measure["water_saved_liters_per_day"] == 0 for measure in shower_measures)

    def test_zero_usage_plan(self) -> None:
        plan = generate_conservation_plan(0.0, 10.0, False)
        assert plan["target_achievable"] is False
        assert plan["projected_savings"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# 5. 异常与边界值
# ---------------------------------------------------------------------------


class TestValidation:
    """验证所有非法输入都抛出清晰的异常而非崩溃。"""

    def test_negative_shower_minutes_raises(self) -> None:
        with pytest.raises(ValueError, match="shower_minutes_per_day"):
            analyze_usage_breakdown({"people": 2, "shower_minutes_per_day": -1.0})

    def test_zero_people_raises(self) -> None:
        with pytest.raises(ValueError, match="people"):
            analyze_usage_breakdown({"people": 0})

    def test_bool_people_raises(self) -> None:
        with pytest.raises(TypeError, match="people"):
            analyze_usage_breakdown({"people": True})

    def test_unknown_city_raises(self) -> None:
        with pytest.raises(ValueError, match="未知城市"):
            check_drought_status("Paris", 5)

    def test_month_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="month"):
            check_drought_status("hong_kong", 13)
        with pytest.raises(ValueError, match="month"):
            check_drought_status("hong_kong", 0)

    def test_unknown_dishwashing_habit_raises(self) -> None:
        with pytest.raises(ValueError, match="洗碗习惯"):
            analyze_usage_breakdown({"people": 2, "dishwashing_habit": "magic"})

    def test_negative_usage_raises(self, hk_brackets: List[Dict[str, Any]]) -> None:
        with pytest.raises(ValueError, match="total_m3"):
            calculate_tiered_bill(-1.0, hk_brackets)

    def test_empty_brackets_raises(self) -> None:
        with pytest.raises(ValueError, match="阶梯水价表"):
            calculate_tiered_bill(10.0, [])

    def test_mid_table_null_bracket_rejected(self) -> None:
        with pytest.raises(ValueError, match="只允许出现在最后一档"):
            calculate_tiered_bill(
                10.0,
                [
                    {"up_to_m3": 12.0, "rate_per_m3": 0.0},
                    {"up_to_m3": None, "rate_per_m3": 4.16},
                    {"up_to_m3": 62.0, "rate_per_m3": 6.45},
                    {"up_to_m3": None, "rate_per_m3": 9.05},
                ],
            )

    def test_non_increasing_brackets_raises(self) -> None:
        with pytest.raises(ValueError, match="递增"):
            calculate_tiered_bill(
                10.0,
                [
                    {"up_to_m3": 20.0, "rate_per_m3": 1.0},
                    {"up_to_m3": 20.0, "rate_per_m3": 2.0},
                    {"up_to_m3": None, "rate_per_m3": 3.0},
                ],
            )

    def test_negative_target_raises(self) -> None:
        with pytest.raises(ValueError, match="target_savings_hkd"):
            generate_conservation_plan(20.0, -5.0, False)

    def test_non_bool_drought_mode_raises(self) -> None:
        with pytest.raises(TypeError, match="drought_mode"):
            generate_conservation_plan(20.0, 10.0, "yes")  # type: ignore[arg-type]

    def test_unknown_tariff_raises(self) -> None:
        with pytest.raises(ValueError, match="未知阶梯水价地区"):
            generate_conservation_plan(20.0, 10.0, False, "mars")
