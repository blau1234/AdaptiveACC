import os
from pathlib import Path
from typing import List

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

from data_models.shared_models import RetrievedDocument
from config import Config

# Load environment variables
load_dotenv()


class DocumentRetriever:
    """Specialized retriever for document operations only"""
    
    def __init__(self, vectordb_path: str = "vectordb/docs", collection_name: str = "ifcopenshell_langchain_docs"):
        self.vectordb_path = Path(vectordb_path)
        self.collection_name = collection_name
        
        # Use dedicated embedding API configuration
        embedding_kwargs = {
            "model": Config.EMBEDDING_MODEL_NAME,
            "openai_api_key": Config.EMBEDDING_API_KEY,
            "dimensions": 1536
        }
        
        # Add base URL if specified for embedding API
        if Config.EMBEDDING_API_BASE:
            embedding_kwargs["openai_api_base"] = Config.EMBEDDING_API_BASE
            
        self.embeddings = OpenAIEmbeddings(**embedding_kwargs)
        self.vector_store = self._load_vector_store()
    
    def _load_vector_store(self) -> Chroma:
        """Load the existing document vector store"""
        if not self.vectordb_path.exists():
            raise FileNotFoundError(f"Document vector database not found at {self.vectordb_path}")
        
        return Chroma(
            persist_directory=str(self.vectordb_path),
            embedding_function=self.embeddings,
            collection_name=self.collection_name
        )
    
    def retrieve_relevant_docs(self, query: str, k: int = 5, metadata_filter: dict = None) -> List[RetrievedDocument]:
        """
        Retrieve relevant documentation based on query
        
        Args:
            query: Search query
            k: Number of documents to return
            metadata_filter: Optional metadata filter
            
        Returns:
            List of RetrievedDocument objects
        """
        try:
            # Execute vector search directly
            if metadata_filter:
                results = self.vector_store.similarity_search_with_score(
                    query, k=k, filter=metadata_filter
                )
            else:
                results = self.vector_store.similarity_search_with_score(query, k=k)
            
            # Process results into RetrievedDocument objects
            retrieved_docs = []
            for doc, score in results:
                retrieved_doc = RetrievedDocument(
                    content=doc.page_content,
                    metadata=doc.metadata,
                    relevance_score=score
                )
                retrieved_docs.append(retrieved_doc)
            
            return retrieved_docs
            
        except Exception as e:
            print(f"Document vector search error: {e}")
            return []