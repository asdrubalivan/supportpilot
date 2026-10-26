"""Retrieval over policy chunks: vector search by default; hybrid (vector + full-text, fused with
Reciprocal Rank Fusion) is kept for comparison in evals.

Try it with: uv run python -m supportpilot.retrieval "Can I get my money back?"
"""

import sys
from dataclasses import dataclass

from llama_index.core import VectorStoreIndex
from llama_index.core.llms import MockLLM
from llama_index.core.retrievers import BaseRetriever, QueryFusionRetriever

from supportpilot.ingest import get_embed_model, get_vector_store

DEFAULT_K = 4
# Vector beat or matched hybrid in evals once chunks were enriched with questions: full-text added
# noise from common words ("get", "buy") and doesn't see the generated questions. Hybrid stays for evals.
DEFAULT_MODE = "vector"
# Each retriever returns this many candidates before fusion.
CANDIDATES_PER_RETRIEVER = 8


@dataclass
class PolicyChunk:
    id: str
    document: str
    section: str
    text: str
    score: float


def build_retriever(k: int = DEFAULT_K, mode: str = DEFAULT_MODE) -> BaseRetriever:
    """mode="vector" is vector search only; mode="hybrid" fuses vector + full-text with RRF."""
    index = VectorStoreIndex.from_vector_store(get_vector_store(), embed_model=get_embed_model())
    if mode == "vector":
        return index.as_retriever(vector_store_query_mode="default", similarity_top_k=k)

    vector_retriever = index.as_retriever(
        vector_store_query_mode="default", similarity_top_k=CANDIDATES_PER_RETRIEVER
    )
    text_retriever = index.as_retriever(
        vector_store_query_mode="sparse",
        similarity_top_k=CANDIDATES_PER_RETRIEVER,
        sparse_top_k=CANDIDATES_PER_RETRIEVER,
    )
    return QueryFusionRetriever(
        [vector_retriever, text_retriever],
        mode="reciprocal_rerank",
        similarity_top_k=k,
        # num_queries=1 disables LLM query rewriting; MockLLM keeps LlamaIndex from defaulting to OpenAI.
        num_queries=1,
        llm=MockLLM(),
        use_async=False,
    )


def search_policies(query: str, k: int = DEFAULT_K) -> list[PolicyChunk]:
    results = build_retriever(k).retrieve(query)
    return [
        PolicyChunk(
            id=r.node.node_id,
            document=r.node.metadata["document"],
            section=r.node.metadata["section"],
            text=r.node.get_content(),
            score=r.score or 0.0,
        )
        for r in results
    ]


if __name__ == "__main__":
    for chunk in search_policies(" ".join(sys.argv[1:])):
        print(f"{chunk.score:.4f}  {chunk.id}")
