
import os
from pathlib import Path
from typing import List

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

from .data_models import RetrievedDocument
from config import Config

# Load environment variables
load_dotenv()


class RAGRetriever:
    
    def __init__(self, vectordb_path: str = "langchain_vectordb"):
        self.vectordb_path = Path(vectordb_path)
        
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
        """Load the existing vector store"""
        if not self.vectordb_path.exists():
            raise FileNotFoundError(f"Vector database not found at {self.vectordb_path}")
        
        return Chroma(
            persist_directory=str(self.vectordb_path),
            embedding_function=self.embeddings,
            collection_name="ifcopenshell_langchain_docs"
        )
    
    def retrieve_relevant_docs(self, query: str, k: int = 5) -> List[RetrievedDocument]:
        """Retrieve relevant documentation based on query"""
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            
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
            print(f"Error retrieving documents: {e}")
            return []
    
    def retrieve_with_filter(self, query: str, metadata_filter: dict, k: int = 5) -> List[RetrievedDocument]:
        """Retrieve documents with metadata filtering"""
        try:
            results = self.vector_store.similarity_search_with_score(
                query, 
                k=k,
                filter=metadata_filter
            )
            
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
            print(f"Error retrieving filtered documents: {e}")
            return []
    
    def get_similar_functions(self, function_description: str, k: int = 3) -> List[RetrievedDocument]:
        """Retrieve similar function implementations"""
        function_filter = {"chunk_type": "function"}
        return self.retrieve_with_filter(function_description, function_filter, k)
    
    def get_usage_examples(self, api_name: str, k: int = 3) -> List[RetrievedDocument]:
        """Retrieve usage examples for specific API"""
        query = f"{api_name} usage example implementation"
        return self.retrieve_relevant_docs(query, k)
    
    def health_check(self) -> bool:
        """Check if the vector store is accessible and working"""
        try:
            # Try a simple query
            test_results = self.vector_store.similarity_search("test", k=1)
            return len(test_results) > 0
        except Exception as e:
            print(f"Health check failed: {e}")
            return False