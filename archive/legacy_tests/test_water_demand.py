
import unittest

from water_demand import (
    calculate_garden_demand,
    calculate_toilet_demand,
    calculate_total_demand,
)


class TestWaterDemand(unittest.TestCase):

    def test_vegetables(self):
        self.assertEqual(
            calculate_garden_demand(20, "vegetables"),
            80.0
        )

    def test_flowers(self):
        self.assertEqual(
            calculate_garden_demand(10, "flowers"),
            30.0
        )

    def test_trees(self):
        self.assertEqual(
            calculate_garden_demand(10, "trees"),
            20.0
        )

    def test_lawn(self):
        self.assertEqual(
            calculate_garden_demand(10, "lawn"),
            50.0
        )

    def test_zero_area(self):
        self.assertEqual(
            calculate_garden_demand(0, "vegetables"),
            0.0
        )

    def test_negative_area(self):
        with self.assertRaises(ValueError):
            calculate_garden_demand(-5, "vegetables")

    def test_invalid_plant(self):
        with self.assertRaises(ValueError):
            calculate_garden_demand(10, "unknown")

    def test_invalid_area_type(self):
        with self.assertRaises(TypeError):
            calculate_garden_demand("20", "vegetables")

    def test_toilet_demand(self):
        self.assertEqual(
            calculate_toilet_demand(2),
            50.0
        )

    def test_invalid_people(self):
        with self.assertRaises(ValueError):
            calculate_toilet_demand(-1)

    def test_fractional_people(self):
        with self.assertRaises(TypeError):
            calculate_toilet_demand(2.5)

    def test_total_demand(self):
        result = calculate_total_demand(
            garden_area=20,
            plant_type="vegetables",
            lawn_area=10,
            people=2
        )

        self.assertEqual(result["garden_l"], 80.0)
        self.assertEqual(result["lawn_l"], 50.0)
        self.assertEqual(result["toilet_l"], 50.0)
        self.assertEqual(result["total_l"], 180.0)


if __name__ == "__main__":
    unittest.main()
