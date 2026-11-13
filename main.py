
# main.py
"""RainWise CLI entry point."""

from pathlib import Path

from calculator import simulate_period
from input_data import load_rainfall_csv
from water_demand import calculate_total_demand


def main():
    project_dir = Path(__file__).resolve().parent

    csv_path = project_dir / "data" / "rainfall_7days.csv"

    rainfall = load_rainfall_csv(csv_path)

    demand = calculate_total_demand(
        garden_area=20,
        plant_type="vegetables",
        lawn_area=10,
        people=2
    )

    results = simulate_period(
        rainfall_mm=rainfall,
        initial_storage_l=100,
        roof_area_m2=20,
        efficiency=0.8,
        tank_capacity_l=500,
        primary_demand_l=demand["toilet_l"],
        secondary_demand_l=(
            demand["garden_l"] + demand["lawn_l"]
        ),
        reserve_l=20
    )

    print("\nRAINWISE - 7 DAY SIMULATION")
    print("=" * 92)

    print(
        f"{'Day':<6}"
        f"{'Rain(mm)':<12}"
        f"{'Collected':<13}"
        f"{'Overflow':<12}"
        f"{'External':<12}"
        f"{'Shortage':<12}"
        f"{'End(L)':<12}"
    )

    print("-" * 92)

    for row in results:
        print(
            f"{row['day']:<6}"
            f"{row['rain_mm']:<12.1f}"
            f"{row['collected_l']:<13.1f}"
            f"{row['overflow_l']:<12.1f}"
            f"{row['external_supply_l']:<12.1f}"
            f"{row['secondary_shortage_l']:<12.1f}"
            f"{row['end_l']:<12.1f}"
        )

    print("=" * 92)

    print(
        f"Total collected: "
        f"{sum(r['collected_l'] for r in results):.1f} L"
    )

    print(
        f"Total external supply: "
        f"{sum(r['external_supply_l'] for r in results):.1f} L"
    )

    print(
        f"Total secondary shortage: "
        f"{sum(r['secondary_shortage_l'] for r in results):.1f} L"
    )

    print(
        f"Final storage: {results[-1]['end_l']:.1f} L"
    )


if __name__ == "__main__":
    main()
