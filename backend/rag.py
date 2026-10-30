from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


ROOT = Path(__file__).resolve().parents[1]
FAQ_PATH = ROOT / "knowledge_base" / "faq.md"

load_dotenv(ROOT / ".env")


@lru_cache(maxsize=1)
def get_vector_store():
    if not FAQ_PATH.exists():
        raise RuntimeError("FAQ knowledge-base file was not found.")

    faq_text = FAQ_PATH.read_text(encoding="utf-8")

    if not faq_text.strip():
        raise RuntimeError("The FAQ knowledge base is empty.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
    )

    chunks = splitter.split_text(faq_text)

    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2"
    )

    vector_store = InMemoryVectorStore(
        embedding=embeddings
    )

    # Create all documents first
    documents = [
        Document(
            page_content=f"title: Support FAQ | text: {chunk}",
            metadata={
                "source": "knowledge_base/faq.md",
                "chunk": index,
            },
        )
        for index, chunk in enumerate(chunks, start=1)
    ]

    # Embed all documents in one batch instead of one request per chunk
    if documents:
        vector_store.add_documents(documents=documents)

    return vector_store


def retrieve_faq(query: str, k: int = 3) -> list[Document]:
    vector_store = get_vector_store()

    formatted_query = (
        f"task: question answering | query: {query}"
    )

    return vector_store.similarity_search(
        query=formatted_query,
        k=k,
    )