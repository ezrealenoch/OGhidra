"""
Data structures for session memory and tool call tracking.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Literal, Optional
import datetime
import uuid

@dataclass
class ToolCallRecord:
    """Represents a single tool call made during a session."""
    tool_name: str
    parameters: Dict[str, Any]
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    status: Optional[Literal["success", "error"]] = None
    result_preview: Optional[str] = None  # A brief summary of the tool's output

@dataclass
class SessionRecord:
    """Represents a single conversation session with the user."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: datetime.datetime = field(default_factory=datetime.datetime.utcnow)
    end_time: Optional[datetime.datetime] = None
    
    user_task_description: str  # The core task, problem, or question from the user for this session.
    
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    
    outcome: Literal["success", "failure", "partial_success", "in_progress", "aborted"] = "in_progress"
    outcome_reason: Optional[str] = None  # Brief explanation for the outcome
    
    session_summary: Optional[str] = None  # LLM-generated summary of key findings or solution 