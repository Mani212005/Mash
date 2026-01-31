"""
Mash Voice - Knowledge Service

Manages FAQ and knowledge base for customer service chatbot.
Supports semantic search using embeddings for finding relevant answers.
"""

import json
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime

from google import genai
from google.genai import types

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class KnowledgeEntry:
    """A single knowledge base entry."""
    id: str
    category: str
    question: str
    answer: str
    keywords: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "question": self.question,
            "answer": self.answer,
            "keywords": self.keywords,
            "metadata": self.metadata,
        }


@dataclass
class SearchResult:
    """Result from knowledge base search."""
    entry: KnowledgeEntry
    relevance_score: float
    matched_keywords: list[str] = field(default_factory=list)


class KnowledgeService:
    """
    Service for managing and searching the knowledge base.
    
    Provides:
    - FAQ lookup by category
    - Semantic search using Gemini
    - Keyword matching
    - Business info retrieval
    """

    def __init__(self):
        self._settings = get_settings()
        self._gemini_client = genai.Client(api_key=self._settings.gemini_api_key)
        self._entries: dict[str, KnowledgeEntry] = {}
        self._categories: dict[str, list[str]] = {}  # category -> entry IDs
        self._business_info: dict[str, Any] = {}
        self._loaded = False

    def load_knowledge_base(self, file_path: str | None = None) -> None:
        """
        Load knowledge base from JSON file.
        
        Args:
            file_path: Path to knowledge base JSON. Defaults to app/data/knowledge_base.json
        """
        if file_path is None:
            file_path = Path(__file__).parent.parent / "data" / "knowledge_base.json"
        else:
            file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"Knowledge base file not found: {file_path}")
            self._loaded = True
            return
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            # Load business info
            self._business_info = data.get("business_info", {})
            
            # Load FAQ entries
            for entry_data in data.get("faqs", []):
                entry = KnowledgeEntry(
                    id=entry_data["id"],
                    category=entry_data.get("category", "general"),
                    question=entry_data["question"],
                    answer=entry_data["answer"],
                    keywords=entry_data.get("keywords", []),
                    metadata=entry_data.get("metadata", {}),
                )
                self._entries[entry.id] = entry
                
                # Index by category
                if entry.category not in self._categories:
                    self._categories[entry.category] = []
                self._categories[entry.category].append(entry.id)
            
            self._loaded = True
            logger.info(
                "Knowledge base loaded",
                entries=len(self._entries),
                categories=list(self._categories.keys()),
            )
            
        except Exception as e:
            logger.exception("Failed to load knowledge base", error=str(e))
            self._loaded = True

    def get_business_info(self, key: str | None = None) -> Any:
        """
        Get business information.
        
        Args:
            key: Specific key to retrieve, or None for all info
            
        Returns:
            Business info value or full dict
        """
        if not self._loaded:
            self.load_knowledge_base()
        
        if key is None:
            return self._business_info
        return self._business_info.get(key)

    def get_entry(self, entry_id: str) -> KnowledgeEntry | None:
        """Get a specific knowledge entry by ID."""
        if not self._loaded:
            self.load_knowledge_base()
        return self._entries.get(entry_id)

    def get_by_category(self, category: str) -> list[KnowledgeEntry]:
        """Get all entries in a category."""
        if not self._loaded:
            self.load_knowledge_base()
        
        entry_ids = self._categories.get(category, [])
        return [self._entries[eid] for eid in entry_ids if eid in self._entries]

    def get_categories(self) -> list[str]:
        """Get all available categories."""
        if not self._loaded:
            self.load_knowledge_base()
        return list(self._categories.keys())

    def search_by_keywords(self, query: str, limit: int = 5) -> list[SearchResult]:
        """
        Search knowledge base by keyword matching.
        
        Args:
            query: User query
            limit: Maximum results to return
            
        Returns:
            List of matching entries with scores
        """
        if not self._loaded:
            self.load_knowledge_base()
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        results = []
        
        for entry in self._entries.values():
            score = 0.0
            matched = []
            
            # Check keywords
            for keyword in entry.keywords:
                if keyword.lower() in query_lower:
                    score += 2.0
                    matched.append(keyword)
            
            # Check question similarity
            question_words = set(entry.question.lower().split())
            common_words = query_words & question_words
            if common_words:
                score += len(common_words) * 0.5
            
            # Check if query is in question or answer
            if query_lower in entry.question.lower():
                score += 3.0
            if query_lower in entry.answer.lower():
                score += 1.0
            
            if score > 0:
                results.append(SearchResult(
                    entry=entry,
                    relevance_score=score,
                    matched_keywords=matched,
                ))
        
        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]

    async def semantic_search(self, query: str, limit: int = 3) -> list[SearchResult]:
        """
        Search knowledge base using Gemini for semantic understanding.
        
        Args:
            query: User query
            limit: Maximum results to return
            
        Returns:
            List of relevant entries
        """
        if not self._loaded:
            self.load_knowledge_base()
        
        if not self._entries:
            return []
        
        # Build context of all FAQs
        faq_context = "\n\n".join([
            f"[{entry.id}] Q: {entry.question}\nA: {entry.answer}"
            for entry in self._entries.values()
        ])
        
        prompt = f"""Given the user query and the FAQ database below, identify the most relevant FAQ entries that could answer the user's question.

User Query: {query}

FAQ Database:
{faq_context}

Return ONLY the IDs of the top {limit} most relevant FAQs, one per line. If no FAQs are relevant, return "NONE".
Format: Just the IDs, nothing else."""

        try:
            response = await self._gemini_client.aio.models.generate_content(
                model=self._settings.gemini_model,
                contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=100,
                ),
            )
            
            if response.candidates and response.candidates[0].content:
                text = response.candidates[0].content.parts[0].text.strip()
                
                if text == "NONE":
                    return []
                
                # Parse IDs from response
                results = []
                for line in text.split("\n"):
                    entry_id = line.strip()
                    if entry_id in self._entries:
                        results.append(SearchResult(
                            entry=self._entries[entry_id],
                            relevance_score=1.0 - (len(results) * 0.1),  # Decreasing score
                        ))
                
                return results[:limit]
                
        except Exception as e:
            logger.exception("Semantic search failed", error=str(e))
        
        # Fallback to keyword search
        return self.search_by_keywords(query, limit)

    async def find_answer(self, query: str) -> tuple[str | None, KnowledgeEntry | None]:
        """
        Find the best answer for a user query.
        
        Args:
            query: User question
            
        Returns:
            Tuple of (answer text, source entry) or (None, None) if not found
        """
        # Try semantic search first
        results = await self.semantic_search(query, limit=1)
        
        if results and results[0].relevance_score > 0.5:
            entry = results[0].entry
            return entry.answer, entry
        
        # Fallback to keyword search
        keyword_results = self.search_by_keywords(query, limit=1)
        if keyword_results and keyword_results[0].relevance_score > 2.0:
            entry = keyword_results[0].entry
            return entry.answer, entry
        
        return None, None

    def add_entry(self, entry: KnowledgeEntry) -> None:
        """Add a new entry to the knowledge base."""
        self._entries[entry.id] = entry
        
        if entry.category not in self._categories:
            self._categories[entry.category] = []
        if entry.id not in self._categories[entry.category]:
            self._categories[entry.category].append(entry.id)

    def remove_entry(self, entry_id: str) -> bool:
        """Remove an entry from the knowledge base."""
        if entry_id not in self._entries:
            return False
        
        entry = self._entries.pop(entry_id)
        if entry.category in self._categories:
            self._categories[entry.category] = [
                eid for eid in self._categories[entry.category] if eid != entry_id
            ]
        return True


# Singleton instance
_knowledge_service: KnowledgeService | None = None


def get_knowledge_service() -> KnowledgeService:
    """Get the knowledge service singleton."""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
