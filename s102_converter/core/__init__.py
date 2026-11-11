# Core functions expect GDAL and OSR exceptions enabled by the caller:
#   with gdal.ExceptionMgr(), osr.ExceptionMgr(): ...
# gdal.UseExceptions() is global and would change GDAL behaviour
# for QGIS and all other plugins in the same process.
