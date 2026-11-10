def classFactory(iface):
    """QGIS entry point: return the plugin instance"""
    from .plugin import S102ConverterPlugin
    return S102ConverterPlugin(iface)
