import csv
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRectangle,
)


ERA5_DATASET_LABEL = "ERA5 hourly data on single levels from 1940 to present"
ERA5_VARIABLE_LABEL = "GHI - Global Horizontal Irradiance"
ERA5_VARIABLE_SOURCE = "surface_solar_radiation_downwards"
WGS84_AUTHID = "EPSG:4326"
ERA5_GRID_DEG = 0.25


def _import_cdsapi():
    try:
        import cdsapi
    except ImportError as exc:
        raise RuntimeError(
            "No se encontro el paquete 'cdsapi' en el Python de QGIS. "
            "Instalelo y configure ~/.cdsapirc antes de usar ERA5."
        ) from exc
    return cdsapi


def cdsapi_available():
    try:
        _import_cdsapi()
        return True
    except RuntimeError:
        return False


def _import_gdal_numpy():
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("No se encontro 'numpy' en el Python de QGIS.") from exc
    try:
        from osgeo import gdal, osr
    except ImportError as exc:
        raise RuntimeError("No se encontro GDAL Python (osgeo) en el Python de QGIS.") from exc
    return gdal, osr, np


def _normalize_download_exception(exc):
    message = str(exc)
    if "None of the data you have requested is available yet" in message:
        latest_marker = "The latest date available for this dataset is:"
        latest_text = ""
        if latest_marker in message:
            latest_text = message.split(latest_marker, 1)[1].strip().splitlines()[0].strip()
        human = (
            "ERA5 todavia no tiene publicados todos los datos para el periodo solicitado. "
            "Reduzca la fecha final del analisis a una fecha anterior."
        )
        if latest_text:
            human += f" La fecha mas reciente disponible reportada por Copernicus es: {latest_text}."
        return RuntimeError(human)
    return exc


def dem_extent_to_wgs84(layer):
    target_crs = QgsCoordinateReferenceSystem(WGS84_AUTHID)
    transform = QgsCoordinateTransform(layer.crs(), target_crs, QgsProject.instance().transformContext())
    return transform.transformBoundingBox(layer.extent())


def build_download_area(layer, buffer_deg):
    extent = dem_extent_to_wgs84(layer)
    buffered = QgsRectangle(
        extent.xMinimum() - buffer_deg,
        extent.yMinimum() - buffer_deg,
        extent.xMaximum() + buffer_deg,
        extent.yMaximum() + buffer_deg,
    )
    width = buffered.xMaximum() - buffered.xMinimum()
    height = buffered.yMaximum() - buffered.yMinimum()
    # ERA5 works on a coarse regular grid. Tiny extents can fail if they do not
    # intersect at least one grid point, so enforce a minimum span slightly
    # larger than one cell in both directions.
    min_span = ERA5_GRID_DEG * 1.2
    if width < min_span:
        expand = (min_span - width) / 2.0
        buffered.setXMinimum(buffered.xMinimum() - expand)
        buffered.setXMaximum(buffered.xMaximum() + expand)
    if height < min_span:
        expand = (min_span - height) / 2.0
        buffered.setYMinimum(buffered.yMinimum() - expand)
        buffered.setYMaximum(buffered.yMaximum() + expand)
    north = buffered.yMaximum()
    west = buffered.xMinimum()
    south = buffered.yMinimum()
    east = buffered.xMaximum()
    return [north, west, south, east]


def area_summary(area):
    north, west, south, east = area
    return {
        "north": north,
        "west": west,
        "south": south,
        "east": east,
    }


def _daily_chunks(start_date, end_date):
    chunks = []
    cursor = start_date
    while cursor <= end_date:
        chunks.append((cursor.year, cursor.month, cursor.day))
        cursor += timedelta(days=1)
    return chunks


def build_era5_request_plan(config, dem_layer):
    start_date = config.analysis_start()
    end_date = config.analysis_end()
    area = build_download_area(dem_layer, config.era5_buffer_deg)
    hours = config.analysis_hours()
    requests = []
    for year, month, day_value in _daily_chunks(start_date, end_date):
        requests.append({
            "dataset": config.era5_dataset,
            "dataset_label": ERA5_DATASET_LABEL,
            "variable_label": ERA5_VARIABLE_LABEL,
            "product_type": ["reanalysis"],
            "variable": [config.era5_variable],
            "year": [f"{year:04d}"],
            "month": [f"{month:02d}"],
            "day": [f"{day_value:02d}"],
            "time": [f"{hour:02d}:00" for hour in hours],
            "area": area,
            "data_format": "netcdf",
            "download_format": "unarchived",
            "year_value": year,
            "month_value": month,
            "day_value": day_value,
        })
    return {
        "dataset": config.era5_dataset,
        "dataset_label": ERA5_DATASET_LABEL,
        "variable_label": ERA5_VARIABLE_LABEL,
        "variable": config.era5_variable,
        "area": area,
        "start_date": config.analysis_start_date,
        "end_date": config.analysis_end_date,
        "hour_mode": config.analysis_hour_mode,
        "hours": hours,
        "output_temporal_resolution": config.output_temporal_resolution,
        "requests": requests,
    }


