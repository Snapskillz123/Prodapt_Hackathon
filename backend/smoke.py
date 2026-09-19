"""Explicit live-provider smoke test. Uses a few Gemini/Maps requests, no personal data."""
import asyncio
import json
import time
from datetime import date, timedelta

from .config import ROOT, Settings
from .services import Services
from .graph import build_graph


async def main():
    services = Services(Settings())
    graph = build_graph(services)
    start = time.monotonic()
    departure = (date.today() + timedelta(days=1)).isoformat()
    message = f'Plan a 2-day trip to Jaipur, India starting {departure}, for 2 adults, with a total INR 20000 budget excluding getting there. We like history and architecture. Keep the pace relaxed.'
    try:
        result = await graph.ainvoke({'history': [], 'message': message, 'previous_profile': {}, 'previous_plan': None}, config={'recursion_limit': 15})
        if not result.get('plan'):
            raise RuntimeError('Expected a plan, got clarification: ' + result['reply'])
        plan = result['plan']
        assert len(plan['days']) == 2
        assert all(a['place']['id'] for d in plan['days'] for a in d['activities'])
        artifact = ROOT / 'artifacts'
        artifact.mkdir(exist_ok=True)
        (artifact / 'live-plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
        print('LIVE PLAN OK', {'days': len(plan['days']), 'activities': sum(len(d['activities']) for d in plan['days']),
                             'total': plan['budget']['total'], 'seconds': round(time.monotonic() - start, 1), 'trace': plan['trace']})
    finally:
        await services.close()


if __name__ == '__main__':
    asyncio.run(main())
