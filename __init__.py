# -*- coding: utf-8 -*-
"""Complemento QGIS Solar Site Suitability (AHP): aptitud espacial para parques solares (MCDA-AHP)."""


def classFactory(iface):
    """Punto de entrada que QGIS invoca para cargar el complemento."""
    from .main_plugin import SolarSiteSuitabilityPlugin
    return SolarSiteSuitabilityPlugin(iface)
