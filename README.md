# S-102 Converter

QGIS plugin that converts a bathymetric GeoTIFF or gridded XYZ points into an
IHO S-102 Edition 3.0.0 dataset (HDF5). Based on s102_f_conv: writing is done by
the GDAL S102 driver, the result is checked by `core/validate_s102.py`.

## Requirements

- QGIS 3.40 or newer (QGIS 4 supported)
- GDAL 3.13 or newer with the S102 driver (check: `gdalinfo --formats | grep S102`)
- h5py, optional: without it the file is written, validation is skipped with a warning

h5py is not bundled with QGIS. On macOS it can be installed into the QGIS
Python user site:

```
R=/Applications/QGIS.app/Contents/Resources/python3.11
PYTHONHOME=$R PYTHONPATH=$R:$R/site-packages:$R/lib-dynload \
  /Applications/QGIS.app/Contents/MacOS/python3.12 -m pip install --user h5py
```

It loads only inside the QGIS application; `qgis_process` and the bundled
`python3.12` reject it because of macOS library validation.

## Installation

Development, link the plugin folder into the QGIS profile:

```
ln -s "$PWD/s102_converter" \
  ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/s102_converter
```

Then enable "S-102 Converter" in Plugins > Manage and Install Plugins.

## Usage

Processing Toolbox > S-102:

- `GeoTIFF` (`s102converter:geotiff_to_s102`)
- `XYZ` (`s102converter:xyz_to_s102`)

Output name is `102<producer_code><dataset_name>.H5` in the chosen folder, an
existing file is overwritten. The run fails on any error in parameters, input
or the written file; errors and warnings are shown in the log.

From the command line (enum parameters take the option index):

```
qgis_process run s102converter:geotiff_to_s102 -- INPUT=input.tif \
  VERTICAL_DATUM=22 PRODUCER_CODE=TEST DATASET_NAME=AREA_1 OUTPUT_DIR=output
```

## Input

- single band with depth or elevation in metres, uncertainty is not supported
- regular, non-rotated grid
- CRS: EPSG 4326, WGS 84 / UTM (32601-32660, 32701-32760) or UPS (5041, 5042)

XYZ input:

- three columns, WGS 84 degrees in `lat_lon` or `lon_lat` order, then depth
- any of `,` `;` space or tab as separator, leading header lines are skipped
- grid CRS (Table 5-1), steps and tolerance are given by the user; every point
  must lie within the tolerance of a grid node and at most one point per cell,
  points are never interpolated
- the bounding grid is held in memory, limit 50 million cells

## Quality

With "Add QualityOfBathymetryCoverage table" switched on, the filled fields of
the advanced group are written as a single record (`id = 1`) for all cells with
depth. Fields are checked against S-102 Table 10-8; empty fields are skipped.

## Layout

- `s102_converter/plugin.py` - registers the Processing provider
- `s102_converter/provider.py` - Processing provider
- `s102_converter/base_algorithm.py` - dataset fields and conversion run
- `s102_converter/geotiff_algorithm.py`, `xyz_algorithm.py` - input algorithms
- `s102_converter/quality.py` - quality table fields
- `s102_converter/codes.py` - code lists for the enum fields
- `s102_converter/core/` - conversion from s102_f_conv: settings checks,
  reading, gridding, CRS detection, writing and the validator

## Not implemented

- exchange set (CATALOG.XML, signatures)
- producer code check against the IHO registry

## License

GPL-2.0-or-later. `core/validate_s102.py` is from GDAL, MIT.
