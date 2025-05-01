from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import os

class RAG:
    def __init__(self, path_db):
        """Initialize RAG with FAISS vector database."""
        self.presistant_directory = path_db
        self.embedder = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")
        self.db = None
        self.load_db()

    def load_db(self):
        """Load FAISS vector database if available."""
        if os.path.exists(self.presistant_directory):
            self.db = FAISS.load_local(self.presistant_directory, self.embedder, allow_dangerous_deserialization=True)
        else:
            print(f"Warning: Database directory '{self.presistant_directory}' not found.")

    def check_rag_relevance(self, query):
        """
        Determines if the query is relevant to the RAG database by checking similarity.
        Returns True if relevant, False otherwise.
        """
        if not self.db:
            return False  # No database loaded

        retriever = self.db.as_retriever(search_type="similarity", search_kwargs={"k": 1})
        retrieved_docs = retriever.invoke(query)

        if not retrieved_docs:
            return False

        return True 

    def get_rag_response(self, query):
        """
        Retrieves relevant documents from the vector database.
        """
        if not self.db:
            return "Error: No vector database loaded."

        retriever = self.db.as_retriever(search_type="similarity", search_kwargs={"k": 6})
        retrieved_docs = retriever.invoke(query)

        if not retrieved_docs:
            return "Sorry, I couldn't find relevant information."

    # Store retrieved document content for use in LLM response generation
        self.retrieved_doc_content = " ".join([doc.page_content for doc in retrieved_docs])  
        return self.retrieved_doc_content
