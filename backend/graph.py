"""Workflow topology only. See nodes.py for orchestration and tools.py for capabilities."""
from langgraph.graph import StateGraph, START, END

from .nodes import PlannerNodes
from .schemas import PlanningState, Profile
from .tools import build_tools


def after_extraction(state):
    incomplete = Profile.model_validate(state['profile']).missing()
    return 'clarify' if incomplete or state['intent'] == 'conversation' else 'retrieve'


def after_validation(state):
    return 'generate' if state.get('validation_error') else 'finalize'


def build_graph(services):
    nodes = PlannerNodes(build_tools(services))
    builder = StateGraph(PlanningState)
    for name in ('extract', 'clarify', 'retrieve', 'weather', 'generate', 'validate', 'finalize'):
        builder.add_node(name, getattr(nodes, name))
    builder.add_edge(START, 'extract')
    builder.add_conditional_edges('extract', after_extraction, {'clarify': 'clarify', 'retrieve': 'retrieve'})
    builder.add_edge('clarify', END)
    builder.add_edge('retrieve', 'weather')
    builder.add_edge('weather', 'generate')
    builder.add_edge('generate', 'validate')
    builder.add_conditional_edges('validate', after_validation, {'generate': 'generate', 'finalize': 'finalize'})
    builder.add_edge('finalize', END)
    return builder.compile()
