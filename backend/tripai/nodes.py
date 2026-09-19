"""Every node invokes a useful schema-validated tool; no placeholder nodes."""
import logging

from ..services import ServiceError
from .schemas import TripState

logger = logging.getLogger('roam.tripai')


class TripNodes:
    def __init__(self, tools):
        self.tools = tools

    async def call(self, name, payload, state):
        logger.info('tripai_step start=%s trace=%s', name, '>'.join(state.get('trace', [])) or 'start')
        value = await self.tools[name].ainvoke(payload)
        trace = [*state.get('trace', []), name]
        logger.info('tripai_step complete=%s trace=%s', name, '>'.join(trace))
        return value, trace

    async def intake(self, state: TripState):
        value, trace = await self.call('validate_trip_request', {'request': state['request']}, {})
        return {'preferences': value, 'trace': trace, 'repairs': 0, 'correction': None, 'warnings': []}

    async def places(self, state: TripState):
        value, trace = await self.call('lookup_trip_places', {'preferences': state['preferences']}, state)
        return {'places': value, 'trace': trace}

    async def weather(self, state: TripState):
        value, trace = await self.call('lookup_trip_weather', {
            'preferences': state['preferences'], 'places': state['places']}, state)
        return {**value, 'trace': trace}

    async def draft(self, state, name):
        payload = {key: state[key] for key in ('request', 'preferences', 'places', 'weather', 'correction')}
        value, trace = await self.call(name, payload, state)
        return {'draft': value, 'trace': trace}

    async def generate(self, state: TripState):
        return await self.draft(state, 'generate_trip_draft')

    async def modify(self, state: TripState):
        return await self.draft(state, 'revise_trip_draft')

    async def validate(self, state: TripState):
        value, trace = await self.call('validate_trip_draft', {
            'request': state['request'], 'draft': state['draft'], 'places': state['places']}, state)
        if value['correction']:
            if state['repairs'] >= 1:
                raise ServiceError('Trip validation failed after one repair. Your existing trip has not been changed.')
            return {'correction': value['correction'], 'repairs': state['repairs'] + 1, 'trace': trace}
        return {**value, 'trace': trace}

    async def finalize(self, state: TripState):
        name = 'calculate_trip_budget'
        trace = [*state['trace'], name]
        logger.info('tripai_step start=%s trace=%s', name, '>'.join(state['trace']))
        result = await self.tools[name].ainvoke({
            'trip': state['trip'], 'weather': state['weather'], 'warnings': state['warnings'],
            'notes': state['draft']['notes'], 'trace': trace})
        logger.info('tripai_step complete=%s trace=%s', name, '>'.join(trace))
        return {'result': result, 'trace': trace}
