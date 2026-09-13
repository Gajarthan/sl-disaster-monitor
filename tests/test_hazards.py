import pytest
from scraper.hazard_detector import detect_hazards
from scraper.severity_detector import detect_severity

@pytest.mark.parametrize('text,hazard',[
 ('Heavy rain advisory','heavy_rain'),('Flood warning','flood'),
 ('River water level report','river_flood'),('Landslide early warning','landslide'),
 ('Severe lightning advisory','lightning'),('Strong winds','strong_wind'),
 ('High waves','high_waves'),('Rough sea','rough_sea'),('Cyclone warning','cyclone'),
 ('Drought bulletin','drought'),('Weather forecast','general_weather'),('Meeting','other'),
 ('பலத்த மழை','heavy_rain'),('නායයෑම්','landslide'),
])
def test_hazards(text,hazard):
    assert hazard in detect_hazards(text)

def test_advisory_for_severe_lightning_is_not_severe_warning():
    assert detect_severity('Advisory for Severe Lightning','')['severity']=='advisory'

def test_no_unsupported_severity():
    assert detect_severity('Water level report','Flood warning levels are shown in the table')['severity']=='unknown'

def test_explicit_warning_and_red_alert():
    assert detect_severity('Flood Warning','')['severity']=='warning'
    assert detect_severity('Red Alert: Landslide','')['severity']=='severe'
