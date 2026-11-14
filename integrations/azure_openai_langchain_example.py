"""Optional Azure OpenAI/LangChain adapter; not called in tests or local demo."""
import os
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate

def build_components():
    required = [
        "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_CHAT_DEPLOYMENT", "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError("Missing env vars: " + ", ".join(missing))
    llm = AzureChatOpenAI(
        azure_deployment=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"], api_version="2024-10-21"
    )
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"], api_version="2024-10-21"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer only from context. If context is insufficient, say so. Cite source IDs."),
        ("human", "Context: {context}\nQuestion: {question}")
    ])
    return llm, embeddings, prompt
