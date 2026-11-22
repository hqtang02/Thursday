
def generate_recommendations(comparison, dates, tasks):
    """根据模拟结果生成智能用水建议。"""

    baseline = comparison["baseline"]
    optimized = comparison["optimized"]

    recommendations = []

    def add(level, title, message, day=None):
        recommendations.append({
            "level": level,
            "title": title,
            "message": message,
            "day": day,
        })

    overflow_reduction = (
        baseline["total_overflow"]
        - optimized["total_overflow"]
    )

    shortage_reduction = (
        baseline["total_shortage"]
        - optimized["total_shortage"]
    )

    if shortage_reduction > 0.001:
        add(
            "success",
            "用水保障改善",
            f"智能方案减少了 {shortage_reduction:.1f} L "
            "的用水缺口。",
        )

    if overflow_reduction > 0.001:
        add(
            "success",
            "雨水溢流减少",
            f"智能方案减少了 {overflow_reduction:.1f} L "
            "的雨水溢流。",
        )

    if not comparison["schedule_changed"]:
        add(
            "info",
            "无需调整任务日期",
            "当前没有找到比基础方案更优的调度安排。",
        )

    for index, task in enumerate(tasks):
        old_day = baseline["schedule"][index]
        new_day = optimized["schedule"][index]

        if old_day != new_day:
            add(
                "success",
                f"调整任务：{task.name}",
                f"建议将任务从 {dates[old_day]} "
                f"调整至 {dates[new_day]}，"
                f"计划用水量为 {task.amount:.1f} L。",
                dates[new_day],
            )

    for index, record in enumerate(optimized["records"]):
        date = dates[index]

        if record["shortage"] > 0.001:
            add(
                "warning",
                f"{date} · 预计雨水不足",
                f"当天预计缺水 {record['shortage']:.1f} L，"
                "建议优先保障高优先级用途，"
                "并准备其他合规补充水源。",
                date,
            )

        if record["overflow"] > 0.001:
            add(
                "warning",
                f"{date} · 预计水箱溢流",
                f"当天预计溢流 {record['overflow']:.1f} L，"
                "建议检查排水设施并评估储水容量。",
                date,
            )

    if not recommendations:
        add(
            "info",
            "运行情况正常",
            "当前没有发现明显的缺水、"
            "溢流或需要调整的任务。",
        )

    return recommendations
