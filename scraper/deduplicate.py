import hashlib

def content_hash(content: bytes):
    return hashlib.sha256(content).hexdigest()

def stable_id(content: bytes):
    return 'dmc-' + content_hash(content)
