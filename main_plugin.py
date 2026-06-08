import os

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .ui.main_dialog import SolarSiteSuitabilityDialog

PLUGIN_TITLE = "Solar Site Suitability (AHP)"


class SolarSiteSuitabilityPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def tr(self, message):
        return QCoreApplication.translate("SolarSiteSuitability", message)

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.action = QAction(icon, self.tr(PLUGIN_TITLE), self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        # Recomendacion del repositorio QGIS: ubicar el plugin en el menu Raster.
        self.iface.addPluginToRasterMenu(self.tr(PLUGIN_TITLE), self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action is not None:
            self.iface.removePluginRasterMenu(self.tr(PLUGIN_TITLE), self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        if self.dialog is None:
            self.dialog = SolarSiteSuitabilityDialog(self.iface)
        self.dialog.refresh_layers()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
