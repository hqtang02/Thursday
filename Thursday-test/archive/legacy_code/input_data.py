
# input_data.py
"""Read and validate rainfall CSV data."""

import csv
import math
from pathlib import Path


def load_rainfall_csv(file_path):
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Rainfall file not found: {path}"
        )

    rainfall = []

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("CSV file is empty.")

        required = {"day", "rainfall_mm"}

        if not required.issubset(reader.fieldnames):
            raise ValueError(
                "CSV must contain day and rainfall_mm columns."
            )

        for row_number, row in enumerate(reader, start=2):
            try:
                day = int(row["day"])
                rain = float(row["rainfall_mm"])
            except (ValueError, TypeError):
                raise ValueError(
                    f"Invalid data at CSV row {row_number}."
                ) from None

            if day != len(rainfall) + 1:
                raise ValueError(
                    f"Invalid day sequence at row {row_number}."
                )

            if not math.isfinite(rain) or rain < 0:
                raise ValueError(
                    f"Invalid rainfall at row {row_number}."
                )

            rainfall.append(rain)

    if not rainfall:
        raise ValueError("CSV contains no rainfall records.")

    return rainfall