def write_era5_request(output_path, request_payload):
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(request_payload, handle, indent=2, ensure_ascii=True)
    return output_path


def _internal_output_path(output_folder, filename):
    return os.path.join(output_folder, f"__{filename}")


def download_era5_plan(request_plan, output_folder):
    cdsapi = _import_cdsapi()
    os.makedirs(output_folder, exist_ok=True)
    client = cdsapi.Client()
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("No se encontro el paquete 'requests' en el Python de QGIS.") from exc
    downloaded_files = []
    for item in request_plan["requests"]:
        output_path = os.path.join(
            output_folder,
            f"era5_ssrd_{item['year_value']:04d}{item['month_value']:02d}{item['day_value']:02d}.nc",
        )
        payload = {
            "product_type": item["product_type"],
            "variable": item["variable"],
            "year": item["year"],
            "month": item["month"],
            "day": item["day"],
            "time": item["time"],
            "area": item["area"],
            "data_format": item["data_format"],
            "download_format": item["download_format"],
        }
        try:
            if hasattr(client, "client") and hasattr(client.client, "submit_and_wait_on_results"):
                results = client.client.submit_and_wait_on_results(item["dataset"], payload)
                if hasattr(results, "location"):
                    response = requests.get(results.location, timeout=300, stream=True)
                    response.raise_for_status()
                    with open(output_path, "wb") as handle:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                handle.write(chunk)
                else:
                    raise RuntimeError("El cliente de ECMWF no devolvio una URL de descarga valida.")
            else:
                client.retrieve(item["dataset"], payload, output_path)
        except Exception as exc:
            raise _normalize_download_exception(exc)
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError("La descarga ERA5 finalizo sin generar un archivo NetCDF valido.")
        downloaded_files.append({
            "path": output_path,
            "year": item["year_value"],
            "month": item["month_value"],
            "day": item["day_value"],
            "days": [int(day) for day in item["day"]],
            "hours": [int(value.split(":", 1)[0]) for value in item["time"]],
        })
    return downloaded_files


def cleanup_files(paths):
    for path in paths:
        if not path:
            continue
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def _chunk_datetimes(chunk_info):
    stamps = []
    for day_value in chunk_info["days"]:
        for hour_value in chunk_info["hours"]:
            stamps.append(datetime(chunk_info["year"], chunk_info["month"], day_value, hour_value))
    return stamps


def _open_reference_grid(path):
    gdal, osr, np = _import_gdal_numpy()
    dataset = gdal.Open(path)
    if dataset is None:
        raise RuntimeError(f"No fue posible abrir el NetCDF descargado: {path}")
    return gdal, osr, np, dataset


def _era5_georeferencing(dataset, osr):
    metadata = dataset.GetMetadata()
    if dataset.RasterCount > 0:
        band_metadata = dataset.GetRasterBand(1).GetMetadata()
        metadata = {**metadata, **band_metadata}

    lon_key = metadata.get("GRIB_longitudeOfFirstGridPointInDegrees")
    lat_key = metadata.get("GRIB_latitudeOfFirstGridPointInDegrees")
    dx_key = metadata.get("GRIB_iDirectionIncrementInDegrees")
    dy_key = metadata.get("GRIB_jDirectionIncrementInDegrees")
    j_scan_key = metadata.get("GRIB_jScansPositively")

    if lon_key is not None and lat_key is not None and dx_key is not None and dy_key is not None:
        lon_first = float(lon_key)
        lat_first = float(lat_key)
        dx = abs(float(dx_key))
        dy = abs(float(dy_key))
        scans_positive = str(j_scan_key or "0") == "1"
        pixel_height = dy if scans_positive else -dy
        origin_x = lon_first - (dx / 2.0)
        origin_y = lat_first - (pixel_height / 2.0)
        spatial_ref = osr.SpatialReference()
        spatial_ref.ImportFromEPSG(4326)
        return (origin_x, dx, 0.0, origin_y, 0.0, pixel_height), spatial_ref.ExportToWkt()

    geotransform = dataset.GetGeoTransform()
    projection_wkt = dataset.GetProjection()
    if not projection_wkt:
        spatial_ref = osr.SpatialReference()
        spatial_ref.ImportFromEPSG(4326)
        projection_wkt = spatial_ref.ExportToWkt()
    return geotransform, projection_wkt


