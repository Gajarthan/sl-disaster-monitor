"""Typed yearly Parquet is the durable structured archive, never a giant JSON."""
import argparse
import json
import os
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from scraper.normalizer import validate_alert
from scraper.district_detector import dictionary

STRING_FIELDS='id source document_type hazard severity title description summary language language_reason issued_at valid_from valid_until source_page source_pdf content_hash processed_at'.split()
LIST_FIELDS=['districts','provinces','hazards','languages_detected']

def district_column(name):
    return 'district_'+name.lower().replace(' ','_')

def arrow_schema():
    return pa.schema([(k,pa.string()) for k in STRING_FIELDS]+
        [(k,pa.list_(pa.string())) for k in LIST_FIELDS]+
        [('language_confidence',pa.float64()),('official_json',pa.string()),('extraction_json',pa.string())]+
        [(district_column(d['name']),pa.bool_()) for d in dictionary()['districts']]+
        [('language_'+code,pa.bool_()) for code in ['en','si','ta']])

def to_row(record):
    row={k:record[k] for k in STRING_FIELDS+LIST_FIELDS+['language_confidence']}
    row['official_json']=json.dumps(record['official'],ensure_ascii=False,sort_keys=True)
    row['extraction_json']=json.dumps(record['extraction'],ensure_ascii=False,sort_keys=True)
    row.update({district_column(d['name']):d['name'] in record['districts'] for d in dictionary()['districts']})
    row.update({'language_'+code:code in record['languages_detected'] for code in ['en','si','ta']})
    return row

def from_row(row):
    if row.get('languages_detected') is None:
        row=dict(row,languages_detected=[row['language']] if row['language'] in ['en','si','ta'] else [])
    record={k:row[k] for k in STRING_FIELDS+LIST_FIELDS+['language_confidence']}
    record['official']=json.loads(row['official_json'])
    record['extraction']=json.loads(row['extraction_json'])
    return record

def read_archive(root):
    rows=[]
    for path in sorted((Path(root)/'archive').glob('alerts-*.parquet')):
        rows.extend(from_row(r) for r in pq.read_table(path).to_pylist())
    return rows

def save_records(root, records):
    grouped={}
    for record in records:
        validate_alert(record)
        year=(record['issued_at'] or record['official']['report_date'])[:4]
        grouped.setdefault(year,[]).append(record)
    archive=Path(root)/'archive'; archive.mkdir(parents=True,exist_ok=True)
    for year, additions in grouped.items():
        path=archive/f'alerts-{year}.parquet'
        original={r['id']:r for r in (pq.read_table(path).to_pylist() if path.exists() else [])}
        existing={key:to_row(from_row(r)) for key,r in original.items()}
        before=original
        existing.update({r['id']:to_row(r) for r in additions})
        if before==existing: continue
        table=pa.Table.from_pylist(sorted(existing.values(),key=lambda r:r['id']),schema=arrow_schema())
        temporary=path.with_suffix('.parquet.tmp')
        pq.write_table(table,temporary,compression='zstd')
        os.replace(temporary,path)

def validate_archive(root):
    records=read_archive(root)
    seen=set()
    for record in records:
        validate_alert(record)
        if record['id'] in seen: raise ValueError('Duplicate archive record')
        seen.add(record['id'])
    return len(records)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    print(f'Validated {validate_archive(args.root)} historical records')
