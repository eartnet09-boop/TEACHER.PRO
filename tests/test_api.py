# tests/test_api.py
import pytest
import httpx
import time

BASE_URL = 'http://localhost:8000'

async def get_client():
    return httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)

class TestSystem:
    @pytest.mark.asyncio
    async def test_health_check(self):
        async with await get_client() as client:
            response = await client.get('/api/health')
            assert response.status_code == 200
            data = response.json()
            assert data['status'] in ['ok', 'degraded']
    
    @pytest.mark.asyncio
    async def test_categories(self):
        async with await get_client() as client:
            response = await client.get('/api/categories')
            assert response.status_code == 200
            data = response.json()
            assert data['total'] >= 10
    
    @pytest.mark.asyncio
    async def test_words(self):
        async with await get_client() as client:
            response = await client.get('/api/categories/1/words?limit=5')
            assert response.status_code == 200
            words = response.json()['words']
            assert len(words) > 0
    
    @pytest.mark.asyncio
    async def test_dialogs(self):
        async with await get_client() as client:
            response = await client.get('/api/dialogs/themes')
            assert response.status_code == 200
            themes = response.json()['themes']
            assert len(themes) > 0
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        async with await get_client() as client:
            response = await client.post('/api/session')
            assert response.status_code == 200
            assert 'session_id' in response.json()
    
    @pytest.mark.asyncio
    async def test_record_progress(self):
        async with await get_client() as client:
            response = await client.post('/api/study/word', json={'word_id': 1, 'score': 85})
            assert response.status_code == 200
            assert response.json()['xp_earned'] > 0
    
    @pytest.mark.asyncio
    async def test_user_stats(self):
        async with await get_client() as client:
            response = await client.get('/api/user/stats')
            assert response.status_code == 200
            data = response.json()
            assert 'level' in data
    
    @pytest.mark.asyncio
    async def test_404_error(self):
        async with await get_client() as client:
            response = await client.get('/api/nao-existe')
            assert response.status_code == 404

class TestPerformance:
    @pytest.mark.asyncio
    async def test_response_times(self):
        async with await get_client() as client:
            start = time.time()
            for _ in range(5):
                response = await client.get('/api/health')
                assert response.status_code == 200
            elapsed = time.time() - start
            avg = elapsed / 5
            assert avg < 0.5, f'Muito lento: {avg:.2f}s por requisicao'
