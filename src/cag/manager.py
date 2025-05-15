"""
CAG Manager for Ollama-GhidraMCP Bridge.

This module implements the main manager for Cache-Augmented Generation
that integrates with the Bridge class.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple

from .knowledge_cache import GhidraKnowledgeCache
from .session_cache import SessionCache
from .init_dirs import ensure_cag_directories
from .vector_store import create_vector_store_from_docs

logger = logging.getLogger("ollama-ghidra-bridge.cag.manager")

class CAGManager:
    """
    Manager for Cache-Augmented Generation in the Ollama-GhidraMCP Bridge.
    
    This class orchestrates the knowledge and session caches, and integrates
    with the Bridge to augment prompts with relevant cached information.
    """
    
    def __init__(self, config):
        """
        Initialize the CAG manager.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.enable_kb = getattr(config, 'ENABLE_KNOWLEDGE_BASE', False)
        self.kb_dir = getattr(config, 'KNOWLEDGE_BASE_DIR', 'knowledge_base')
        
        # Ensure directories exist
        self.cache_dir = ensure_cag_directories()
        
        # Initialize session cache
        self.session_cache = SessionCache(self.cache_dir)
        
        # Initialize vector store
        self.vector_store = self._initialize_vector_store()
        
        logger.info("CAG Manager initialized")
    
    def enhance_prompt(self, query: str, phase: str = None, token_limit: int = 2000) -> str:
        """
        Enhance a prompt with relevant cached information.
        
        Args:
            query: The current query
            phase: The current phase ("planning", "execution", "analysis")
            token_limit: Maximum number of tokens to include
            
        Returns:
            Enhanced context to include in the prompt
        """
        enhanced_sections = []
        total_tokens = 0
        
        # Add relevant knowledge if enabled
        if self.enable_kb and self.vector_store:
            # Adjust token limit based on the phase
            phase_token_allocation = {
                "planning": 0.4,  # 40% of token limit for planning
                "execution": 0.3,  # 30% for execution
                "analysis": 0.5,   # 50% for analysis
                None: 0.4          # Default
            }
            
            knowledge_token_limit = int(token_limit * phase_token_allocation.get(phase, 0.4))
            
            knowledge_section = self.vector_store.get_relevant_knowledge(query, knowledge_token_limit)
            if knowledge_section:
                knowledge_tokens = len(knowledge_section) // 4  # Rough approximation
                enhanced_sections.append(knowledge_section)
                total_tokens += knowledge_tokens
                logger.debug(f"Added knowledge context ({knowledge_tokens} tokens)")
        
        # Add session cache if enabled
        if self.session_cache:
            # Adjust token limit based on remaining tokens
            session_token_limit = token_limit - total_tokens
            
            if session_token_limit > 200:  # Only if we have enough tokens left
                pruned_cache = self.session_cache.prune_cache_for_query(query, session_token_limit)
                session_section = self.session_cache.format_pruned_cache(pruned_cache)
                
                if session_section:
                    session_tokens = len(session_section) // 4  # Rough approximation
                    enhanced_sections.append(session_section)
                    total_tokens += session_tokens
                    logger.debug(f"Added session context ({session_tokens} tokens)")
        
        # Combine all sections
        if enhanced_sections:
            enhanced_prompt = "\n\n".join(enhanced_sections)
            logger.info(f"Enhanced prompt with {total_tokens} tokens of additional context")
            return enhanced_prompt
        
        return ""
    
    def update_session_from_bridge_context(self, context_history: List[Dict[str, Any]]) -> None:
        """
        Update the session cache from the Bridge's context history.
        
        Args:
            context_history: List of context items from the Bridge
        """
        if not self.session_cache:
            return
        
        # Context could be a list of dictionaries or a list
        if not isinstance(context_history, list):
            # Convert to list if it's not already
            logger.warning(f"Expected context_history to be a list, got {type(context_history)}")
            return
            
        for item in context_history:
            if isinstance(item, dict) and "role" in item and "content" in item:
                self.session_cache.add_context_item(item["role"], item["content"])
            else:
                logger.warning(f"Unexpected context item format: {item}")
                continue
    
    def update_from_function_decompile(self, address: str, name: str, decompiled_code: str) -> None:
        """
        Update the session cache with a decompiled function.
        
        Args:
            address: Function address
            name: Function name
            decompiled_code: Decompiled code
        """
        if not self.session_cache:
            return
            
        self.session_cache.add_decompiled_function(address, name, decompiled_code)
    
    def update_from_function_rename(self, old_name_or_address: str, new_name: str) -> None:
        """
        Update the session cache with a renamed function.
        
        Args:
            old_name_or_address: Old function name or address
            new_name: New function name
        """
        if not self.session_cache:
            return
            
        # Determine if this is an address or name (simple heuristic)
        entity_type = "function"
        if all(c in "0123456789abcdefABCDEF" for c in old_name_or_address.replace("0x", "")):
            entity_type = "function_address"
            
        self.session_cache.add_renamed_entity(old_name_or_address, new_name, entity_type)
    
    def update_from_analysis_result(self, query: str, context: str, result: str) -> None:
        """
        Update the session cache with an analysis result.
        
        Args:
            query: The query that triggered the analysis
            context: Context used for the analysis
            result: Analysis result
        """
        if not self.session_cache:
            return
            
        self.session_cache.add_analysis_result(query, context, result)
    
    def save_session(self) -> None:
        """Save the session cache to disk."""
        if self.session_cache:
            self.session_cache.save_to_disk()
            logger.info("Session cache saved to disk")
    
    def find_similar_analysis(self, query: str) -> Optional[str]:
        """
        Find a similar previous analysis result.
        
        Args:
            query: Query to find similar analysis for
            
        Returns:
            Similar analysis result or None
        """
        if not self.session_cache:
            return None
            
        return self.session_cache.find_similar_analysis(query)
    
    def get_available_sessions(self) -> List[str]:
        """
        Get a list of available session IDs.
        
        Returns:
            List of session IDs
        """
        return SessionCache.list_available_sessions()
    
    def load_session(self, session_id: str) -> bool:
        """
        Load a session from disk.
        
        Args:
            session_id: ID of the session to load
            
        Returns:
            True if successful, False otherwise
        """
        if not self.session_cache:
            return False
            
        return self.session_cache.load_from_disk(session_id)
    
    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get debug information about the CAG manager.
        
        Returns:
            Dictionary with debug information
        """
        info = {
            "enable_kb": self.enable_kb,
            "session_cache": None
        }
        
        if self.enable_kb and self.vector_store:
            info["vector_store"] = {
                "function_signatures": len(self.vector_store.function_signatures),
                "binary_patterns": len(self.vector_store.binary_patterns),
                "analysis_rules": len(self.vector_store.analysis_rules),
                "common_workflows": len(self.vector_store.common_workflows)
            }
            
        if self.session_cache:
            info["session_cache"] = {
                "session_id": self.session_cache.session_id,
                "context_history": len(self.session_cache.context_history),
                "decompiled_functions": len(self.session_cache.decompiled_functions),
                "renamed_entities": len(self.session_cache.renamed_entities),
                "analysis_results": len(self.session_cache.analysis_results)
            }
            
        return info

    def _initialize_vector_store(self):
        """Initialize the vector store with context documents."""
        try:
            docs = []
            
            # Load workplans
            workplan_files = [
                "workplans/knowledge_capture.md", 
                "workplans/progressive_analysis.md",
                "workplans/ghidra_tasks.md",  # Add the new workplan
                "workplans/malware_analysis_triage.md" # Added new malware triage workplan
            ]
            
            for file_path in workplan_files:
                full_path = os.path.join(os.path.dirname(__file__), file_path)
                if os.path.exists(full_path):
                    with open(full_path, 'r') as f:
                        content = f.read()
                        docs.append({"text": content, "type": "workplan", "name": os.path.basename(file_path)})
                else:
                    logging.warning(f"Workplan file not found: {full_path}")

            # Load knowledge base if enabled and exists
            if self.enable_kb:
                kb_path = os.path.join(self.kb_dir, "knowledge_base.md")
                if os.path.exists(kb_path):
                    with open(kb_path, 'r') as f:
                        content = f.read()
                        docs.append({"text": content, "type": "knowledge_base", "name": "knowledge_base.md"})
                else:
                    logging.warning(f"Knowledge base file not found: {kb_path}")
                    
            # Initialize vector store with documents
            self.vector_store = create_vector_store_from_docs(docs)
            logging.info(f"Initialized vector store with {len(docs)} documents")
            
        except Exception as e:
            logging.error(f"Error initializing vector store: {str(e)}")
            self.vector_store = None 