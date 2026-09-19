import json
import sqlite3
import time
import uuid
from contextlib import contextmanager


class Store:
    """Short transactions; no database lock is held during external API calls."""

    def __init__(self, folder):
        folder.mkdir(parents=True, exist_ok=True)
        self.path = folder / 'roam.sqlite'
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users(
                id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
                password_hash TEXT NOT NULL, created_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(
                token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS conversations(
                id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL, profile_json TEXT NOT NULL DEFAULT '{}', updated INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK(role IN ('user','assistant')), content TEXT NOT NULL, created_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS plans(
                id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                version INTEGER NOT NULL, plan_json TEXT NOT NULL, created_at INTEGER NOT NULL,
                UNIQUE(conversation_id, version));
            CREATE INDEX IF NOT EXISTS conversation_owner ON conversations(user_id, updated DESC);
            CREATE INDEX IF NOT EXISTS message_thread ON messages(conversation_id, id);
            CREATE INDEX IF NOT EXISTS plan_thread ON plans(conversation_id, version DESC);
            CREATE INDEX IF NOT EXISTS session_expiry ON sessions(expires);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA secure_delete=ON')
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def chat(self, chat_id, user_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM conversations WHERE id=? AND user_id=?', (chat_id, user_id)).fetchone()
            if not row:
                return None
            messages = db.execute('SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id', (chat_id,)).fetchall()
            plan = db.execute('SELECT plan_json,version FROM plans WHERE conversation_id=? ORDER BY version DESC LIMIT 1', (chat_id,)).fetchone()
        return {'id': row['id'], 'title': row['title'], 'profile': json.loads(row['profile_json']),
                'messages': [dict(m) for m in messages], 'plan': json.loads(plan['plan_json']) if plan else None,
                'version': plan['version'] if plan else 0}

    def save_turn(self, chat_id, user_id, text, result):
        now = int(time.time() * 1000)
        profile = result['profile']
        with self.connect() as db:
            # Recheck ownership: account/conversation may have been deleted while AI was running.
            if not db.execute('SELECT id FROM conversations WHERE id=? AND user_id=?', (chat_id, user_id)).fetchone():
                raise ValueError('Conversation was deleted while the response was being generated.')
            title = f"Trip to {profile['destination']}" if profile.get('destination') else 'A new adventure'
            db.execute('UPDATE conversations SET title=?,profile_json=?,updated=? WHERE id=? AND user_id=?',
                       (title, json.dumps(profile), now, chat_id, user_id))
            db.executemany('INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)',
                           [(chat_id, 'user', text, now), (chat_id, 'assistant', result['reply'], now)])
            if result.get('plan'):
                version = db.execute('SELECT COALESCE(MAX(version),0)+1 FROM plans WHERE conversation_id=?', (chat_id,)).fetchone()[0]
                db.execute('INSERT INTO plans VALUES(?,?,?,?,?)', (str(uuid.uuid4()), chat_id, version, json.dumps(result['plan']), now))
        return self.chat(chat_id, user_id)
