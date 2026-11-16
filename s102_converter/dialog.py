import os

from qgis.gui import QgsFileWidget
from qgis.PyQt.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
)

INPUT_FILTERS = {
    'tiff': 'GeoTIFF (*.tif *.tiff);;Все файлы (*)',
    'xyz': 'XYZ (*.xyz *.txt *.csv);;Все файлы (*)',
}
# the format follows the extension of the chosen file
INPUT_EXTENSIONS = {'.tif': 'tiff', '.tiff': 'tiff', '.xyz': 'xyz', '.txt': 'xyz', '.csv': 'xyz'}


class ConverterDialog(QDialog):
    """Conversion form, same fields and checks as gui.py of s102_f_conv"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('S-102 Converter')
        self.formats = {}

        layout = QGridLayout(self)
        layout.addWidget(self.build_files(), 0, 0, 1, 2)

    def build_files(self):
        group = QGroupBox('Файлы')
        grid = QGridLayout(group)

        self.input = QgsFileWidget()
        self.input.setStorageMode(QgsFileWidget.StorageMode.GetFile)
        self.input.fileChanged.connect(self.on_input_changed)
        self.output_dir = QgsFileWidget()
        self.output_dir.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)

        grid.addWidget(QLabel('Формат'), 0, 0)
        formats = QHBoxLayout()
        for value, text in (('tiff', 'GeoTIFF'), ('xyz', 'XYZ')):
            # radio buttons with the same parent are exclusive
            button = QRadioButton(text)
            button.toggled.connect(self.toggle_xyz)
            formats.addWidget(button)
            self.formats[value] = button
        formats.addStretch()
        grid.addLayout(formats, 0, 1)
        self.formats['tiff'].setChecked(True)

        for row, (label, widget) in enumerate(
                (('Входной файл', self.input), ('Папка вывода', self.output_dir)), start=1):
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(widget, row, 1)
        return group

    def input_type(self):
        return 'xyz' if self.formats['xyz'].isChecked() else 'tiff'

    def toggle_xyz(self):
        self.input.setFilter(INPUT_FILTERS[self.input_type()])

    def on_input_changed(self, path):
        """Switch the format by the extension of the chosen file"""
        ext = os.path.splitext(path)[1].lower()
        if ext in INPUT_EXTENSIONS:
            self.formats[INPUT_EXTENSIONS[ext]].setChecked(True)
