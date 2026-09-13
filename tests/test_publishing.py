from pathlib import Path
from unittest.mock import Mock
from huggingface.upload_dataset import publish
from huggingface.build_dataset import save_records
from tests.test_schema import sample

def test_upload_excludes_pdfs_and_state(tmp_path):
    save_records(tmp_path,[sample()])
    (tmp_path/'huggingface').mkdir()
    (tmp_path/'huggingface/README.md').write_text('Dataset card')
    (tmp_path/'secret.pdf').write_bytes(b'not uploaded')
    api=Mock()
    def check_upload(**kwargs):
        files={str(p.relative_to(kwargs['folder_path'])).replace('\\','/') for p in Path(kwargs['folder_path']).rglob('*') if p.is_file()}
        assert files=={'README.md','data/alerts-2026.parquet'}
        assert kwargs['repo_type']=='dataset'
        return 'commit-url'
    api.upload_folder.side_effect=check_upload
    assert publish(tmp_path,'owner/test',api)=='commit-url'
