import os
import tempfile
import unittest

from solar_site_suitability.models.config import AnalysisConfig
from solar_site_suitability.reporting.summary import write_summary_csv, write_summary_report


def _fixture():
    config = AnalysisConfig(target_crs_authid="EPSG:32618", output_folder=".")
    ahp = {"named_weights": {"GHI": 0.286, "Pendiente": 0.571, "Orientacion": 0.143}, "cr": 0.0}
    stats = {"polygon_count": 3, "area_ha_total": 120.0, "area_ha_max": 80.0, "area_ha_min": 10.0}
    paths = {"viable_sites": os.path.join(tempfile.gettempdir(), "v.gpkg")}
    return config, ahp, stats, paths


class ReportingTests(unittest.TestCase):
    def test_report_is_written(self):
        config, ahp, stats, paths = _fixture()
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "r.html")
            write_summary_report(out, config, ahp, stats, paths)
            self.assertTrue(os.path.exists(out))
            with open(out, encoding="utf-8") as stream:
                self.assertIn("Solar Site Suitability", stream.read())

    def test_csv_is_written(self):
        config, ahp, stats, paths = _fixture()
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "r.csv")
            write_summary_csv(out, config, ahp, stats, paths)
            self.assertTrue(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()
