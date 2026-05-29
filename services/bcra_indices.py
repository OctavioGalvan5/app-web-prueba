import json
import os
import requests
import urllib3
from datetime import date

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_INDICES_FILE = os.path.join(_BASE_DIR, 'datos', 'indices_bcra.json')
_BCRA_URL = 'https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/43'


def _load_stored():
    if os.path.exists(_INDICES_FILE):
        with open(_INDICES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'indices': {}, 'last_updated': None}


def _save_stored(data):
    with open(_INDICES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, separators=(',', ':'))


def _fetch_page(offset=0):
    """Fetch one page (up to 1000 entries) from BCRA API."""
    params = {'offset': offset} if offset else {}
    r = requests.get(_BCRA_URL, params=params, verify=False, timeout=15)
    r.raise_for_status()
    data = r.json()
    meta = data['metadata']['resultset']
    detalle = data['results'][0]['detalle']
    entries = {item['fecha'].replace('-', ''): item['valor'] for item in detalle}
    return entries, meta['count']


def _fetch_all():
    """Fetch complete history from BCRA API (paginated)."""
    all_entries = {}
    offset = 0
    while True:
        entries, total = _fetch_page(offset)
        all_entries.update(entries)
        offset += len(entries)
        if offset >= total or not entries:
            break
    return all_entries


def get_indices():
    """Return the full indices dict {YYYYMMDD: valor}, updating from BCRA if needed."""
    stored = _load_stored()
    today = date.today().isoformat()

    # First run: download complete history
    if not stored['indices']:
        stored['indices'] = _fetch_all()
        stored['last_updated'] = today
        _save_stored(stored)
        return stored['indices']

    # Daily update: fetch only the first page (most recent 1000 entries)
    if stored.get('last_updated') != today:
        try:
            new_data, _ = _fetch_page()
            stored['indices'].update(new_data)
            stored['last_updated'] = today
            _save_stored(stored)
        except Exception:
            pass  # Serve stale data rather than fail

    return stored['indices']
