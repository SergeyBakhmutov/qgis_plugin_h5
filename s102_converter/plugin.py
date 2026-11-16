try:
    from qgis.PyQt.QtGui import QAction  # Qt6, QGIS 4
except ImportError:
    from qgis.PyQt.QtWidgets import QAction  # Qt5, QGIS 3

from .dialog import ConverterDialog

MENU = 'S-102 Converter'


class S102ConverterPlugin:
    """Add the converter window to the Plugins menu"""

    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
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
        """Remove the window and menu entry, QGIS keeps dead objects otherwise"""
        if self.dialog is not None:
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None
        if self.action is not None:
            self.iface.removePluginMenu(MENU, self.action)
            self.action = None
