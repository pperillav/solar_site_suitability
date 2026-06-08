import html
import csv


def write_summary_report(output_path, config, ahp_result, stats, output_paths):
    rows = [
        ("Fuente solar", "ERA5 SSRD" if config.uses_era5_source() else "GHI manual"),
        ("Resolucion temporal solar", config.output_temporal_resolution),
        ("Guardar NetCDF ERA5", "Si" if config.save_era5_netcdf else "No"),
        ("Guardar GeoTIFF ERA5", "Si" if config.save_era5_geotiff else "No"),
        ("Guardar CSV ERA5", "Si" if config.save_era5_csv else "No"),
        ("Guardar raster recortado", "Si" if config.save_era5_clipped_raster else "No"),
        ("CRS objetivo", config.target_crs_authid),
        ("Resolucion objetivo", f"{config.target_resolution} m"),
        ("Pendiente maxima", f"{config.slope_threshold_deg} grados"),
        ("Umbral de aptitud", str(config.suitability_threshold)),
        ("Area minima", f"{config.min_area_ha} ha"),
        ("Aspectos excluidos", ", ".join(config.excluded_aspects)),
        ("Clases LULC excluidas", config.excluded_lulc_classes),
        ("CR", f"{ahp_result['cr']:.4f}"),
        ("Poligonos finales", str(stats.get("polygon_count", 0))),
        ("Area total viable", f"{stats.get('area_ha_total', 0.0):.2f} ha"),
        ("Area maxima", f"{stats.get('area_ha_max', 0.0):.2f} ha"),
        ("Area minima", f"{stats.get('area_ha_min', 0.0):.2f} ha"),
    ]
    weight_items = "".join(
        f"<li>{html.escape(label)}: {value:.4f}</li>" for label, value in ahp_result["named_weights"].items()
    )
    output_items = "".join(
        f"<li>{html.escape(name)}: {html.escape(path)}</li>" for name, path in output_paths.items()
    )
    table_rows = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>" for label, value in rows
    )
    document = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Solar Site Suitability (AHP) - Reporte</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    h1, h2 {{ color: #1f4d3a; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    th {{ background: #f4f6f8; width: 32%; }}
  </style>
</head>
<body>
  <h1>Solar Site Suitability (AHP)</h1>
  <p>Reporte resumido de una ejecucion del modelo de aptitud solar.</p>
  <h2>Parametros</h2>
  <table>{table_rows}</table>
  <h2>Pesos AHP</h2>
  <ul>{weight_items}</ul>
  <h2>Salidas</h2>
  <ul>{output_items}</ul>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as report_file:
        report_file.write(document)
    return output_path


def write_summary_csv(output_path, config, ahp_result, stats, output_paths):
    rows = [
        ("solar_source", "era5_ssrd" if config.uses_era5_source() else "manual_ghi"),
        ("solar_temporal_resolution", config.output_temporal_resolution),
        ("save_era5_netcdf", config.save_era5_netcdf),
        ("save_era5_geotiff", config.save_era5_geotiff),
        ("save_era5_csv", config.save_era5_csv),
        ("save_era5_clipped_raster", config.save_era5_clipped_raster),
        ("target_crs", config.target_crs_authid),
        ("target_resolution_m", config.target_resolution),
        ("slope_threshold_deg", config.slope_threshold_deg),
        ("suitability_threshold", config.suitability_threshold),
        ("min_area_ha", config.min_area_ha),
        ("excluded_aspects", "|".join(config.excluded_aspects)),
        ("excluded_lulc_classes", config.excluded_lulc_classes),
        ("ghi_breaks", config.ghi_breaks),
        ("slope_breaks", config.slope_breaks),
        ("aspect_score_table", config.aspect_score_table),
        ("ahp_cr", ahp_result["cr"]),
        ("weight_ghi", ahp_result["named_weights"].get("GHI", 0.0)),
        ("weight_slope", ahp_result["named_weights"].get("Pendiente", 0.0)),
        ("weight_aspect", ahp_result["named_weights"].get("Orientacion", 0.0)),
        ("polygon_count", stats.get("polygon_count", 0)),
        ("area_ha_total", stats.get("area_ha_total", 0.0)),
        ("area_ha_max", stats.get("area_ha_max", 0.0)),
        ("area_ha_min", stats.get("area_ha_min", 0.0)),
    ]
    for key, value in output_paths.items():
        rows.append((f"output_{key}", value))
    with open(output_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["key", "value"])
        writer.writerows(rows)
    return output_path
