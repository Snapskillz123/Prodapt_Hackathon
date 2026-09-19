"""Generate JSON contracts and a diagram from the actual schemas and graph."""
import asyncio
import json

from ..config import ROOT, Settings
from ..services import Services
from .graph import build_trip_graph
from .schemas import TripRequest, TripResult


async def main():
    destination = ROOT / 'docs' / 'tripai-contract'
    destination.mkdir(exist_ok=True)
    for model in (TripRequest, TripResult):
        (destination / f'{model.__name__}.schema.json').write_text(
            json.dumps(model.model_json_schema(), indent=2), encoding='utf-8')
    services = Services(Settings())
    try:
        diagram = build_trip_graph(services).get_graph().draw_mermaid()
        (destination / 'workflow.mmd').write_text(diagram, encoding='utf-8')
    finally:
        await services.close()
    print('Exported TripAI request/result JSON schemas and workflow; no API calls made.')


if __name__ == '__main__':
    asyncio.run(main())
