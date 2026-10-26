import unittest
from services.gps_service import validate_coordinates, haversine_meters

class GPSTests(unittest.TestCase):
    def test_valid_coordinates(self):
        loc, error = validate_coordinates({"latitude":10.0,"longitude":123.0,"accuracy":10},100)
        self.assertIsNone(error)
        self.assertEqual(loc["latitude"],10.0)
    def test_reject_poor_accuracy(self):
        loc, error = validate_coordinates({"latitude":10,"longitude":123,"accuracy":500},100)
        self.assertIsNone(loc)
        self.assertIn("accuracy", error.lower())
    def test_invalid_latitude(self):
        loc, error = validate_coordinates({"latitude":100,"longitude":123,"accuracy":10},100)
        self.assertIsNone(loc)
        self.assertIsNotNone(error)
    def test_haversine_same_point(self):
        self.assertAlmostEqual(haversine_meters(10,123,10,123),0,places=3)
