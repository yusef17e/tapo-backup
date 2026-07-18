import json
import os


class UploadState:
    """
    Tracks filenames already uploaded to Drive so reruns are idempotent.
    Persisted to a JSON file on disk after every change.
    """

    def __init__(self, path='state.json'):
        self.path = path
        self._data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                return json.load(f)
        return {'uploaded': []}

    def _save(self):
        with open(self.path, 'w') as f:
            json.dump(self._data, f, indent=2)

    def is_uploaded(self, filename):
        return filename in self._data['uploaded']

    def mark_uploaded(self, filename):
        if filename not in self._data['uploaded']:
            self._data['uploaded'].append(filename)
            self._save()
