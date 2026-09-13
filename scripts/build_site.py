"""Build the GitHub Pages site using a strict public-data allowlist.

Never copy the archive, raw documents, scraper state, or arbitrary data files.
"""
from pathlib import Path
import argparse
import shutil

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DATA = ('alerts_latest.json', 'alerts_recent.json', 'metadata.json',
               'districts.json', 'districts.geojson', 'config.json')


def build_site(root=ROOT, destination=None):
    root = Path(root).resolve()
    destination = Path(destination or root / 'build' / 'site').resolve()
    # A rerun must not retain an old accidentally copied archive.
    build_root = (root / 'build').resolve()
    if destination == build_root or build_root not in destination.parents:
        raise ValueError('Site destination must be a child of the project build directory')
    frontend = root / 'frontend'
    missing = [name for name in PUBLIC_DATA if not (root / 'data' / name).is_file()]
    if missing:
        raise FileNotFoundError('Missing public data: ' + ', '.join(missing))
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(frontend, destination)
    data_dir = destination / 'data'
    data_dir.mkdir(exist_ok=True)
    for name in PUBLIC_DATA:
        shutil.copy2(root / 'data' / name, data_dir / name)
    (destination / '.nojekyll').touch()
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(build_site(destination=args.output))
