# tests/conftest.py
import pytest
import httpx
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
BASE_URL = 'http://localhost:8000'

def pytest_configure(config):
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 8000))
    sock.close()
    if result != 0:
        print('')
        print('=' * 60)
        print('SERVIDOR NAO ESTA RODANDO!')
        print('Inicie com: python -m src.main')
        print('=' * 60)
        print('')

@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as ac:
        yield ac

@pytest.fixture
async def session_id(client):
    response = await client.post('/api/session')
    data = response.json()
    return data['session_id']

@pytest.fixture
async def test_user():
    return f'test_user_{int(time.time())}'
