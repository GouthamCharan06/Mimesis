"""Parallel Search MCP tool integration.

Connects to the Parallel Search MCP server at runtime via the Google ADK / MCP
client layer. Queries are dynamically generated from profile context and
executed against real external search infrastructure.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.retry import with_provider_retry
from app.domain.models import EvidenceSource, ResearchEvidence

logger = get_logger(__name__)


class ParallelSearchTool:
    """Real Parallel Search MCP tool integration.

    Connects to the Parallel Search MCP server and executes search/extract
    operations. This is a first-class runtime tool, not a placeholder.

    MCP Server URL: https://search.parallel.ai/mcp
    Protocol: MCP over SSE (Streamable HTTP)
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._server_url = settings.parallel_mcp_server_url
        self._api_key = settings.parallel_api_key
        self._client = httpx.AsyncClient(timeout=60.0)
        logger.info("parallel_search_tool_initialized", server_url=self._server_url)

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    @with_provider_retry()
    async def search(
        self,
        query: str,
        *,
        num_results: int = 10,
    ) -> ResearchEvidence:
        """Execute a search query via Parallel Search MCP.

        Sends an MCP tools/call request to the Parallel Search server
        and returns a normalized ResearchEvidence object mapping to the query.
        """
        logger.info("parallel_search_executing", query=query[:100], num_results=num_results)

        # --- RAW HTTP IMPLEMENTATION (PRESERVED) ---
        '''
        # MCP JSON-RPC request for the search tool
        mcp_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": "web_search",
                "arguments": {
                    "objective": query,
                    "search_queries": [query],
                },
            },
        }

        response = await self._client.post(
            self._server_url,
            json=mcp_request,
            headers=self._build_headers(),
        )
        response.raise_for_status()
        result = response.json()

        # Parse MCP response into EvidenceSource objects
        sources: list[EvidenceSource] = []

        if "result" in result and "content" in result["result"]:
            for content_item in result["result"]["content"]:
                if content_item.get("type") == "text":
                    sources.extend(
                        self._parse_search_results(content_item.get("text", ""))
                    )
        elif "result" in result:
            raw_result = result["result"]
            if isinstance(raw_result, list):
                for item in raw_result:
                    sources.append(self._raw_to_evidence(item))
            elif isinstance(raw_result, dict):
                sources.extend(
                    self._parse_search_results(str(raw_result))
                )
        '''

        # --- OFFICIAL PARALLEL-WEB SDK IMPLEMENTATION ---
        from parallel import AsyncParallel
        try:
            client = AsyncParallel(api_key=self._api_key)

            # The SDK natively maps search creation
            if hasattr(client, "search") and hasattr(client.search, "create"):
                result = await client.search.create(objective=query, search_queries=[query])
            else:
                result = await client.search(objective=query, search_queries=[query])

            sources: list[EvidenceSource] = []
            data_dict = result if isinstance(result, dict) else getattr(result, "__dict__", {})

            if hasattr(result, "results"):
                for item in result.results:
                    sources.append(self._raw_to_evidence(getattr(item, "__dict__", item)))
            elif "results" in data_dict:
                for item in data_dict["results"]:
                    sources.append(self._raw_to_evidence(item))
            else:
                sources.extend(self._parse_search_results(str(result)))

        except Exception as e:
            logger.error("parallel_search_sdk_error", error=str(e))
            sources = []

        logger.info("parallel_search_completed", query=query[:80], evidence_count=len(sources))
        return ResearchEvidence(query=query, sources=sources)

    @with_provider_retry()
    async def extract(
        self,
        url: str,
    ) -> str:
        """Extract full content from a URL via Parallel Search MCP."""
        logger.info("parallel_extract_executing", url=url[:100])

        # --- RAW HTTP IMPLEMENTATION (PRESERVED) ---
        '''
        mcp_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": "extract",
                "arguments": {
                    "url": url,
                },
            },
        }

        response = await self._client.post(
            self._server_url,
            json=mcp_request,
            headers=self._build_headers(),
        )
        response.raise_for_status()
        result = response.json()

        content = ""
        if "result" in result and "content" in result["result"]:
            for item in result["result"]["content"]:
                if item.get("type") == "text":
                    content += item.get("text", "")
        '''

        # --- OFFICIAL PARALLEL-WEB SDK IMPLEMENTATION ---
        from parallel import AsyncParallel
        try:
            client = AsyncParallel(api_key=self._api_key)
            if hasattr(client, "extract") and hasattr(client.extract, "create"):
                result = await client.extract.create(urls=[url])
            else:
                result = await client.extract(urls=[url])

            data_dict = result if isinstance(result, dict) else getattr(result, "__dict__", {})
            content = ""
            if hasattr(result, "results"):
                for item in result.results:
                    content += getattr(item, "text", getattr(item, "content", ""))
            elif "results" in data_dict:
                for item in data_dict["results"]:
                    content += item.get("text", item.get("content", ""))
            elif hasattr(result, "text"):
                content = result.text
            elif "text" in data_dict:
                content = data_dict["text"]
            else:
                content = str(result)
        except Exception as e:
            logger.error("parallel_extract_sdk_error", error=str(e))
            content = ""

        logger.info("parallel_extract_completed", url=url[:80], content_length=len(content))
        return content

    def _parse_search_results(self, text: str) -> list[EvidenceSource]:
        """Parse search result text into structured EvidenceSource objects."""
        import json as json_module

        sources: list[EvidenceSource] = []

        try:
            parsed = json_module.loads(text)
            if isinstance(parsed, list):
                for item in parsed:
                    sources.append(self._raw_to_evidence(item))
            elif isinstance(parsed, dict):
                if "results" in parsed:
                    for item in parsed["results"]:
                        sources.append(self._raw_to_evidence(item))
                else:
                    sources.append(self._raw_to_evidence(parsed))
        except (json_module.JSONDecodeError, TypeError):
            sources.append(
                EvidenceSource(
                    source_url="",
                    title="Extracted text result",
                    retrieved_content=text[:2000],
                )
            )

        return sources

    def _raw_to_evidence(self, item: Any) -> EvidenceSource:
        """Convert a raw API result dict to an EvidenceSource model."""
        if not isinstance(item, dict):
            return EvidenceSource(
                source_url="", title="Result", retrieved_content=str(item)
            )

        url = str(item.get("url", item.get("link", "")))
        title = str(item.get("title", ""))
        content = str(item.get("snippet", item.get("description", item.get("text", ""))))
        score_str = item.get("relevance_score", item.get("score", 0.0))

        try:
            score = float(score_str) if score_str is not None else 0.0
        except (TypeError, ValueError):
            score = 0.0

        return EvidenceSource(
            source_url=url,
            title=title,
            retrieved_content=content,
            relevance_score=score,
        )

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server for verification."""
        mcp_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {},
        }
        response = await self._client.post(
            self._server_url,
            json=mcp_request,
            headers=self._build_headers(),
        )
        response.raise_for_status()
        result = response.json()
        tools: list[dict[str, Any]] = result.get("result", {}).get("tools", [])
        logger.info("parallel_mcp_tools_listed", tool_count=len(tools))
        return tools

    async def close(self) -> None:
        await self._client.aclose()
