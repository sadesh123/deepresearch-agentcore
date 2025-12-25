"""
arXiv API Tool for searching academic papers.

This tool provides search functionality for the arXiv repository,
returning paper metadata including titles, abstracts, authors, and links.
"""

import urllib.request
import urllib.parse
import feedparser
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ArxivTool:
    """Tool for searching and retrieving papers from arXiv."""

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self, max_results: int = 5):
        """
        Initialize the arXiv tool.

        Args:
            max_results: Maximum number of results to return per query
        """
        self.max_results = max_results

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        sort_by: str = "relevance",
        sort_order: str = "descending"
    ) -> List[Dict[str, str]]:
        """
        Search arXiv for papers matching the query.

        Args:
            query: Search query (e.g., "all:quantum computing" or "ti:neural networks")
            max_results: Override default max results
            sort_by: Sort by 'relevance', 'lastUpdatedDate', or 'submittedDate'
            sort_order: 'ascending' or 'descending'

        Returns:
            List of paper dictionaries with keys:
                - id: arXiv ID
                - title: Paper title
                - summary: Abstract
                - authors: Comma-separated author names
                - published: Publication date
                - pdf_url: Link to PDF
                - categories: Paper categories
        """
        try:
            results_limit = max_results or self.max_results

            # Build query parameters
            params = {
                'search_query': query,
                'start': 0,
                'max_results': results_limit,
                'sortBy': sort_by,
                'sortOrder': sort_order
            }

            url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
            logger.info(f"Querying arXiv: {url}")

            # Fetch results
            response = urllib.request.urlopen(url)
            data = response.read().decode('utf-8')

            # Parse Atom feed using feedparser
            feed = feedparser.parse(data)

            papers = []
            for entry in feed.entries:
                paper = {
                    'id': entry.id.split('/abs/')[-1] if 'id' in entry else '',
                    'title': entry.title.replace('\n', ' ').strip() if 'title' in entry else '',
                    'summary': entry.summary.replace('\n', ' ').strip() if 'summary' in entry else '',
                    'authors': ', '.join([author.name for author in entry.authors]) if 'authors' in entry else '',
                    'published': entry.published if 'published' in entry else '',
                    'pdf_url': next((link.href for link in entry.links if link.type == 'application/pdf'), ''),
                    'categories': ', '.join([tag.term for tag in entry.tags]) if 'tags' in entry else ''
                }
                papers.append(paper)

            logger.info(f"Found {len(papers)} papers for query: {query}")
            return papers

        except Exception as e:
            logger.error(f"Error searching arXiv: {str(e)}")
            return []

    def search_by_category(self, category: str, max_results: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Search arXiv by category.

        Args:
            category: arXiv category (e.g., 'cs.AI', 'physics.quantum-ph')
            max_results: Override default max results

        Returns:
            List of paper dictionaries
        """
        query = f"cat:{category}"
        return self.search(query, max_results=max_results)

    def search_by_title(self, title: str, max_results: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Search arXiv by title keywords.

        Args:
            title: Title keywords
            max_results: Override default max results

        Returns:
            List of paper dictionaries
        """
        query = f"ti:{title}"
        return self.search(query, max_results=max_results)

    def search_by_author(self, author: str, max_results: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Search arXiv by author name.

        Args:
            author: Author name
            max_results: Override default max results

        Returns:
            List of paper dictionaries
        """
        query = f"au:{author}"
        return self.search(query, max_results=max_results)

    def format_results_for_llm(self, papers: List[Dict[str, str]]) -> str:
        """
        Format search results in a clean text format for LLM consumption.

        Args:
            papers: List of paper dictionaries from search

        Returns:
            Formatted string with paper information
        """
        if not papers:
            return "No papers found."

        formatted = []
        for i, paper in enumerate(papers, 1):
            formatted.append(f"""
Paper {i}:
Title: {paper['title']}
Authors: {paper['authors']}
Published: {paper['published']}
Categories: {paper['categories']}
Abstract: {paper['summary'][:500]}{'...' if len(paper['summary']) > 500 else ''}
PDF: {paper['pdf_url']}
arXiv ID: {paper['id']}
""")

        return "\n---\n".join(formatted)


# Tool description for AgentCore
ARXIV_TOOL_DESCRIPTION = """
Search academic papers from arXiv repository.

Usage:
- General search: Use query like "quantum computing" or "neural networks"
- Specific fields: Use prefixes like "ti:title keywords", "au:author name", "cat:cs.AI"
- Returns up to 5 most relevant papers with titles, abstracts, authors, and PDF links

Examples:
- "quantum computing cryptography"
- "ti:transformer attention mechanism"
- "au:Yoshua Bengio"
- "cat:cs.LG" (machine learning category)
"""


def create_arxiv_tool(max_results: int = 5) -> ArxivTool:
    """Factory function to create an arXiv tool instance."""
    return ArxivTool(max_results=max_results)


if __name__ == "__main__":
    # Test the tool
    tool = ArxivTool(max_results=3)

    print("Testing arXiv search...")
    results = tool.search("all:quantum computing")

    print(f"\nFound {len(results)} papers\n")
    print(tool.format_results_for_llm(results))
