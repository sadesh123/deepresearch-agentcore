"""
DxO Decision Framework Agent - Sequential research workflow.

Roles:
1. Lead Researcher: Initial research and analysis
2. Critical Reviewer: Challenge assumptions and identify gaps
3. Domain Expert: Validate and add specialized knowledge
4. Lead Researcher (Synthesis): Final comprehensive report
"""

import logging
from typing import Dict, Any, List
from .bedrock_client import create_bedrock_client
from .tools.arxiv_tool import create_arxiv_tool

logger = logging.getLogger(__name__)


class DxOAgent:
    """
    DxO Decision Framework orchestrator implementing sequential research workflow.
    """

    def __init__(self, arxiv_max_results: int = 5):
        """
        Initialize DxO Agent.

        Args:
            arxiv_max_results: Maximum papers to retrieve from arXiv per query
        """
        self.bedrock_client = create_bedrock_client()
        self.arxiv_tool = create_arxiv_tool(max_results=arxiv_max_results)
        logger.info("Initialized DxO Agent with arXiv integration")

    def _search_arxiv(self, question: str) -> str:
        """
        Search arXiv for relevant papers based on the question.

        Args:
            question: Research question

        Returns:
            Formatted string with paper information
        """
        logger.info(f"Searching arXiv for: {question[:100]}...")

        # Extract key terms (simple approach - can be enhanced)
        # For demo, we'll search the question as-is
        papers = self.arxiv_tool.search(f"all:{question}", max_results=5)

        if not papers:
            return "No relevant papers found on arXiv."

        return self.arxiv_tool.format_results_for_llm(papers)

    async def lead_researcher_initial(self, question: str) -> Dict[str, Any]:
        """
        Role 1: Lead Researcher conducts initial research and analysis.

        Args:
            question: User's research question

        Returns:
            Dict with 'content' (findings), 'papers' (arXiv results), 'usage'
        """
        logger.info("DxO Step 1: Lead Researcher - Initial research...")

        # Search arXiv for relevant papers
        arxiv_results = self._search_arxiv(question)

        system_prompt = """You are a lead researcher conducting initial research on a question.

Your responsibilities:
1. Analyze the research question thoroughly
2. Review the provided academic papers from arXiv
3. Synthesize key findings and insights
4. Propose a research approach and methodology
5. Identify initial answers and hypotheses

Provide a structured response (400-500 words) covering:
- Research context and significance
- Key findings from the papers
- Initial conclusions
- Proposed approach for deeper investigation"""

        user_message = f"""Research Question: {question}

Relevant Academic Papers from arXiv:
{arxiv_results}

Based on these papers and your knowledge, provide your initial research findings and proposed approach."""

        result = await self.bedrock_client.invoke_async(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.7,
            max_tokens=2000
        )

        logger.info("Lead Researcher initial analysis complete")
        return {
            'role': 'Lead Researcher',
            'step': 'Initial Research',
            'content': result['content'],
            'papers': arxiv_results,
            'usage': result.get('usage', {})
        }

    async def critical_reviewer(
        self,
        question: str,
        lead_findings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Role 2: Critical Reviewer challenges assumptions and identifies gaps.

        Args:
            question: Original research question
            lead_findings: Lead researcher's initial findings

        Returns:
            Dict with 'content' (critique), 'usage'
        """
        logger.info("DxO Step 2: Critical Reviewer - Challenging assumptions...")

        system_prompt = """You are a critical reviewer with expertise in identifying weaknesses and gaps in research.

Your responsibilities:
1. Critically examine the lead researcher's findings
2. Challenge assumptions and identify logical flaws
3. Point out missing perspectives or overlooked factors
4. Identify gaps in the analysis
5. Suggest improvements and additional considerations

Be constructively critical. Your goal is to strengthen the research by identifying issues.

Provide a structured critique (300-400 words) covering:
- Assumptions that need validation
- Potential flaws or weaknesses
- Missing perspectives or gaps
- Counterarguments or alternative interpretations
- Suggestions for improvement"""

        user_message = f"""Research Question: {question}

Lead Researcher's Findings:
{lead_findings['content']}

Papers Reviewed:
{lead_findings['papers']}

Provide your critical review and identify areas for improvement."""

        result = await self.bedrock_client.invoke_async(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.6,
            max_tokens=1500
        )

        logger.info("Critical review complete")
        return {
            'role': 'Critical Reviewer',
            'step': 'Critical Review',
            'content': result['content'],
            'usage': result.get('usage', {})
        }

    async def domain_expert(
        self,
        question: str,
        lead_findings: Dict[str, Any],
        critique: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Role 3: Domain Expert validates and adds specialized knowledge.

        Args:
            question: Original research question
            lead_findings: Lead researcher's findings
            critique: Critical reviewer's critique

        Returns:
            Dict with 'content' (expert analysis), 'usage'
        """
        logger.info("DxO Step 3: Domain Expert - Validating and adding expertise...")

        system_prompt = """You are a domain expert with deep specialized knowledge in the subject area.

Your responsibilities:
1. Validate the technical accuracy of the research findings
2. Add specialized knowledge and nuanced insights
3. Address the concerns raised by the critical reviewer
4. Provide expert perspective on the topic
5. Clarify technical details and terminology

Provide authoritative expert analysis (300-400 words) covering:
- Technical validation of key claims
- Specialized insights from your domain expertise
- Response to the critic's concerns
- Additional context or nuances
- Expert recommendations"""

        user_message = f"""Research Question: {question}

Lead Researcher's Findings:
{lead_findings['content']}

Critical Reviewer's Concerns:
{critique['content']}

Papers Reviewed:
{lead_findings['papers']}

As a domain expert, provide your specialized analysis and validation."""

        result = await self.bedrock_client.invoke_async(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.6,
            max_tokens=1500
        )

        logger.info("Domain expert analysis complete")
        return {
            'role': 'Domain Expert',
            'step': 'Expert Validation',
            'content': result['content'],
            'usage': result.get('usage', {})
        }

    async def lead_researcher_synthesis(
        self,
        question: str,
        lead_findings: Dict[str, Any],
        critique: Dict[str, Any],
        expert_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Role 4: Lead Researcher synthesizes final comprehensive report.

        Args:
            question: Original research question
            lead_findings: Initial findings
            critique: Critical review
            expert_analysis: Domain expert analysis

        Returns:
            Dict with 'content' (final report), 'usage'
        """
        logger.info("DxO Step 4: Lead Researcher - Final synthesis...")

        system_prompt = """You are the lead researcher producing the final comprehensive research report.

Your responsibilities:
1. Integrate all feedback from the critical reviewer and domain expert
2. Address identified gaps and weaknesses
3. Incorporate specialized insights
4. Resolve contradictions and refine conclusions
5. Produce a balanced, authoritative final report

Provide a comprehensive final report (500-700 words) with this structure:

## Research Summary
[Brief overview of the question and approach]

## Key Findings
[Main discoveries and insights, incorporating all feedback]

## Critical Considerations
[Addressing the reviewer's concerns and limitations]

## Expert Insights
[Integrating domain expert's specialized knowledge]

## Conclusions
[Final balanced conclusions with citations to arXiv papers where relevant]

## References
[List key arXiv papers referenced]"""

        user_message = f"""Research Question: {question}

=== INITIAL FINDINGS ===
{lead_findings['content']}

=== CRITICAL REVIEW ===
{critique['content']}

=== DOMAIN EXPERT ANALYSIS ===
{expert_analysis['content']}

=== PAPERS REVIEWED ===
{lead_findings['papers']}

Synthesize all inputs into a comprehensive final research report."""

        result = await self.bedrock_client.invoke_async(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.6,
            max_tokens=3000
        )

        logger.info("Final synthesis complete")
        return {
            'role': 'Lead Researcher',
            'step': 'Final Synthesis',
            'content': result['content'],
            'usage': result.get('usage', {})
        }

    async def research(self, question: str) -> Dict[str, Any]:
        """
        Run complete DxO sequential research workflow.

        Args:
            question: User's research question

        Returns:
            Dict containing all steps' outputs
        """
        logger.info(f"Starting DxO research workflow on: {question[:100]}...")

        # Step 1: Lead Researcher - Initial research
        lead_initial = await self.lead_researcher_initial(question)

        # Step 2: Critical Reviewer - Challenge assumptions
        critique = await self.critical_reviewer(question, lead_initial)

        # Step 3: Domain Expert - Validate and add expertise
        expert = await self.domain_expert(question, lead_initial, critique)

        # Step 4: Lead Researcher - Final synthesis
        final_report = await self.lead_researcher_synthesis(
            question, lead_initial, critique, expert
        )

        logger.info("DxO research workflow complete")

        return {
            'question': question,
            'workflow': [
                lead_initial,
                critique,
                expert,
                final_report
            ],
            'metadata': {
                'papers_found': len(self._extract_paper_count(lead_initial['papers'])),
                'total_steps': 4
            }
        }

    def _extract_paper_count(self, papers_text: str) -> List[str]:
        """Extract paper count from formatted text."""
        import re
        papers = re.findall(r'Paper \d+:', papers_text)
        return papers


def create_dxo_agent(arxiv_max_results: int = 5) -> DxOAgent:
    """Factory function to create a DxO Agent."""
    return DxOAgent(arxiv_max_results=arxiv_max_results)


if __name__ == "__main__":
    # Test the agent
    import asyncio

    async def test():
        agent = create_dxo_agent()
        result = await agent.research("What are the latest advances in quantum error correction?")

        print("\n=== DXO RESEARCH WORKFLOW ===\n")
        for i, step in enumerate(result['workflow'], 1):
            print(f"\n{'='*60}")
            print(f"Step {i}: {step['role']} - {step['step']}")
            print('='*60)
            print(step['content'][:300] + "...\n")

        print("\n=== FINAL REPORT ===")
        print(result['workflow'][-1]['content'])

    asyncio.run(test())
