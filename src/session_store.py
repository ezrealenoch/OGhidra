"""
Session history storage and retrieval.
"""

import json
import os
import datetime
from typing import List, Dict, Any, Optional

from .memory_models import SessionRecord, ToolCallRecord

class SessionHistoryStore:
    def __init__(self, storage_path: str = "session_history.jsonl"):
        self.storage_path = storage_path
        # Ensure the directory for the storage path exists
        storage_dir = os.path.dirname(self.storage_path)
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)

    def _to_dict(self, record: SessionRecord) -> Dict[str, Any]:
        """Converts a SessionRecord to a JSON-serializable dictionary."""
        data = record.__dict__.copy()
        data['start_time'] = record.start_time.isoformat()
        if record.end_time:
            data['end_time'] = record.end_time.isoformat()
        
        # Convert tool calls to dictionaries
        tool_calls = []
        for tc in record.tool_calls:
            tc_dict = tc.__dict__.copy()
            tc_dict['timestamp'] = tc.timestamp.isoformat()
            tool_calls.append(tc_dict)
        
        data['tool_calls'] = tool_calls
        return data

    def _from_dict(self, data: Dict[str, Any]) -> SessionRecord:
        """Converts a dictionary (from JSON) back to a SessionRecord."""
        # Create a deep copy to avoid modifying the input
        record_data = data.copy()
        
        # Convert datetime strings back to datetime objects
        record_data['start_time'] = datetime.datetime.fromisoformat(record_data['start_time'])
        if record_data.get('end_time'):
            record_data['end_time'] = datetime.datetime.fromisoformat(record_data['end_time'])
        
        # Convert tool calls data back to ToolCallRecord objects
        tool_calls_data = record_data.pop('tool_calls', [])
        tool_calls = []
        for tc_data in tool_calls_data:
            tc_data_copy = tc_data.copy()
            if 'timestamp' in tc_data_copy:
                tc_data_copy['timestamp'] = datetime.datetime.fromisoformat(tc_data_copy['timestamp'])
            tool_calls.append(ToolCallRecord(**tc_data_copy))
        
        # Create SessionRecord without tool_calls first, then add them
        session_record = SessionRecord(**record_data)
        session_record.tool_calls = tool_calls
        
        return session_record

    def save_session(self, record: SessionRecord):
        """Appends a session record to the storage file."""
        if record.outcome == "in_progress" and record.end_time is None:
            record.end_time = datetime.datetime.utcnow()

        with open(self.storage_path, "a", encoding="utf-8") as f:
            json.dump(self._to_dict(record), f)
            f.write("\n")

    def load_all_sessions(self) -> List[SessionRecord]:
        """Loads all session records from the storage file."""
        if not os.path.exists(self.storage_path):
            return []
        
        records = []
        with open(self.storage_path, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, 1):
                if line.strip():
                    try:
                        data = json.loads(line)
                        records.append(self._from_dict(data))
                    except json.JSONDecodeError as e:
                        print(f"Warning: Skipping malformed JSON line {line_number} in '{self.storage_path}': {e}")
                    except Exception as e:
                        print(f"Warning: Skipping record on line {line_number} due to data conversion error: {e}")
        return records
    
    def get_session_by_id(self, session_id: str) -> Optional[SessionRecord]:
        """Retrieves a specific session by its ID."""
        for session in self.load_all_sessions():
            if session.session_id == session_id:
                return session
        return None 