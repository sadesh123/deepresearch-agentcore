"""
LLM Council Agent - 3-stage deliberation system.

Stage 1: Parallel responses from multiple models
Stage 2: Anonymized peer review and ranking
Stage 3: Chairman synthesis
"""

import asyncio
import logging
from typing import Dict, List, Any, Tuple
import re
from .bedrock_client import create_bedrock_client

logger = logging.getLogger(__name__)


class CouncilAgent:
    """
    LLM Council orchestrator implementing 3-stage deliberation.
    """

    def __init__(self, num_council_members: int = 3):
        """
        Initialize Council Agent.

        Args:
            num_council_members: Number of council members (default 3)
        """
        self.num_members = num_council_members
        self.bedrock_client = create_bedrock_client()
        logger.info(f"Initialized Council Agent with {num_council_members} members")

    async def stage1_collect_responses(self, question: str) -> List[Dict[str, str]]:
        """
        Stage 1: Collect parallel responses from council members.

        Args:
            question: User's research question

        Returns:
            List of responses with 'member_id' and 'content'
        """
        logger.info(f"Stage 1: Collecting responses for question: {question[:100]}...")

        system_prompt = """You are a knowledgeable AI assistant and member of a research council.
Provide a thoughtful, well-reasoned response to the user's question.
Be analytical and consider multiple perspectives.
Keep your response concise but comprehensive (300-500 words)."""

        # Create tasks for parallel execution
        tasks = []
        for i in range(self.num_members):
            tasks.append(
                self.bedrock_client.invoke_async(
                    system_prompt=system_prompt,
                    user_message=question,
                    temperature=0.7 + (i * 0.1)  # Slight variation per member
                )
            )

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Council member {i+1} failed: {str(result)}")
                continue

            responses.append({
                'member_id': f"Member {i+1}",
                'content': result['content'],
                'usage': result.get('usage', {})
            })

        logger.info(f"Stage 1 complete: {len(responses)} responses collected")
        return responses

    def _anonymize_responses(self, responses: List[Dict[str, str]]) -> Tuple[str, Dict[str, str]]:
        """
        Anonymize responses as Response A, B, C, etc.

        Args:
            responses: List of responses with member_id

        Returns:
            Tuple of (anonymized_text, label_to_member_mapping)
        """
        labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        label_map = {}
        anonymized = []

        for i, response in enumerate(responses[:len(labels)]):
            label = f"Response {labels[i]}"
            label_map[label] = response['member_id']

            anonymized.append(f"""
{label}:
{response['content']}
""")

        return "\n---\n".join(anonymized), label_map

    def _parse_ranking_from_text(self, text: str) -> List[str]:
        """
        Extract ranking from model response.

        Expected format:
        FINAL RANKING:
        1. Response C
        2. Response A
        3. Response B

        Args:
            text: Raw model response

        Returns:
            List of response labels in ranked order
        """
        # Look for FINAL RANKING section
        ranking_match = re.search(r'FINAL RANKING:?\s*\n(.*?)(?:\n\n|\Z)', text, re.DOTALL | re.IGNORECASE)

        if ranking_match:
            ranking_text = ranking_match.group(1)
        else:
            ranking_text = text

        # Extract "Response X" patterns
        responses = re.findall(r'Response\s+([A-H])', ranking_text, re.IGNORECASE)

        # Remove duplicates while preserving order
        seen = set()
        unique_responses = []
        for r in responses:
            r_upper = r.upper()
            if r_upper not in seen:
                seen.add(r_upper)
                unique_responses.append(f"Response {r_upper}")

        return unique_responses

    async def stage2_collect_rankings(
        self,
        question: str,
        responses: List[Dict[str, str]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        Stage 2: Collect anonymized peer review rankings.

        Args:
            question: Original question
            responses: Stage 1 responses

        Returns:
            Tuple of (rankings_list, label_to_member_mapping)
        """
        logger.info("Stage 2: Collecting peer review rankings...")

        # Anonymize responses
        anonymized_text, label_map = self._anonymize_responses(responses)

        system_prompt = """You are an expert evaluator in a research council.
Evaluate the quality of each response based on:
- Accuracy and correctness
- Depth of insight
- Clarity of explanation
- Consideration of multiple perspectives

Provide your evaluation in this EXACT format:

[Brief evaluation of each response]

FINAL RANKING:
1. Response [Letter]
2. Response [Letter]
3. Response [Letter]

Be objective and rank based solely on quality."""

        user_message = f"""Question: {question}

Here are the responses to evaluate:

{anonymized_text}

Provide your evaluation and ranking."""

        # Get rankings from each member
        tasks = []
        for i in range(self.num_members):
            tasks.append(
                self.bedrock_client.invoke_async(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    temperature=0.5
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process rankings
        rankings = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Ranking from member {i+1} failed: {str(result)}")
                continue

            raw_text = result['content']
            parsed_ranking = self._parse_ranking_from_text(raw_text)

            rankings.append({
                'member_id': f"Member {i+1}",
                'raw_text': raw_text,
                'parsed_ranking': parsed_ranking,
                'usage': result.get('usage', {})
            })

        logger.info(f"Stage 2 complete: {len(rankings)} rankings collected")
        return rankings, label_map

    def _calculate_aggregate_rankings(
        self,
        rankings: List[Dict[str, Any]],
        label_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Calculate aggregate rankings from peer reviews.

        Args:
            rankings: List of ranking dictionaries
            label_map: Mapping from Response labels to member IDs

        Returns:
            List of aggregate rankings sorted by average position
        """
        # Count positions for each response
        position_sums = {}
        vote_counts = {}

        for ranking_data in rankings:
            parsed = ranking_data['parsed_ranking']
            for position, response_label in enumerate(parsed, start=1):
                if response_label not in position_sums:
                    position_sums[response_label] = 0
                    vote_counts[response_label] = 0

                position_sums[response_label] += position
                vote_counts[response_label] += 1

        # Calculate averages
        aggregate = []
        for response_label, total_pos in position_sums.items():
            count = vote_counts[response_label]
            avg_position = total_pos / count if count > 0 else 999

            aggregate.append({
                'response_label': response_label,
                'member_id': label_map.get(response_label, 'Unknown'),
                'average_position': avg_position,
                'vote_count': count
            })

        # Sort by average position (lower is better)
        aggregate.sort(key=lambda x: x['average_position'])

        return aggregate

    async def stage3_synthesize_final(
        self,
        question: str,
        stage1_responses: List[Dict[str, str]],
        stage2_rankings: List[Dict[str, Any]],
        aggregate_rankings: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Stage 3: Chairman synthesizes final answer.

        Args:
            question: Original question
            stage1_responses: All stage 1 responses
            stage2_rankings: All stage 2 rankings
            aggregate_rankings: Calculated aggregate rankings

        Returns:
            Dict with 'content' (final answer)
        """
        logger.info("Stage 3: Chairman synthesizing final answer...")

        # Prepare context
        responses_text = "\n\n---\n\n".join([
            f"{r['member_id']}: {r['content']}"
            for r in stage1_responses
        ])

        rankings_summary = "\n".join([
            f"{i+1}. {r['member_id']} (avg rank: {r['average_position']:.2f})"
            for i, r in enumerate(aggregate_rankings)
        ])

        system_prompt = """You are the chairman of a research council.
Synthesize a comprehensive final answer by:
1. Considering all council members' responses
2. Weighing inputs based on peer review rankings
3. Integrating the strongest points from each perspective
4. Resolving any contradictions
5. Providing a balanced, authoritative conclusion

Produce a clear, well-structured final answer (400-600 words)."""

        user_message = f"""Question: {question}

Council Members' Responses:
{responses_text}

Peer Review Rankings (by quality):
{rankings_summary}

Synthesize a comprehensive final answer that represents the council's collective wisdom."""

        result = await self.bedrock_client.invoke_async(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.6,
            max_tokens=2000
        )

        logger.info("Stage 3 complete: Final synthesis generated")
        return {
            'content': result['content'],
            'usage': result.get('usage', {})
        }

    async def deliberate(self, question: str) -> Dict[str, Any]:
        """
        Run complete 3-stage council deliberation.

        Args:
            question: User's research question

        Returns:
            Dict containing all stages' outputs and metadata
        """
        logger.info(f"Starting council deliberation on: {question[:100]}...")

        # Stage 1: Collect responses
        stage1_responses = await self.stage1_collect_responses(question)

        if not stage1_responses:
            raise Exception("No responses collected in Stage 1")

        # Stage 2: Collect rankings
        stage2_rankings, label_map = await self.stage2_collect_rankings(question, stage1_responses)

        if not stage2_rankings:
            raise Exception("No rankings collected in Stage 2")

        # Calculate aggregate rankings
        aggregate_rankings = self._calculate_aggregate_rankings(stage2_rankings, label_map)

        # Stage 3: Synthesize final answer
        stage3_result = await self.stage3_synthesize_final(
            question,
            stage1_responses,
            stage2_rankings,
            aggregate_rankings
        )

        return {
            'question': question,
            'stage1': stage1_responses,
            'stage2': stage2_rankings,
            'stage3': stage3_result,
            'metadata': {
                'label_to_member': label_map,
                'aggregate_rankings': aggregate_rankings
            }
        }


def create_council_agent(num_members: int = 3) -> CouncilAgent:
    """Factory function to create a Council Agent."""
    return CouncilAgent(num_council_members=num_members)


if __name__ == "__main__":
    # Test the agent
    async def test():
        agent = create_council_agent(num_members=3)
        result = await agent.deliberate("What are the key challenges in quantum computing?")

        print("\n=== STAGE 1: Council Responses ===")
        for r in result['stage1']:
            print(f"\n{r['member_id']}:")
            print(r['content'][:200] + "...")

        print("\n=== STAGE 2: Rankings ===")
        for r in result['stage2']:
            print(f"\n{r['member_id']} ranking: {r['parsed_ranking']}")

        print("\n=== STAGE 3: Final Answer ===")
        print(result['stage3']['content'])

    asyncio.run(test())
