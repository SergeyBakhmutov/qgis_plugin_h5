import html
import os
from datetime import date

from qgis.core import QgsApplication, QgsProject, QgsRasterLayer, QgsTask
from qgis.gui import QgsFileWidget
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from .codes import GRID_CRS, QUALITY_FORM, VERTICAL_DATUMS, XYZ_COLUMNS, choices
from .core.config import QUALITY_FIELDS, apply_defaults, check_settings
from .core.converter import convert
from .core.writer import make_filename

INPUT_FILTERS = {
    'tiff': 'GeoTIFF (*.tif *.tiff);;Все файлы (*)',
    'xyz': 'XYZ (*.xyz *.txt *.csv);;Все файлы (*)',
}
# the format follows the extension of the chosen file
INPUT_EXTENSIONS = {'.tif': 'tiff', '.tiff': 'tiff', '.xyz': 'xyz', '.txt': 'xyz', '.csv': 'xyz'}
FILE_CRS = '4326 — WGS 84, градусы'


def parse_code(text):
    return int(text.split(' — ')[0]) if text else None


def parse_number(text):
    return float(text.strip().replace(',', '.'))


def field_text(widget):
    return widget.currentText() if isinstance(widget, QComboBox) else widget.text()


def run_convert(task, input_path, settings, output_dir):
    """Run convert() in a QGIS background task, the task argument is unused"""
    return convert(input_path, settings, output_dir)


def make_field(values=None, default=''):
    """Return a combo box with values or a line edit"""
    if values:
        widget = QComboBox()
        widget.addItems(values)
        widget.setCurrentText(default)
    else:
        widget = QLineEdit(default)
    return widget


