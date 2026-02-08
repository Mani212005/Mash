"""
Mash Voice - Knowledge Base Routes

REST API endpoints for knowledge base management (FAQs, business info).
"""

import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import get_settings
from app.services import get_knowledge_service
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeEntry(BaseModel):
    """FAQ/Knowledge entry model."""
    id: Optional[str] = None
    category: str = "General"
    question: str
    answer: str
    keywords: List[str] = []
    metadata: Optional[dict] = None


class BusinessInfo(BaseModel):
    """Business information model."""
    name: str
    tagline: Optional[str] = None
    tone: Optional[str] = None
    timezone: Optional[str] = None
    operating_hours: Optional[dict] = None
    contact: Optional[dict] = None


class KnowledgeBase(BaseModel):
    """Complete knowledge base model."""
    business_info: BusinessInfo
    faqs: List[KnowledgeEntry]


@router.get("", response_model=KnowledgeBase)
async def get_knowledge_base():
    """
    Get the complete knowledge base including business info and FAQs.
    
    Returns:
    - business_info: Company/business details
    - faqs: All FAQ entries organized by category
    """
    try:
        knowledge_service = get_knowledge_service()
        
        # Get business info using the proper method
        business_info_dict = knowledge_service.get_business_info() or {}
        # Provide defaults for required fields
        business_info = BusinessInfo(
            name=business_info_dict.get('name', 'My Business'),
            tagline=business_info_dict.get('tagline'),
            tone=business_info_dict.get('tone'),
            timezone=business_info_dict.get('timezone'),
            operating_hours=business_info_dict.get('operating_hours'),
            contact=business_info_dict.get('contact'),
        )
        
        # Get all FAQs from internal entries dict
        faqs = [
            KnowledgeEntry(
                id=entry.id,
                category=entry.category,
                question=entry.question,
                answer=entry.answer,
                keywords=entry.keywords,
                metadata=entry.metadata,
            )
            for entry in knowledge_service._entries.values()
        ]
        
        return KnowledgeBase(
            business_info=business_info,
            faqs=faqs
        )
        
    except Exception as e:
        logger.error(f"Error getting knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=List[KnowledgeEntry])
async def search_knowledge(
    q: str = Query(..., description="Search query for knowledge base")
):
    """
    Search the knowledge base using semantic similarity.
    
    Query Parameters:
    - q: Search query string
    
    Returns matching FAQ entries ranked by relevance.
    """
    try:
        knowledge_service = get_knowledge_service()
        
        # Use knowledge service keyword search
        results = knowledge_service.search_by_keywords(q, limit=10)
        
        return [
            KnowledgeEntry(
                id=result.entry.id,
                category=result.entry.category,
                question=result.entry.question,
                answer=result.entry.answer,
                keywords=result.entry.keywords,
                metadata=result.entry.metadata,
            )
            for result in results
        ]
        
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/faqs", response_model=KnowledgeEntry)
async def add_knowledge_entry(entry: KnowledgeEntry):
    """
    Add a new FAQ entry to the knowledge base.
    
    Request Body:
    - Knowledge entry with question, answer, category, keywords
    
    Returns the created entry with generated ID.
    """
    try:
        knowledge_service = get_knowledge_service()
        settings = get_settings()
        
        # Load current knowledge base
        kb_path = Path(settings.cs_knowledge_base_path or "app/data/knowledge_base.json")
        with open(kb_path, 'r') as f:
            kb_data = json.load(f)
        
        # Add new entry
        new_entry = entry.dict()
        if not new_entry.get('id'):
            # Generate ID
            existing_ids = [faq.get('id', '') for faq in kb_data.get('faqs', [])]
            new_id = f"faq_{len(existing_ids) + 1}"
            new_entry['id'] = new_id
        
        kb_data['faqs'].append(new_entry)
        
        # Save back to file
        with open(kb_path, 'w') as f:
            json.dump(kb_data, f, indent=2)
        
        # Reload knowledge service
        knowledge_service.load_knowledge_base()
        
        logger.info(f"Added knowledge entry: {new_entry['id']}")
        return KnowledgeEntry(**new_entry)
        
    except Exception as e:
        logger.error(f"Error adding knowledge entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/faqs/{entry_id}", response_model=KnowledgeEntry)
async def update_knowledge_entry(entry_id: str, entry: KnowledgeEntry):
    """
    Update an existing FAQ entry.
    
    Path Parameters:
    - entry_id: ID of the entry to update
    
    Request Body:
    - Updated knowledge entry fields
    """
    try:
        knowledge_service = get_knowledge_service()
        settings = get_settings()
        
        # Load current knowledge base
        kb_path = Path(settings.cs_knowledge_base_path or "app/data/knowledge_base.json")
        with open(kb_path, 'r') as f:
            kb_data = json.load(f)
        
        # Find and update entry
        found = False
        for idx, faq in enumerate(kb_data.get('faqs', [])):
            if faq.get('id') == entry_id:
                kb_data['faqs'][idx] = entry.dict()
                kb_data['faqs'][idx]['id'] = entry_id  # Preserve ID
                found = True
                break
        
        if not found:
            raise HTTPException(status_code=404, detail="Knowledge entry not found")
        
        # Save back to file
        with open(kb_path, 'w') as f:
            json.dump(kb_data, f, indent=2)
        
        # Reload knowledge service
        knowledge_service.load_knowledge_base()
        
        logger.info(f"Updated knowledge entry: {entry_id}")
        return entry
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating knowledge entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/faqs/{entry_id}")
async def delete_knowledge_entry(entry_id: str):
    """
    Delete an FAQ entry from the knowledge base.
    
    Path Parameters:
    - entry_id: ID of the entry to delete
    """
    try:
        knowledge_service = get_knowledge_service()
        settings = get_settings()
        
        # Load current knowledge base
        kb_path = Path(settings.cs_knowledge_base_path or "app/data/knowledge_base.json")
        with open(kb_path, 'r') as f:
            kb_data = json.load(f)
        
        # Find and remove entry
        original_count = len(kb_data.get('faqs', []))
        kb_data['faqs'] = [
            faq for faq in kb_data.get('faqs', [])
            if faq.get('id') != entry_id
        ]
        
        if len(kb_data['faqs']) == original_count:
            raise HTTPException(status_code=404, detail="Knowledge entry not found")
        
        # Save back to file
        with open(kb_path, 'w') as f:
            json.dump(kb_data, f, indent=2)
        
        # Reload knowledge service
        knowledge_service.load_knowledge_base()
        
        logger.info(f"Deleted knowledge entry: {entry_id}")
        return {"status": "success", "message": f"Entry {entry_id} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting knowledge entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))
