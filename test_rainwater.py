
from rainwater_engine import (
    WaterTask,
    compare_strategies,
)

rainfall = [0, 0, 20, 0, 30, 0, 0]

tasks = [
    WaterTask(
        "冲厕",
        amount=60,
        priority=1,
        earliest_day=0,
        latest_day=0,
    ),
    WaterTask(
        "户外清洁",
        amount=100,
        priority=2,
        flexible=True,
        earliest_day=0,
        latest_day=3,
    ),
]

result = compare_strategies(
    rainfall=rainfall,
    area=50,
    capacity=500,
    tasks=tasks,
    initial_storage=400,
)

print("基础方案：")
print(result["baseline"])

print("\n智能方案：")
print(result["optimized"])

print("\n溢流减少量：")
print("溢流减少量：", result["overflow_reduction"], "L")

print("\n===== 第二组：有效调度测试 =====")

tasks2 = [
    WaterTask(
        "户外清洁",
        amount=100,
        priority=2,
        flexible=True,
        earliest_day=0,
        latest_day=2,
    )
]

result2 = compare_strategies(
    rainfall=[0, 20, 0],
    area=50,
    capacity=500,
    tasks=tasks2,
    initial_storage=400,
)

print("基础溢流:",
      result2["baseline"]["total_overflow"])

print("智能溢流:",
      result2["optimized"]["total_overflow"])

print("减少溢流:",
      result2["overflow_reduction"])

print("是否调整日期:",
      result2["schedule_changed"])

print("优化执行日期:",
      result2["optimized"]["schedule"])
