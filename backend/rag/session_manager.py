"""
Session Manager - Quản lý conversation sessions
Xử lý tạo, lưu trữ, và quản lý phiên chat của người dùng
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import redis
from models import ConversationSession, ConversationMessage, ConversationMemory, SecurityLog
from cache import redisClient
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# Redis key patterns
SESSION_PREFIX = "session:"
SESSION_MESSAGES_PREFIX = "session_messages:"
SESSION_MEMORY_PREFIX = "session_memory:"
ACTIVE_SESSIONS_PREFIX = "active_sessions:"

def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid int for {name}: {value}, using default {default}")
        return default


class SessionManager:
    """Quản lý conversation sessions"""
    
    def __init__(self, redis_client: redis.Redis = None, session_timeout_hours: int = None):
        """
        Initialize SessionManager
        
        Args:
            redis_client: Redis client instance
            session_timeout_hours: Thời gian session hết hiệu lực (giờ)
        """
        self.redis_client = redis_client or redisClient
        if session_timeout_hours is None:
            session_timeout_hours = _get_env_int("SESSION_TIMEOUT_HOURS", 24)
        self.session_timeout = timedelta(hours=session_timeout_hours)
    
    def create_session(self, email: str, session_name: str = None) -> str:
        """
        Tạo một session mới
        
        Args:
            email: Email của user
            session_name: Tên session (optional)
            
        Returns:
            session_id: ID của session vừa tạo
        """
        try:
            session_id = str(uuid.uuid4())
            
            # Lưu session vào database
            session = ConversationSession.create(
                email=email,
                session_name=session_name or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                status='active',
                last_message_at=datetime.now()
            )
            
            # Cache session info vào Redis
            session_data = {
                'session_id': session_id,
                'db_id': session.id,
                'email': email,
                'session_name': session.session_name,
                'created_at': datetime.now().isoformat(),
                'last_message_at': datetime.now().isoformat(),
                'message_count': 0,
                'total_tokens': 0
            }
            
            self.redis_client.setex(
                f"{SESSION_PREFIX}{session_id}",
                int(self.session_timeout.total_seconds()),
                json.dumps(session_data)
            )
            
            # Add to user's active sessions list
            self.redis_client.sadd(
                f"{ACTIVE_SESSIONS_PREFIX}{email}",
                session_id
            )
            
            logger.info(f"Created new session {session_id} for user {email}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Lấy thông tin session
        
        Args:
            session_id: ID của session
            
        Returns:
            Session data hoặc None nếu không tìm thấy
        """
        try:
            session_data = self.redis_client.get(f"{SESSION_PREFIX}{session_id}")
            if session_data:
                return json.loads(session_data)
            return None
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            return None
    
    def get_user_sessions(self, email: str) -> List[Dict[str, Any]]:
        """
        Lấy danh sách sessions của user
        
        Args:
            email: Email của user
            
        Returns:
            List of session data
        """
        try:
            session_ids = self.redis_client.smembers(f"{ACTIVE_SESSIONS_PREFIX}{email}")
            sessions = []
            
            for session_id in session_ids:
                session = self.get_session(session_id.decode() if isinstance(session_id, bytes) else session_id)
                if session:
                    sessions.append(session)
            
            # Sort by last_message_at descending
            sessions.sort(
                key=lambda x: x.get('last_message_at', ''),
                reverse=True
            )
            
            return sessions
        except Exception as e:
            logger.error(f"Error getting user sessions: {str(e)}")
            return []
    
    def add_message_to_session(self, session_id: str, turn_number: int, 
                               user_query: str, ai_response: str, 
                               citations: List[Dict], email: str,
                               tokens_info: Dict = None) -> Optional[int]:
        """
        Thêm message vào session
        
        Args:
            session_id: ID của session
            turn_number: Số lượt trò chuyện
            user_query: Câu hỏi của user
            ai_response: Câu trả lời của AI
            citations: Danh sách citations
            email: Email của user
            tokens_info: Thông tin về tokens {query_tokens, response_tokens, api_response_time_ms}
            
        Returns:
            message_id hoặc None nếu lỗi
        """
        try:
            # Lấy session info từ database
            session = ConversationSession.get_by_id(
                int(self.get_session(session_id).get('db_id'))
            )
            
            # Tạo message mới trong database
            message = ConversationMessage.create(
                session=session,
                email=email,
                turn_number=turn_number,
                user_query=user_query,
                ai_response=ai_response,
                citations=json.dumps(citations),
                query_tokens=tokens_info.get('query_tokens', 0) if tokens_info else 0,
                response_tokens=tokens_info.get('response_tokens', 0) if tokens_info else 0,
                total_tokens=(tokens_info.get('query_tokens', 0) + 
                             tokens_info.get('response_tokens', 0)) if tokens_info else 0,
                api_response_time_ms=tokens_info.get('api_response_time_ms', 0) if tokens_info else 0
            )
            
            # Update session metadata
            session.message_count = turn_number
            session.total_messages += 1
            session.total_tokens_used += message.total_tokens
            session.last_message_at = datetime.now()
            session.save()
            
            # Update Redis cache
            session_data = self.get_session(session_id)
            if session_data:
                session_data['message_count'] = turn_number
                session_data['total_tokens'] = session.total_tokens_used
                session_data['last_message_at'] = datetime.now().isoformat()
                
                self.redis_client.setex(
                    f"{SESSION_PREFIX}{session_id}",
                    int(self.session_timeout.total_seconds()),
                    json.dumps(session_data)
                )
            
            # Cache message vào Redis (cho quick access)
            message_data = {
                'message_id': message.id,
                'turn_number': turn_number,
                'user_query': user_query,
                'ai_response': ai_response,
                'total_tokens': message.total_tokens,
                'created_at': message.createdAt.isoformat()
            }
            
            self.redis_client.lpush(
                f"{SESSION_MESSAGES_PREFIX}{session_id}",
                json.dumps(message_data)
            )
            
            # Keep only last 100 messages in Redis cache
            self.redis_client.ltrim(
                f"{SESSION_MESSAGES_PREFIX}{session_id}",
                0, 99
            )
            
            logger.info(f"Added message {message.id} to session {session_id}")
            return message.id
            
        except Exception as e:
            logger.error(f"Error adding message to session: {str(e)}")
            return None
    
    def get_session_messages(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Lấy danh sách messages trong một session
        
        Args:
            session_id: ID của session
            limit: Số lượng messages cần lấy (latest)
            
        Returns:
            List of messages
        """
        try:
            session = self.get_session(session_id)
            if not session:
                return []
            
            db_session_id = session.get('db_id')
            session_obj = ConversationSession.get_by_id(int(db_session_id))
            
            # Lấy từ database (for persistence)
            messages = ConversationMessage.select().where(
                ConversationMessage.session == session_obj
            ).order_by(ConversationMessage.turn_number.desc()).limit(limit)
            
            result = []
            for msg in messages:
                result.append({
                    'id': msg.id,
                    'turn_number': msg.turn_number,
                    'user_query': msg.user_query,
                    'ai_response': msg.ai_response,
                    'citations': json.loads(msg.citations) if msg.citations else [],
                    'total_tokens': msg.total_tokens,
                    'created_at': msg.createdAt.isoformat()
                })
            
            # Reverse để trả về theo thứ tự cũ nhất đến mới nhất
            result.reverse()
            return result
        except Exception as e:
            logger.error(f"Error getting session messages: {str(e)}")
            return []
    
    def clear_session(self, session_id: str) -> bool:
        """
        Xóa session (xóa messages nhưng giữ session metadata)
        
        Args:
            session_id: ID của session
            
        Returns:
            Success status
        """
        try:
            session = self.get_session(session_id)
            if not session:
                return False
            
            db_session_id = session.get('db_id')
            
            # Xóa messages từ database
            ConversationMessage.delete().where(
                ConversationMessage.session == int(db_session_id)
            ).execute()
            
            # Reset session metadata
            session_obj = ConversationSession.get_by_id(int(db_session_id))
            session_obj.message_count = 0
            session_obj.total_messages = 0
            session_obj.total_tokens_used = 0
            session_obj.save()
            
            # Update Redis cache
            session['message_count'] = 0
            session['total_tokens'] = 0
            self.redis_client.setex(
                f"{SESSION_PREFIX}{session_id}",
                int(self.session_timeout.total_seconds()),
                json.dumps(session)
            )
            
            # Clear message cache
            self.redis_client.delete(f"{SESSION_MESSAGES_PREFIX}{session_id}")
            
            logger.info(f"Cleared session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing session: {str(e)}")
            return False
    
    def archive_session(self, session_id: str) -> bool:
        """
        Archive một session
        
        Args:
            session_id: ID của session
            
        Returns:
            Success status
        """
        try:
            session = self.get_session(session_id)
            if not session:
                return False
            
            db_session_id = session.get('db_id')
            email = session.get('email')
            
            # Update database
            session_obj = ConversationSession.get_by_id(int(db_session_id))
            session_obj.status = 'archived'
            session_obj.is_archived = True
            session_obj.save()
            
            # Update Redis
            session['status'] = 'archived'
            self.redis_client.setex(
                f"{SESSION_PREFIX}{session_id}",
                int(self.session_timeout.total_seconds()),
                json.dumps(session)
            )
            
            # Remove from active sessions
            self.redis_client.srem(f"{ACTIVE_SESSIONS_PREFIX}{email}", session_id)
            
            logger.info(f"Archived session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error archiving session: {str(e)}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Xóa hoàn toàn một session
        
        Args:
            session_id: ID của session
            
        Returns:
            Success status
        """
        try:
            session = self.get_session(session_id)
            if not session:
                return False
            
            db_session_id = session.get('db_id')
            email = session.get('email')
            
            # Detach security logs first to satisfy FK constraints
            # Keep logs for audit; just null out the session reference.
            SecurityLog.update(session=None).where(
                SecurityLog.session == int(db_session_id)
            ).execute()

            # Delete messages
            ConversationMessage.delete().where(
                ConversationMessage.session == int(db_session_id)
            ).execute()
            
            # Delete memory
            ConversationMemory.delete().where(
                ConversationMemory.session == int(db_session_id)
            ).execute()
            
            # Delete session
            ConversationSession.delete_by_id(int(db_session_id))
            
            # Delete from Redis
            self.redis_client.delete(f"{SESSION_PREFIX}{session_id}")
            self.redis_client.delete(f"{SESSION_MESSAGES_PREFIX}{session_id}")
            self.redis_client.delete(f"{SESSION_MEMORY_PREFIX}{session_id}")
            self.redis_client.srem(f"{ACTIVE_SESSIONS_PREFIX}{email}", session_id)
            
            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            return False


# Initialize singleton
session_manager = SessionManager()
