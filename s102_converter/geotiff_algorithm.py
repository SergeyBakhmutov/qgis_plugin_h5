from qgis.core import QgsProcessingParameterRasterLayer

from .base_algorithm import S102Algorithm


class GeoTiffToS102(S102Algorithm):
    """Convert a single band GeoTIFF with depths to S-102"""

    INPUT = 'INPUT'

    def name(self):
        # part of the algorithm id, never change or translate
        return 'geotiff_to_s102'

    def displayName(self):
        return 'GeoTIFF'

    def shortHelpString(self):
        return ('Записывает S-102 ред. 3.0.0 из однослойного GeoTIFF с глубинами '
                'или высотами в метрах. Имя файла: 102 + код производителя + '
                'название набора + .H5')

    def createInstance(self):
        return GeoTiffToS102()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.INPUT, 'Входной GeoTIFF'))
        self.add_dataset_parameters()
        self.add_output_parameters()

    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        raw = self.read_dataset_settings(parameters, context)
        return self.run_conversion(layer.source(), raw, parameters, context, feedback)
