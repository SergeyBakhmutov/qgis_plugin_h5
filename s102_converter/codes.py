# S-100 Part 10c Table 10c-25, values allowed by S-102 Table 10-2
VERTICAL_DATUMS = {
    1: 'meanLowWaterSprings (MLWS)', 2: 'meanLowerLowWaterSprings',
    3: 'meanSeaLevel (MSL)', 4: 'lowestLowWater', 5: 'meanLowWater (MLW)',
    6: 'lowestLowWaterSprings', 7: 'approximateMeanLowWaterSprings',
    8: 'indianSpringLowWater', 9: 'lowWaterSprings',
    10: 'approximateLowestAstronomicalTide', 11: 'nearlyLowestLowWater',
    12: 'meanLowerLowWater (MLLW)', 13: 'lowWater (LW)',
    14: 'approximateMeanLowWater', 15: 'approximateMeanLowerLowWater',
    16: 'meanHighWater (MHW)', 17: 'meanHighWaterSprings (MHWS)',
    18: 'highWater (HW)', 19: 'approximateMeanSeaLevel', 20: 'highWaterSprings',
    21: 'meanHigherHighWater (MHHW)', 22: 'equinoctialSpringLowWater',
    23: 'lowestAstronomicalTide (LAT)', 24: 'localDatum',
    25: 'internationalGreatLakesDatum1985', 26: 'meanWaterLevel',
    27: 'lowerLowWaterLargeTide', 28: 'higherHighWaterLargeTide',
    29: 'nearlyHighestHighWater', 30: 'highestAstronomicalTide (HAT)',
    44: 'balticSeaChartDatum2000',
}

YES_NO = {1: 'да', 0: 'нет'}
# labels and code names for the featureAttributeTable (S-102 Table 10-8, 10-9)
QUALITY_FORM = (
    ('dataAssessment', 'Оценка данных', {1: 'assessed', 2: 'unassessed', 3: 'oceanic'}),
    ('surveyDateRange.dateStart', 'Начало съёмки (ГГГГММДД)', None),
    ('surveyDateRange.dateEnd', 'Конец съёмки (ГГГГММДД)', None),
    ('surveyAuthority', 'Организация', None),
    ('sourceSurveyID', 'Идентификатор съёмки', None),
    ('fullSeafloorCoverageAchieved', 'Полное покрытие дна', YES_NO),
    ('bathyCoverage', 'Глубины измерены', YES_NO),
    ('featuresDetected.significantFeaturesDetected', 'Обнаружение опасностей', YES_NO),
    ('featuresDetected.leastDepthOfDetectedFeaturesMeasured',
     'Определение наим. глубин', YES_NO),
    ('featuresDetected.sizeOfFeaturesDetected', 'Размер объектов, м³', None),
    ('featureSizeVar', 'Размер объекта, % глубины', None),
    ('zoneOfConfidence.horizontalPositionUncertainty.uncertaintyFixed',
     'Погрешность в плане, м', None),
    ('zoneOfConfidence.horizontalPositionUncertainty.uncertaintyVariableFactor',
     'Множитель погрешности', None),
    ('typeOfBathymetricEstimationUncertainty', 'Тип погрешности глубины', {
        1: 'rawStandardDeviation', 2: 'cUBEStandardDeviation',
        3: 'productUncertainty', 4: 'historicalStandardDeviation'}),
)


def code_options(codes):
    """Return enum labels 'code — name' in the order of codes"""
    return [f'{code} — {name}' for code, name in codes.items()]
