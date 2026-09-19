"""Small graph nodes: each invokes a named, schema-validated tool."""
from .schemas import PlanningState
from .services import ServiceError


class PlannerNodes:
    def __init__(self, tools):
        self.tools = tools

    async def extract(self, state: PlanningState):
        if state.get('form_profile') is not None:
            result = self.tools['validate_form_profile'].invoke({'profile': state['form_profile']})
            return {**result, 'trace': ['validate_form_profile'], 'repairs': 0, 'warnings': []}
        result = await self.tools['extract_preferences'].ainvoke({
            'history': state['history'][-12:], 'message': state['message'],
            'previous_profile': state['previous_profile'], 'previous_plan': state.get('previous_plan')})
        return {**result, 'trace': ['extract_preferences'], 'repairs': 0, 'warnings': []}

    def clarify(self, state: PlanningState):
        result = self.tools['check_missing_preferences'].invoke({'profile': state['profile'], 'reply': state['reply']})
        return {'reply': result['reply'], 'plan': None, 'trace': [*state['trace'], 'check_missing_preferences']}

    async def retrieve(self, state: PlanningState):
        places = await self.tools['search_destination_places'].ainvoke({
            'destination': state['profile']['destination'], 'interests': state['profile']['interests']})
        return {'places': places, 'trace': [*state['trace'], 'search_destination_places']}

    async def weather(self, state: PlanningState):
        result = await self.tools['fetch_trip_weather'].ainvoke({'profile': state['profile'], 'place': state['places'][0]})
        return {**result, 'trace': [*state['trace'], 'fetch_trip_weather']}

    async def generate(self, state: PlanningState):
        draft = await self.tools['draft_grounded_itinerary'].ainvoke({
            'profile': state['profile'], 'message': state['message'], 'places': state['places'],
            'weather': state['weather'], 'previous_plan': state.get('previous_plan'),
            'validation_error': state.get('validation_error')})
        return {'draft': draft, 'trace': [*state['trace'], 'draft_grounded_itinerary' if not state['repairs'] else 'repair_grounded_itinerary']}

    def validate(self, state: PlanningState):
        result = self.tools['validate_itinerary'].invoke({
            'draft': state['draft'], 'profile': state['profile'], 'places': state['places']})
        if result['error']:
            if state['repairs'] >= 1:
                raise ServiceError('The itinerary failed validation after one repair. Try a shorter trip or rephrase your preferences.')
            return {'validation_error': result['error'], 'repairs': state['repairs'] + 1,
                    'trace': [*state['trace'], 'validation_requested_repair']}
        return {'plan': result['plan'], 'validation_error': None, 'trace': [*state['trace'], 'validate_itinerary']}

    def finalize(self, state: PlanningState):
        trace = [*state['trace'], 'package_travel_plan']
        plan = self.tools['package_travel_plan'].invoke({
            'plan': state['plan'], 'profile': state['profile'], 'weather': state['weather'],
            'warnings': state['warnings'], 'trace': trace})
        return {'plan': plan, 'reply': plan['summary'], 'trace': trace}
