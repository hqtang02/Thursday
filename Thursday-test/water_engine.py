"""SmartWater Optimizer 的纯 Python 计算引擎。

本模块不依赖 Streamlit、网络或任何第三方库，只从
``data/water_config.json`` 读取本地知识库。所有对外函数均带完整类型注解、
文档字符串，并对非法输入主动抛出 ``ValueError`` / ``TypeError``。

公开 API：
    * :func:`calculate_tiered_bill`      —— 分段累进阶梯水费
    * :func:`analyze_usage_breakdown`    —— 4 个月周期用水拆解
    * :func:`check_drought_status`       —— 干旱预警与动态配额
    * :func:`generate_conservation_plan` —— 最低舒适度折损的节水组合
"""

from __future__ import annotations

import copy
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

__all__ = [
    "load_config",
    "calculate_tiered_bill",
    "analyze_usage_breakdown",
    "check_drought_status",
    "generate_conservation_plan",
]

CONFIG_PATH: Path = Path(__file__).resolve().parent / "data" / "water_config.json"

_DROUGHT_REDUCTION: Dict[str, float] = {
    "normal": 0.0,
    "warning": 0.20,
    "critical": 0.35,
}


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------


@lru_cache(maxsize=8)
def _load_cached_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """读取并缓存 JSON 配置文件（内部函数）。"""
    path = Path(config_path) if config_path else CONFIG_PATH
    if not path.is_file():
        raise FileNotFoundError(f"找不到本地配置文件：{path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"配置文件根节点必须是对象：{path}")
    return data


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """返回本地配置的深拷贝，避免调用方意外污染缓存。

    Args:
        config_path: 可选的自定义配置路径；为 ``None`` 时使用内置文件。

    Returns:
        配置字典的独立副本。

    Raises:
        FileNotFoundError: 配置文件不存在。
        ValueError: 配置文件格式非法。
    """
    return copy.deepcopy(_load_cached_config(config_path))


def _validate_number(
    name: str,
    value: Any,
    *,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
    allow_zero: bool = True,
) -> float:
    """校验数值参数，返回标准化后的 ``float``。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} 必须是数字，收到 {type(value).__name__}。")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} 必须是有限数值。")
    if not allow_zero and number == 0.0:
        raise ValueError(f"{name} 不能为 0。")
    if minimum is not None and number < minimum:
        raise ValueError(f"{name} 不能小于 {minimum}，收到 {number}。")
    if maximum is not None and number > maximum:
        raise ValueError(f"{name} 不能大于 {maximum}，收到 {number}。")
    return number


def _validate_positive_int(name: str, value: Any, *, minimum: int = 1) -> int:
    """校验正整数参数（拒绝 bool 与 0）。"""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} 必须是整数，收到 {type(value).__name__}。")
    if value < minimum:
        raise ValueError(f"{name} 不能小于 {minimum}，收到 {value}。")
    return value


def _normalise_brackets(
    tariff_brackets: Sequence[Mapping[str, Any]],
) -> List[Tuple[Optional[float], float]]:
    """校验阶梯定义，返回 ``(累计上限, 单价)`` 的有序列表。"""
    if not isinstance(tariff_brackets, Sequence) or not tariff_brackets:
        raise ValueError("阶梯水价表不能为空。")

    normalised: List[Tuple[Optional[float], float]] = []
    previous_upper: Optional[float] = None

    for index, bracket in enumerate(tariff_brackets, start=1):
        if not isinstance(bracket, Mapping):
            raise TypeError(f"第 {index} 档必须是映射类型。")
        if "up_to_m3" not in bracket or "rate_per_m3" not in bracket:
            raise ValueError(f"第 {index} 档缺少 up_to_m3 或 rate_per_m3 字段。")

        upper_raw = bracket["up_to_m3"]
        if upper_raw is None:
            upper: Optional[float] = None
        else:
            upper = _validate_number(
                f"第 {index} 档累计上限", upper_raw, minimum=0.0
            )
            if previous_upper is not None and upper <= previous_upper:
                raise ValueError(f"第 {index} 档累计上限必须严格递增。")

        rate = _validate_number(
            f"第 {index} 档单价", bracket["rate_per_m3"], minimum=0.0
        )
        normalised.append((upper, rate))
        previous_upper = upper

    if normalised[-1][0] is not None:
        raise ValueError("最后一档的 up_to_m3 必须为 null（表示无上限）。")
    return normalised


# ---------------------------------------------------------------------------
# 1. 阶梯水费
# ---------------------------------------------------------------------------


def calculate_tiered_bill(
    total_m3: float,
    tariff_brackets: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """精确计算分段累进阶梯水费。

    采用逐档累进方式：每一档只对落在该档区间内的用水量计价。最后一档
    ``up_to_m3`` 为 ``None``，代表无上限。

    Args:
        total_m3: 账单周期内的总用水量，单位立方米。
        tariff_brackets: 阶梯定义序列，每项含 ``up_to_m3``（累计上限，
            最后一档为 ``None``）与 ``rate_per_m3``（每立方米单价）。

    Returns:
        字典，含以下键：
        ``total_m3``、``total_bill``（未舍入的精确金额）、
        ``current_tier``（1 起算）、``next_tier_threshold_m3``、
        ``m3_to_next_tier``、``marginal_rate`` 以及逐档 ``breakdown``。

    Raises:
        TypeError: 参数类型错误。
        ValueError: 用水量为负，或阶梯表结构非法。

    Examples:
        >>> brackets = [{"up_to_m3": 12.0, "rate_per_m3": 0.0},
        ...             {"up_to_m3": None, "rate_per_m3": 4.16}]
        >>> calculate_tiered_bill(14.0, brackets)["total_bill"]
        8.32
    """
    usage = _validate_number("total_m3", total_m3, minimum=0.0)
    brackets = _normalise_brackets(tariff_brackets)

    remaining = usage
    lower = 0.0
    total_bill = 0.0
    breakdown: List[Dict[str, Any]] = []
    current_tier = len(brackets)
    next_threshold: Optional[float] = None
    marginal_rate = brackets[-1][1]

    for tier, (upper, rate) in enumerate(brackets, start=1):
        width = math.inf if upper is None else upper - lower
        billable = min(remaining, width)
        charge = billable * rate
        total_bill += charge
        remaining -= billable

        breakdown.append(
            {
                "tier": tier,
                "from_m3": lower,
                "to_m3": upper,
                "rate_per_m3": rate,
                "billable_m3": billable,
                "charge": charge,
            }
        )

        if upper is None or usage <= upper:
            current_tier = tier
            next_threshold = upper
            marginal_rate = rate
            break
        lower = upper

    m3_to_next = (
        None
        if next_threshold is None
        else max(0.0, next_threshold - usage)
    )

    return {
        "total_m3": usage,
        "total_bill": total_bill,
        "current_tier": current_tier,
        "next_tier_threshold_m3": next_threshold,
        "m3_to_next_tier": m3_to_next,
        "marginal_rate": marginal_rate,
        "breakdown": breakdown,
    }


# ---------------------------------------------------------------------------
# 2. 用水拆解
# ---------------------------------------------------------------------------


def _normalise_usage_params(
    usage_params: Mapping[str, Any],
    rates: Mapping[str, Any],
) -> Dict[str, Any]:
    """校验并补齐用水参数默认值。"""
    if not isinstance(usage_params, Mapping):
        raise TypeError("usage_params 必须是映射类型。")

    people = _validate_positive_int(
        "people", usage_params.get("people", 1), minimum=1
    )
    cycle_days = _validate_positive_int(
        "cycle_days",
        usage_params.get("cycle_days", rates["cycle_days"]),
        minimum=1,
    )

    shower_minutes = _validate_number(
        "shower_minutes_per_day",
        usage_params.get("shower_minutes_per_day", 0.0),
        minimum=0.0,
    )
    laundry_loads = _validate_number(
        "laundry_loads_per_week",
        usage_params.get("laundry_loads_per_week", 0.0),
        minimum=0.0,
    )
    toilet_flushes = _validate_number(
        "toilet_flushes_per_person_per_day",
        usage_params.get(
            "toilet_flushes_per_person_per_day",
            rates["toilet"]["flushes_per_person_per_day"],
        ),
        minimum=0.0,
    )
    cooking_liters = _validate_number(
        "drinking_cooking_liters_per_person_per_day",
        usage_params.get(
            "drinking_cooking_liters_per_person_per_day",
            rates["drinking_cooking"]["liters_per_person_per_day"],
        ),
        minimum=0.0,
    )

    habit = usage_params.get("dishwashing_habit", "basin_soak")
    if not isinstance(habit, str) or habit not in rates["dishwashing"]:
        valid = ", ".join(sorted(rates["dishwashing"]))
        raise ValueError(f"未知洗碗习惯：{habit}。可选值：{valid}")

    return {
        "people": people,
        "cycle_days": cycle_days,
        "shower_minutes_per_day": shower_minutes,
        "laundry_loads_per_week": laundry_loads,
        "dishwashing_habit": habit,
        "toilet_flushes_per_person_per_day": toilet_flushes,
        "drinking_cooking_liters_per_person_per_day": cooking_liters,
    }


def analyze_usage_breakdown(usage_params: Mapping[str, Any]) -> Dict[str, Any]:
    """计算 4 个月账单周期的用水量、分类占比与头号费水项。

    分类为淋浴、洗衣、洗碗、冲厕、饮用烹饪。耗水定额全部来自本地配置。

    Args:
        usage_params: 含 ``people``（正整数）、``shower_minutes_per_day``、
            ``laundry_loads_per_week``、``dishwashing_habit`` 等键的映射；
            缺失的可选键使用配置中的默认值。

    Returns:
        字典，含 ``total_liters``、``total_m3``、``categories``、``top_consumer``
        与 ``top_consumer_share_pct`` 等键。

    Raises:
        TypeError: 参数类型错误。
        ValueError: 人数为 0/负数、时间为负数或洗碗习惯未知。

    Examples:
        >>> result = analyze_usage_breakdown({
        ...     "people": 1,
        ...     "shower_minutes_per_day": 10.0,
        ...     "laundry_loads_per_week": 0.0,
        ...     "dishwashing_habit": "basin_soak",
        ... })
        >>> result["top_consumer"]
        'shower'
    """
    config = load_config()
    rates = config["usage_rates"]
    params = _normalise_usage_params(usage_params, rates)
    days = params["cycle_days"]
    people = params["people"]

    shower_lpd = (
        people
        * params["shower_minutes_per_day"]
        * rates["shower"]["liters_per_minute"]
    )
    laundry_lpd = (
        params["laundry_loads_per_week"]
        * rates["laundry"]["liters_per_load"]
        / 7.0
    )
    habit_rates = rates["dishwashing"][params["dishwashing_habit"]]
    dishwashing_lpd = (
        habit_rates["liters_per_session"] * habit_rates["sessions_per_day"]
    )
    toilet_lpd = (
        people
        * params["toilet_flushes_per_person_per_day"]
        * rates["toilet"]["liters_per_flush"]
    )
    cooking_lpd = (
        people * params["drinking_cooking_liters_per_person_per_day"]
    )

    definitions = [
        ("shower", rates["shower"], shower_lpd),
        ("laundry", rates["laundry"], laundry_lpd),
        (
            "dishwashing",
            habit_rates,
            dishwashing_lpd,
        ),
        ("toilet", rates["toilet"], toilet_lpd),
        ("drinking_cooking", rates["drinking_cooking"], cooking_lpd),
    ]

    daily_total = sum(item[2] for item in definitions)
    total_liters = daily_total * days
    categories: Dict[str, Dict[str, Any]] = {}
    for key, meta, daily_liters in definitions:
        cycle_liters = daily_liters * days
        categories[key] = {
            "label_zh": meta["label_zh"],
            "label_en": meta["label_en"],
            "daily_liters": daily_liters,
            "cycle_liters": cycle_liters,
            "cycle_m3": cycle_liters / 1000.0,
            "share_pct": (
                cycle_liters / total_liters * 100.0
                if total_liters > 0
                else 0.0
            ),
        }

    top_key = max(categories, key=lambda key: categories[key]["cycle_liters"])

    return {
        "cycle_days": days,
        "daily_total_liters": daily_total,
        "total_liters": total_liters,
        "total_m3": total_liters / 1000.0,
        "categories": categories,
        "top_consumer": top_key,
        "top_consumer_label_zh": categories[top_key]["label_zh"],
        "top_consumer_label_en": categories[top_key]["label_en"],
        "top_consumer_share_pct": categories[top_key]["share_pct"],
        "usage_params": params,
    }


# ---------------------------------------------------------------------------
# 3. 干旱检测
# ---------------------------------------------------------------------------


def _resolve_city(city: Any, cities: Mapping[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """按中文名、英文名、键名或别名解析城市。"""
    if not isinstance(city, str) or not city.strip():
        raise ValueError("city 必须是非空城市名称字符串。")

    query = city.strip().lower()
    if query in cities:
        return query, dict(cities[query])

    for key, data in cities.items():
        aliases = [key, data["name_zh"], data["name_en"]]
        aliases.extend(data.get("aliases", []))
        if query in {str(alias).lower() for alias in aliases}:
            return key, dict(data)

    valid = ", ".join(sorted(cities))
    raise ValueError(f"未知城市：{city}。可选城市键：{valid}")


def check_drought_status(city: str, month: int) -> Dict[str, Any]:
    """根据本地历史降水判断当月是否处于少雨干旱期。

    预警分三级：``normal``（无预警）、``warning``（低于月均警戒线）、
    ``critical``（低于严重干旱线）。干旱越严重，每日安全用水红线配额
    收紧幅度越大（分别为 0%、20%、35%）。

    Args:
        city: 城市键名、中文名、英文名或别名，如 ``"hong_kong"`` / ``"香港"``。
        month: 月份，1 至 12 的整数。

    Returns:
        字典，含 ``is_drought``、``alert_level``、``rainfall_mm``、
        ``quota_reduction_pct``、``safe_daily_quota_l_per_person`` 与
        ``message_zh`` 等键。配额单位为升/人/日。

    Raises:
        TypeError: 参数类型错误。
        ValueError: 月份越界或城市未知。

    Examples:
        >>> status = check_drought_status("hong_kong", 8)
        >>> status["is_drought"]
        False
    """
    month = _validate_positive_int("month", month, minimum=1)
    if month > 12:
        raise ValueError(f"month 必须在 1–12 之间，收到 {month}。")

    cities = load_config()["cities"]
    city_key, city_data = _resolve_city(city, cities)

    rainfall_series = city_data["monthly_rainfall_mm"]
    if len(rainfall_series) != 12:
        raise ValueError(f"{city_key} 的降水数据必须恰好包含 12 个月。")
    rainfall = _validate_number(
        f"{city_key} 第 {month} 月降水量",
        rainfall_series[month - 1],
        minimum=0.0,
    )
    threshold = _validate_number(
        "干旱警戒阈值", city_data["drought_threshold_mm"], minimum=0.0
    )
    critical_threshold = _validate_number(
        "严重干旱阈值", city_data["critical_threshold_mm"], minimum=0.0
    )
    base_quota = _validate_number(
        "基准每日配额",
        city_data["base_daily_quota_l_per_person"],
        minimum=0.0,
        allow_zero=False,
    )

    if rainfall < critical_threshold:
        alert_level = "critical"
    elif rainfall < threshold:
        alert_level = "warning"
    else:
        alert_level = "normal"

    reduction = _DROUGHT_REDUCTION[alert_level]
    safe_quota = base_quota * (1.0 - reduction)

    messages = {
        "normal": (
            f"{city_data['name_zh']} {month} 月历史均雨 {rainfall:.0f} mm，"
            f"高于 {threshold:.0f} mm 警戒线，供水正常。"
        ),
        "warning": (
            f"城市供水紧张预警：{city_data['name_zh']} {month} 月历史均雨仅 "
            f"{rainfall:.0f} mm，低于 {threshold:.0f} mm 警戒线，"
            f"每日安全用水配额已收紧 {reduction:.0%}。"
        ),
        "critical": (
            f"严重干旱预警：{city_data['name_zh']} {month} 月历史均雨仅 "
            f"{rainfall:.0f} mm，低于 {critical_threshold:.0f} mm 严重干旱线，"
            f"每日安全用水配额已收紧 {reduction:.0%}。"
        ),
    }

    messages_en = {
        "normal": (
            f"{city_data['name_en']} averages {rainfall:.0f} mm in month {month}, "
            f"above the {threshold:.0f} mm alert line. Supply is normal."
        ),
        "warning": (
            f"City supply warning: {city_data['name_en']} averages only "
            f"{rainfall:.0f} mm in month {month}, below the {threshold:.0f} mm "
            f"alert line. The safe daily quota has been tightened by "
            f"{reduction:.0%}."
        ),
        "critical": (
            f"Severe drought warning: {city_data['name_en']} averages only "
            f"{rainfall:.0f} mm in month {month}, below the "
            f"{critical_threshold:.0f} mm severe-drought line. The safe daily "
            f"quota has been tightened by {reduction:.0%}."
        ),
    }

    return {
        "city": city_key,
        "city_name_zh": city_data["name_zh"],
        "city_name_en": city_data["name_en"],
        "month": month,
        "rainfall_mm": rainfall,
        "drought_threshold_mm": threshold,
        "critical_threshold_mm": critical_threshold,
        "is_drought": alert_level != "normal",
        "alert_level": alert_level,
        "quota_reduction_pct": reduction * 100.0,
        "base_daily_quota_l_per_person": base_quota,
        "safe_daily_quota_l_per_person": safe_quota,
        "message_zh": messages[alert_level],
        "message_en": messages_en[alert_level],
    }


# ---------------------------------------------------------------------------
# 4. 节水组合优化
# ---------------------------------------------------------------------------


def generate_conservation_plan(
    current_usage: float,
    target_savings_hkd: float,
    drought_mode: bool,
    tariff_key: str = "hong_kong",
    usage_categories: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """挑选舒适度折损最小、且达成省钱目标的节水行动组合。

    对措施库做穷举式 0/1 背包搜索（10 条措施共 1024 种组合），逐个计算
    真实账单下降额——由于阶梯累进特性，跨档下降带来的省钱额高于按单一
    边际单价的估算。在所有满足目标的组合中，取 ``comfort_penalty_score``
    总和最小者。

    Args:
        current_usage: 当前 4 个月周期用水量，单位立方米。
        target_savings_hkd: 期望每期省下的金额，单位与所选阶梯币种的符号一致
            （默认 HKD）。
        drought_mode: 是否处于城市供水紧张预警状态。
        tariff_key: 阶梯表键名，默认 ``"hong_kong"``。
        usage_categories: 可选的各类别每日用水量（升/日）。提供后，措施
            的节水量不会超过对应类别的实际用水量，避免推荐用户根本没在
            使用的用水项目。

    Returns:
        字典，含 ``selected_measures``（按舒适度折损升序排列）、
        ``projected_savings``、``target_achievable``、``total_comfort_penalty``、
        ``projected_usage_m3`` 等键。

    Raises:
        TypeError: 参数类型错误。
        ValueError: 用水量为负、目标金额为负或阶梯键未知。

    Examples:
        >>> plan = generate_conservation_plan(30.0, 10.0, False)
        >>> plan["projected_savings"] >= 10.0
        True
    """
    usage = _validate_number("current_usage", current_usage, minimum=0.0)
    target = _validate_number(
        "target_savings_hkd", target_savings_hkd, minimum=0.0
    )
    if not isinstance(drought_mode, bool):
        raise TypeError("drought_mode 必须是 bool。")
    if not isinstance(tariff_key, str) or tariff_key not in load_config()["tariffs"]:
        raise ValueError(f"未知阶梯水价地区：{tariff_key}")

    category_limits: Optional[Dict[str, float]] = None
    total_daily_limit: Optional[float] = None
    if usage_categories is not None:
        if not isinstance(usage_categories, Mapping):
            raise TypeError("usage_categories 必须是映射类型。")
        category_limits = {
            str(category): _validate_number(
                f"usage_categories[{category}]", value, minimum=0.0
            )
            for category, value in usage_categories.items()
        }
        total_daily_limit = sum(category_limits.values())

    config = load_config()
    tariff = config["tariffs"][tariff_key]
    brackets = tariff["brackets"]
    currency = tariff["currency"]
    cycle_days = _validate_positive_int(
        "billing_cycle_days", config["meta"]["billing_cycle_days"]
    )
    measures = config["conservation_measures"]
    effective_target = target

    current_bill = calculate_tiered_bill(usage, brackets)["total_bill"]

    def evaluate(indices: Tuple[int, ...]) -> Dict[str, Any]:
        chosen: List[Dict[str, Any]] = []
        used_by_category: Dict[str, float] = {}
        for index in indices:
            measure = dict(measures[index])
            if category_limits is not None:
                category = str(measure.get("category", "general"))
                limit = category_limits.get(
                    category,
                    total_daily_limit if total_daily_limit is not None else 0.0,
                )
                already_used = used_by_category.get(category, 0.0)
                effective = min(
                    float(measure["water_saved_liters_per_day"]),
                    max(0.0, limit - already_used),
                )
                used_by_category[category] = already_used + effective
                if effective <= 1e-9:
                    continue
                measure["water_saved_liters_per_day"] = effective
            chosen.append(measure)
        saved_lpd = sum(
            measure["water_saved_liters_per_day"] for measure in chosen
        )
        if total_daily_limit is not None:
            saved_lpd = min(saved_lpd, total_daily_limit)
        saved_m3 = saved_lpd * cycle_days / 1000.0
        projected = max(0.0, usage - saved_m3)
        projected_bill = calculate_tiered_bill(projected, brackets)["total_bill"]
        return {
            "measures": chosen,
            "saved_lpd": saved_lpd,
            "saved_m3": saved_m3,
            "projected_usage": projected,
            "projected_bill": projected_bill,
            "savings": current_bill - projected_bill,
            "penalty": sum(
                measure["comfort_penalty_score"] for measure in chosen
            ),
        }

    best: Optional[Dict[str, Any]] = None
    best_rank: Optional[Tuple[float, ...]] = None
    for mask in range(1 << len(measures)):
        indices = tuple(
            index for index in range(len(measures)) if mask & (1 << index)
        )
        candidate = evaluate(indices)
        if candidate["savings"] + 1e-9 < effective_target:
            continue
        rank = (
            float(candidate["penalty"]),
            float(len(indices)),
            -candidate["savings"],
        )
        if best_rank is None or rank < best_rank:
            best, best_rank = candidate, rank

    target_achievable = best is not None
    if best is None:
        # 目标不可达：返回"全部措施"作为最大努力方案。
        best = evaluate(tuple(range(len(measures))))
        best_rank = (float(best["penalty"]), float(len(measures)), -best["savings"])

    ordered = sorted(
        (
            item
            for item in best["measures"]
            if item["water_saved_liters_per_day"] > 1e-9
        ),
        key=lambda item: (
            item["comfort_penalty_score"],
            -item["water_saved_liters_per_day"],
        ),
    )

    # 按执行顺序逐条分摊省钱额，分摊之和严格等于总省钱额。
    selected_measures: List[Dict[str, Any]] = []
    running_usage = usage
    for measure in ordered:
        before = calculate_tiered_bill(running_usage, brackets)["total_bill"]
        running_usage = max(
            0.0,
            running_usage
            - measure["water_saved_liters_per_day"] * cycle_days / 1000.0,
        )
        after = calculate_tiered_bill(running_usage, brackets)["total_bill"]
        selected_measures.append(
            {
                **measure,
                "savings": before - after,
            }
        )

    shortfall = max(0.0, effective_target - best["savings"])

    return {
        "tariff_key": tariff_key,
        "currency": currency,
        "cycle_days": cycle_days,
        "current_usage_m3": usage,
        "projected_usage_m3": best["projected_usage"],
        "current_bill": current_bill,
        "projected_bill": best["projected_bill"],
        "target_savings": target,
        "effective_target": effective_target,
        "projected_savings": best["savings"],
        "target_achievable": target_achievable,
        "shortfall": shortfall,
        "total_comfort_penalty": int(best["penalty"]),
        "water_saved_liters_per_day": best["saved_lpd"],
        "water_saved_m3_per_cycle": best["saved_m3"],
        "drought_mode": drought_mode,
        "selected_measures": selected_measures,
        "algorithm": "穷举 0/1 背包搜索，最小化舒适度折损总分",
    }
