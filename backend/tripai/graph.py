"""Form generation and AI modification share evidence retrieval and strict validation."""
from langgraph.graph import START, END, StateGraph

from .nodes import TripNodes
from .schemas import TripState
from .tools import build_tools


def operation(state):
    return state['request']['operation']


def after_validation(state):
    return operation(state) if state.get('correction') else 'finalize'


def build_trip_graph(services):
    nodes = TripNodes(build_tools(services))
    graph = StateGraph(TripState)
    for name in ('intake', 'places', 'weather', 'generate', 'modify', 'validate', 'finalize'):
        graph.add_node(name, getattr(nodes, name))
    graph.add_edge(START, 'intake')
    graph.add_edge('intake', 'places')
    graph.add_edge('places', 'weather')
    graph.add_conditional_edges('weather', operation, {'generate': 'generate', 'modify': 'modify'})
    graph.add_edge('generate', 'validate')
    graph.add_edge('modify', 'validate')
    graph.add_conditional_edges('validate', after_validation,
                                {'generate': 'generate', 'modify': 'modify', 'finalize': 'finalize'})
    graph.add_edge('finalize', END)
    return graph.compile()
