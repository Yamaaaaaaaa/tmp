"""
Memory Manager - Quản lý conversation memory và context
Xử lý context length, summarization, và memory optimization
"""

import json
import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from models import ConversationMemory, ConversationSession, ConversationMessage
from cache import redisClient
import logging
from google import genai
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# Token estimation (approximate)
TOKENS_PER_WORD = 0.25
DEFAULT_MAX_CONTEXT_TOKENS = 4000  # Safe limit for context
DEFAULT_SUMMARY_PROMPT_TOKENS = 500  # Reserve tokens for summary prompt

def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid int for {name}: {value}, using default {default}")
        return default


class MemoryManager:
    """Quản lý conversation memory và context"""
    
    def __init__(self, 
                 max_context_tokens: int = None,
                 gemini_model: str = "gemini-2.5-flash"):
        """
        Initialize MemoryManager
        
        Args:
            max_context_tokens: Maximum tokens cho conversation context
            gemini_model: Gemini model để dùng cho summarization
        """
        if max_context_tokens is None:
            max_context_tokens = _get_env_int("MAX_CONTEXT_TOKENS", DEFAULT_MAX_CONTEXT_TOKENS)
        self.max_context_tokens = max_context_tokens
        self.gemini_model = gemini_model
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    
    def estimate_tokens(self, text: str) -> int:
        """
        Ước tính số tokens (approximate)
        
        Args:
            text: Text để ước tính
            
        Returns:
            Estimated token count
        """
        words = len(text.split())
        return max(1, int(words * TOKENS_PER_WORD))
    
    def get_conversation_context(self, session_id: str, db_session_id: int,
                                max_turns: int = None) -> Tuple[str, int, Dict]:
        """
        Lấy conversation context (từ messages hoặc memory)
        
        Args:
            session_id: Redis session ID
            db_session_id: Database session ID
            max_turns: Max số turns để include (None = all available)
            
        Returns:
            Tuple of (context_text, token_count, metadata)
        """
        try:
            # Kiểm tra nếu có summarized memory
            memory = ConversationMemory.select().where(
                ConversationMemory.session_id == db_session_id
            ).order_by(ConversationMemory.version.desc()).first()
            
            context_parts = []
            total_tokens = 0
            
            if memory and memory.is_context_summarized:
                # Thêm summary vào context
                summary = f"[CONVERSATION SUMMARY]\n{memory.conversation_summary}\n\n"
                context_parts.append(summary)
                total_tokens += self.estimate_tokens(summary)
            
            # Lấy recent messages
            session = ConversationSession.select().where(
                ConversationSession.id == db_session_id
            ).first()
            
            if not session:
                return "", 0, {}
            
            messages = ConversationMessage.select().where(
                ConversationMessage.session == session
            ).order_by(
                ConversationMessage.turn_number.asc()
            )
            
            if max_turns:
                total_messages = messages.count()
                skip_turns = max(0, total_messages - max_turns)
                messages = messages.where(
                    ConversationMessage.turn_number > skip_turns
                )
            
            # Build context từ messages
            for msg in messages:
                msg_context = (f"[Turn {msg.turn_number}]\n"
                              f"User: {msg.user_query}\n"
                              f"Assistant: {msg.ai_response}\n\n")
                
                msg_tokens = self.estimate_tokens(msg_context)
                
                # Check nếu adding this message sẽ exceed limit
                if (total_tokens + msg_tokens) > self.max_context_tokens:
                    logger.warning(f"Context exceeds max tokens for session {session_id}")
                    break
                
                context_parts.append(msg_context)
                total_tokens += msg_tokens
            
            context_text = "".join(context_parts)
            
            return context_text, total_tokens, {
                'is_summarized': memory and memory.is_context_summarized,
                'memory_version': memory.version if memory else None,
                'messages_included': len(list(messages))
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            return "", 0, {}
    
    def should_create_summary(self, db_session_id: int) -> bool:
        """
        Check nếu cần tạo summary (khi context quá dài)
        
        Args:
            db_session_id: Database session ID
            
        Returns:
            True nếu cần summary
        """
        try:
            session = ConversationSession.get_by_id(db_session_id)
            
            # Tạo summary nếu:
            # 1. Số messages > 15
            # 2. Total tokens > 80% của max
            if session.message_count > 15:
                return True
            
            # Estimate total tokens từ messages
            messages = ConversationMessage.select().where(
                ConversationMessage.session == session
            )
            
            total_tokens = sum(msg.total_tokens for msg in messages)
            if total_tokens > (self.max_context_tokens * 0.8):
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking if summary needed: {str(e)}")
            return False
    
    def create_summary(self, session_id: str, db_session_id: int, 
                      context: str) -> Optional[Dict[str, Any]]:
        """
        Tạo summary của conversation
        
        Args:
            session_id: Redis session ID
            db_session_id: Database session ID
            context: Full conversation context
            
        Returns:
            Summary data hoặc None nếu lỗi
        """
        try:
            # Get current memory version
            existing_memory = ConversationMemory.select().where(
                ConversationMemory.session_id == db_session_id
            ).order_by(ConversationMemory.version.desc()).first()
            
            current_version = (existing_memory.version + 1) if existing_memory else 1
            
            # Prompt cho summarization
            summary_prompt = (
                "Hãy tóm tắt cuộc trò chuyện hỏi đáp pháp luật trên một cách ngắn gọn. "
                "Tập trung vào:\n"
                "1. Các chủ đề chính được thảo luận\n"
                "2. Những câu hỏi quan trọng và câu trả lời\n"
                "3. Những điểm pháp luật chính được giải thích\n\n"
                f"Conversation:\n{context}"
            )
            
            # Call Gemini để tạo summary
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=summary_prompt,
            )
            
            summary_text = response.text
            
            # Extract key topics (simple extraction)
            key_topics = self._extract_key_topics(context, summary_text)
            
            # Extract important facts
            important_facts = self._extract_important_facts(context)
            
            # Tính context length của summary
            summary_tokens = self.estimate_tokens(summary_text)
            
            # Lưu memory vào database
            memory = ConversationMemory.create(
                session_id=db_session_id,
                email=ConversationSession.get_by_id(db_session_id).email,
                conversation_summary=summary_text,
                key_topics=json.dumps(key_topics),
                important_facts=json.dumps(important_facts),
                current_context_length=summary_tokens,
                max_context_length=self.max_context_tokens,
                is_context_summarized=True,
                version=current_version,
                truncated_from_turn=ConversationSession.get_by_id(
                    db_session_id
                ).message_count - 10  # Keep last 10 turns in full
            )
            
            logger.info(f"Created summary version {current_version} for session {session_id}")
            
            return {
                'memory_id': memory.id,
                'version': memory.version,
                'summary': summary_text,
                'key_topics': key_topics,
                'important_facts': important_facts,
                'token_count': summary_tokens
            }
            
        except Exception as e:
            logger.error(f"Error creating summary: {str(e)}")
            return None
    
    def _extract_key_topics(self, context: str, summary: str) -> List[str]:
        """
        Extract key topics từ conversation
        
        Args:
            context: Full conversation
            summary: Generated summary
            
        Returns:
            List of key topics
        """
        try:
            # Simple keyword extraction từ summary
            # Có thể improve bằng NLP library như spaCy
            topics = []
            
            # Look cho "Điều" references (common in Vietnamese law)
            import re
            dieu_refs = re.findall(r'Điều\s+(\d+)', context)
            for dieu in set(dieu_refs[:5]):  # Top 5
                topics.append(f"Điều {dieu}")
            
            # Look cho "Luật" references
            luat_refs = re.findall(r'(Luật\s+\w+(?:\s+\w+)*)', context)
            for luat in set(luat_refs[:3]):  # Top 3
                topics.append(luat)
            
            return topics if topics else ["Tư vấn pháp luật chung"]
        except Exception as e:
            logger.error(f"Error extracting key topics: {str(e)}")
            return []
    
    def _extract_important_facts(self, context: str) -> List[str]:
        """
        Extract important facts từ conversation
        
        Args:
            context: Full conversation
            
        Returns:
            List of important facts
        """
        try:
            facts = []
            lines = context.split('\n')
            
            # Look cho answer lines (lines starting with "Assistant:")
            for i, line in enumerate(lines):
                if "Assistant:" in line:
                    answer = line.replace("Assistant:", "").strip()
                    if len(answer) > 20 and "trả lời" not in answer.lower():
                        facts.append(answer[:200])  # First 200 chars
            
            return facts[:5]  # Top 5 facts
        except Exception as e:
            logger.error(f"Error extracting important facts: {str(e)}")
            return []
    
    def get_memory(self, session_id: str, db_session_id: int) -> Optional[Dict[str, Any]]:
        """
        Lấy memory data
        
        Args:
            session_id: Redis session ID
            db_session_id: Database session ID
            
        Returns:
            Memory data hoặc None
        """
        try:
            memory = ConversationMemory.select().where(
                ConversationMemory.session_id == db_session_id
            ).order_by(ConversationMemory.version.desc()).first()
            
            if not memory:
                return None
            
            return {
                'id': memory.id,
                'version': memory.version,
                'summary': memory.conversation_summary,
                'key_topics': json.loads(memory.key_topics) if memory.key_topics else [],
                'important_facts': json.loads(memory.important_facts) if memory.important_facts else [],
                'is_context_summarized': memory.is_context_summarized,
                'truncated_from_turn': memory.truncated_from_turn
            }
        except Exception as e:
            logger.error(f"Error getting memory: {str(e)}")
            return None
    
    def clear_memory(self, db_session_id: int) -> bool:
        """
        Clear memory cho một session
        
        Args:
            db_session_id: Database session ID
            
        Returns:
            Success status
        """
        try:
            ConversationMemory.delete().where(
                ConversationMemory.session_id == db_session_id
            ).execute()
            
            logger.info(f"Cleared memory for session {db_session_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing memory: {str(e)}")
            return False


# Initialize singleton
memory_manager = MemoryManager()
