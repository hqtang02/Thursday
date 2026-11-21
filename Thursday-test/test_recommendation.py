
from rainwater_engine import (
    WaterTask,
    compare_strategies,
)
from recommendation_engine import generate_recommendations


dates = [
    "2026-11-21",
    "2026-11-22",
    "2026-11-23",
]

rainfall = [0, 20, 0]

tasks = [
    WaterTask(
        name="户外清洁",
        amount=100,
        priority=2,
        flexible=True,
        earliest_day=0,
        latest_day=2,
    )
]

comparison = compare_strategies(
    rainfall=rainfall,
    area=50,
    capacity=500,
    tasks=tasks,
    initial_storage=400,
)

recommendations = generate_recommendations(
    comparison,
    dates,
    tasks,
)

print("===== 智能用水建议 =====")

for item in recommendations:
    print(f"\n[{item['level']}] {item['title']}")
    print(item["message"])

assert comparison["overflow_reduction"] == 100.0
assert comparison["schedule_changed"] is True

assert any(
    item["title"] == "雨水溢流减少"
    for item in recommendations
)

assert any(
    item["title"] == "调整任务：户外清洁"
    for item in recommendations
)

print("\nAll recommendation tests passed!")
