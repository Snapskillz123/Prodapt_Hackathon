import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from backend.schemas import Extraction
from backend.services import Services, ServiceError


def response(text=None, finish='STOP'):
    return {'candidates': [{'finishReason': finish, 'content': {'parts': [
        {'text': 'private reasoning should be ignored', 'thought': True},
        {'text': text or json.dumps({'profile': {}, 'reply': 'Where would you like to go?', 'intent': 'conversation'})}
    ]}}]}


def invoke(handler, messages=None, key='dummy-test-key', model='gemini-2.5-flash'):
    async def run():
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        service = Services(SimpleNamespace(gemini_key=key, model=model), client=client)
        try:
            return await service.structured(messages or [{'role': 'user', 'content': 'Hello'}], Extraction)
        finally:
            await service.close()
    return asyncio.run(run())


def test_native_request_and_response_contract():
    def handler(request):
        assert request.url.host == 'generativelanguage.googleapis.com'
        assert request.url.path.endswith('/gemini-2.5-flash:generateContent')
        assert not request.url.query
        assert request.headers['x-goog-api-key'] == 'dummy-test-key'
        payload = json.loads(request.content)
        assert payload['generationConfig']['responseMimeType'] == 'application/json'
        assert 'properties' in payload['systemInstruction']['parts'][0]['text']
        assert [c['role'] for c in payload['contents']] == ['user', 'model', 'user']
        return httpx.Response(200, json=response())
    result = invoke(handler, [{'role': 'system', 'content': 'Travel assistant'},
        {'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello'},
        {'role': 'user', 'content': 'Thanks'}])
    assert result.intent == 'conversation'


def test_schema_repair_once():
    calls = []
    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=response('not json') if len(calls) == 1 else response())
    invoke(handler)
    assert len(calls) == 2
    assert 'previous response was invalid' in calls[1]['contents'][-1]['parts'][0]['text']


@pytest.mark.parametrize('payload', [response('not json'), response(finish='MAX_TOKENS'),
    {'promptFeedback': {'blockReason': 'SAFETY'}}, {'candidates': []}])
def test_incomplete_or_invalid_response_fails_safely(payload):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=payload)
    with pytest.raises(ServiceError, match='schema validation'):
        invoke(handler)
    assert len(calls) == 2


def test_invalid_key_error_does_not_echo_provider_body():
    def handler(request):
        return httpx.Response(400, json={'error': {'message': 'secret-provider-content',
            'details': [{'reason': 'API_KEY_INVALID'}]}})
    with pytest.raises(ServiceError, match='key as invalid') as error:
        invoke(handler)
    assert 'secret-provider-content' not in str(error.value)
    assert 'dummy-test-key' not in str(error.value)


def test_rate_limit_does_not_retry():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(429)
    with pytest.raises(ServiceError, match='usage limit'):
        invoke(handler)
    assert len(calls) == 1


@pytest.mark.parametrize('key,model', [('', 'gemini-2.5-flash'), ('dummy', 'https://other.example')])
def test_invalid_configuration_never_calls_network(key, model):
    def handler(request):
        pytest.fail('Should not send a request')
    with pytest.raises(ServiceError):
        invoke(handler, key=key, model=model)
