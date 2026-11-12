from qgis.core import (
    Qgis,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from .codes import QUALITY_FORM, code_options
from .core.config import QUALITY_FIELDS

WRITE_QUALITY = 'WRITE_QUALITY'


def param_name(key):
    """Return the Processing parameter name of a Table 10-8 field"""
    # no dots in names: they are typed as NAME=value in qgis_process
    return key.replace('.', '_')


def add_quality_parameters(alg):
    """Add the switch and the optional Table 10-8 fields to the algorithm"""
    alg.addParameter(QgsProcessingParameterBoolean(
        WRITE_QUALITY, 'Добавить таблицу QualityOfBathymetryCoverage (п. 10.2.8)',
        defaultValue=False))
    for key, label, codes in QUALITY_FORM:
        name = param_name(key)
        if codes:
            param = QgsProcessingParameterEnum(
                name, label, options=code_options(codes), optional=True)
        elif QUALITY_FIELDS[key] == 'real':
            param = QgsProcessingParameterNumber(
                name, label, type=Qgis.ProcessingNumberParameterType.Double, optional=True)
        else:
            # text and S100_TruncatedDate, checked in core.config
            param = QgsProcessingParameterString(name, label, optional=True)
        # the table is optional, keep its fields in the collapsed group
        param.setFlags(param.flags() | Qgis.ProcessingParameterFlag.Advanced)
        alg.addParameter(param)


def read_quality(alg, parameters, context):
    """Return the quality record with settings.yaml keys, None if switched off"""
    if not alg.parameterAsBool(parameters, WRITE_QUALITY, context):
        return None
    quality = {}
    for key, _, codes in QUALITY_FORM:
        name = param_name(key)
        # empty fields are not written, as in gui.py
        if parameters.get(name) in (None, ''):
            continue
        if codes:
            quality[key] = list(codes)[alg.parameterAsEnum(parameters, name, context)]
        elif QUALITY_FIELDS[key] == 'real':
            quality[key] = alg.parameterAsDouble(parameters, name, context)
        else:
            text = alg.parameterAsString(parameters, name, context).strip()
            if text:
                quality[key] = text
    return quality
