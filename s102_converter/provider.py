from qgis.core import QgsProcessingProvider

from .geotiff_algorithm import GeoTiffToS102


class S102Provider(QgsProcessingProvider):
    """Processing provider for the S-102 algorithms"""

    def id(self):
        # part of algorithm ids (s102converter:<name>), never change or translate
        return 's102converter'

    def name(self):
        return 'S-102'

    def loadAlgorithms(self):
        self.addAlgorithm(GeoTiffToS102())
