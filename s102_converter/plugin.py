from qgis.core import QgsApplication

from .provider import S102Provider


class S102ConverterPlugin:
    """Register the S-102 Processing provider while the plugin is loaded"""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initProcessing(self):
        """Add the provider to the Processing registry"""
        # also called without GUI (qgis_process) when hasProcessingProvider=yes
        self.provider = S102Provider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        """Remove the provider, the registry would keep a dead object otherwise"""
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
