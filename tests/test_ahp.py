import unittest

from solar_site_suitability.ahp.calculations import build_pairwise_matrix, calculate_ahp


class AhpCalculationTests(unittest.TestCase):
    def test_consistent_matrix_has_small_cr(self):
        matrix = build_pairwise_matrix(2, 4, 2)
        result = calculate_ahp(matrix, labels=["GHI", "Pendiente", "Orientacion"])
        self.assertLess(result["cr"], 0.1)
        self.assertAlmostEqual(sum(result["weights"]), 1.0, places=6)

    def test_pendiente_dominant_weights(self):
        # GHI vs Pendiente = 0.5, GHI vs Orientacion = 2, Pendiente vs Orientacion = 4
        matrix = build_pairwise_matrix(0.5, 2, 4)
        r = calculate_ahp(matrix, labels=["GHI", "Pendiente", "Orientacion"])
        self.assertAlmostEqual(r["named_weights"]["Pendiente"], 0.5714, places=3)
        self.assertLess(r["cr"], 0.1)

    def test_invalid_pairwise_value_raises(self):
        with self.assertRaises(ValueError):
            build_pairwise_matrix(0, 1, 1)


if __name__ == "__main__":
    unittest.main()
