from scraper.district_detector import detect_locations

def test_districts_and_derived_provinces():
    result=detect_locations('Jaffna, Kilinochchi and Nuwara Eliya districts')
    assert set(result['districts'])=={'Jaffna','Kilinochchi','Nuwara Eliya'}
    assert set(result['provinces'])=={'Northern','Central'}

def test_local_names_and_word_boundaries():
    assert 'Colombo' in detect_locations('කොළඹ')['districts']
    assert 'Jaffna' in detect_locations('யாழ்ப்பாணம்')['districts']
    assert detect_locations('Gallestone')['districts']==[]

def test_province_does_not_invent_districts():
    result=detect_locations('Northern province')
    assert result['districts']==[]
    assert result['provinces']==['Northern']

def test_compound_province_names_do_not_match_contained_provinces():
    assert detect_locations('North Western Province')['provinces']==['North Western']
    assert detect_locations('North Central Province')['provinces']==['North Central']
    assert detect_locations('North Central Province and Central Province')['provinces']==['Central','North Central']
