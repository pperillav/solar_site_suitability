import unittest

from solar_site_suitability.models.config import AnalysisConfig


class ConfigTests(unittest.TestCase):
    def test_excluded_lulc_values_are_parsed(self):
        config = AnalysisConfig(excluded_lulc_classes="1, 24,33")
        self.assertEqual(config.excluded_lulc_class_values(), [1, 24, 33])

    def test_excluded_lulc_values_support_empty_tokens(self):
        config = AnalysisConfig(excluded_lulc_classes="1, , 33")
        self.assertEqual(config.excluded_lulc_class_values(), [1, 33])

    def test_invalid_lulc_value_raises(self):
        config = AnalysisConfig(excluded_lulc_classes="1,a")
        with self.assertRaises(ValueError):
            config.excluded_lulc_class_values()

    def test_ghi_breaks_are_parsed(self):
        config = AnalysisConfig(ghi_breaks="4.5,5.0,5.5")
        self.assertEqual(config.ghi_break_values(), [4.5, 5.0, 5.5])

    def test_slope_breaks_are_parsed(self):
        config = AnalysisConfig(slope_breaks="5,10,15")
        self.assertEqual(config.slope_break_values(), [5.0, 10.0, 15.0])

    def test_unsorted_breaks_raise(self):
        config = AnalysisConfig(ghi_breaks="5.5,4.5,5.0")
        with self.assertRaises(ValueError):
            config.ghi_break_values()

    def test_aspect_score_table_parsed(self):
        config = AnalysisConfig(aspect_score_table="S=5,SE=5,N=1")
        self.assertEqual(config.aspect_score_table_values(), {"S": 5, "SE": 5, "N": 1})

    def test_aspect_score_table_invalid_dir(self):
        config = AnalysisConfig(aspect_score_table="X=5")
        with self.assertRaises(ValueError):
            config.aspect_score_table_values()

    def test_analysis_period_is_parsed(self):
        config = AnalysisConfig(analysis_start_date="2020-01-01", analysis_end_date="2020-12-31")
        self.assertEqual(config.analysis_start().isoformat(), "2020-01-01")
        self.assertEqual(config.analysis_end().isoformat(), "2020-12-31")

    def test_analysis_hours_all_day(self):
        config = AnalysisConfig(analysis_hour_mode="all")
        self.assertEqual(config.analysis_hours()[0], 0)
        self.assertEqual(config.analysis_hours()[-1], 23)

    def test_analysis_hours_range(self):
        config = AnalysisConfig(analysis_hour_mode="range", analysis_hour_start=8, analysis_hour_end=17)
        self.assertEqual(config.analysis_hours(), list(range(8, 18)))

    def test_analysis_hours_invalid_range(self):
        config = AnalysisConfig(analysis_hour_mode="range", analysis_hour_start=17, analysis_hour_end=8)
        with self.assertRaises(ValueError):
            config.analysis_hours()


if __name__ == "__main__":
    unittest.main()
