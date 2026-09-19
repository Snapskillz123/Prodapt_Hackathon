import asyncio
import hashlib
import logging
import secrets
import sqlite3
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pwdlib import PasswordHash

from .config import ROOT, Settings
from .db import Store
from .schemas import Register, Login, MessageRequest
from .graph import build_graph
from .services import Services, ServiceError
from .tripai.graph import build_trip_graph
from .tripai.schemas import TripRequest, TripResult, TripPreferences

logger = logging.getLogger('roam.api')

passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash('timing-placeholder-not-an-account')


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def create_app(settings=None, services=None):
    settings = settings or Settings()
    store = Store(settings.data_dir)
    providers = services or Services(settings)
    graph = build_graph(providers)
    trip_graph = build_trip_graph(providers)
    attempts = defaultdict(deque)
    active_users = set()

    @asynccontextmanager
    async def lifespan(app):
        with store.connect() as db:
            db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
        yield
        await providers.close()

    app = FastAPI(title='Roam Travel Planner', version='1.0.0', lifespan=lifespan,
                  description='Pydantic-validated travel conversations orchestrated with LangGraph.')
    app.state.store = store
    app.state.graph = graph
    app.state.trip_graph = trip_graph

    @app.middleware('http')
    async def protections(request, call_next):
        started = time.monotonic()
        if request.url.path.startswith('/api'):
            if request.method not in ('GET', 'HEAD', 'OPTIONS'):
                origin = request.headers.get('origin')
                if origin and origin not in settings.origins:
                    return JSONResponse({'error': 'Cross-origin request rejected.'}, status_code=403)
                length = request.headers.get('content-length', '0')
                body_limit = 262144 if request.url.path == '/api/tripai/plan' else 16384
                if not length.isdigit() or int(length) > body_limit:
                    return JSONResponse({'error': 'Request body is too large.'}, status_code=413)
        response = await call_next(request)
        if request.url.path.startswith('/api'):
            logger.info('api_request method=%s path=%s status=%s duration_ms=%s', request.method,
                        request.url.path, response.status_code, round((time.monotonic() - started) * 1000))
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if request.url.path.startswith('/api'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Never return the rejected input: it may contain passwords or personal data.
        descriptions = [f"{'.'.join(str(x) for x in e['loc'][1:])}: {e['msg']}" for e in error.errors()]
        return JSONResponse({'error': '; '.join(descriptions)}, status_code=422)

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        return JSONResponse({'error': str(error.detail)}, status_code=error.status_code)

    @app.exception_handler(ServiceError)
    async def service_error(request, error):
        return JSONResponse({'error': str(error)}, status_code=502)

    def throttle(key, limit=20, seconds=600):
        now = time.monotonic()
        if len(attempts) > 2048:
            for old in list(attempts):
                if not attempts[old] or attempts[old][-1] < now - seconds:
                    del attempts[old]
        queue = attempts[key]
        while queue and queue[0] < now - seconds:
            queue.popleft()
        if len(queue) >= limit:
            raise HTTPException(429, 'Too many requests. Please wait a few minutes and try again.')
        queue.append(now)

    def current_user(request: Request):
        token = request.cookies.get('roam_session', '')
        if not token:
            return None
        with store.connect() as db:
            row = db.execute('SELECT u.id,u.name,u.email FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>?',
                             (digest(token), time.time())).fetchone()
        return dict(row) if row else None

    def require_user(request: Request):
        user = current_user(request)
        if not user:
            raise HTTPException(401, 'Please sign in to continue.')
        return user

    def set_session(response, user_id):
        token = secrets.token_hex(32)
        with store.connect() as db:
            db.execute('INSERT INTO sessions VALUES(?,?,?)', (digest(token), user_id, time.time() + 7 * 86400))
        response.set_cookie('roam_session', token, max_age=7 * 86400, httponly=True, samesite='strict',
                            secure=settings.secure_cookies, path='/')

    @app.get('/api/health')
    def health():
        return {'ok': True, 'geminiConfigured': bool(settings.gemini_key), 'mapsConfigured': bool(settings.maps_key),
                'validation': 'Pydantic v2', 'workflow': 'LangGraph'}

    @app.get('/api/auth/me')
    def me(request: Request):
        return {'user': current_user(request)}

    @app.post('/api/auth/register')
    def register(payload: Register, request: Request, response: Response):
        throttle('auth:' + request.client.host)
        user_id, email = str(uuid.uuid4()), str(payload.email).casefold()
        password_hash = passwords.hash(payload.password.get_secret_value())
        try:
            with store.connect() as db:
                db.execute('INSERT INTO users VALUES(?,?,?,?,?)', (user_id, email, payload.name, password_hash, int(time.time())))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'This email is already registered. Sign in instead.') from None
        set_session(response, user_id)
        return {'user': {'id': user_id, 'email': email, 'name': payload.name}}

    @app.post('/api/auth/login')
    def login(payload: Login, request: Request, response: Response):
        throttle('auth:' + request.client.host)
        with store.connect() as db:
            row = db.execute('SELECT * FROM users WHERE email=?', (str(payload.email).casefold(),)).fetchone()
        correct = passwords.verify(payload.password.get_secret_value(), row['password_hash'] if row else DUMMY_HASH)
        if not row or not correct:
            raise HTTPException(401, 'Email or password is incorrect.')
        set_session(response, row['id'])
        return {'user': {k: row[k] for k in ('id', 'email', 'name')}}

    @app.post('/api/auth/logout')
    def logout(request: Request, response: Response):
        with store.connect() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=?', (digest(request.cookies.get('roam_session', '')),))
        response.delete_cookie('roam_session', path='/')
        return {'ok': True}

    @app.delete('/api/auth/me')
    def delete_account(response: Response, user=Depends(require_user)):
        if user['id'] in active_users:
            raise HTTPException(409, 'Wait for the current response before deleting your account.')
        with store.connect() as db:
            db.execute('DELETE FROM users WHERE id=?', (user['id'],))
        response.delete_cookie('roam_session', path='/')
        return {'ok': True}

    @app.get('/api/chats')
    def list_chats(user=Depends(require_user)):
        with store.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,title,updated FROM conversations WHERE user_id=? ORDER BY updated DESC', (user['id'],)).fetchall()]

    @app.post('/api/chats')
    def new_chat(user=Depends(require_user)):
        throttle('create:' + user['id'], limit=30)
        chat_id = str(uuid.uuid4())
        with store.connect() as db:
            db.execute('INSERT INTO conversations(id,user_id,title,updated) VALUES(?,?,?,?)',
                       (chat_id, user['id'], 'A new adventure', int(time.time() * 1000)))
        return store.chat(chat_id, user['id'])

    @app.get('/api/chats/{chat_id}')
    def get_chat(chat_id: str, user=Depends(require_user)):
        chat = store.chat(chat_id, user['id'])
        if not chat:
            raise HTTPException(404, 'Conversation not found.')
        return chat

    @app.delete('/api/chats/{chat_id}')
    def delete_chat(chat_id: str, user=Depends(require_user)):
        with store.connect() as db:
            count = db.execute('DELETE FROM conversations WHERE id=? AND user_id=?', (chat_id, user['id'])).rowcount
        if not count:
            raise HTTPException(404, 'Conversation not found.')
        return {'ok': True}

    @app.post('/api/chats/{chat_id}/messages')
    async def send_message(chat_id: str, payload: MessageRequest, user=Depends(require_user)):
        return await run_chat_plan(chat_id, payload.message, user)

    @app.post('/api/chats/{chat_id}/preferences')
    async def plan_from_form(chat_id: str, payload: TripPreferences, user=Depends(require_user)):
        # Reuse the request-level past-date check as well as the form field constraints.
        try:
            TripRequest(operation='generate', preferences=payload)
        except ValueError:
            raise HTTPException(422, 'Departure date must be today or later.') from None
        profile = {'destination': payload.destination, 'startDate': payload.startDate.isoformat(),
                   'days': payload.day_count, 'travelers': payload.travellers, 'budget': payload.totalBudget,
                   'currency': 'INR', 'interests': ', '.join(payload.interests),
                   'style': payload.style, 'requirements': payload.requirements}
        message = (f'Plan a {payload.day_count}-day trip to {payload.destination}, '
                   f'{payload.startDate} to {payload.endDate}, for {payload.travellers} travelers. '
                   f'Total group budget: INR {payload.totalBudget:,.0f}, excluding travel to the destination. '
                   f'Interests: {", ".join(payload.interests)}. Pace: {payload.style}. '
                   f'Special requirements: {payload.requirements or "None specified"}.')
        return await run_chat_plan(chat_id, message, user, profile)

    async def run_chat_plan(chat_id, message, user, form_profile=None):
        chat = store.chat(chat_id, user['id'])
        if not chat:
            raise HTTPException(404, 'Conversation not found.')
        throttle('ai:' + user['id'], limit=20)
        if user['id'] in active_users:
            raise HTTPException(409, 'Your previous message is still being processed.')
        active_users.add(user['id'])
        try:
            result = await asyncio.wait_for(graph.ainvoke({'history': chat['messages'][-12:],
                'message': message, 'previous_profile': chat['profile'], 'previous_plan': chat['plan'],
                'form_profile': form_profile},
                config={'recursion_limit': 15}), timeout=240)
            return store.save_turn(chat_id, user['id'], message, result)
        except TimeoutError:
            raise ServiceError('Planning took too long. Your previous plan is safe; please try again.') from None
        except ValueError:
            raise ServiceError('The response could not be saved or validated. Please retry.') from None
        finally:
            active_users.discard(user['id'])

    @app.post('/api/tripai/plan', response_model=TripResult)
    async def plan_trip(payload: TripRequest, user=Depends(require_user)):
        # Stateless TripAI adapter: never overwrites the older chat-plan format.
        throttle('ai:' + user['id'], limit=20)
        if user['id'] in active_users:
            raise HTTPException(409, 'Your previous request is still being processed.')
        active_users.add(user['id'])
        try:
            state = await asyncio.wait_for(app.state.trip_graph.ainvoke(
                {'request': payload.model_dump(mode='json')}, config={'recursion_limit': 16}), timeout=240)
            return state['result']
        except TimeoutError:
            raise ServiceError('Planning timed out. Your existing trip has not been changed.') from None
        except ValueError:
            raise ServiceError('The generated trip failed validation. Please retry.') from None
        finally:
            active_users.discard(user['id'])

    @app.get('/api/{unknown:path}')
    def unknown_api(unknown):
        raise HTTPException(404, 'Endpoint not found.')

    # A production build can be served by FastAPI alone; development uses Vite's same-origin proxy.
    if (ROOT / 'dist' / 'assets').exists():
        app.mount('/assets', StaticFiles(directory=ROOT / 'dist' / 'assets'), name='assets')

    @app.get('/{path:path}', include_in_schema=False)
    def frontend(path: str):
        index = ROOT / 'dist' / 'index.html'
        if index.exists():
            return FileResponse(index)
        return JSONResponse({'message': 'Run npm run dev and open http://localhost:5173, or build the frontend first.'})

    return app


app = create_app()
