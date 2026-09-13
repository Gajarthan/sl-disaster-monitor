import re

RULES = {
 'heavy_rain': ['heavy rain','heavy rainfall','பலத்த மழை','கடும் மழை','තද වැසි'],
 'river_flood': ['river water','water level','river flood','riverine flood','ஆற்று','ගංගා'],
 'flood': ['flood','வெள்ள','ගංවතුර'],
 'landslide': ['landslide','land slide','மண்சரிவு','නායයෑම්','නාය යෑම්'],
 'lightning': ['lightning','மின்னல்','අකුණු'],
 'strong_wind': ['strong wind','gusty wind','பலத்த காற்று','තද සුළං'],
 'high_waves': ['high wave','உயர் அலை','ඉහළ රළ'],
 'rough_sea': ['rough sea','sea will be rough','கடல் கொந்தளி','මුහුද රළු'],
 'cyclone': ['cyclone','cyclonic','சூறாவளி','සුළි කුණාටු'],
 'drought': ['drought','வரட்சி','නියඟ'],
}

def detect_hazards(text):
    text = re.sub(r'\s+',' ',text.casefold())
    matches = [hazard for hazard, words in RULES.items() if any(word in text for word in words)]
    if matches: return matches
    if any(w in text for w in ['weather','forecast','வானிலை','කාලගුණ']): return ['general_weather']
    return ['other']
