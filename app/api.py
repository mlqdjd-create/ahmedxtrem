from __future__ import annotations
import os
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from .db import connect, init_db, server_row
from .xtream import sync_server, stream_url

app = FastAPI(title='Ahmed Al Ali TV API', version='1.0.0')

class AppSetting(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    value: str = Field(max_length=2000)

def admin_key(x_api_key: str | None):
    if not x_api_key or x_api_key != os.getenv('APP_API_KEY'):
        raise HTTPException(401, 'invalid api key')

def public_base():
    return os.getenv('PUBLIC_BASE_URL', 'http://localhost:8000').rstrip('/')

@app.on_event('startup')
def startup(): init_db()

@app.get('/health')
def health():
    with connect() as con:
        servers = con.execute('SELECT COUNT(*) c FROM servers').fetchone()['c']
        channels = con.execute('SELECT COUNT(*) c FROM channels').fetchone()['c']
    return {'ok': True, 'servers': servers, 'channels': channels}

@app.get('/api/config')
def config(x_api_key: str | None = Header(default=None)):
    admin_key(x_api_key)
    with connect() as con:
        rows = con.execute('SELECT key,value FROM app_settings').fetchall()
    return {'settings': {r['key']: r['value'] for r in rows}}

@app.get('/api/categories')
def categories(x_api_key: str | None = Header(default=None)):
    admin_key(x_api_key)
    with connect() as con:
        rows = con.execute('SELECT category_id,name,kind FROM categories ORDER BY name').fetchall()
    return {'categories': [dict(r) for r in rows]}

@app.get('/api/channels')
def channels(x_api_key: str | None = Header(default=None)):
    admin_key(x_api_key)
    with connect() as con:
        rows = con.execute('SELECT id,stream_id,name,icon,category_id,category_name,stream_type FROM channels ORDER BY name').fetchall()
    return {'updated_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
            'channels': [{**dict(r), 'stream_url': f"{public_base()}/api/stream/{r['id']}"} for r in rows]}

@app.get('/api/stream/{channel_id}')
def stream(channel_id: int):
    with connect() as con:
        row = con.execute('SELECT * FROM channels WHERE id=?', (channel_id,)).fetchone()
    if not row: raise HTTPException(404, 'channel not found')
    server = server_row(row['server_id'])
    return RedirectResponse(stream_url(server, row['stream_id'], row['container_extension']), status_code=307)
