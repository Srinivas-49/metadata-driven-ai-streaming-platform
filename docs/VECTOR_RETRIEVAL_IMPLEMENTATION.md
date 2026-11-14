# Tested embedding-vector retrieval and Azure OpenAI integration

The repo provides a deterministic lexical retrieval baseline plus a new **cosine-similarity vector retrieval engine** with pluggable embedding functions. Source-chunk IDs are preserved, scores can be thresholded for abstention, and query/document vector dimensions are validated.

The original four lexical-retrieval tests and four new vector tests pass locally (8 total). **New vector unit tests use mock embeddings; they do not verify the quality of Azure OpenAI semantic embeddings.**

Optional integration `integrations/azure_vector_rag.py` calls real Azure OpenAI embeddings and chat through `langchain-openai` when configured. Required environment variables: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`, and optional `AZURE_OPENAI_API_VERSION`. Do not commit secrets.

**No Azure deployment or live inference has been verified.** For production use, add tenant-aware document ACL enforcement, managed vector indexing, robust API authentication, ingestion monitoring, prompt injection defenses, more labelled retrieval evaluation, answer faithfulness checks, cost and latency budgets. Citations do not guarantee an LLM's statements are accurate.

Run: `python -m pytest -q`.
