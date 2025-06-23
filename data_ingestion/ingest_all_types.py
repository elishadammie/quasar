# data_ingestion/ingest.py (Enhanced Ingestion Pipeline with Multi-Format & Archive Support)

import os
import zipfile
from typing import List
import httpx # type: ignore

from langchain_community.vectorstores.pgvector import PGVector # type: ignore
from langchain_text_splitters import RecursiveCharacterTextSplitter # type: ignore
from langchain_unstructured import UnstructuredLoader # type: ignore
from langchain_openai import OpenAIEmbeddings # type: ignore

from app.core.config import settings

# --- GLOBAL CONFIG ---
DOCUMENTS_DIR = "documents"
TEMP_EXTRACT_DIR = os.path.join(DOCUMENTS_DIR, "_extracted")
COLLECTION_NAME = "quasar_doc_collection"

# --- SSL FIX FOR CORPORATE PROXY ---
insecure_client = httpx.Client(verify=False)  # ⚠️ Use only in development

# --- EMBEDDINGS SETUP ---
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    openai_api_key=settings.OPENAI_API_KEY,
    http_client=insecure_client,
)

# --- DATABASE SETUP ---
DB_URL = settings.DATABASE_URL

# --- CORE INGESTION FUNCTIONS ---

def extract_zip(file_path: str, extract_to: str = TEMP_EXTRACT_DIR) -> List[str]:
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
        return [os.path.join(extract_to, f) for f in zip_ref.namelist() if os.path.isfile(os.path.join(extract_to, f))]

def load_document(file_path: str) -> List:
    print(f"Loading document: {file_path}")
    loader = UnstructuredLoader(file_path, mode="single", strategy="fast")
    return loader.load()

def chunk_documents(documents: List) -> List:
    print("Chunking documents...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(documents)
    print(f"Successfully chunked into {len(chunks)} documents.")
    return chunks

def embed_and_store(chunks: List, collection_name: str):
    print(f"Embedding and storing {len(chunks)} chunks into collection '{collection_name}'...")
    PGVector.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=collection_name,
        connection_string=DB_URL,
        pre_delete_collection=True,
    )
    print("Ingestion complete. Documents embedded and stored.")

# --- MAIN PIPELINE ENTRY ---

def main():
    print(f"--- Starting Quasar Data Ingestion Pipeline for directory: {DOCUMENTS_DIR} ---")

    if not os.path.exists(DOCUMENTS_DIR):
        print(f"Directory '{DOCUMENTS_DIR}' does not exist.")
        return

    all_chunks = []

    for filename in os.listdir(DOCUMENTS_DIR):
        file_path = os.path.join(DOCUMENTS_DIR, filename)

        if os.path.isfile(file_path):
            try:
                # If it's a zip file, extract and parse contents
                if filename.endswith(".zip"):
                    extracted_files = extract_zip(file_path)
                    for subfile in extracted_files:
                        try:
                            docs = load_document(subfile)
                            chunks = chunk_documents(docs)
                            all_chunks.extend(chunks)
                        except Exception as inner_e:
                            print(f"Failed to process extracted file: {subfile}\nError: {inner_e}")
                else:
                    docs = load_document(file_path)
                    chunks = chunk_documents(docs)
                    all_chunks.extend(chunks)

                print(f"Processed: {filename}")

            except Exception as e:
                print(f"Failed to process file: {filename}\nError: {e}")

        print("-" * 40)

    if all_chunks:
        embed_and_store(all_chunks, COLLECTION_NAME)
    else:
        print("No valid documents found to process.")

    print("--- Ingestion Pipeline Finished ---")

if __name__ == "__main__":
    main()
# This script is designed to ingest various document types, including PDFs and ZIP archives,