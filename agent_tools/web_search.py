
from models.common_models import AgentToolResult
from models.shared_context import SharedContext
from utils.llm_client import LLMClient
from config import Config
from telemetry.tracing import trace_method
from tavily import TavilyClient

class WebSearch:
    """Agent tool for web search to gather information during compliance checking"""

    def __init__(self):
        self.shared_context = SharedContext.get_instance()
        self.llm_client = LLMClient()
        self.tavily_client = TavilyClient(api_key=Config.TAVILY_API_KEY)

    @trace_method("search_and_summarize")
    def search_and_summarize(self, query: str, purpose: str, max_results: int = 5) -> AgentToolResult:
        """
        Search the web and generate a focused summary for a specific purpose.

        This tool combines web search with LLM-powered summarization to provide
        concise, relevant information without overwhelming the agent's context.

        Args:
            query: Search query (e.g., "IFC clear width definition", "building code exit requirements")
            purpose: What you need this information for (e.g., "understand clear width for door compliance checking")
            max_results: Maximum number of search results to fetch (default: 5)

        Returns:
            AgentToolResult with a brief preview in result field.
            Full summary (~500 chars) is stored in SharedContext for use by other tools.
        """
        try:
            print(f"WebSearch: Searching for '{query}' (purpose: {purpose})")

            # Step 1: Execute Tavily search
            response = self.tavily_client.search(
                query=query,
                max_results=max_results,
                include_answer=True  # Get LLM-generated answer from Tavily
            )

            # Step 2: Extract search results
            tavily_answer = response.get('answer', '')
            results = response.get('results', [])

            if not results:
                return AgentToolResult(
                    success=False,
                    agent_tool_name="search_and_summarize",
                    error=f"No search results found for query: {query}"
                )

            # Format results for summarization
            formatted_results = []
            for i, result in enumerate(results[:max_results], 1):
                formatted_results.append(
                    f"Result {i}: {result.get('title', 'No title')}\n"
                    f"URL: {result.get('url', 'No URL')}\n"
                    f"Content: {result.get('content', 'No content')}\n"
                )

            raw_content = "\n".join(formatted_results)

            # Step 3: Use LLM to generate focused summary
            system_prompt = f"""
            You are a technical research assistant specializing in building codes and IFC standards.
            Your task is to analyze web search results and create a concise, focused summary.

            **PURPOSE**: {purpose}

            **Guidelines**:
            - Focus ONLY on information relevant to the stated purpose
            - Maximum 500 characters
            - Use technical terminology when appropriate
            - Cite key facts and definitions
            - Ignore irrelevant information
            - Be precise and actionable"""

            user_prompt = f"""
            Search Query: {query}

            Tavily's Quick Answer:
            {tavily_answer}

            Detailed Search Results:
            {raw_content}

            Generate a focused summary (max 500 chars) addressing the purpose: {purpose}"""

            print(f"WebSearch: Generating focused summary with LLM...")
            summary = self.llm_client.generate_response(
                user_prompt,
                system_prompt
            )

            print(f"WebSearch: Summary generated ({len(summary)} chars)")

            # Step 4: Store full summary in SharedContext
            self.shared_context.add_search_summary(query, summary)

            # Step 5: Return brief preview to agent (saves tokens in agent_history)
            preview = summary[:100] + "..." if len(summary) > 100 else summary

            return AgentToolResult(
                success=True,
                agent_tool_name="search_and_summarize",
                result=f"Search completed: {preview}"
            )

        except Exception as e:
            print(f"WebSearch: Search and summarize failed: {e}")
            return AgentToolResult(
                success=False,
                agent_tool_name="search_and_summarize",
                error=f"Search and summarize failed: {str(e)}"
            )
