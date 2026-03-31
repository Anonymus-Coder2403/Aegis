from typing import Any
import asyncio
from dataclasses import dataclass
from enum import Enum


class MCPServerType(str, Enum):
    CONTEXT7 = "context7"


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]


class Context7MCPServer:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.base_url = "https://api.context7.com"
        self._session = None

    async def _get_session(self):
        if self._session is None:
            import httpx

            self._session = httpx.AsyncClient(timeout=30.0)
        return self._session

    async def get_documentation(
        self,
        library: str,
        query: str | None = None,
        version: str | None = None,
    ) -> dict[str, Any]:
        session = await self._get_session()

        params = {"library": library}
        if version:
            params["version"] = version
        if query:
            params["query"] = query

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = await session.get(
                f"{self.base_url}/v1/docs",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "library": library, "query": query}

    async def search_code_examples(
        self,
        library: str,
        query: str,
        language: str = "python",
    ) -> dict[str, Any]:
        session = await self._get_session()

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "library": library,
            "query": query,
            "language": language,
        }

        try:
            response = await session.post(
                f"{self.base_url}/v1/examples",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "library": library, "query": query}

    def get_tools(self) -> list[MCPTool]:
        return [
            MCPTool(
                name="get_documentation",
                description="Get up-to-date documentation for a library/framework",
                input_schema={
                    "type": "object",
                    "properties": {
                        "library": {
                            "type": "string",
                            "description": "Library name (e.g., 'fastapi', 'numpy')",
                        },
                        "query": {
                            "type": "string",
                            "description": "Specific topic to search for",
                        },
                        "version": {
                            "type": "string",
                            "description": "Specific version to get docs for",
                        },
                    },
                    "required": ["library"],
                },
            ),
            MCPTool(
                name="search_code_examples",
                description="Search for code examples for a library",
                input_schema={
                    "type": "object",
                    "properties": {
                        "library": {
                            "type": "string",
                            "description": "Library name",
                        },
                        "query": {
                            "type": "string",
                            "description": "What to search for (e.g., 'how to create endpoint')",
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language",
                            "default": "python",
                        },
                    },
                    "required": ["library", "query"],
                },
            ),
        ]


class MCPServer:
    def __init__(self, server_type: MCPServerType, **kwargs):
        if server_type == MCPServerType.CONTEXT7:
            self.server = Context7MCPServer(api_key=kwargs.get("api_key"))
        else:
            raise ValueError(f"Unknown MCP server type: {server_type}")

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if tool_name == "get_documentation":
            return await self.server.get_documentation(
                library=arguments["library"],
                query=arguments.get("query"),
                version=arguments.get("version"),
            )
        elif tool_name == "search_code_examples":
            return await self.server.search_code_examples(
                library=arguments["library"],
                query=arguments["query"],
                language=arguments.get("language", "python"),
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
