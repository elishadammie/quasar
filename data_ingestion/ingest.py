# data_ingestion/ingest.py (Self-Contained Version)

import os
import httpx
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

from langchain_community.vectorstores.pgvector import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_unstructured import UnstructuredLoader
from langchain_openai import OpenAIEmbeddings

# --- 1. SETTINGS AND CONFIGURATION  ---

class Settings(BaseSettings):
    """Loads and validates application settings from a .env file."""
    OPENAI_API_KEY: str
    DATABASE_URL: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Create a single, reusable instance of the settings
settings = Settings()

# --- 2. SSL FIX AND CLIENT SETUP ---

# Create a custom httpx client that disables SSL certificate verification for OPENAI connection
insecure_client = httpx.Client(verify=False)

# Initialize the OpenAI embeddings model with our fix
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large", 
    openai_api_key=settings.OPENAI_API_KEY,
    http_client=insecure_client
)

# Database connection details
DB_URL = settings.DATABASE_URL
COLLECTION_NAME = "quasar_doc_collection"


# --- 3. INGESTION PIPELINE FUNCTIONS ---

def load_document(file_path: str) -> List:
    """Loads a single document using the new UnstructuredLoader."""
    print(f"Loading document: {file_path}")
    loader = UnstructuredLoader(file_path, mode="single", strategy="fast")
    return loader.load()

def chunk_documents(documents: List) -> List:
    """Splits documents into smaller chunks."""
    print("Chunking documents...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    docs = text_splitter.split_documents(documents)
    print(f"Successfully chunked into {len(docs)} documents.")
    return docs

def embed_and_store(chunks: List, collection_name: str):
    """Embeds chunks and stores them in the PGVector database."""
    print(f"Embedding and storing {len(chunks)} chunks into collection '{collection_name}'...")

    PGVector.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        connection_string=DB_URL,
        pre_delete_collection=True,
    )
    
    print("Ingestion process complete. Data has been embedded and stored.")


def main():
    """Main function to run the ingestion pipeline."""
    sample_file_path = "documents/PhD Sys.pdf"
    
    if not os.path.exists(sample_file_path):
        print(f"Error: File not found at '{sample_file_path}'")
        return

    loaded_docs = load_document(sample_file_path)
    chunked_docs = chunk_documents(loaded_docs)
    embed_and_store(chunked_docs, COLLECTION_NAME)


if __name__ == "__main__":
    print("--- Starting Quasar Data Ingestion Pipeline ---")
    main()
    print("--- Ingestion Pipeline Finished ---")