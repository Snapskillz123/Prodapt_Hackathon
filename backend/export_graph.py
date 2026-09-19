"""Write the actual compiled topology for the submission documentation."""
import asyncio
from .config import ROOT, Settings
from .services import Services
from .graph import build_graph


async def main():
    services = Services(Settings())
    try:
        diagram = build_graph(services).get_graph().draw_mermaid()
        (ROOT / 'docs').mkdir(exist_ok=True)
        (ROOT / 'docs' / 'workflow.mmd').write_text(diagram, encoding='utf-8')
        print('Exported docs/workflow.mmd from the compiled LangGraph.')
    finally:
        await services.close()


if __name__ == '__main__':
    asyncio.run(main())