class ConverterDialog(QDialog):
    """Conversion form, same fields and checks as gui.py of s102_f_conv"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('S-102 Converter')
        self.formats = {}
        self.fields = {}
        self.quality_fields = {}
        self.task = None
        self.output_path = None

        layout = QGridLayout(self)
        layout.addWidget(self.build_files(), 0, 0, 1, 2)
        layout.addWidget(self.build_metadata(), 1, 0)
        layout.addWidget(self.build_xyz(), 2, 0)
        layout.addWidget(self.build_quality(), 1, 1, 2, 1)

        buttons = QHBoxLayout()
        self.convert_button = QPushButton('Конвертировать')
        self.convert_button.clicked.connect(self.run)
        buttons.addWidget(self.convert_button)
        self.open_button = QPushButton('Открыть в QGIS')
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_result)
        buttons.addWidget(self.open_button)
        self.filename = QLabel()
        buttons.addWidget(self.filename)
        buttons.addStretch()
        layout.addLayout(buttons, 3, 0, 1, 2)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 4, 0, 1, 2)

        for name in ('producer_code', 'dataset_name'):
            self.fields[name].textChanged.connect(self.update_filename)
        self.update_filename()
        self.toggle_xyz()
        self.toggle_quality()

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
            formats.addWidget(button)
            self.formats[value] = button
        formats.addStretch()
        grid.addLayout(formats, 0, 1)
        self.formats['tiff'].setChecked(True)
        # connected after the default is set, the XYZ group does not exist yet
        for button in self.formats.values():
            button.toggled.connect(self.toggle_xyz)

        for row, (label, widget) in enumerate(
                (('Входной файл', self.input), ('Папка вывода', self.output_dir)), start=1):
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(widget, row, 1)
        return group

    def build_metadata(self):
        group = QGroupBox('Данные файла')
        form = QFormLayout(group)
        rows = (
            ('vertical_datum', 'Вертикальный датум *', choices(VERTICAL_DATUMS), ''),
            ('producer_code', 'Код производителя *', None, ''),
            ('dataset_name', 'Название набора *', None, ''),
            ('issue_date', 'Дата выпуска (ГГГГММДД) *', None, date.today().strftime('%Y%m%d')),
            ('issue_time', 'Время выпуска (ччммссZ)', None, ''),
            ('input_values', 'Значения во входном файле',
             ['auto', 'depth', 'elevation'], 'auto'),
            ('horizontal_position_uncertainty', 'Погрешность в плане, м (-1 = неизв.)', None, '-1'),
            ('vertical_uncertainty', 'Погрешность по глубине, м (-1 = неизв.)', None, '-1'),
        )
        for name, label, values, default in rows:
            form.addRow(label, self.add_field(name, values, default))
        form.addRow(QLabel('* обязательные поля'))
        return group

    def build_xyz(self):
        self.xyz_group = QGroupBox('Параметры XYZ')
        form = QFormLayout(self.xyz_group)

        # points are always read as WGS 84 degrees
        file_crs = QComboBox()
        file_crs.addItem(FILE_CRS)
        file_crs.setEnabled(False)
        form.addRow('Система координат файла', file_crs)
        form.addRow('Порядок колонок',
                    self.add_field('columns', list(XYZ_COLUMNS), next(iter(XYZ_COLUMNS))))
        form.addRow('Система координат сетки *', self.add_field('grid_epsg', choices(GRID_CRS)))
        self.fields['grid_epsg'].currentTextChanged.connect(self.update_units)

        self.unit_labels = []
        rows = (
            ('step_x', 'Шаг по X *'),
            ('step_y', 'Шаг по Y (пусто = как по X)'),
            ('tolerance', 'Допуск до узла *'),
        )
        for name, label in rows:
            row = QHBoxLayout()
            row.addWidget(self.add_field(name))
            unit = QLabel()
            unit.setMinimumWidth(16)
            row.addWidget(unit)
            self.unit_labels.append(unit)
            form.addRow(label, row)
        return self.xyz_group

    def build_quality(self):
        group = QGroupBox('QualityOfBathymetryCoverage, п. 10.2.8')
        layout = QVBoxLayout(group)
        self.write_quality = QCheckBox('Добавить таблицу')
        self.write_quality.toggled.connect(self.toggle_quality)
        layout.addWidget(self.write_quality)

        # fields are enabled together by the checkbox
        self.quality_box = QWidget()
        form = QFormLayout(self.quality_box)
        form.setContentsMargins(0, 0, 0, 0)
        for key, label, codes in QUALITY_FORM:
            widget = make_field(choices(codes) if codes else None)
            self.quality_fields[key] = widget
            form.addRow(label, widget)
        layout.addWidget(self.quality_box)
        layout.addStretch()
        return group

    def add_field(self, name, values=None, default=''):
        """Create a field of the form and keep it by name"""
        self.fields[name] = make_field(values, default)
        return self.fields[name]

    def input_type(self):
        return 'xyz' if self.formats['xyz'].isChecked() else 'tiff'

    def toggle_xyz(self):
        self.input.setFilter(INPUT_FILTERS[self.input_type()])
        self.xyz_group.setEnabled(self.input_type() == 'xyz')

    def toggle_quality(self):
        self.quality_box.setEnabled(self.write_quality.isChecked())

    def update_units(self):
        # steps are in the units of the grid CRS (S-102 Table 10-6)
        epsg = parse_code(self.fields['grid_epsg'].currentText())
        unit = '' if epsg is None else '°' if epsg == 4326 else 'м'
        for label in self.unit_labels:
            label.setText(unit)

    def on_input_changed(self, path):
        """Switch the format by the extension of the chosen file"""
        ext = os.path.splitext(path)[1].lower()
        if ext in INPUT_EXTENSIONS:
            self.formats[INPUT_EXTENSIONS[ext]].setChecked(True)

    def update_filename(self):
        names = {name: field_text(self.fields[name]).strip() for name in ('producer_code', 'dataset_name')}
        self.filename.setText(f'Имя файла: {make_filename(names)}')

    def collect(self):
        """Return raw settings as read from YAML and form errors"""
        get = {name: field_text(widget).strip() for name, widget in self.fields.items()}
        raw = {
            'input_values': get['input_values'],
            'producer_code': get['producer_code'],
            'dataset_name': get['dataset_name'],
            'issue_date': get['issue_date'],
        }
        errors = []
        datum = parse_code(get['vertical_datum'])
        if datum is not None:
            raw['vertical_datum'] = datum
        if get['issue_time']:
            raw['issue_time'] = get['issue_time']
        for name in ('horizontal_position_uncertainty', 'vertical_uncertainty'):
            try:
                raw[name] = parse_number(get[name])
            except ValueError:
                errors.append(f'{name} = {get[name]!r}: нужно число')

        if self.write_quality.isChecked():
            quality = {}
            for key, widget in self.quality_fields.items():
                text = field_text(widget).strip()
                if not text:
                    continue
                kind = QUALITY_FIELDS[key]
                if isinstance(kind, tuple):
                    quality[key] = parse_code(text)
                elif kind == 'real':
                    try:
                        quality[key] = parse_number(text)
                    except ValueError:
                        errors.append(f'quality.{key} = {text!r}: нужно число')
                else:
                    quality[key] = text
            raw['quality'] = quality

        if self.input_type() == 'xyz':
            xyz = {'columns': XYZ_COLUMNS[get['columns']]}
            epsg = parse_code(get['grid_epsg'])
            if epsg is not None:
                xyz['grid_epsg'] = epsg
            # empty step_y falls back to step_x in apply_defaults
            for name in ('step_x', 'step_y', 'tolerance'):
                if not get[name]:
                    continue
                try:
                    xyz[name] = parse_number(get[name])
                except ValueError:
                    errors.append(f'xyz.{name} = {get[name]!r}: нужно число')
            raw['xyz'] = xyz
        return raw, errors

    def write_log(self, text, error=False):
        text = html.escape(text)
        self.log.appendHtml(f'<span style="color:red">{text}</span>' if error else text)

    def run(self):
        self.log.clear()

        raw, errors = self.collect()
        input_path = self.input.filePath().strip()
        output_dir = self.output_dir.filePath().strip()
        if not output_dir:
            errors.insert(0, 'не выбрана папка вывода')
        if not input_path:
            errors.insert(0, 'не выбран входной файл')
        settings = apply_defaults(raw)
        if errors:
            # show the rest of the settings errors at once
            errors.extend(check_settings(settings)[0])
            for e in errors:
                self.write_log(f'ошибка: {e}', error=True)
            return

        self.output_path = os.path.join(output_dir, make_filename(settings))
        self.convert_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.write_log('Конвертация…')
        # QGIS stays responsive while the file is written
        self.task = QgsTask.fromFunction('S-102 Converter', run_convert, input_path, settings,
                                         output_dir, on_finished=self.on_finished)
        QgsApplication.taskManager().addTask(self.task)

    def on_finished(self, exception, result=None):
        """Show the conversion log, called in the main thread when the task ends"""
        self.task = None
        self.convert_button.setEnabled(True)
        if exception is not None:
            summary, log = None, [('', [f'{type(exception).__name__}: {exception}'], [])]
        else:
            summary, log = result

        for source, errors, warnings in log:
            prefix = f'{source}: ' if source else ''
            for w in warnings:
                self.write_log(f'{prefix}предупреждение: {w}')
            for e in errors:
                self.write_log(f'{prefix}ошибка: {e}', error=True)
        if summary:
            self.write_log(summary)
            self.write_log('Проверка пройдена, ошибок нет')
            self.open_button.setEnabled(True)
        else:
            self.write_log('Файл не создан или не прошёл проверку', error=True)

    def open_result(self):
        """Add the written S-102 file to the current project"""
        name = os.path.splitext(os.path.basename(self.output_path))[0]
        layer = QgsRasterLayer(self.output_path, name, 'gdal')
        if not layer.isValid():
            self.write_log(f'ошибка: {self.output_path}: QGIS не открыл файл', error=True)
            return
        QgsProject.instance().addMapLayer(layer)
