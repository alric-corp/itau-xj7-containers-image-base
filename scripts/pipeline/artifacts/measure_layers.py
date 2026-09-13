"""Measure compressed layer storage/sharing in real multi-architecture OCI layouts."""
import argparse
import json
from pathlib import Path


def measure(layouts):
    images, unique, total = [], {}, 0
    for location in layouts:
        layout = Path(location)
        def read(digest):
            return json.loads((layout / 'blobs/sha256' / digest[7:]).read_text())
        index = json.loads((layout / 'index.json').read_text())
        if len(index['manifests']) == 1 and index['manifests'][0].get('mediaType', '').endswith('index.v1+json'):
            index = read(index['manifests'][0]['digest'])
        for entry in index['manifests']:
            manifest = read(entry['digest'])
            config = read(manifest['config']['digest'])
            layers = manifest['layers']
            size = sum(layer['size'] for layer in layers)
            total += size
            for layer in layers:
                unique[layer['digest']] = layer['size']
            images.append({'layout': layout.name, 'platform': entry['platform'],
                           'digest': entry['digest'], 'layers': len(layers), 'compressed_bytes': size,
                           'user': config['config'].get('User'), 'created': config.get('created')})
    shared = total - sum(unique.values())
    return {'images': images, 'summed_compressed_bytes': total,
            'unique_compressed_bytes': sum(unique.values()), 'reused_compressed_bytes': shared,
            'reuse_fraction': shared / total if total else 0, 'unique_layers': len(unique)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('layouts', nargs='+')
    args = parser.parse_args()
    print(json.dumps(measure(args.layouts), indent=2))
