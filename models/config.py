from dataclasses import dataclass, field
from datetime import datetime

_VALID_ASPECT_CODES = {"N", "NE", "E", "SE", "S", "SW", "W", "NW"}


@dataclass
class AnalysisConfig:
    dem_layer_id: str = ""
    ghi_layer_id: str = ""
    lulc_layer_id: str = ""
    lulc_field_name: str = ""
    solar_source_mode: str = "era5_ssrd"
    target_crs_authid: str = ""
    target_resolution: float = 12.5
    slope_threshold_deg: float = 15.0
    suitability_threshold: float = 4.0
    min_area_ha: float = 10.0
    era5_buffer_deg: float = 0.10
    analysis_start_date: str = "2020-01-01"
    analysis_end_date: str = "2020-12-31"
    analysis_hour_mode: str = "all"
    analysis_hour_start: int = 0
    analysis_hour_end: int = 23
    output_temporal_resolution: str = "monthly"
    era5_dataset: str = "reanalysis-era5-single-levels"
    era5_variable: str = "surface_solar_radiation_downwards"
    era5_ghi_percentiles: str = "25,50,75"
    save_era5_netcdf: bool = True
    save_era5_geotiff: bool = True
    save_era5_csv: bool = True
    save_era5_clipped_raster: bool = True
    excluded_aspects: list = field(default_factory=lambda: ["N", "NW"])
    excluded_lulc_classes: str = "1,2,3,4,5,6,24,33"
    ghi_breaks: str = "4.5,5.0,5.5"
    slope_breaks: str = "5,10,15"
    aspect_score_table: str = "SE=5,S=5,SW=4,E=3,W=3,NE=1,NW=1"
    output_folder: str = ""
    ahp_matrix: list = field(default_factory=list)

    def analysis_start(self):
        return datetime.strptime(self.analysis_start_date, "%Y-%m-%d").date()

    def analysis_end(self):
        return datetime.strptime(self.analysis_end_date, "%Y-%m-%d").date()

    def analysis_hours(self):
        if self.analysis_hour_mode == "all":
            return list(range(24))
        if self.analysis_hour_start > self.analysis_hour_end:
            raise ValueError("La hora inicial no puede ser mayor que la hora final.")
        return list(range(self.analysis_hour_start, self.analysis_hour_end + 1))

    def uses_era5_source(self):
        return self.solar_source_mode == "era5_ssrd"

    def excluded_lulc_class_values(self):
        if not self.excluded_lulc_classes.strip():
            return []
        values = []
        for token in self.excluded_lulc_classes.split(","):
            cleaned = token.strip()
            if not cleaned:
                continue
            values.append(int(cleaned))
        return values

    def _parse_float_list(self, raw_value, label):
        values = []
        for token in raw_value.split(","):
            cleaned = token.strip()
            if not cleaned:
                continue
            values.append(float(cleaned))
        if not values:
            raise ValueError(f"{label} no puede estar vacio.")
        return values

    def ghi_break_values(self):
        values = self._parse_float_list(self.ghi_breaks, "Los cortes de GHI")
        if len(values) != 3:
            raise ValueError("Los cortes de GHI deben tener exactamente 3 valores.")
        if values != sorted(values):
            raise ValueError("Los cortes de GHI deben estar en orden ascendente.")
        return values

    def era5_ghi_percentile_values(self):
        values = self._parse_float_list(self.era5_ghi_percentiles, "Los percentiles ERA5 de GHI")
        if len(values) != 3:
            raise ValueError("Los percentiles ERA5 de GHI deben tener exactamente 3 valores.")
        if values != sorted(values):
            raise ValueError("Los percentiles ERA5 de GHI deben estar en orden ascendente.")
        for value in values:
            if value <= 0 or value >= 100:
                raise ValueError("Los percentiles ERA5 de GHI deben estar entre 0 y 100, sin incluir los extremos.")
        return values

    def slope_break_values(self):
        values = self._parse_float_list(self.slope_breaks, "Los cortes de pendiente")
        if len(values) != 3:
            raise ValueError("Los cortes de pendiente deben tener exactamente 3 valores.")
        if values != sorted(values):
            raise ValueError("Los cortes de pendiente deben estar en orden ascendente.")
        return values

    def aspect_score_table_values(self):
        table = {}
        for token in self.aspect_score_table.split(","):
            token = token.strip()
            if not token:
                continue
            if "=" not in token:
                raise ValueError(
                    f"Formato invalido en tabla de orientacion: '{token}'. Use 'DIR=puntuacion'."
                )
            key, val = token.split("=", 1)
            key = key.strip().upper()
            if key not in _VALID_ASPECT_CODES:
                raise ValueError(
                    f"Orientacion no reconocida: '{key}'. Use N, NE, E, SE, S, SW, W o NW."
                )
            try:
                table[key] = int(val.strip())
            except ValueError:
                raise ValueError(
                    f"La puntuacion para '{key}' debe ser un entero, no '{val.strip()}'."
                )
        if not table:
            raise ValueError("La tabla de puntuaciones por orientacion no puede estar vacia.")
        return table
