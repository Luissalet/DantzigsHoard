"""Pure tools announce their effect through the real MCP wire catalogue."""
import json
import os
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.anyio
async def test_pure_tools_are_readonly_but_persisting_tools_are_not(tmp_path):
    data = tmp_path / 'data'
    params = StdioServerParameters(command=sys.executable,
        args=['-m', 'dantzig.mcp_server'], env={**os.environ, 'DANTZIG_DATA': str(data)})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {tool.name: tool for tool in (await session.list_tools()).tools}
            for name in ('dantzig_example', 'dantzig_validate'):
                ann = tools[name].annotations.model_dump(by_alias=True)
                assert ann['readOnlyHint'] is True
                assert ann['openWorldHint'] is False
            for name in ('dantzig_solve', 'dantzig_save_problem', 'dantzig_export', 'dantzig_config_save_catalog'):
                ann = tools[name].annotations
                assert ann is None or ann.model_dump(by_alias=True).get('readOnlyHint') is not True
            example = await session.call_tool('dantzig_example', {})
            problem = json.loads(next(block.text for block in example.content if block.type == 'text'))
            result = await session.call_tool('dantzig_validate', {'problem': problem})
            assert not result.is_error
            validated = json.loads(next(block.text for block in result.content if block.type == 'text'))
            assert validated['name'] == problem['name']
    assert not data.exists(), 'Pure example/validation unexpectedly created application data'
