
"""Rainwater collection and seven-day scheduling optimization."""

from dataclasses import dataclass
from itertools import product
from math import prod


@dataclass
class WaterTask:
    name: str
    amount: float
    priority: int = 2
    flexible: bool = False
    earliest_day: int = 0
    latest_day: int = 0


def validate(rainfall, area, capacity, tasks,
             efficiency, initial_storage, reserve):
    if not rainfall:
        raise ValueError("Rainfall data cannot be empty")

    if area <= 0 or capacity <= 0:
        raise ValueError("Area and capacity must be positive")

    if not 0 <= efficiency <= 1:
        raise ValueError("Invalid efficiency")

    if not 0 <= initial_storage <= capacity:
        raise ValueError("Invalid initial storage")

    if not 0 <= reserve <= capacity:
        raise ValueError("Invalid reserve")

    if any(r is None or r < 0 for r in rainfall):
        raise ValueError("Invalid rainfall")

    for task in tasks:
        if task.amount < 0:
            raise ValueError("Negative task demand")

        if not isinstance(task.priority, int):
            raise ValueError("Priority must be an integer")

        if not (
            0 <= task.earliest_day
            <= task.latest_day
            < len(rainfall)
        ):
            raise ValueError("Invalid task window")

        if not task.flexible and (
            task.earliest_day != task.latest_day
        ):
            raise ValueError("Fixed task has multiple dates")


def run_schedule(
    rainfall,
    area,
    capacity,
    tasks,
    schedule,
    efficiency=0.8,
    initial_storage=0,
    reserve=0,
):
    """Simulate one complete schedule."""

    validate(
        rainfall, area, capacity, tasks,
        efficiency, initial_storage, reserve
    )

    if len(schedule) != len(tasks):
        raise ValueError("Schedule length mismatch")

    for task, day in zip(tasks, schedule):
        if not task.earliest_day <= day <= task.latest_day:
            raise ValueError("Task scheduled outside window")

    storage = float(initial_storage)
    records = []
    total_shortage = 0.0
    weighted_shortage = 0.0
    completed_tasks = 0
    total_overflow = 0.0
    total_collected = 0.0
    total_allocated = 0.0

    for day, rain in enumerate(rainfall):
        opening = storage
        collected = rain * area * efficiency

        overflow = max(
            0.0, opening + collected - capacity
        )
        storage = min(capacity, opening + collected)

        available = max(0.0, storage - reserve)

        today = [
            (i, task)
            for i, task in enumerate(tasks)
            if schedule[i] == day
        ]

        today.sort(key=lambda x: (x[1].priority, x[0]))

        allocations = []
        daily_shortage = 0.0

        for task_id, task in today:
            supplied = min(available, task.amount)
            shortage = task.amount - supplied

            available -= supplied
            storage -= supplied

            daily_shortage += shortage
            weighted_shortage += (
                shortage / task.priority
                if task.priority > 0
                else shortage
            )

            if shortage <= 1e-9:
                completed_tasks += 1

            allocations.append({
                "task": task.name,
                "requested": round(task.amount, 2),
                "supplied": round(supplied, 2),
                "shortage": round(shortage, 2),
                "scheduled": (
                    task.flexible
                    and day != task.latest_day
                ),
            })

        daily_allocated = sum(
            item["supplied"] for item in allocations
        )

        total_shortage += daily_shortage
        total_overflow += overflow
        total_collected += collected
        total_allocated += daily_allocated

        records.append({
            "day": day + 1,
            "rainfall": round(rain, 2),
            "opening": round(opening, 2),
            "collected": round(collected, 2),
            "overflow": round(overflow, 2),
            "allocated": round(daily_allocated, 2),
            "shortage": round(daily_shortage, 2),
            "remaining": round(storage, 2),
            "allocations": allocations,
        })

    return {
        "records": records,
        "total_collected": round(total_collected, 2),
        "total_allocated": round(total_allocated, 2),
        "total_overflow": round(total_overflow, 2),
        "total_shortage": round(total_shortage, 2),
        "weighted_shortage": round(weighted_shortage, 4),
        "final_storage": round(storage, 2),
        "completed_tasks": completed_tasks,
        "total_tasks": len(tasks),
        "schedule": list(schedule),
    }


