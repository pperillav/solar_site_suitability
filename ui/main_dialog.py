from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QDoubleSpinBox,
    QPlainTextEdit,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qgis.PyQt.QtCore import QDate, Qt
from qgis.core import QgsMapLayer, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsWkbTypes

from ..ahp.calculations import build_pairwise_matrix, calculate_ahp
from ..core.era5 import ERA5_DATASET_LABEL, ERA5_VARIABLE_LABEL, ERA5_VARIABLE_SOURCE, area_summary, build_download_area
from ..core.workflow import run_analysis
from ..models.config import AnalysisConfig

# Presets de orientacion favorable segun hemisferio (uso mundial).
ASPECT_PRESETS = {
    "N": ("SE=5,S=5,SW=4,E=3,W=3,NE=1,NW=1", ["N", "NW"]),
    "S": ("NE=5,N=5,NW=4,E=3,W=3,SE=1,SW=1", ["S", "SW"]),
}

SUITABILITY_PRESETS = [
    ("Flexible", 3.5, "Incluye zonas aceptables y favorables."),
    ("Media (recomendado)", 4.0, "Prioriza zonas favorables y muy favorables."),
    ("Alta exigencia", 4.5, "Conserva solo zonas muy favorables."),
]


class SolarSiteSuitabilityDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.setWindowTitle("Solar Site Suitability (AHP)")
        self._build_ui()
        self._fit_to_screen()
        self.refresh_layers()

    def _fit_to_screen(self):
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            self.resize(760, 720)
            return
        available = screen.availableGeometry()
        width = max(720, min(860, available.width() - 80))
        height = max(620, min(820, available.height() - 80))
        self.resize(width, height)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        content_layout = QVBoxLayout(container)
        intro = QLabel(
            "Analisis de aptitud espacial para parques solares (MCDA-AHP). "
            "Elija si desea ingresar el GHI manualmente o prepararlo desde ERA5 SSRD, "
            "configure los parametros y ejecute el flujo."
        )
        intro.setWordWrap(True)
        content_layout.addWidget(intro)
        content_layout.addWidget(self._build_input_group())
        content_layout.addWidget(self._build_rules_group())
        content_layout.addWidget(self._build_ahp_group())
        content_layout.addWidget(self._build_summary_group())
        content_layout.addWidget(self._build_output_group())
        content_layout.addWidget(self._build_log_group())
        content_layout.addStretch()
        self._connect_summary_signals()
        self._apply_tooltips()
        self._update_model_summary()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        layout.addLayout(self._build_actions())

    def _build_input_group(self):
        group = QGroupBox("Entradas")
        form = QFormLayout(group)
        self.dem_combo = QComboBox()
        self.ghi_combo = QComboBox()
        self.lulc_combo = QComboBox()
        self.lulc_combo.currentIndexChanged.connect(self._update_lulc_field_options)
        self.source_mode_combo = QComboBox()
        self.source_mode_combo.addItem("Ingresar GHI manualmente", "manual_ghi")
        self.source_mode_combo.addItem("Calcular GHI desde ERA5 SSRD", "era5_ssrd")
        self.source_mode_combo.currentIndexChanged.connect(self._update_source_mode)
        self.era5_dataset_label = QLabel(ERA5_DATASET_LABEL)
        self.era5_dataset_label.setWordWrap(True)
        self.era5_variable_label = QLabel(
            f"{ERA5_VARIABLE_LABEL}\nFuente: ERA5 Surface solar radiation downwards"
        )
        self.era5_variable_label.setWordWrap(True)
        self.buffer_spin = QDoubleSpinBox()
        self.buffer_spin.setRange(0.0, 5.0)
        self.buffer_spin.setDecimals(2)
        self.buffer_spin.setSingleStep(0.05)
        self.buffer_spin.setValue(0.10)
        self.buffer_spin.setSuffix(" grados")
        self.calculate_area_button = QPushButton("Calcular area ERA5")
        self.calculate_area_button.clicked.connect(self._calculate_era5_area)
        self.area_label = QLabel("Norte: - | Oeste: - | Sur: - | Este: -")
        self.area_label.setWordWrap(True)
        form.addRow("DEM", self.dem_combo)
        form.addRow("Fuente solar", self.source_mode_combo)
        self.era5_dataset_row_label = QLabel("Dataset ERA5")
        form.addRow(self.era5_dataset_row_label, self.era5_dataset_label)
        self.era5_variable_row_label = QLabel("Variable solar")
        form.addRow(self.era5_variable_row_label, self.era5_variable_label)
        self.ghi_row_label = QLabel("GHI manual")
        form.addRow(self.ghi_row_label, self.ghi_combo)
        form.addRow("Uso/Cobertura", self.lulc_combo)
        self.lulc_field_label = QLabel("Campo LULC")
        self.lulc_field_combo = QComboBox()
        self.lulc_field_combo.currentIndexChanged.connect(self._update_lulc_exclusions_ui)
        form.addRow(self.lulc_field_label, self.lulc_field_combo)
        self.era5_buffer_row_label = QLabel("Buffer geografico")
        form.addRow(self.era5_buffer_row_label, self.buffer_spin)
        self.era5_area_button_row_label = QLabel("Area de descarga")
        form.addRow(self.era5_area_button_row_label, self.calculate_area_button)
        self.era5_bbox_row_label = QLabel("BBox ERA5")
        form.addRow(self.era5_bbox_row_label, self.area_label)
        return group

    def _build_rules_group(self):
        group = QGroupBox("Parametros Base")
        layout = QVBoxLayout(group)
        self.resolution_spin = QDoubleSpinBox()
        self.resolution_spin.setRange(0.1, 1000.0)
        self.resolution_spin.setValue(12.5)
        self.resolution_spin.setSuffix(" m")
        self.slope_spin = QDoubleSpinBox()
        self.slope_spin.setRange(0.1, 90.0)
        self.slope_spin.setValue(15.0)
        self.slope_spin.setSuffix(" grados")
        self.suitability_spin = QDoubleSpinBox()
        self.suitability_spin.setRange(0.1, 10.0)
        self.suitability_spin.setValue(4.0)
        self.suitability_spin.setSingleStep(0.1)
        self.min_area_spin = QDoubleSpinBox()
        self.min_area_spin.setRange(0.1, 1000000.0)
        self.min_area_spin.setValue(10.0)
        self.min_area_spin.setSuffix(" ha")
        self.hemisphere_combo = QComboBox()
        self.hemisphere_combo.addItem("Norte (favorable: Sur)", "N")
        self.hemisphere_combo.addItem("Sur (favorable: Norte)", "S")
        self.lulc_excluded_edit = QLineEdit("")
        self.lulc_excluded_edit.setPlaceholderText("Ejemplo: 1,2,3,24,33")
        self.lulc_excluded_help = QLabel(
            "Excluya clases no aptas como agua, urbano, bosques protegidos o humedales."
        )
        self.lulc_excluded_help.setWordWrap(True)
        self.lulc_excluded_list = QListWidget()
        self.lulc_excluded_list.setMaximumHeight(120)
        self.lulc_excluded_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.ghi_break_low_spin = QDoubleSpinBox()
        self.ghi_break_low_spin.setRange(-99999.0, 99999.0)
        self.ghi_break_low_spin.setDecimals(2)
        self.ghi_break_low_spin.setValue(4.5)
        self.ghi_break_mid_spin = QDoubleSpinBox()
        self.ghi_break_mid_spin.setRange(-99999.0, 99999.0)
        self.ghi_break_mid_spin.setDecimals(2)
        self.ghi_break_mid_spin.setValue(5.0)
        self.ghi_break_high_spin = QDoubleSpinBox()
        self.ghi_break_high_spin.setRange(-99999.0, 99999.0)
        self.ghi_break_high_spin.setDecimals(2)
        self.ghi_break_high_spin.setValue(5.5)
        self.era5_ghi_percentile_low_spin = QDoubleSpinBox()
        self.era5_ghi_percentile_low_spin.setRange(1.0, 99.0)
        self.era5_ghi_percentile_low_spin.setDecimals(0)
        self.era5_ghi_percentile_low_spin.setValue(25.0)
        self.era5_ghi_percentile_mid_spin = QDoubleSpinBox()
        self.era5_ghi_percentile_mid_spin.setRange(1.0, 99.0)
        self.era5_ghi_percentile_mid_spin.setDecimals(0)
        self.era5_ghi_percentile_mid_spin.setValue(50.0)
        self.era5_ghi_percentile_high_spin = QDoubleSpinBox()
        self.era5_ghi_percentile_high_spin.setRange(1.0, 99.0)
        self.era5_ghi_percentile_high_spin.setDecimals(0)
        self.era5_ghi_percentile_high_spin.setValue(75.0)
        self.era5_ghi_percentile_help = QLabel(
            "En modo ERA5, los niveles de irradiacion se calculan automaticamente sobre el GHI descargado usando estos percentiles."
        )
        self.era5_ghi_percentile_help.setWordWrap(True)
        self.slope_break_low_spin = QDoubleSpinBox()
        self.slope_break_low_spin.setRange(0.0, 90.0)
        self.slope_break_low_spin.setDecimals(1)
        self.slope_break_low_spin.setValue(5.0)
        self.slope_break_mid_spin = QDoubleSpinBox()
        self.slope_break_mid_spin.setRange(0.0, 90.0)
        self.slope_break_mid_spin.setDecimals(1)
        self.slope_break_mid_spin.setValue(10.0)
        self.slope_break_high_spin = QDoubleSpinBox()
        self.slope_break_high_spin.setRange(0.0, 90.0)
        self.slope_break_high_spin.setDecimals(1)
        self.slope_break_high_spin.setValue(15.0)
        self.suitability_preset_combo = QComboBox()
        for label, value, help_text in SUITABILITY_PRESETS:
            self.suitability_preset_combo.addItem(label, (value, help_text))
        self.suitability_preset_combo.addItem("Personalizado", None)
        self.suitability_preset_combo.currentIndexChanged.connect(self._apply_suitability_preset)
        self.suitability_spin.valueChanged.connect(self._sync_suitability_preset)
        self.suitability_help_label = QLabel()
        self.suitability_help_label.setWordWrap(True)
        self.suitability_note_label = QLabel(
            "Rango de calificacion del modelo: 0 a 5.\n"
            "1.0 a 2.0: muy permisivo, deja entrar areas con aptitud baja a media.\n"
            "2.5 a 3.5: intermedio, deja entrar areas razonables a buenas.\n"
            "4.0 a 5.0: muy restrictivo, deja entrar solo areas muy favorables."
        )
        self.suitability_note_label.setWordWrap(True)
        self.start_date_edit = QDateEdit(QDate(2020, 1, 1))
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit = QDateEdit(QDate(2020, 12, 31))
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.hour_mode_combo = QComboBox()
        self.hour_mode_combo.addItem("Todas", "all")
        self.hour_mode_combo.addItem("Rango horario especifico", "range")
        self.hour_mode_combo.currentIndexChanged.connect(self._update_hour_mode)
        self.hour_start_spin = QSpinBox()
        self.hour_start_spin.setRange(0, 23)
        self.hour_end_spin = QSpinBox()
        self.hour_end_spin.setRange(0, 23)
        self.hour_end_spin.setValue(23)
        hour_range_wrapper = QWidget()
        hour_range_layout = QHBoxLayout(hour_range_wrapper)
        hour_range_layout.setContentsMargins(0, 0, 0, 0)
        hour_range_layout.addWidget(self.hour_start_spin)
        hour_range_layout.addWidget(QLabel("a"))
        hour_range_layout.addWidget(self.hour_end_spin)
        self.temporal_resolution_combo = QComboBox()
        self.temporal_resolution_combo.addItem("Horaria", "hourly")
        self.temporal_resolution_combo.addItem("Diaria", "daily")
        self.temporal_resolution_combo.addItem("Mensual", "monthly")
        self.temporal_resolution_combo.addItem("Promedio anual", "annual_mean")
        self.temporal_resolution_combo.addItem("Promedio multianual mensual", "multiannual_monthly_mean")
        general_group = QGroupBox("General")
        general_form = QFormLayout(general_group)
        general_form.addRow("Resolucion objetivo", self.resolution_spin)
        general_form.addRow("Exigencia de seleccion", self.suitability_preset_combo)
        general_form.addRow("Ayuda umbral", self.suitability_help_label)
        general_form.addRow("Nota del umbral", self.suitability_note_label)
        general_form.addRow("Umbral de aptitud", self.suitability_spin)
        general_form.addRow("Area minima", self.min_area_spin)

        solar_group = QGroupBox("Solar")
        solar_form = QFormLayout(solar_group)
        self.era5_start_date_row_label = QLabel("Fecha inicial")
        solar_form.addRow(self.era5_start_date_row_label, self.start_date_edit)
        self.era5_end_date_row_label = QLabel("Fecha final")
        solar_form.addRow(self.era5_end_date_row_label, self.end_date_edit)
        self.era5_hours_row_label = QLabel("Horas")
        solar_form.addRow(self.era5_hours_row_label, self.hour_mode_combo)
        self.era5_hour_range_row_label = QLabel("Rango horario")
        solar_form.addRow(self.era5_hour_range_row_label, hour_range_wrapper)
        self.era5_processing_row_label = QLabel("Procesamiento solar")
        solar_form.addRow(self.era5_processing_row_label, self.temporal_resolution_combo)
        self.ghi_break_low_row_label = QLabel("Irradiacion baja/media")
        solar_form.addRow(self.ghi_break_low_row_label, self.ghi_break_low_spin)
        self.ghi_break_mid_row_label = QLabel("Irradiacion media/alta")
        solar_form.addRow(self.ghi_break_mid_row_label, self.ghi_break_mid_spin)
        self.ghi_break_high_row_label = QLabel("Irradiacion alta/muy alta")
        solar_form.addRow(self.ghi_break_high_row_label, self.ghi_break_high_spin)
        self.era5_ghi_percentile_low_row_label = QLabel("Percentil GHI bajo/medio")
        solar_form.addRow(self.era5_ghi_percentile_low_row_label, self.era5_ghi_percentile_low_spin)
        self.era5_ghi_percentile_mid_row_label = QLabel("Percentil GHI medio/alto")
        solar_form.addRow(self.era5_ghi_percentile_mid_row_label, self.era5_ghi_percentile_mid_spin)
        self.era5_ghi_percentile_high_row_label = QLabel("Percentil GHI alto/muy alto")
        solar_form.addRow(self.era5_ghi_percentile_high_row_label, self.era5_ghi_percentile_high_spin)
        self.era5_ghi_percentile_help_row_label = QLabel("Ayuda GHI ERA5")
        solar_form.addRow(self.era5_ghi_percentile_help_row_label, self.era5_ghi_percentile_help)

        terrain_group = QGroupBox("Topografia")
        terrain_form = QFormLayout(terrain_group)
        terrain_form.addRow("Pendiente maxima", self.slope_spin)
        terrain_form.addRow("Pendiente muy favorable/favorable", self.slope_break_low_spin)
        terrain_form.addRow("Pendiente favorable/aceptable", self.slope_break_mid_spin)
        terrain_form.addRow("Pendiente aceptable/limite", self.slope_break_high_spin)
        terrain_form.addRow("Hemisferio", self.hemisphere_combo)

        restrictions_group = QGroupBox("Restricciones")
        restrictions_form = QFormLayout(restrictions_group)
        self.lulc_excluded_row_label = QLabel("Clases LULC excluidas")
        restrictions_form.addRow(self.lulc_excluded_row_label, self.lulc_excluded_edit)
        self.lulc_excluded_help_row_label = QLabel("Ayuda LULC")
        restrictions_form.addRow(self.lulc_excluded_help_row_label, self.lulc_excluded_help)
        self.lulc_excluded_list_row_label = QLabel("Seleccion LULC")
        restrictions_form.addRow(self.lulc_excluded_list_row_label, self.lulc_excluded_list)

        layout.addWidget(general_group)
        layout.addWidget(solar_group)
        layout.addWidget(terrain_group)
        layout.addWidget(restrictions_group)
        self._sync_suitability_preset()
        return group

    def _build_summary_group(self):
        group = QGroupBox("Resumen del Modelo")
        layout = QVBoxLayout(group)
        self.model_summary_label = QLabel()
        self.model_summary_label.setWordWrap(True)
        layout.addWidget(self.model_summary_label)
        return group

    def _build_ahp_group(self):
        group = QGroupBox("AHP")
        layout = QVBoxLayout(group)
        help_label = QLabel(
            "Defina que criterio pesa mas usando lenguaje verbal. "
            "El plugin traduce estas decisiones a la matriz AHP y valida automaticamente la consistencia."
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        form = QFormLayout()
        self.ghi_vs_slope_combo = self._build_ahp_combo("GHI", "Pendiente", 0.5)
        self.ghi_vs_aspect_combo = self._build_ahp_combo("GHI", "Orientacion", 2.0)
        self.slope_vs_aspect_combo = self._build_ahp_combo("Pendiente", "Orientacion", 4.0)
        for widget in (self.ghi_vs_slope_combo, self.ghi_vs_aspect_combo, self.slope_vs_aspect_combo):
            widget.currentIndexChanged.connect(self._update_ahp_summary)
        form.addRow("Importancia: GHI vs Pendiente", self.ghi_vs_slope_combo)
        form.addRow("Importancia: GHI vs Orientacion", self.ghi_vs_aspect_combo)
        form.addRow("Importancia: Pendiente vs Orientacion", self.slope_vs_aspect_combo)
        layout.addLayout(form)
        self.ahp_table = QTableWidget(3, 3)
        self.ahp_table.setHorizontalHeaderLabels(["GHI", "Pendiente", "Orientacion"])
        self.ahp_table.setVerticalHeaderLabels(["GHI", "Pendiente", "Orientacion"])
        self.ahp_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.ahp_table)
        self.ahp_summary_label = QLabel()
        self.ahp_summary_label.setWordWrap(True)
        layout.addWidget(self.ahp_summary_label)
        self._update_ahp_summary()
        return group

    def _build_output_group(self):
        group = QGroupBox("Salida")
        form = QFormLayout(group)
        self.output_folder_edit = QLineEdit()
        self.output_folder_button = QPushButton("Seleccionar...")
        self.output_folder_button.clicked.connect(self._select_output_folder)
        self.save_netcdf_check = QCheckBox("Guardar NetCDF original ERA5")
        self.save_netcdf_check.setChecked(True)
        self.save_geotiff_check = QCheckBox("Guardar GeoTIFF procesado")
        self.save_geotiff_check.setChecked(True)
        self.save_csv_check = QCheckBox("Guardar CSV de serie temporal")
        self.save_csv_check.setChecked(True)
        self.save_clipped_check = QCheckBox("Guardar raster recortado al DEM")
        self.save_clipped_check.setChecked(True)
        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(self.output_folder_edit)
        wrapper_layout.addWidget(self.output_folder_button)
        form.addRow("Carpeta de salida", wrapper)
        self.era5_save_netcdf_row_label = QLabel("Salida ERA5")
        form.addRow(self.era5_save_netcdf_row_label, self.save_netcdf_check)
        self.era5_save_geotiff_row_label = QLabel("Salida raster")
        form.addRow(self.era5_save_geotiff_row_label, self.save_geotiff_check)
        self.era5_save_csv_row_label = QLabel("Salida serie")
        form.addRow(self.era5_save_csv_row_label, self.save_csv_check)
        self.era5_save_clipped_row_label = QLabel("Salida recortada")
        form.addRow(self.era5_save_clipped_row_label, self.save_clipped_check)
        return group

    def _build_log_group(self):
        group = QGroupBox("Estado")
        layout = QVBoxLayout(group)
        self.status_log = QPlainTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setPlaceholderText("Aqui aparecera el estado de la validacion y la ejecucion.")
        layout.addWidget(self.status_log)
        return group

    def _build_actions(self):
        layout = QHBoxLayout()
        layout.addStretch()
        self.refresh_button = QPushButton("Actualizar capas")
        self.refresh_button.clicked.connect(self.refresh_layers)
        layout.addWidget(self.refresh_button)
        self.run_button = QPushButton("Validar y ejecutar")
        self.run_button.setDefault(True)
        self.run_button.clicked.connect(self._run)
        layout.addWidget(self.run_button)
        self.close_button = QPushButton("Cerrar")
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button)
        return layout

    def refresh_layers(self):
        raster_layers = [
            layer for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayer.RasterLayer
        ]
        polygon_layers = [
            layer for layer in QgsProject.instance().mapLayers().values()
            if layer.type() == QgsMapLayer.VectorLayer and QgsWkbTypes.geometryType(layer.wkbType()) == QgsWkbTypes.PolygonGeometry
        ]
        self._populate_layer_combo(self.dem_combo, raster_layers)
        self._populate_layer_combo(self.ghi_combo, raster_layers)
        self._populate_layer_combo(self.lulc_combo, raster_layers + polygon_layers)
        self._update_lulc_field_options()
        self._update_source_mode()
        self._update_hour_mode()

    def _build_ahp_combo(self, left_label, right_label, default_value):
        combo = QComboBox()
        options = [
            (f"{left_label} mucho mas importante", 5.0),
            (f"{left_label} moderadamente mas importante", 3.0),
            (f"{left_label} ligeramente mas importante", 2.0),
            ("Igual importancia", 1.0),
            (f"{right_label} ligeramente mas importante", 0.5),
            (f"{right_label} moderadamente mas importante", 1.0 / 3.0),
            (f"{right_label} mucho mas importante", 0.2),
        ]
        for label, value in options:
            combo.addItem(label, value)
        index = combo.findData(default_value)
        combo.setCurrentIndex(index if index >= 0 else 3)
        return combo

    def _apply_tooltips(self):
        tooltips = {
            self.dem_combo: "Modelo digital de elevacion usado como base espacial del analisis.",
            self.source_mode_combo: "Elija entre usar un raster GHI ya preparado o calcularlo desde ERA5 SSRD.",
            self.ghi_combo: "Raster GHI cargado manualmente. Se usa solo si no selecciona ERA5.",
            self.lulc_combo: "Capa de uso/cobertura del suelo. Puede ser raster o una capa vectorial de poligonos.",
            self.lulc_field_combo: "Campo que contiene el codigo de clase LULC cuando la capa es vectorial.",
            self.buffer_spin: "Margen adicional en grados alrededor del DEM para descargar ERA5 sin perder bordes.",
            self.calculate_area_button: "Calcula la caja de descarga ERA5 a partir del DEM en EPSG:4326.",
            self.resolution_spin: "Tamano de pixel objetivo para armonizar las capas del analisis.",
            self.suitability_preset_combo: "Nivel de exigencia para aceptar celdas como aptas en el resultado final.",
            self.suitability_spin: "Valor minimo del raster de aptitud para conservar una celda como candidata.",
            self.min_area_spin: "Area minima continua para reportar poligonos viables en hectareas.",
            self.start_date_edit: "Fecha inicial del periodo ERA5.",
            self.end_date_edit: "Fecha final del periodo ERA5.",
            self.hour_mode_combo: "Permite usar todas las horas o limitar el analisis a un rango horario.",
            self.hour_start_spin: "Hora inicial del rango horario ERA5.",
            self.hour_end_spin: "Hora final del rango horario ERA5.",
            self.temporal_resolution_combo: "Producto temporal que se exporta a partir de la descarga horaria ERA5.",
            self.ghi_break_low_spin: "Limite entre irradiacion baja y media para la reclasificacion del criterio solar.",
            self.ghi_break_mid_spin: "Limite entre irradiacion media y alta para la reclasificacion del criterio solar.",
            self.ghi_break_high_spin: "Limite entre irradiacion alta y muy alta para la reclasificacion del criterio solar.",
            self.era5_ghi_percentile_low_spin: "Percentil usado para separar irradiacion baja de media cuando el GHI viene de ERA5.",
            self.era5_ghi_percentile_mid_spin: "Percentil usado para separar irradiacion media de alta cuando el GHI viene de ERA5.",
            self.era5_ghi_percentile_high_spin: "Percentil usado para separar irradiacion alta de muy alta cuando el GHI viene de ERA5.",
            self.slope_spin: "Pendiente maxima admitida antes de excluir una celda del analisis.",
            self.slope_break_low_spin: "Limite entre pendiente muy favorable y favorable.",
            self.slope_break_mid_spin: "Limite entre pendiente favorable y aceptable.",
            self.slope_break_high_spin: "Limite superior de pendiente aceptable antes de la exclusion.",
            self.hemisphere_combo: "Define la orientacion favorable de laderas segun el hemisferio.",
            self.lulc_excluded_edit: "Escriba los codigos de clases LULC que deben excluirse del resultado final.",
            self.lulc_excluded_list: "Marque las clases LULC que desea excluir cuando la capa sea vectorial.",
            self.ghi_vs_slope_combo: "Indique si GHI pesa mas que la pendiente o viceversa.",
            self.ghi_vs_aspect_combo: "Indique si GHI pesa mas que la orientacion o viceversa.",
            self.slope_vs_aspect_combo: "Indique si la pendiente pesa mas que la orientacion o viceversa.",
            self.save_netcdf_check: "Conserva o elimina los archivos NetCDF descargados desde ERA5 al finalizar.",
            self.save_geotiff_check: "Conserva los GeoTIFF procesados de ERA5 en la carpeta de salida.",
            self.save_csv_check: "Conserva la serie temporal resumida generada a partir de ERA5.",
            self.save_clipped_check: "Conserva el raster ERA5 recortado y alineado con el DEM.",
        }
        for widget, text in tooltips.items():
            widget.setToolTip(text)

    def _connect_summary_signals(self):
        widgets = [
            self.source_mode_combo,
            self.resolution_spin,
            self.suitability_preset_combo,
            self.suitability_spin,
            self.min_area_spin,
            self.slope_spin,
            self.ghi_break_low_spin,
            self.ghi_break_mid_spin,
            self.ghi_break_high_spin,
            self.era5_ghi_percentile_low_spin,
            self.era5_ghi_percentile_mid_spin,
            self.era5_ghi_percentile_high_spin,
            self.slope_break_low_spin,
            self.slope_break_mid_spin,
            self.slope_break_high_spin,
            self.hemisphere_combo,
            self.lulc_field_combo,
            self.ghi_vs_slope_combo,
            self.ghi_vs_aspect_combo,
            self.slope_vs_aspect_combo,
            self.temporal_resolution_combo,
            self.hour_mode_combo,
            self.hour_start_spin,
            self.hour_end_spin,
        ]
        for widget in widgets:
            if hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self._update_model_summary)
            elif hasattr(widget, "currentIndexChanged"):
                widget.currentIndexChanged.connect(self._update_model_summary)
        self.lulc_combo.currentIndexChanged.connect(self._update_model_summary)
        self.lulc_excluded_edit.textChanged.connect(self._update_model_summary)
        self.lulc_excluded_list.itemChanged.connect(self._update_model_summary)

    def _current_ahp_text(self, combo):
        return combo.currentText().strip()

    def _update_model_summary(self):
        if not hasattr(self, "model_summary_label"):
            return
        source_mode = self.source_mode_combo.currentData() if hasattr(self, "source_mode_combo") else "manual_ghi"
        source_text = "GHI manual cargado en QGIS" if source_mode == "manual_ghi" else "GHI calculado desde ERA5 SSRD"
        exclusions = self._selected_lulc_exclusions_text() if hasattr(self, "lulc_excluded_edit") else ""
        exclusion_text = exclusions if exclusions else "ninguna clase definida"
        hour_mode = self.hour_mode_combo.currentData() if hasattr(self, "hour_mode_combo") else "all"
        if hour_mode == "range":
            hours_text = f"entre las {self.hour_start_spin.value():02d}:00 y {self.hour_end_spin.value():02d}:00"
        else:
            hours_text = "en todas las horas del dia"
        irradiance_text = (
            f"La irradiacion se reclasificara con cortes {self.ghi_break_low_spin.value():.2f}, {self.ghi_break_mid_spin.value():.2f} y {self.ghi_break_high_spin.value():.2f}. "
            if source_mode == "manual_ghi"
            else "La irradiacion se reclasificara automaticamente a partir de percentiles del GHI ERA5 descargado. "
        )
        summary = (
            f"Fuente solar: {source_text}. "
            f"Se trabajara a {self.resolution_spin.value():.2f} m por pixel y se exigira una aptitud minima de {self.suitability_spin.value():.1f}. "
            f"Se excluiran pendientes mayores a {self.slope_spin.value():.1f} grados y poligonos menores de {self.min_area_spin.value():.1f} ha. "
            f"{irradiance_text}"
            f"La pendiente se evaluara con cortes {self.slope_break_low_spin.value():.1f}, {self.slope_break_mid_spin.value():.1f} y {self.slope_break_high_spin.value():.1f} grados. "
            f"Hemisferio seleccionado: {self.hemisphere_combo.currentText()}. "
            f"Clases LULC excluidas: {exclusion_text}. "
            f"Preferencias AHP: {self._current_ahp_text(self.ghi_vs_slope_combo)}; {self._current_ahp_text(self.ghi_vs_aspect_combo)}; {self._current_ahp_text(self.slope_vs_aspect_combo)}."
        )
        if source_mode == "era5_ssrd":
            summary += (
                f" Para ERA5 se usara salida {self.temporal_resolution_combo.currentText().lower()} y se procesara {hours_text}. "
                f"Los niveles de irradiacion se calcularan automaticamente con los percentiles {self.era5_ghi_percentile_low_spin.value():.0f}, {self.era5_ghi_percentile_mid_spin.value():.0f} y {self.era5_ghi_percentile_high_spin.value():.0f}."
            )
        if self.lulc_field_combo.isVisible() and self.lulc_field_combo.currentData():
            summary += f" La capa LULC vectorial se rasterizara usando el campo {self.lulc_field_combo.currentData()}."
        self.model_summary_label.setText(summary)

    def _apply_suitability_preset(self):
        preset = self.suitability_preset_combo.currentData()
        if preset is None:
            self.suitability_help_label.setText(
                "Defina manualmente el umbral minimo del raster final para aceptar una zona como apta."
            )
            return
        value, help_text = preset
        self.suitability_spin.blockSignals(True)
        self.suitability_spin.setValue(value)
        self.suitability_spin.blockSignals(False)
        self.suitability_help_label.setText(help_text)

    def _sync_suitability_preset(self):
        current_value = round(self.suitability_spin.value(), 2)
        matched = False
        self.suitability_preset_combo.blockSignals(True)
        for index in range(self.suitability_preset_combo.count() - 1):
            preset = self.suitability_preset_combo.itemData(index)
            if preset and round(preset[0], 2) == current_value:
                self.suitability_preset_combo.setCurrentIndex(index)
                self.suitability_help_label.setText(preset[1])
                matched = True
                break
        if not matched:
            self.suitability_preset_combo.setCurrentIndex(self.suitability_preset_combo.count() - 1)
            self.suitability_help_label.setText(
                "Valor personalizado: ajuste fino del nivel minimo de aptitud requerido."
            )
        self.suitability_preset_combo.blockSignals(False)

    def _update_source_mode(self):
        uses_era5 = (self.source_mode_combo.currentData() or "era5_ssrd") == "era5_ssrd"
        self.ghi_combo.setEnabled(not uses_era5)
        self.calculate_area_button.setEnabled(uses_era5)
        self.buffer_spin.setEnabled(uses_era5)
        self.start_date_edit.setEnabled(uses_era5)
        self.end_date_edit.setEnabled(uses_era5)
        self.hour_mode_combo.setEnabled(uses_era5)
        self.hour_start_spin.setEnabled(uses_era5 and self.hour_mode_combo.currentData() == "range")
        self.hour_end_spin.setEnabled(uses_era5 and self.hour_mode_combo.currentData() == "range")
        self.temporal_resolution_combo.setEnabled(uses_era5)
        self._set_row_visibility(self.ghi_row_label, self.ghi_combo, not uses_era5)
        for label_widget, field_widget in (
            (self.era5_dataset_row_label, self.era5_dataset_label),
            (self.era5_variable_row_label, self.era5_variable_label),
            (self.era5_buffer_row_label, self.buffer_spin),
            (self.era5_area_button_row_label, self.calculate_area_button),
            (self.era5_bbox_row_label, self.area_label),
            (self.era5_start_date_row_label, self.start_date_edit),
            (self.era5_end_date_row_label, self.end_date_edit),
            (self.era5_hours_row_label, self.hour_mode_combo),
            (self.era5_hour_range_row_label, self.hour_start_spin.parentWidget()),
            (self.era5_processing_row_label, self.temporal_resolution_combo),
            (self.era5_ghi_percentile_low_row_label, self.era5_ghi_percentile_low_spin),
            (self.era5_ghi_percentile_mid_row_label, self.era5_ghi_percentile_mid_spin),
            (self.era5_ghi_percentile_high_row_label, self.era5_ghi_percentile_high_spin),
            (self.era5_ghi_percentile_help_row_label, self.era5_ghi_percentile_help),
            (self.era5_save_netcdf_row_label, self.save_netcdf_check),
            (self.era5_save_geotiff_row_label, self.save_geotiff_check),
            (self.era5_save_csv_row_label, self.save_csv_check),
            (self.era5_save_clipped_row_label, self.save_clipped_check),
        ):
            self._set_row_visibility(label_widget, field_widget, uses_era5)
        for label_widget, field_widget in (
            (self.ghi_break_low_row_label, self.ghi_break_low_spin),
            (self.ghi_break_mid_row_label, self.ghi_break_mid_spin),
            (self.ghi_break_high_row_label, self.ghi_break_high_spin),
        ):
            self._set_row_visibility(label_widget, field_widget, not uses_era5)
        if uses_era5:
            self.area_label.setText("Norte: - | Oeste: - | Sur: - | Este: -")
        self._update_model_summary()

    def _update_lulc_field_options(self):
        layer = self._selected_layer(self.lulc_combo)
        self.lulc_field_combo.blockSignals(True)
        self.lulc_field_combo.clear()
        self.lulc_field_combo.addItem("No aplica", "")
        is_vector_polygon = (
            isinstance(layer, QgsVectorLayer)
            and QgsWkbTypes.geometryType(layer.wkbType()) == QgsWkbTypes.PolygonGeometry
        )
        if is_vector_polygon:
            for field in layer.fields():
                self.lulc_field_combo.addItem(field.name(), field.name())
            current = self.lulc_field_combo.findData("class")
            if current > 0:
                self.lulc_field_combo.setCurrentIndex(current)
            elif self.lulc_field_combo.count() > 1:
                self.lulc_field_combo.setCurrentIndex(1)
        self.lulc_field_combo.blockSignals(False)
        self._set_row_visibility(self.lulc_field_label, self.lulc_field_combo, is_vector_polygon)
        self._update_lulc_exclusions_ui()
        self._update_model_summary()

    def _update_lulc_exclusions_ui(self):
        layer = self._selected_layer(self.lulc_combo)
        is_vector_polygon = (
            isinstance(layer, QgsVectorLayer)
            and QgsWkbTypes.geometryType(layer.wkbType()) == QgsWkbTypes.PolygonGeometry
            and bool(self.lulc_field_combo.currentData())
        )
        self._set_row_visibility(self.lulc_excluded_row_label, self.lulc_excluded_edit, not is_vector_polygon)
        self._set_row_visibility(self.lulc_excluded_help_row_label, self.lulc_excluded_help, is_vector_polygon)
        self._set_row_visibility(self.lulc_excluded_list_row_label, self.lulc_excluded_list, is_vector_polygon)
        if not is_vector_polygon:
            return
        self.lulc_excluded_list.clear()
        field_index = layer.fields().indexOf(self.lulc_field_combo.currentData())
        if field_index < 0:
            return
        selected_values = {token.strip() for token in self.lulc_excluded_edit.text().split(",") if token.strip()}
        values = sorted(layer.uniqueValues(field_index), key=lambda value: str(value))
        for value in values:
            item = QListWidgetItem(str(value))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if str(value) in selected_values else Qt.Unchecked)
            self.lulc_excluded_list.addItem(item)
        self._update_model_summary()

    def _set_row_visibility(self, label_widget, field_widget, visible):
        label_widget.setVisible(visible)
        field_widget.setVisible(visible)

    def _update_hour_mode(self):
        enabled = (self.source_mode_combo.currentData() or "era5_ssrd") == "era5_ssrd" and self.hour_mode_combo.currentData() == "range"
        self.hour_start_spin.setEnabled(enabled)
        self.hour_end_spin.setEnabled(enabled)

    def _selected_layer(self, combo):
        layer_id = combo.currentData() or ""
        return QgsProject.instance().mapLayer(layer_id) if layer_id else None

    def _calculate_era5_area(self):
        dem_layer = self._selected_layer(self.dem_combo)
        if dem_layer is None:
            QMessageBox.warning(self, "Area ERA5", "Seleccione primero una capa DEM valida.")
            return
        try:
            area = build_download_area(dem_layer, self.buffer_spin.value())
        except Exception as exc:
            QMessageBox.critical(self, "Area ERA5", f"No fue posible calcular el area:\n{exc}")
            return
        bounds = area_summary(area)
        self.area_label.setText(
            "Norte: "
            f"{bounds['north']:.5f} | Oeste: {bounds['west']:.5f} | "
            f"Sur: {bounds['south']:.5f} | Este: {bounds['east']:.5f}"
        )

    def _populate_layer_combo(self, combo, layers):
        current_layer_id = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Seleccione una capa...", "")
        for layer in layers:
            combo.addItem(layer.name(), layer.id())
        if current_layer_id:
            index = combo.findData(current_layer_id)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def _select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de salida")
        if folder:
            self.output_folder_edit.setText(folder)

    def _build_ahp_matrix(self):
        return build_pairwise_matrix(
            float(self.ghi_vs_slope_combo.currentData()),
            float(self.ghi_vs_aspect_combo.currentData()),
            float(self.slope_vs_aspect_combo.currentData()),
        )

    def _selected_lulc_exclusions_text(self):
        if self.lulc_excluded_list.isVisible():
            values = []
            for index in range(self.lulc_excluded_list.count()):
                item = self.lulc_excluded_list.item(index)
                if item.checkState() == Qt.Checked:
                    values.append(item.text())
            return ",".join(values)
        return self.lulc_excluded_edit.text().strip()

    def _update_ahp_summary(self):
        matrix = self._build_ahp_matrix()
        result = calculate_ahp(matrix, labels=["GHI", "Pendiente", "Orientacion"])
        for row_index, row in enumerate(matrix):
            for col_index, value in enumerate(row):
                item = QTableWidgetItem(f"{value:.3f}")
                self.ahp_table.setItem(row_index, col_index, item)
        weights_text = ", ".join(
            f"{label}: {value:.3f}" for label, value in result["named_weights"].items()
        )
        consistency_text = (
            f"Pesos -> {weights_text} | "
            f"lambda_max={result['lambda_max']:.4f}, CI={result['ci']:.4f}, CR={result['cr']:.4f}"
        )
        consistency_text += " | Consistencia valida" if result["cr"] < 0.1 else " | Consistencia invalida"
        self.ahp_summary_label.setText(consistency_text)

    def _collect_config(self):
        hemisphere = self.hemisphere_combo.currentData() or "N"
        aspect_score_table, excluded_aspects = ASPECT_PRESETS[hemisphere]
        project_crs = QgsProject.instance().crs().authid() if QgsProject.instance().crs().isValid() else ""
        return AnalysisConfig(
            dem_layer_id=self.dem_combo.currentData() or "",
            ghi_layer_id=self.ghi_combo.currentData() or "",
            lulc_layer_id=self.lulc_combo.currentData() or "",
            lulc_field_name=self.lulc_field_combo.currentData() or "",
            solar_source_mode=self.source_mode_combo.currentData() or "era5_ssrd",
            target_crs_authid=project_crs,
            target_resolution=self.resolution_spin.value(),
            slope_threshold_deg=self.slope_spin.value(),
            suitability_threshold=self.suitability_spin.value(),
            min_area_ha=self.min_area_spin.value(),
            era5_buffer_deg=self.buffer_spin.value(),
            analysis_start_date=self.start_date_edit.date().toString("yyyy-MM-dd"),
            analysis_end_date=self.end_date_edit.date().toString("yyyy-MM-dd"),
            analysis_hour_mode=self.hour_mode_combo.currentData() or "all",
            analysis_hour_start=self.hour_start_spin.value(),
            analysis_hour_end=self.hour_end_spin.value(),
            output_temporal_resolution=self.temporal_resolution_combo.currentData() or "monthly",
            era5_dataset="reanalysis-era5-single-levels",
            era5_variable=ERA5_VARIABLE_SOURCE,
            save_era5_netcdf=self.save_netcdf_check.isChecked(),
            save_era5_geotiff=self.save_geotiff_check.isChecked(),
            save_era5_csv=self.save_csv_check.isChecked(),
            save_era5_clipped_raster=self.save_clipped_check.isChecked(),
            excluded_aspects=list(excluded_aspects),
            aspect_score_table=aspect_score_table,
            excluded_lulc_classes=self._selected_lulc_exclusions_text(),
            ghi_breaks=(
                f"{self.ghi_break_low_spin.value():.2f},"
                f"{self.ghi_break_mid_spin.value():.2f},"
                f"{self.ghi_break_high_spin.value():.2f}"
            ),
            era5_ghi_percentiles=(
                f"{self.era5_ghi_percentile_low_spin.value():.0f},"
                f"{self.era5_ghi_percentile_mid_spin.value():.0f},"
                f"{self.era5_ghi_percentile_high_spin.value():.0f}"
            ),
            slope_breaks=(
                f"{self.slope_break_low_spin.value():.1f},"
                f"{self.slope_break_mid_spin.value():.1f},"
                f"{self.slope_break_high_spin.value():.1f}"
            ),
            output_folder=self.output_folder_edit.text().strip(),
            ahp_matrix=self._build_ahp_matrix(),
        )

    def _run(self):
        config = self._collect_config()
        self.status_log.clear()
        self.run_button.setEnabled(False)
        try:
            result = run_analysis(config)
        except Exception as exc:
            self.status_log.appendPlainText(f"Error de ejecucion: {exc}")
            QMessageBox.critical(self, "Solar Site Suitability (AHP)", f"La ejecucion fallo:\n{exc}")
            return
        finally:
            self.run_button.setEnabled(True)
        if result.validation_errors:
            self.status_log.appendPlainText("Errores de validacion:")
            for error in result.validation_errors:
                self.status_log.appendPlainText(f"- {error}")
            QMessageBox.warning(self, "Validacion fallida", "Revise los errores antes de ejecutar el analisis.")
            return
        for line in result.log_lines:
            self.status_log.appendPlainText(line)
        self.status_log.appendPlainText(result.message)
        self._load_outputs(result.output_paths)
        QMessageBox.information(self, "Solar Site Suitability (AHP)", result.message)

    def _load_outputs(self, output_paths):
        preferred_order = [
            "era5_product_clipped",
            "ghi_aligned",
            "suitability_final",
            "optimal_binary",
            "viable_sites",
            "optimal_polygons",
        ]
        for key in preferred_order:
            path = output_paths.get(key)
            if not path:
                continue
            if key in {"viable_sites", "optimal_polygons"}:
                layer = QgsVectorLayer(path, key, "ogr")
            else:
                layer = QgsRasterLayer(path, key)
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
