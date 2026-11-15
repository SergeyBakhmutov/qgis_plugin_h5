try:
    from qgis.PyQt.QtGui import QAction  # Qt6, QGIS 4
except ImportError:
    from qgis.PyQt.QtWidgets import QAction  # Qt5, QGIS 3
from qgis.core import QgsApplication

from .provider import S102Provider

MENU = 'S-102 Converter'
# menu text and Processing algorithm id
ALGORITHMS = (
    ('GeoTIFF', 's102converter:geotiff_to_s102'),
    ('XYZ', 's102converter:xyz_to_s102'),
)


class S102ConverterPlugin:
    """Register the S-102 Processing provider and its Plugins menu entries"""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.actions = []

    def initProcessing(self):
        """Add the provider to the Processing registry"""
        # also called without GUI (qgis_process) when hasProcessingProvider=yes
        self.provider = S102Provider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()
        for text, alg_id in ALGORITHMS:
            action = QAction(text, self.iface.mainWindow())
            # triggered passes 'checked' first, alg_id is bound by the default value
            action.triggered.connect(lambda checked=False, alg_id=alg_id: self.open_dialog(alg_id))
            self.iface.addPluginToMenu(MENU, action)
            self.actions.append(action)

    def open_dialog(self, alg_id):
        """Open the Processing dialog of the algorithm"""
        import processing
        processing.execAlgorithmDialog(alg_id)

    def unload(self):
        """Remove menu entries and the provider, QGIS keeps dead objects otherwise"""
        for action in self.actions:
            self.iface.removePluginMenu(MENU, action)
        self.actions = []
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
