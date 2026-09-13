import json
import os
from pathlib import Path

def write_json(path, value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    content=json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n'
    if path.exists() and path.read_text(encoding='utf-8')==content: return False
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(content,encoding='utf-8')
    os.replace(temporary,path)
    return True

def read_json(path, default):
    path=Path(path)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
