"""Load/tag a verified OCI candidate locally, without rebuilding it."""
import argparse
from pathlib import Path
import tempfile

from scripts.pipeline.runtime.runtime_images import command, loaded_platform, verified_layout


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('layout', type=Path)
    parser.add_argument('tag')
    parser.add_argument('--arch', choices=['amd64', 'arm64', 'x86_64', 'aarch64'], required=True)
    args = parser.parse_args()
    architecture = {'x86_64': 'amd64', 'aarch64': 'arm64'}.get(args.arch, args.arch)
    layout, _ = verified_layout(args.layout)
    with tempfile.TemporaryDirectory(prefix='image-base-load-') as directory:
        with loaded_platform(layout, architecture, Path(directory)) as (_, image, _):
            command('docker', 'tag', image, args.tag)
    print(args.tag)
