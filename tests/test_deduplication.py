from scraper.deduplicate import content_hash, stable_id

def test_content_based_identity():
    assert len(content_hash(b'pdf'))==64
    assert stable_id(b'pdf')==stable_id(b'pdf')
    assert stable_id(b'pdf')!=stable_id(b'other pdf')
