"""Offline ingestion: policy markdown -> one chunk per heading -> embeddings -> pgvector.

Run with: uv run python -m supportpilot.ingest [--questions]

--questions enriches each chunk with LLM-generated customer questions (doc2query) before embedding.
"""

import re
import sys

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.extractors import QuestionsAnsweredExtractor
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.schema import MetadataMode, TextNode
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from supportpilot import config

# Only these metadata keys are prepended to the chunk text before embedding.
CONTEXT_KEYS = ["document", "section"]
QUESTIONS_KEY = "questions_this_excerpt_can_answer"

QUESTIONS_PROMPT = """Here is a section of a bookstore's policy:
{context_str}

Write {num_questions} short questions that a customer might ask, in everyday words, which this section answers.
Use different wording from the section where a customer naturally would. Output only the questions, one per line."""

# Explicit anchor at the end of a heading: "## Refunds <!-- id: refunds -->".
# Chunk IDs come from anchors, not titles, so renaming a heading doesn't break golden cases.
ANCHOR_RE = re.compile(r"\s*<!--\s*id:\s*([a-z0-9-]+)\s*-->\s*$")


def parse_heading(line: str) -> tuple[str, str | None]:
    """Return (title without '#' and anchor, anchor id or None)."""
    match = ANCHOR_RE.search(line)
    title = ANCHOR_RE.sub("", line).lstrip("#").strip()
    return title, match.group(1) if match else None


def get_embed_model() -> OllamaEmbedding:
    # nomic-embed-text was trained with these task prefixes; queries and documents get different ones.
    return OllamaEmbedding(
        model_name=config.EMBED_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        query_instruction="search_query: ",
        text_instruction="search_document: ",
    )


def get_vector_store() -> PGVectorStore:
    return PGVectorStore.from_params(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        table_name=config.POLICY_TABLE,
        embed_dim=config.EMBED_DIM,
        # Adds a full-text column so hybrid retrieval stays an option without re-ingesting.
        hybrid_search=True,
        text_search_config="english",
    )


def load_documents() -> list[Document]:
    documents = []
    for path in sorted(config.POLICIES_DIR.glob("*.md")):
        text = path.read_text()
        title, _ = parse_heading(text.splitlines()[0])
        documents.append(
            Document(text=text, id_=path.name, metadata={"source": path.name, "document": title})
        )
    return documents


def build_chunks(documents: list[Document]) -> list[TextNode]:
    chunks = []
    for node in MarkdownNodeParser().get_nodes_from_documents(documents):
        heading, _, body = node.text.partition("\n")
        if not body.strip():
            continue  # A title with no text under it (e.g. the H1 of returns.md) has nothing to retrieve.

        title, anchor = parse_heading(heading)
        source = node.metadata["source"]
        if anchor is None:
            raise ValueError(f"{source}: heading '{title}' has no '<!-- id: ... -->' anchor")

        is_top_level = heading.startswith("# ")
        node.metadata["section"] = "Overview" if is_top_level else title
        node.id_ = f"{source}#{anchor}"
        # Keep the anchor out of the embedded and full-text-indexed text.
        node.text = f"{heading.split(' ')[0]} {title}\n{body}"

        node.excluded_embed_metadata_keys = [k for k in node.metadata if k not in CONTEXT_KEYS]
        node.excluded_llm_metadata_keys = [k for k in node.metadata if k not in CONTEXT_KEYS]
        chunks.append(node)

    ids = [chunk.id_ for chunk in chunks]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"Duplicate chunk IDs: {sorted(duplicates)}")
    return chunks


def add_questions(chunks: list[TextNode]) -> None:
    """doc2query: embed the questions a chunk answers, so customer phrasing matches policy phrasing.

    The questions are embedded but hidden from the answering LLM, which only sees the policy text.
    """
    # Imported here so plain ingestion doesn't need the chat model.
    from supportpilot.agent import get_llm

    extractor = QuestionsAnsweredExtractor(llm=get_llm(), questions=3, prompt_template=QUESTIONS_PROMPT)
    for chunk, metadata in zip(chunks, extractor.extract(chunks)):
        # build_chunks set the exclusion lists before this key existed, so it's already embedded;
        # only hide it from the answering LLM.
        chunk.metadata[QUESTIONS_KEY] = metadata[QUESTIONS_KEY]
        chunk.excluded_llm_metadata_keys.append(QUESTIONS_KEY)


def main() -> None:
    chunks = build_chunks(load_documents())
    if "--questions" in sys.argv:
        add_questions(chunks)

    vector_store = get_vector_store()
    vector_store.clear()
    VectorStoreIndex(
        chunks,
        storage_context=StorageContext.from_defaults(vector_store=vector_store),
        embed_model=get_embed_model(),
    )

    for chunk in chunks:
        print(f"--- {chunk.id_}")
        print(chunk.get_content(metadata_mode=MetadataMode.EMBED))
    print(f"\nIngested {len(chunks)} chunks into data_{config.POLICY_TABLE}.")


if __name__ == "__main__":
    main()
