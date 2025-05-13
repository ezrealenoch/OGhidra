"""
Vector store implementation for the CAG system.
"""

import logging
import os
import json
from typing import List, Dict, Any, Optional
import numpy as np

logger = logging.getLogger("ollama-ghidra-bridge.cag.vector_store")

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.warning("sentence_transformers not available, vector search will be disabled")
    EMBEDDINGS_AVAILABLE = False

class SimpleVectorStore:
    """Simple vector store implementation for document search."""
    
    def __init__(self, documents: List[Dict[str, Any]], embeddings: List[np.ndarray]):
        """
        Initialize the vector store.
        
        Args:
            documents: List of document dictionaries
            embeddings: List of document embeddings
        """
        self.documents = documents
        self.embeddings = embeddings
        
        # For compatibility with older code
        self.function_signatures = []
        self.binary_patterns = []
        self.analysis_rules = []
        self.common_workflows = []
        
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search the vector store for documents similar to the query.
        
        Args:
            query: The search query
            top_k: Number of top results to return
            
        Returns:
            List of document dictionaries with similarity scores
        """
        if not EMBEDDINGS_AVAILABLE:
            logger.warning("Embeddings not available, returning random documents")
            import random
            indices = random.sample(range(len(self.documents)), min(top_k, len(self.documents)))
            return [{"document": self.documents[i], "score": 0.5} for i in indices]
            
        # Load model for query embedding
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = model.encode(query)
        
        # Calculate cosine similarity
        similarities = []
        for doc_embedding in self.embeddings:
            similarity = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
            )
            similarities.append(similarity)
            
        # Get top-k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Return top-k documents with scores
        results = []
        for idx in top_indices:
            results.append({
                "document": self.documents[idx],
                "score": float(similarities[idx])
            })
            
        return results

    def get_relevant_knowledge(self, query: str, token_limit: int = 2000) -> str:
        """
        Get relevant knowledge for a query.
        
        Args:
            query: The query string
            token_limit: Maximum number of tokens to return
            
        Returns:
            Relevant knowledge as a string
        """
        results = self.search(query, top_k=3)
        
        if not results:
            return ""
            
        # Combine results into a single string, respecting token limit
        # Rough estimate: 4 chars = 1 token
        char_limit = token_limit * 4
        relevant_docs = []
        
        total_chars = 0
        for result in results:
            doc = result["document"]
            doc_text = doc["text"]
            doc_type = doc["type"]
            doc_name = doc.get("name", "Unnamed")
            
            # Add header for the document
            header = f"## {doc_type.upper()}: {doc_name}\n"
            
            # If adding this document would exceed the limit, skip it
            if total_chars + len(header) + len(doc_text) > char_limit:
                if not relevant_docs:  # If no docs added yet, add a truncated version
                    truncated_text = doc_text[:char_limit - len(header) - 3] + "..."
                    relevant_docs.append(f"{header}\n{truncated_text}")
                break
                
            relevant_docs.append(f"{header}\n{doc_text}")
            total_chars += len(header) + len(doc_text)
            
        return "\n\n".join(relevant_docs)

def create_vector_store_from_docs(documents: List[Dict[str, Any]]) -> Optional[SimpleVectorStore]:
    """
    Create a vector store from documents.
    
    Args:
        documents: List of document dictionaries
        
    Returns:
        SimpleVectorStore instance or None if embeddings not available
    """
    if not EMBEDDINGS_AVAILABLE:
        logger.warning("sentence_transformers not available, vector store will have limited functionality")
        return SimpleVectorStore(documents, [])
        
    try:
        # Load embedding model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Create embeddings
        texts = [doc["text"] for doc in documents]
        embeddings = model.encode(texts)
        
        # Create vector store
        return SimpleVectorStore(documents, embeddings)
    except Exception as e:
        logger.error(f"Error creating vector store: {str(e)}")
        return None 