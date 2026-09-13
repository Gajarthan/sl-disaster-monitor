"""Upload only validated Parquet and the dataset card; use cached auth or HF_TOKEN."""
import argparse
import os
from pathlib import Path
import shutil
import tempfile
from huggingface_hub import HfApi
from .build_dataset import validate_archive

def publish(root, repo_id, api=None):
    root=Path(root)
    count=validate_archive(root)
    if not count: raise ValueError('Refusing to publish an empty archive')
    api=api or HfApi()
    api.create_repo(repo_id=repo_id,repo_type='dataset',private=False,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dmc-hub-') as directory:
        stage=Path(directory); (stage/'data').mkdir()
        shutil.copyfile(root/'huggingface/README.md',stage/'README.md')
        for path in (root/'archive').glob('alerts-*.parquet'):
            shutil.copyfile(path,stage/'data'/path.name)
        result=api.upload_folder(repo_id=repo_id,repo_type='dataset',folder_path=stage,
            allow_patterns=['README.md','data/*.parquet'],commit_message=f'Update DMC structured archive ({count} records)')
    return str(result)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo-id',default=os.environ.get('HF_DATASET_REPO','gajarthan/sl-disaster-alerts'))
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    print(publish(args.root,args.repo_id))
