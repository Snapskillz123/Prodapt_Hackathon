import time
from .conftest import register


def test_register_login_logout_and_password_storage(client, app):
    response = register(client)
    assert response.status_code == 200
    assert 'httponly' in response.headers['set-cookie'].lower()
    assert 'samesite=strict' in response.headers['set-cookie'].lower()
    with app.state.store.connect() as db:
        row = db.execute('SELECT password_hash FROM users').fetchone()
        assert row[0].startswith('$argon2id$')
        assert row[0] != 'correct-horse-2026'
    assert client.get('/api/auth/me').json()['user']['email'] == 'traveler@example.com'
    client.post('/api/auth/logout')
    assert client.get('/api/chats').status_code == 401
    assert client.post('/api/auth/login', json={'email': 'traveler@example.com', 'password': 'wrong'}).status_code == 401
    assert client.post('/api/auth/login', json={'email': 'traveler@example.com', 'password': 'correct-horse-2026'}).status_code == 200


def test_validation_errors_do_not_echo_password(client):
    r = client.post('/api/auth/register', json={'name': 'Test', 'email': 'invalid', 'password': 'secret'})
    assert r.status_code == 422
    assert 'secret' not in r.text


def test_account_isolation_for_read_write_delete(client):
    register(client)
    chat_id = client.post('/api/chats').json()['id']
    client.post('/api/auth/logout')
    register(client, 'other@example.com')
    assert client.get('/api/chats').json() == []
    assert client.get('/api/chats/' + chat_id).status_code == 404
    assert client.delete('/api/chats/' + chat_id).status_code == 404
    assert client.post('/api/chats/' + chat_id + '/messages', json={'message': 'Plan my trip'}).status_code == 404


def test_save_plan_revise_and_version(client, app):
    register(client)
    cid = client.post('/api/chats').json()['id']
    for version in (1, 2):
        r = client.post(f'/api/chats/{cid}/messages', json={'message': 'Plan my trip'})
        assert r.status_code == 200, r.text
        assert r.json()['version'] == version
    saved = client.get('/api/chats/' + cid).json()
    assert len(saved['messages']) == 4
    assert saved['plan']['budget']['total'] == 1500
    with app.state.store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM plans').fetchone()[0] == 2


def test_failed_generation_preserves_previous_plan(client, providers):
    register(client)
    cid = client.post('/api/chats').json()['id']
    assert client.post(f'/api/chats/{cid}/messages', json={'message': 'Plan my trip'}).status_code == 200
    providers.fail_places = True
    assert client.post(f'/api/chats/{cid}/messages', json={'message': 'Change my trip'}).status_code == 502
    saved = client.get('/api/chats/' + cid).json()
    assert saved['version'] == 1
    assert len(saved['messages']) == 2


def test_deletion_cascades_and_revokes_session(client, app):
    register(client)
    cid = client.post('/api/chats').json()['id']
    client.post(f'/api/chats/{cid}/messages', json={'message': 'Plan my trip'})
    assert client.delete('/api/auth/me').status_code == 200
    assert client.get('/api/chats').status_code == 401
    with app.state.store.connect() as db:
        for table in ('users', 'sessions', 'conversations', 'messages', 'plans'):
            assert db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0


def test_cross_origin_mutation_rejected(client):
    assert client.post('/api/auth/logout', headers={'Origin': 'https://evil.example'}).status_code == 403


def test_expired_session_rejected(client, app):
    register(client)
    with app.state.store.connect() as db:
        db.execute('UPDATE sessions SET expires=?', (time.time() - 1,))
    assert client.get('/api/chats').status_code == 401


def test_rate_limit_auth(client):
    for _ in range(20):
        client.post('/api/auth/login', json={'email': 'absent@example.com', 'password': 'invalid'})
    assert client.post('/api/auth/login', json={'email': 'absent@example.com', 'password': 'invalid'}).status_code == 429
