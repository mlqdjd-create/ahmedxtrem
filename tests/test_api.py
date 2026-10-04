import os
from pathlib import Path
os.environ['DATABASE_PATH'] = '/tmp/ahmed_tv_test.db'
os.environ['FERNET_KEY'] = 'x' * 44
os.environ['APP_API_KEY'] = 'test-key'

from cryptography.fernet import Fernet
os.environ['FERNET_KEY'] = Fernet.generate_key().decode()
from fastapi.testclient import TestClient
from app.db import init_db, connect, encrypt
from app.api import app


def setup_module():
    Path(os.environ['DATABASE_PATH']).unlink(missing_ok=True)
    init_db()
    with connect() as con:
        cur=con.execute('INSERT INTO servers(name,url,username_enc,password_enc) VALUES(?,?,?,?)',('test','https://example.test',encrypt('u'),encrypt('p')))
        sid=cur.lastrowid
        con.execute('INSERT INTO channels(server_id,stream_id,name,category_id) VALUES(?,?,?,?)',(sid,42,'قناة اختبار','1'))


def test_health():
    r=TestClient(app).get('/health')
    assert r.status_code == 200 and r.json()['channels'] == 1

def test_channels_requires_key():
    assert TestClient(app).get('/api/channels').status_code == 401

def test_channels_hides_credentials():
    r=TestClient(app).get('/api/channels',headers={'X-API-Key':'test-key'})
    assert r.status_code == 200
    payload=r.json()['channels'][0]
    assert 'stream_url' in payload and 'example.test' not in payload['stream_url']
