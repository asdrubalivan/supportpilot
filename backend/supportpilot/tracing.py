"""Agent traces in Langfuse. Off unless both variables are set, so evals and tests send nothing.

The SDK defaults to Langfuse Cloud without a base URL, and traces contain customer order data.
"""

import os

from langfuse import get_client
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor


def setup_tracing() -> None:
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_BASE_URL")):
        return
    get_client()
    LlamaIndexInstrumentor().instrument()
