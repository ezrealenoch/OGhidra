"""
Vector storage for session records to enable RAG capabilities.
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging

from .memory_models import SessionRecord

logger = logging.getLogger(__name__)

# This is a simplified vector store implementation.
# In a real implementation, you would use a proper vector database.
class SimpleVectorStore:
    """
    A simple vector store for session records using local files.
    In a production environment, consider using a proper vector database like FAISS, Chroma, or Milvus.
    """
    def __init__(self, storage_dir: str = "data/vector_db"):
        self.storage_dir = storage_dir
        self.vectors_file = os.path.join(storage_dir, "vectors.npy")
        self.metadata_file = os.path.join(storage_dir, "metadata.json")
        self.vectors = None
        self.metadata = []
        
        # Create the storage directory if it doesn't exist
        os.makedirs(storage_dir, exist_ok=True)
        
        self._load()
    
    def _load(self):
        """Load vectors and metadata from disk."""
        try:
            if os.path.exists(self.vectors_file) and os.path.exists(self.metadata_file):
                self.vectors = np.load(self.vectors_file)
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded {len(self.metadata)} vectors from disk.")
            else:
                self.vectors = np.zeros((0, 0))  # Empty array, dimension will be set on first add
                self.metadata = []
                logger.info("No existing vector storage found. Starting with empty storage.")
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            self.vectors = np.zeros((0, 0))
            self.metadata = []
    
    def _save(self):
        """Save vectors and metadata to disk."""
        try:
            if self.vectors is not None and len(self.metadata) > 0:
                np.save(self.vectors_file, self.vectors)
                with open(self.metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(self.metadata, f)
                logger.info(f"Saved {len(self.metadata)} vectors to disk.")
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
    
    def add_session(self, session: SessionRecord, embedding: np.ndarray):
        """
        Add a session record to the vector store.
        
        Args:
            session: The session record to add.
            embedding: The embedding vector for the session.
        """
        # Initialize vectors array with correct dimensions if this is the first vector
        if self.vectors.shape[0] == 0:
            self.vectors = np.zeros((0, embedding.shape[0]))
        
        # Ensure the embedding has the right shape
        if self.vectors.shape[1] != embedding.shape[0]:
            logger.error(f"Embedding dimension mismatch: expected {self.vectors.shape[1]}, got {embedding.shape[0]}")
            return
        
        # Add the embedding and metadata
        self.vectors = np.vstack((self.vectors, embedding))
        
        # Store essential metadata for retrieval
        metadata = {
            "session_id": session.session_id,
            "user_task": session.user_task_description,
            "outcome": session.outcome,
            "timestamp": session.start_time.isoformat(),
            "tool_count": len(session.tool_calls),
            "summary": session.session_summary
        }
        self.metadata.append(metadata)
        
        # Save to disk
        self._save()
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar sessions based on embedding similarity.
        
        Args:
            query_embedding: The embedding vector to search for.
            top_k: The number of results to return.
            
        Returns:
            A list of metadata for the most similar sessions.
        """
        if self.vectors.shape[0] == 0:
            return []
        
        # Ensure the query embedding has the right shape
        if self.vectors.shape[1] != query_embedding.shape[0]:
            logger.error(f"Query embedding dimension mismatch: expected {self.vectors.shape[1]}, got {query_embedding.shape[0]}")
            return []
        
        # Compute cosine similarity
        similarities = np.dot(self.vectors, query_embedding) / (
            np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Return metadata for top-k results
        results = []
        for idx in top_indices:
            result = self.metadata[idx].copy()
            result["similarity"] = float(similarities[idx])
            results.append(result)
        
        return results

    def get_session_ids(self) -> List[str]:
        """Returns a list of all session IDs in the store."""
        return [m["session_id"] for m in self.metadata]
    
    def clear(self):
        """Clear the vector store."""
        self.vectors = np.zeros((0, 0))
        self.metadata = []
        if os.path.exists(self.vectors_file):
            os.remove(self.vectors_file)
        if os.path.exists(self.metadata_file):
            os.remove(self.metadata_file)
        logger.info("Vector store cleared.") 