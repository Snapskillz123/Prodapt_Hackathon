import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')


class Settings:
    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir or os.getenv('DATA_DIR', ROOT / 'data'))
        key_file = Path(os.getenv('API_KEYS_FILE', ROOT.parent / 'API.txt'))
        try:
            raw = key_file.read_text(encoding='utf-8-sig')
        except (OSError, UnicodeError):
            raw = ''
        def key(env, pattern):
            match = re.search(pattern, raw)
            return os.getenv(env) or (match.group(0) if match else '')
        # Gemini is configured explicitly so its key cannot be confused with the Maps key.
        self.gemini_key = os.getenv('GEMINI_API_KEY', '')
        self.maps_key = key('GOOGLE_MAPS_API_KEY', r'AIza[A-Za-z0-9_-]+')
        self.model = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash')
        self.secure_cookies = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
        self.origins = {origin.strip() for origin in os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000').split(',')}
