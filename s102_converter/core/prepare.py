import numpy as np
import numpy.ma as ma

FILL_VALUE = 1000000.0  # S-102 4.4.2.1, табл. 10-3


def mask_nodata(data, nodata):
    """Return a masked array with NaN, inf, and nodata cells masked"""
    masked = ma.masked_invalid(data)
    if nodata is not None and not np.isnan(nodata):
        masked = ma.masked_equal(masked, nodata)
    return masked


def decide_flip(data, nodata, input_values):
    """auto func"""
    if input_values == 'depth':
        return False
    if input_values == 'elevation':
        return True

    # auto
    masked = mask_nodata(data, nodata)
    if masked.max() <= 0:  # все ≤ 0
        return True
    if masked.min() >= 0:  # все ≥ 0
        return False
    raise ValueError(
        f'Знак неоднозначен: значения от {masked.min()} до {masked.max()}. '
        'Укажите в настройках input_values: depth или elevation'
    )

def prepare_depths(data, nodata, flip_sign):
    # integer input can't hold FILL_VALUE and wraps on sign flip
    masked = mask_nodata(data, nodata).astype('float64')

    if flip_sign:
        masked = -masked
    fill = masked.filled(FILL_VALUE)
    result = fill.round(decimals=2)
    return result.astype('float32')
