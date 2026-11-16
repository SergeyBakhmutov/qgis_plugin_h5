try:
    from qgis.PyQt.QtGui import QAction  # Qt6, QGIS 4
except ImportError:
    from qgis.PyQt.QtWidgets import QAction  # Qt5, QGIS 3
from qgis.core import QgsApplication

from .dialog import ConverterDialog
from .provider import S102Provider

MENU = 'S-102 Converter'


class S102ConverterPlugin:
    """Register the S-102 Processing provider and the converter window"""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.action = None
        self.dialog = None

    def initProcessing(self):
        """Add the provider to the Processing registry"""
        # also called without GUI (qgis_process) when hasProcessingProvider=yes
        self.provider = S102Provider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()
        self.action = QAction(MENU, self.iface.mainWindow())
        self.action.triggered.connect(self.open_dialog)
        self.iface.addPluginToMenu(MENU, self.action)

    def open_dialog(self):
        """Show the converter window, it keeps the entered values between openings"""
        if self.dialog is None:
            self.dialog = ConverterDialog(self.iface.mainWindow())
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def unload(self):
        """Remove the window, menu entry and provider, QGIS keeps dead objects otherwise"""
        if self.dialog is not None:
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None
        if self.action is not None:
            self.iface.removePluginMenu(MENU, self.action)
            self.action = None
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
