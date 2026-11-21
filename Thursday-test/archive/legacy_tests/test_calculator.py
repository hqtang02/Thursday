
import unittest

from calculator import simulate_day, simulate_period


class TestRainwaterCalculator(unittest.TestCase):

    def setUp(self):
        self.params = {
            "roof_area_m2": 20,
            "efficiency": 0.8,
            "tank_capacity_l": 500,
            "primary_demand_l": 50,
            "secondary_demand_l": 30,
            "reserve_l": 20,
        }

    def run_day(self, start=100, rain=10, **overrides):
        params = {**self.params, **overrides}
        return simulate_day(start, rain, **params)

    def test_rainwater_collection(self):
        result = self.run_day()
        self.assertAlmostEqual(result["collected_l"], 160)

    def test_normal_allocation(self):
        result = self.run_day()
        self.assertAlmostEqual(result["primary_used_l"], 50)
        self.assertAlmostEqual(result["secondary_used_l"], 30)
        self.assertAlmostEqual(result["end_l"], 180)

    def test_no_rain(self):
        result = self.run_day(rain=0)
        self.assertAlmostEqual(result["end_l"], 20)

    def test_overflow(self):
        result = self.run_day(start=450, rain=20)
        self.assertAlmostEqual(result["overflow_l"], 270)
        self.assertAlmostEqual(result["end_l"], 420)

    def test_empty_tank(self):
        result = self.run_day(start=0, rain=0)
        self.assertAlmostEqual(result["external_supply_l"], 50)
        self.assertAlmostEqual(result["secondary_shortage_l"], 30)
        self.assertAlmostEqual(result["end_l"], 0)

    def test_primary_priority(self):
        result = self.run_day(start=40, rain=0)
        self.assertAlmostEqual(result["primary_used_l"], 40)
        self.assertAlmostEqual(result["external_supply_l"], 10)
        self.assertAlmostEqual(result["secondary_used_l"], 0)

    def test_reserve_protection(self):
        result = self.run_day(start=70, rain=0)
        self.assertAlmostEqual(result["secondary_used_l"], 0)
        self.assertAlmostEqual(result["end_l"], 20)

    def test_partial_secondary_allocation(self):
        result = self.run_day(start=90, rain=0)
        self.assertAlmostEqual(result["secondary_used_l"], 20)
        self.assertAlmostEqual(result["secondary_shortage_l"], 10)

    def test_negative_rainfall(self):
        with self.assertRaises(ValueError):
            self.run_day(rain=-5)

    def test_invalid_efficiency(self):
        with self.assertRaises(ValueError):
            self.run_day(efficiency=1.5)

    def test_initial_storage_over_capacity(self):
        with self.assertRaises(ValueError):
            self.run_day(start=600)

    def test_reserve_over_capacity(self):
        with self.assertRaises(ValueError):
            self.run_day(reserve_l=600)

    def test_water_conservation(self):
        result = self.run_day(start=450, rain=20)

        left = result["start_l"] + result["collected_l"]

        right = (
            result["overflow_l"]
            + result["primary_used_l"]
            + result["secondary_used_l"]
            + result["end_l"]
        )

        self.assertAlmostEqual(left, right)

    def test_seven_day_simulation(self):
        rainfall = [10, 0, 5, 20, 0, 15, 0]

        results = simulate_period(
            rainfall_mm=rainfall,
            initial_storage_l=100,
            **self.params
        )

        self.assertEqual(len(results), 7)
        self.assertEqual(results[0]["day"], 1)
        self.assertEqual(results[-1]["day"], 7)

        for i in range(1, len(results)):
            self.assertAlmostEqual(
                results[i]["start_l"],
                results[i - 1]["end_l"]
            )


if __name__ == "__main__":
    unittest.main()