def baseline_schedule(tasks):
    """Execute flexible tasks on their latest allowed day."""
    return [task.latest_day for task in tasks]


def simulate(
    rainfall,
    area,
    capacity,
    tasks,
    efficiency=0.8,
    initial_storage=0,
    reserve=0,
    smart=False,
):
    """Compatibility wrapper for the original interface."""

    if smart:
        result = compare_strategies(
            rainfall, area, capacity, tasks,
            efficiency, initial_storage, reserve
        )
        return result["optimized"]

    return run_schedule(
        rainfall, area, capacity, tasks,
        baseline_schedule(tasks),
        efficiency, initial_storage, reserve
    )


def compare_strategies(
    rainfall,
    area,
    capacity,
    tasks,
    efficiency=0.8,
    initial_storage=0,
    reserve=0,
    max_combinations=50000,
):
    """Search valid task schedules over the full forecast."""

    base_schedule = baseline_schedule(tasks)

    baseline = run_schedule(
        rainfall, area, capacity, tasks,
        base_schedule,
        efficiency, initial_storage, reserve
    )

    flexible_indices = [
        i for i, task in enumerate(tasks)
        if task.flexible
    ]

    windows = [
        range(
            tasks[i].earliest_day,
            tasks[i].latest_day + 1
        )
        for i in flexible_indices
    ]

    combinations = prod(
        len(window) for window in windows
    )

    if combinations > max_combinations:
        raise ValueError(
            "Too many scheduling combinations. "
            "Reduce flexible tasks or scheduling windows."
        )

    best = baseline
    best_schedule = base_schedule[:]

    def score(result, schedule):
        # Lower is better.
        # Compare high-priority shortages first.
        priorities = sorted(set(t.priority for t in tasks))
        shortage_by_priority = {
            p: 0.0 for p in priorities
        }

        for day_index, record in enumerate(result["records"]):
            today_ids = [
                i for i, scheduled_day in enumerate(schedule)
                if scheduled_day == day_index
            ]

            for task_id, allocation in zip(
                sorted(
                    today_ids,
                    key=lambda i: (tasks[i].priority, i)
                ),
                record["allocations"],
            ):
                shortage_by_priority[
                    tasks[task_id].priority
                ] += allocation["shortage"]

        # Tie-breaking keeps the original dates.
        changes = sum(
            schedule[i] != base_schedule[i]
            for i in flexible_indices
        )

        return (
            tuple(
                round(shortage_by_priority[p], 6)
                for p in priorities
            ),
            round(result["total_shortage"], 6),
            round(result["total_overflow"], 6),
            changes,
        )

    best_score = score(baseline, base_schedule)

    for dates in product(*windows):
        candidate_schedule = base_schedule[:]

        for index, date in zip(flexible_indices, dates):
            candidate_schedule[index] = date

        if candidate_schedule == base_schedule:
            continue

        candidate = run_schedule(
            rainfall, area, capacity, tasks,
            candidate_schedule,
            efficiency, initial_storage, reserve
        )

        candidate_score = score(
            candidate, candidate_schedule
        )

        if candidate_score < best_score:
            best = candidate
            best_schedule = candidate_schedule
            best_score = candidate_score

    return {
        "baseline": baseline,
        "optimized": best,
        "overflow_reduction": round(
            baseline["total_overflow"]
            - best["total_overflow"], 2
        ),
        "allocation_difference": round(
            best["total_allocated"]
            - baseline["total_allocated"], 2
        ),
        "schedule_changed": (
            best_schedule != base_schedule
        ),
        "combinations_checked": combinations,
    }
