from dotenv import load_dotenv

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Load env vars (safe even if empty)
load_dotenv()

CHROMA_DIR = "db"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_rag_chain():
    print("Initializing RAG...")

    # 1️⃣ Embeddings (must match ingest.py)
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL
    )

    # 2️⃣ Load existing Chroma DB
    vectordb = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings
    )

    retriever = vectordb.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 8,
            "fetch_k": 20,
            "lambda_mult": 0.7
        }
    )

    # 3️⃣ Local LLM (Ollama)
    llm = ChatOllama(
        model="llama3",
        temperature=0
    )

    # 4️⃣ Prompt
    prompt = PromptTemplate(
        template="""
You are an environmental sustainability expert.

Use ONLY the following context to answer the question.
If exact data is missing, infer carefully using related information
and clearly state assumptions.

Context:
{context}

Question:
{question}

Answer in a structured, factual manner.
""",
        input_variables=["context", "question"]
    )

    # 5️⃣ LCEL RAG chain
    rag_chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    print("RAG chain ready.")
    return rag_chain


if __name__ == "__main__":
    rag = get_rag_chain()

    question = "How does daily car commuting affect carbon emissions in India?"
    answer = rag.invoke(question)

    print("\nAnswer:\n")
    print(answer)