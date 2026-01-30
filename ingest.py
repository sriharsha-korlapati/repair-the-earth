import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

DATA_DIR = "data"
CHROMA_DIR = "db"

def load_all_pdfs(base_dir):
    documents = []

    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_path = os.path.join(root, file)
                print(f"Loading PDF: {pdf_path}")

                loader = PyPDFLoader(pdf_path)
                docs = loader.load()

                # add folder name as metadata
                category = os.path.basename(root)
                for d in docs:
                    d.metadata["category"] = category
                    d.metadata["source"] = pdf_path

                documents.extend(docs)

    return documents


def ingest():
    print("Starting ingestion...")

    docs = load_all_pdfs(DATA_DIR)

    if not docs:
        raise RuntimeError("No documents loaded. Check PDF parsing.")

    print(f"Loaded {len(docs)} pages")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )

    chunks = splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectordb = Chroma(
    persist_directory=CHROMA_DIR,
    embedding_function=embeddings
    )

    print("Ingestion complete. Vectors saved.")


if __name__ == "__main__":
    ingest()
