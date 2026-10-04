from __future__ import annotations
from datetime import datetime, timezone
from urllib.parse import urlencode
import httpx
from .db import connect, server_credentials

TIMEOUT = httpx.Timeout(45.0, connect=15.0)


def clean_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    return url.rstrip('/').split('?')[0]


def fetch_json(row, action: str | None = None):
    base, username, password = server_credentials(row)
    params = {'username': username, 'password': password}
    if action:
        params['action'] = action
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        response = client.get(f'{base}/player_api.php', params=params)
        response.raise_for_status()
        return response.json()


def sync_server(server_id: int) -> dict:
    row = __import__('app.db', fromlist=['server_row']).server_row(server_id)
    if not row:
        raise ValueError('server not found')
    account = fetch_json(row)
    info = account.get('user_info') or {}
    if int(info.get('auth', 0)) != 1 or str(info.get('status', '')).lower() in {'disabled', 'banned'}:
        raise RuntimeError('Xtream credentials rejected or account disabled')
    categories = fetch_json(row, 'get_live_categories')
    channels = fetch_json(row, 'get_live_streams')
    now = datetime.now(timezone.utc).isoformat()
    with connect() as con:
        con.execute('DELETE FROM categories WHERE server_id=?', (server_id,))
        for c in categories if isinstance(categories, list) else []:
            con.execute('INSERT OR REPLACE INTO categories(server_id,category_id,name,kind) VALUES(?,?,?,?)',
                        (server_id, str(c.get('category_id', '')), c.get('category_name', 'غير مصنف'), 'live'))
        con.execute('DELETE FROM channels WHERE server_id=?', (server_id,))
        for ch in channels if isinstance(channels, list) else []:
            con.execute('''INSERT INTO channels(server_id,stream_id,name,icon,category_id,category_name,stream_type,container_extension,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?)''', (server_id, int(ch.get('stream_id', 0)), ch.get('name', 'بدون اسم'), ch.get('stream_icon', ''),
                           str(ch.get('category_id', '')), '', ch.get('stream_type', 'live'), ch.get('container_extension', 'ts'), now))
        con.execute('UPDATE servers SET last_sync=?,last_error=NULL,updated_at=? WHERE id=?', (now, now, server_id))
    return {'channels': len(channels) if isinstance(channels, list) else 0, 'categories': len(categories) if isinstance(categories, list) else 0, 'at': now}


def stream_url(row, stream_id: int, extension: str = 'm3u8') -> str:
    base, username, password = server_credentials(row)
    ext = extension if extension in {'m3u8', 'ts'} else 'ts'
    return f'{base}/live/{username}/{password}/{stream_id}.{ext}'
