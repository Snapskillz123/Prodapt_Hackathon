import asyncio
from datetime import date

from .config import Settings
from .services import Services
from .schemas import Extraction


async def main():
    settings = Settings()
    services = Services(settings)
    print('Configured:', {'gemini': bool(settings.gemini_key), 'maps': bool(settings.maps_key), 'model': settings.model})
    failed = False
    checks = [('Google Places', lambda: services.places('Jaipur, India', 'history')),
              ('Gemini + Pydantic', lambda: services.structured([{'role': 'user', 'content': 'Hello. No trip preferences yet. Use conversation intent and null for missing fields.'}], Extraction)),
              ('Open-Meteo', lambda: services.weather(26.91, 75.78, date.today().isoformat(), 3))]
    for name, fn in checks:
        try:
            result = await fn()
            print(name, 'OK', f'({len(result)} records)' if isinstance(result, list) else '(validated schema)')
        except Exception as error:
            print(name, 'FAILED:', type(error).__name__, str(error)[:200])
            failed = True
    await services.close()
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    asyncio.run(main())
