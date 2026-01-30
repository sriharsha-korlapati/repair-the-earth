from rag import get_rag_chain

qa = get_rag_chain()
query = "carbon impact of mobile phones"
result = qa.run(query)
print(result)
