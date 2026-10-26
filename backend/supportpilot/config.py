import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICIES_DIR = REPO_ROOT / "data" / "policies"

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "supportpilot")
DB_USER = os.getenv("DB_USER", "supportpilot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "supportpilot")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
EMBED_DIM = 768
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen3:8b")

# LlamaIndex prefixes the table name with "data_", so the real table is data_policy_chunks.
POLICY_TABLE = "policy_chunks"

MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
MCP_URL = os.getenv("MCP_URL", f"http://127.0.0.1:{MCP_PORT}/mcp")
