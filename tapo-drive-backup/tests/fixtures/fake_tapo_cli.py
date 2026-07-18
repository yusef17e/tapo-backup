#!/usr/bin/env python3
"""
Fake tapo-cli used by tests.
Parses --path and creates two dummy .mp4 files there, then exits 0.
Pass --exit-code N to simulate a non-zero exit.
"""
import argparse
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument('command')
parser.add_argument('--days', type=int, default=1)
parser.add_argument('--path', default='.')
parser.add_argument('--overwrite', type=int, default=0)
parser.add_argument('--exit-code', type=int, default=0, dest='exit_code')
args = parser.parse_args()

if args.command == 'download-videos':
    base = args.path.rstrip('/\\') + os.sep + 'TestCamera' + os.sep + '2024-01-14' + os.sep
    os.makedirs(base, exist_ok=True)

    clips = [
        base + '2024-01-14 12-00-00.mp4',
        base + '2024-01-14 13-00-00.mp4',
    ]
    for path in clips:
        with open(path, 'wb') as f:
            f.write(b'fake video data')
        print(f'  Downloading to {path}')

    print('\nDownload summary per camera:')
    print('  TestCamera: 2 downloaded, 0 skipped (already existed), 0 failed')

sys.exit(args.exit_code)