def _write_array_geotiff(output_path, array, geotransform, projection_wkt, nodata_value=-9999.0):
    gdal, _, np = _import_gdal_numpy()
    driver = gdal.GetDriverByName("GTiff")
    rows, cols = array.shape
    dataset = driver.Create(output_path, cols, rows, 1, gdal.GDT_Float32)
    if dataset is None:
        raise RuntimeError(f"No fue posible crear el GeoTIFF: {output_path}")
    band = dataset.GetRasterBand(1)
    write_array = np.where(np.isfinite(array), array, nodata_value).astype(np.float32)
    band.WriteArray(write_array)
    band.SetNoDataValue(float(nodata_value))
    dataset.SetGeoTransform(geotransform)
    dataset.SetProjection(projection_wkt)
    band.FlushCache()
    dataset.FlushCache()
    dataset = None
    return output_path


def _series_header_for_mode(mode):
    if mode == "hourly":
        return ("timestamp", "mean_w_m2")
    if mode == "daily":
        return ("date", "mean_kwh_m2_day")
    if mode == "monthly":
        return ("month", "mean_kwh_m2_month")
    if mode == "annual_mean":
        return ("year", "mean_kwh_m2_year")
    return ("month", "mean_daily_kwh_m2_day")


def _write_series_csv(output_path, mode, series_rows):
    key_label, value_label = _series_header_for_mode(mode)
    with open(output_path, "w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([key_label, value_label])
        writer.writerows(series_rows)
    return output_path


def _mean_array(arrays, np):
    if not arrays:
        raise RuntimeError("No se generaron arrays para el producto ERA5 solicitado.")
    stacked = np.stack(arrays, axis=0)
    return np.nanmean(stacked, axis=0)


def _prepare_grouped_products(daily_energy_by_date, hourly_mean_by_timestamp, temporal_mode, np):
    daily_dates = sorted(daily_energy_by_date)
    daily_arrays = [daily_energy_by_date[current_date] for current_date in daily_dates]
    suitability_array = _mean_array(daily_arrays, np)

    monthly_energy = defaultdict(list)
    annual_energy = defaultdict(list)
    monthly_mean_daily_climatology = defaultdict(list)

    for current_date in daily_dates:
        daily_array = daily_energy_by_date[current_date]
        month_key = f"{current_date.year:04d}-{current_date.month:02d}"
        annual_key = f"{current_date.year:04d}"
        monthly_energy[month_key].append(daily_array)
        annual_energy[annual_key].append(daily_array)

    monthly_total_arrays = {}
    annual_total_arrays = {}
    for month_key, arrays in monthly_energy.items():
        month_total = np.sum(np.stack(arrays, axis=0), axis=0)
        monthly_total_arrays[month_key] = month_total
        _, month_value = month_key.split("-")
        monthly_mean_daily_climatology[month_value].append(month_total / len(arrays))
    for year_key, arrays in annual_energy.items():
        annual_total_arrays[year_key] = np.sum(np.stack(arrays, axis=0), axis=0)

    if temporal_mode == "hourly":
        series_rows = [
            (timestamp.isoformat(sep=" "), f"{hourly_mean_by_timestamp[timestamp][0]:.6f}")
            for timestamp in sorted(hourly_mean_by_timestamp)
        ]
        product_array = _mean_array(
            [hourly_mean_by_timestamp[timestamp][1] for timestamp in sorted(hourly_mean_by_timestamp)], np
        )
        product_units = "W/m2"
    elif temporal_mode == "daily":
        series_rows = [(item.isoformat(), f"{float(np.nanmean(daily_energy_by_date[item])):.6f}") for item in daily_dates]
        product_array = suitability_array
        product_units = "kWh/m2/day"
    elif temporal_mode == "monthly":
        month_keys = sorted(monthly_total_arrays)
        series_rows = [(item, f"{float(np.nanmean(monthly_total_arrays[item])):.6f}") for item in month_keys]
        product_array = _mean_array([monthly_total_arrays[item] for item in month_keys], np)
        product_units = "kWh/m2/month"
    elif temporal_mode == "annual_mean":
        year_keys = sorted(annual_total_arrays)
        series_rows = [(item, f"{float(np.nanmean(annual_total_arrays[item])):.6f}") for item in year_keys]
        product_array = _mean_array([annual_total_arrays[item] for item in year_keys], np)
        product_units = "kWh/m2/year"
    else:
        month_keys = sorted(monthly_mean_daily_climatology)
        climatology_arrays = {}
        for month_key in month_keys:
            climatology_arrays[month_key] = _mean_array(monthly_mean_daily_climatology[month_key], np)
        series_rows = [(item, f"{float(np.nanmean(climatology_arrays[item])):.6f}") for item in month_keys]
        product_array = _mean_array([climatology_arrays[item] for item in month_keys], np)
        product_units = "kWh/m2/day"

    return {
        "suitability_array": suitability_array,
        "suitability_units": "kWh/m2/day",
        "product_array": product_array,
        "product_units": product_units,
        "series_rows": series_rows,
    }


def process_era5_ssrd(downloaded_files, config, output_folder):
    if not downloaded_files:
        raise RuntimeError("No se descargaron archivos ERA5 para procesar.")

    daily_ssrd_by_date = {}
    hourly_mean_by_timestamp = {}
    geotransform = None
    projection_wkt = None

    for chunk_info in downloaded_files:
        gdal, osr, np, dataset = _open_reference_grid(chunk_info["path"])
        if geotransform is None:
            geotransform, projection_wkt = _era5_georeferencing(dataset, osr)
        timestamps = _chunk_datetimes(chunk_info)
        if dataset.RasterCount != len(timestamps):
            raise RuntimeError(
                f"El archivo {os.path.basename(chunk_info['path'])} contiene {dataset.RasterCount} bandas, "
                f"pero se esperaban {len(timestamps)} segun la solicitud ERA5."
            )
        for band_index, timestamp in enumerate(timestamps, start=1):
            band = dataset.GetRasterBand(band_index)
            array = band.ReadAsArray().astype(np.float32)
            nodata_value = band.GetNoDataValue()
            if nodata_value is not None:
                array[array == nodata_value] = np.nan
            daily_ssrd_by_date.setdefault(timestamp.date(), []).append(array)
            hourly_wm2 = array / 3600.0
            hourly_mean_by_timestamp[timestamp] = (
                float(np.nanmean(hourly_wm2)),
                hourly_wm2,
            )
        dataset = None

    _, _, np = _import_gdal_numpy()
    daily_energy_by_date = {
        current_date: np.sum(np.stack(arrays, axis=0), axis=0) / 3600000.0
        for current_date, arrays in daily_ssrd_by_date.items()
    }
    grouped = _prepare_grouped_products(
        daily_energy_by_date,
        hourly_mean_by_timestamp,
        config.output_temporal_resolution,
        np,
    )

    raw_product_path = None
    raw_product_internal_path = None
    if config.save_era5_geotiff:
        raw_product_path = _write_array_geotiff(
            os.path.join(output_folder, "era5_ghi_product_wgs84.tif"),
            grouped["product_array"],
            geotransform,
            projection_wkt,
        )
        raw_product_internal_path = raw_product_path
    elif config.save_era5_clipped_raster:
        raw_product_internal_path = _write_array_geotiff(
            _internal_output_path(output_folder, "era5_ghi_product_internal.tif"),
            grouped["product_array"],
            geotransform,
            projection_wkt,
        )

    if config.save_era5_geotiff:
        suitability_path = _write_array_geotiff(
            os.path.join(output_folder, "era5_ghi_suitability_wgs84.tif"),
            grouped["suitability_array"],
            geotransform,
            projection_wkt,
        )
        suitability_internal_path = suitability_path
    else:
        suitability_internal_path = _write_array_geotiff(
            _internal_output_path(output_folder, "era5_ghi_suitability_internal.tif"),
            grouped["suitability_array"],
            geotransform,
            projection_wkt,
        )
        suitability_path = None

    series_path = None
    if config.save_era5_csv:
        series_path = _write_series_csv(
            os.path.join(output_folder, "era5_ghi_series.csv"),
            config.output_temporal_resolution,
            grouped["series_rows"],
        )

    return {
        "product_raster_path": raw_product_path,
        "product_raster_internal_path": raw_product_internal_path,
        "product_units": grouped["product_units"],
        "suitability_raster_path": suitability_path,
        "suitability_raster_internal_path": suitability_internal_path,
        "suitability_units": grouped["suitability_units"],
        "series_csv_path": series_path,
        "stats": {
            "product_mean": float(np.nanmean(grouped["product_array"])),
            "product_min": float(np.nanmin(grouped["product_array"])),
            "product_max": float(np.nanmax(grouped["product_array"])),
            "suitability_mean": float(np.nanmean(grouped["suitability_array"])),
            "suitability_min": float(np.nanmin(grouped["suitability_array"])),
            "suitability_max": float(np.nanmax(grouped["suitability_array"])),
        },
    }


def ssrd_to_hourly_ghi_wm2(ssrd_j_m2):
    return ssrd_j_m2 / 3600.0


def ssrd_to_irradiation_kwhm2(ssrd_j_m2):
    return ssrd_j_m2 / 3600000.0
