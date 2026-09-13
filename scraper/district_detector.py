import json
import re
import unicodedata
from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=1)
def dictionary():
    return json.loads((Path(__file__).resolve().parents[1]/'data/districts.json').read_text(encoding='utf-8'))

def has_alias(text, aliases):
    for alias in aliases:
        # Unicode marks in Sinhala/Tamil must not be treated as word separators.
        pattern = r'(?<![A-Za-z])'+re.escape(alias.casefold())+r'(?![A-Za-z])' if alias.isascii() else re.escape(alias)
        if re.search(pattern,text): return True
    return False

def detect_locations(text):
    text = unicodedata.normalize('NFC',text).casefold()
    districts, provinces = [], set()
    for row in dictionary()['districts']:
        aliases = [row['name']] + [a for group in row['aliases'].values() for a in group]
        if has_alias(text, aliases):
            districts.append(row['name']); provinces.add(row['province'])
    candidates=[]
    for row in dictionary().get('provinces',[]):
        for alias in [a for group in row['aliases'].values() for a in group]:
            pattern=re.escape(alias.casefold())
            if alias.isascii(): pattern=r'(?<![A-Za-z])'+pattern+r'(?![A-Za-z])'
            for match in re.finditer(pattern,text):
                candidates.append((match.start(),match.end(),row['name']))
    accepted=[]
    for start,end,name in sorted(candidates,key=lambda item:item[1]-item[0],reverse=True):
        if not any(start<other_end and end>other_start for other_start,other_end in accepted):
            accepted.append((start,end)); provinces.add(name)
    return dict(districts=sorted(districts), provinces=sorted(provinces))
