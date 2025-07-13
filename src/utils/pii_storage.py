"""
Shared PII storage utility to avoid circular imports between agents
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Global storage for PII mapping (in production, use secure storage like Redis)
pii_mapping_store = {}

def store_pii_mapping(uuid: str, mapping: Dict[str, str]):
    """Store PII mapping for later retrieval"""
    pii_mapping_store[uuid] = mapping
    logger.info(f"Stored PII mapping for UUID: {uuid} with entries: {list(mapping.keys())}")

def retrieve_pii_mapping(uuid: str) -> Dict[str, str]:
    """Retrieve PII mapping by UUID"""
    return pii_mapping_store.get(uuid, {})

def clear_pii_mapping(uuid: str):
    """Clear PII mapping for a specific UUID"""
    if uuid in pii_mapping_store:
        del pii_mapping_store[uuid]
        logger.info(f"Cleared PII mapping for UUID: {uuid}")

def clear_old_mappings(older_than_hours: int = 24):
    """Clear mappings older than specified hours"""
    # In production, you'd track timestamps and clear old entries
    # For now, this is a placeholder
    pass

def get_mapping_count() -> int:
    """Get current number of stored mappings"""
    return len(pii_mapping_store)