import asyncio
import json
import logging
import re
import time
from datetime import date

import httpx
from pydantic import ValidationError

from .schemas import Place, ForecastDay

logger = logging.getLogger('roam.llm')


class ServiceError(Exception):
    pass


class Services:
    def __init__(self, settings, client=None):
        self.settings = settings
        self.client = client or httpx.AsyncClient(timeout=httpx.Timeout(75, connect=15), follow_redirects=False)
        self.weather_cache = {}

    async def close(self):
        await self.client.aclose()

    async def request(self, method, url, service, **kwargs):
        for attempt in range(3):
            try:
                response = await self.client.request(method, url, **kwargs)
            except httpx.RequestError:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise ServiceError(f'{service} could not be reached. Please try again.') from None
            if response.status_code in (502, 503, 504):
                if attempt < 2:
                    logger.warning('%s temporary failure status=%s attempt=%s retry_in_seconds=%s',
                                   service, response.status_code, attempt + 1, 2 ** attempt)
                    await asyncio.sleep(2 ** attempt)
                    continue
                if service == 'Gemini':
                    raise ServiceError('Gemini is temporarily unavailable after three attempts. Please retry shortly.') from None
                raise ServiceError(f'{service} is temporarily unavailable. Please retry shortly.') from None
            if response.status_code == 429:
                raise ServiceError(f'{service} usage limit reached. Please wait and try again.')
            if response.is_error:
                if service == 'Gemini' and response.status_code in (400, 401, 403):
                    try:
                        details = response.json().get('error', {}).get('details', [])
                        invalid_key = any(isinstance(d, dict) and d.get('reason') == 'API_KEY_INVALID' for d in details)
                    except (ValueError, AttributeError, TypeError):
                        invalid_key = False
                    if invalid_key:
                        raise ServiceError('Gemini rejected the API key as invalid. Replace GEMINI_API_KEY with a valid Google AI Studio key.')
                    raise ServiceError(f'Gemini rejected the request (HTTP {response.status_code}). Check GEMINI_API_KEY, model access and API restrictions.')
                raise ServiceError(f'{service} returned {response.status_code}. Check the service key and model/API access.')
            try:
                return response.json()
            except ValueError:
                raise ServiceError(f'{service} returned an unreadable response.') from None

    async def structured(self, messages, schema):
        if not self.settings.gemini_key:
            raise ServiceError('Gemini key is missing. Configure GEMINI_API_KEY in the backend .env file.')
        if not re.fullmatch(r'gemini-[a-zA-Z0-9.-]+', self.settings.model):
            raise ServiceError('Invalid GEMINI_MODEL. Use a Gemini model ID, not a URL.')
        schema_prompt = 'Return only a JSON object matching this schema: ' + json.dumps(schema.model_json_schema())
        prompt = [{'role': 'system', 'content': schema_prompt}, *messages]
        for attempt in range(2):
            logger.info('gemini_request schema=%s attempt=%s model=%s', schema.__name__, attempt + 1, self.settings.model)
            system = '\n\n'.join(m['content'] for m in prompt if m['role'] == 'system')
            contents = [{'role': 'model' if m['role'] == 'assistant' else 'user',
                         'parts': [{'text': m['content']}]} for m in prompt if m['role'] != 'system']
            result = await self.request('POST',
                f'https://generativelanguage.googleapis.com/v1beta/models/{self.settings.model}:generateContent', 'Gemini',
                headers={'x-goog-api-key': self.settings.gemini_key},
                json={'systemInstruction': {'parts': [{'text': system}]}, 'contents': contents,
                      'generationConfig': {'temperature': 0.3, 'maxOutputTokens': 8192,
                                           'responseMimeType': 'application/json'}})
            try:
                candidate = result['candidates'][0]
                if candidate.get('finishReason') != 'STOP':
                    raise ValueError('Incomplete or blocked model response.')
                content = ''.join(part['text'] for part in candidate['content']['parts']
                                  if isinstance(part.get('text'), str) and not part.get('thought'))
                value = schema.model_validate_json(content)
                logger.info('gemini_response schema=%s attempt=%s validated=true', schema.__name__, attempt + 1)
                return value
            except (KeyError, IndexError, TypeError, ValidationError, ValueError) as error:
                if attempt:
                    logger.warning('gemini_response schema=%s attempt=%s validated=false final=true', schema.__name__, attempt + 1)
                    raise ServiceError('The AI response failed schema validation. Please rephrase and try again.') from None
                # Bounded repair; omit input values from validation diagnostics.
                logger.warning('gemini_response schema=%s attempt=%s validated=false retry=true', schema.__name__, attempt + 1)
                issues = error.errors(include_input=False, include_url=False) if isinstance(error, ValidationError) else 'Missing JSON response.'
                prompt += [{'role': 'user', 'content': 'Your previous response was invalid. Generate it again following the schema. Issues: ' + str(issues)[:2000]}]

    async def places(self, destination, interests):
        if not self.settings.maps_key:
            raise ServiceError('Google Maps key is missing. Configure API.txt or GOOGLE_MAPS_API_KEY.')
        result = await self.request('POST', 'https://places.googleapis.com/v1/places:searchText', 'Google Places',
            headers={'X-Goog-Api-Key': self.settings.maps_key,
                     'X-Goog-FieldMask': 'places.id,places.displayName,places.formattedAddress,places.location'},
            json={'textQuery': f'Tourist attractions in {destination}', 'pageSize': 20})
        places = []
        for item in result.get('places', []):
            try:
                places.append(Place(id=item['id'], name=item['displayName']['text'], address=item.get('formattedAddress', ''),
                                    lat=item['location']['latitude'], lng=item['location']['longitude']).model_dump())
            except (KeyError, ValidationError):
                continue
        if not places:
            raise ServiceError('No usable places found. Try a specific city and country.')
        return places

    async def weather(self, lat, lng, start_date, days):
        key = (round(lat, 2), round(lng, 2))
        cached = self.weather_cache.get(key)
        if cached and cached[0] > time.monotonic():
            forecast = cached[1]
        else:
            result = await self.request('GET', 'https://api.open-meteo.com/v1/forecast', 'Open-Meteo', params={
                'latitude': lat, 'longitude': lng, 'daily': 'temperature_2m_max,temperature_2m_min,precipitation_probability_max',
                'timezone': 'auto', 'forecast_days': 16})
            daily = result.get('daily', {})
            forecast = []
            for i, value in enumerate(daily.get('time', [])):
                try:
                    forecast.append(ForecastDay(date=value, high=daily['temperature_2m_max'][i], low=daily['temperature_2m_min'][i],
                                                rain=daily['precipitation_probability_max'][i]).model_dump(mode='json'))
                except (KeyError, IndexError, ValidationError):
                    continue
            if len(self.weather_cache) >= 100:
                self.weather_cache.pop(next(iter(self.weather_cache)))
            self.weather_cache[key] = (time.monotonic() + 1800, forecast)
        start = date.fromisoformat(start_date)
        return [f for f in forecast if 0 <= (date.fromisoformat(f['date']) - start).days < days]
