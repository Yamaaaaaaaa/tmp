"""
Multi-turn Chat Endpoints
Xử lý API endpoints cho multi-turn conversations
"""

from flask import Blueprint, request, jsonify
import jwt
import time
import logging
from typing import Dict, Any, Tuple
from models import ConversationSession, ConversationMessage
from session_manager import session_manager
from memory_manager import memory_manager
from security_manager import security_manager
from directory import ACCESS_TOKEN_KEY
# from vectorize_corpus import vectordb
from transformers import pipeline
import json
import re
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores.chroma import Chroma
import torch

logger = logging.getLogger(__name__)
load_dotenv()

def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid int for {name}: {value}, using default {default}")
        return default

# Initialize Blueprint
chat_bp = Blueprint('chat', __name__, url_prefix='/api/v2/chat')

# Initialize models
current_device = "cpu"
if torch.cuda.is_available():
    current_device = "cuda"

ST_MODEL_PATH = os.getenv("ST_MODEL_PATH")
QA_MODEL_PATH = os.getenv("QA_MODEL_PATH")
TOPIC_DB_PATH = os.getenv("TOPIC_DB_PATH")

embeddings = HuggingFaceEmbeddings(
    model_name=ST_MODEL_PATH,
    model_kwargs={"device": current_device}
)
vectordb = Chroma(
    embedding_function=embeddings,
    persist_directory=TOPIC_DB_PATH
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Rate limit configuration
MAX_REQUESTS_PER_HOUR = _get_env_int("MAX_REQUESTS_PER_HOUR", 100)
MAX_REQUESTS_PER_DAY = _get_env_int("MAX_REQUESTS_PER_DAY", 500)
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 86400


def get_auth_email() -> Tuple[str, int, Dict]:
    """
    Extract và validate email từ JWT token
    
    Returns:
        Tuple of (email, status_code, response)
    """
    try:
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return None, 401, {
                "status": "error",
                "message": "Missing or invalid authorization token"
            }
        
        token = token[7:]
        decoded = jwt.decode(token, ACCESS_TOKEN_KEY, algorithms=['HS256'])
        email = decoded.get('email')
        
        if not email:
            return None, 401, {
                "status": "error",
                "message": "Invalid token: no email found"
            }
        
        return email, 200, {}
    except jwt.ExpiredSignatureError:
        return None, 401, {
            "status": "error",
            "message": "Token has expired"
        }
    except jwt.InvalidTokenError:
        return None, 401, {
            "status": "error",
            "message": "Invalid token"
        }
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        return None, 401, {
            "status": "error",
            "message": "Authentication failed"
        }


@chat_bp.route('/session/create', methods=['POST'])
def create_session():
    """
    Tạo một session chat mới
    
    Request body:
    {
        "session_name": "Optional session name"
    }
    
    Returns:
        {
            "status": "success",
            "data": {
                "session_id": "uuid",
                "session_name": "name",
                "created_at": "timestamp"
            }
        }
    """
    email, status_code, response = get_auth_email()
    if email is None:
        return response, status_code
    
    try:
        data = request.get_json() or {}
        session_name = data.get('session_name')
        
        # Validate input
        if session_name:
            session_name = security_manager.sanitize_user_input(session_name, max_length=255)
        
        # Create session
        session_id = session_manager.create_session(email, session_name)
        
        session_data = session_manager.get_session(session_id)
        
        # Log security event
        security_manager.log_security_event(
            email=email,
            action='session_created',
            status='success'
        )
        
        return {
            "status": "success",
            "data": {
                "session_id": session_id,
                "session_name": session_data.get('session_name'),
                "created_at": session_data.get('created_at')
            }
        }, 201
    
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to create session: {str(e)}"
        }, 500


@chat_bp.route('/session/list', methods=['GET'])
def list_sessions():
    """
    Lấy danh sách sessions của user
    
    Returns:
        {
            "status": "success",
            "data": [
                {
                    "session_id": "uuid",
                    "session_name": "name",
                    "message_count": 5,
                    "total_tokens": 1000,
                    "last_message_at": "timestamp"
                }
            ]
        }
    """
    email, status_code, response = get_auth_email()
    if email is None:
        return response, status_code
    
    try:
        sessions = session_manager.get_user_sessions(email)
        
        return {
            "status": "success",
            "data": sessions,
            "count": len(sessions)
        }, 200
    
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to list sessions: {str(e)}"
        }, 500


@chat_bp.route('/session/<session_id>/messages', methods=['GET'])
def get_session_messages(session_id):
    """
    Lấy messages trong một session
    
    Query params:
        limit: số messages cần lấy (default: 10)
    
    Returns:
        {
            "status": "success",
            "data": [
                {
                    "turn_number": 1,
                    "user_query": "...",
                    "ai_response": "...",
                    "citations": [...],
                    "created_at": "timestamp"
                }
            ]
        }
    """
    email, status_code, response = get_auth_email()
    if email is None:
        return response, status_code
    
    try:
        # Validate access
        session = session_manager.get_session(session_id)
        if not session:
            return {
                "status": "error",
                "message": "Session not found"
            }, 404
        
        if not security_manager.validate_access(email, session_id, session.get('db_id')):
            return {
                "status": "error",
                "message": "Unauthorized access"
            }, 403
        
        limit = request.args.get('limit', default=10, type=int)
        limit = min(max(limit, 1), 100)  # Clamp between 1-100
        
        messages = session_manager.get_session_messages(session_id, limit)
        
        return {
            "status": "success",
            "data": messages,
            "count": len(messages)
        }, 200
    
    except Exception as e:
        logger.error(f"Error getting session messages: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get messages: {str(e)}"
        }, 500


@chat_bp.route('/message/send', methods=['POST'])
def send_message():
    """
    Gửi message trong conversation
    
    Request body:
    {
        "session_id": "uuid",
        "question": "Câu hỏi của user",
        "use_memory": true,  # Có dùng conversation memory không
        "message_type": "query"  # "query" (default) hoặc "chitchat" (không retrieve từ vector DB)
    }
    
    Returns:
        {
            "status": "success",
            "data": {
                "turn_number": 1,
                "user_query": "...",
                "ai_response": "...",
                "citations": [...],
                "tokens_used": {
                    "query_tokens": 10,
                    "response_tokens": 50,
                    "total_tokens": 60
                }
            }
        }
    """
    email, status_code, response = get_auth_email()
    if email is None:
        return response, status_code
    
    try:
        data = request.get_json()
        if not data:
            return {
                "status": "error",
                "message": "Request body is required"
            }, 400
        
        session_id = data.get('session_id')
        question = data.get('question', '').strip()
        use_memory = data.get('use_memory', True)
        message_type = data.get('message_type', 'query').lower()
        keywords = data.get('keywords') or []
        if message_type not in ['query', 'chitchat']:
            message_type = 'query'
        if message_type == 'chitchat':
            use_memory = False
        
        # Validate inputs
        if not session_id:
            return {
                "status": "error",
                "message": "session_id is required"
            }, 400
        
        if not question:
            return {
                "status": "error",
                "message": "question cannot be empty"
            }, 400
        
        # Sanitize input
        question = security_manager.sanitize_user_input(question)

        # Sanitize keywords (optional) for retrieval augmentation
        sanitized_keywords = []
        if isinstance(keywords, list):
            for kw in keywords[:10]:  # hard cap
                if not isinstance(kw, str):
                    continue
                kw = kw.strip()
                if not kw:
                    continue
                kw = security_manager.sanitize_user_input(kw, max_length=80)
                if kw:
                    sanitized_keywords.append(kw)
        
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            return {
                "status": "error",
                "message": "Session not found"
            }, 404
        
        # Validate access
        db_session_id = session.get('db_id')
        if not security_manager.validate_access(email, session_id, db_session_id):
            return {
                "status": "error",
                "message": "Unauthorized access"
            }, 403
        
        # Rate limiting
        if not security_manager.check_rate_limit(
            email,
            'message_sent',
            max_attempts=MAX_REQUESTS_PER_HOUR,
            time_window_seconds=SECONDS_PER_HOUR
        ):
            return {
                "status": "error",
                "message": "Rate limit exceeded"
            }, 429
        
        # Measure API call time
        start_time = time.time()
        
        # Get conversation context (if memory enabled)
        context_for_llm = question
        retrieved_context = ""
        citations = []
        
        if use_memory:
            # Get recent conversation context
            memory_context, memory_tokens, memory_info = memory_manager.get_conversation_context(
                session_id, db_session_id, max_turns=3
            )
            if memory_context:
                context_for_llm = f"{memory_context}\n\nUser's new question: {question}"
        
        # Retrieve relevant documents from vector DB
        retrieval_query = question
        if sanitized_keywords:
            retrieval_query = f"{question}\nKeywords: {', '.join(sanitized_keywords)}"

        output = [] if message_type == 'chitchat' else vectordb.similarity_search(retrieval_query, k=2)
        
        for doc in output:
            result_string = doc.page_content
            index = result_string.find("noidung: ")
            if index != -1:
                result_string = result_string[index + len("noidung: "):].strip()
            result_string = result_string.replace("\n", " ")
            result_string = re.sub(r"\s+", r" ", result_string)
            retrieved_context += f"{result_string} "
            
            citations.append({
                "mapc": doc.metadata.get("mapc", doc.metadata.get("dieu_title", "")),
                "_link": doc.metadata.get("_link", ""),
                "chude_id": doc.metadata.get("chude_id", ""),
                "demuc_id": doc.metadata.get("demuc_id", ""),
                "ten": doc.metadata.get("ten", doc.metadata.get("demuc_name", "")),
                "noidung": result_string
            })
        
        retrieved_context = retrieved_context.strip()
        
        # Prepare prompt for AI
        # IMPORTANT: include conversation context when memory is enabled.
        if retrieved_context:
            prompt = (
                f"[CONTEXT TỪ HỘI THOẠI]\n{context_for_llm}\n\n"
                f"[TÀI LIỆU PHÁP LUẬT LIÊN QUAN]\n{retrieved_context}\n\n"
                f"[YÊU CẦU]\nHãy trả lời câu hỏi của người dùng một cách rõ ràng, có dẫn chiếu điều luật nếu phù hợp."
            )
        else:
            prompt = (
                f"[CONTEXT TỪ HỘI THOẠI]\n{context_for_llm}\n\n"
                f"[YÊU CẦU]\nHãy trả lời câu hỏi pháp luật của người dùng một cách rõ ràng."
            )
        
        if message_type == 'chitchat':
            prompt = (
                "You are a friendly assistant. Reply briefly and politely. "
                "If the user asks outside legal scope, gently remind that you focus on legal questions.\n\n"
                f"Question: {question}"
            )
            citations = []

        # System prompt for legal advisor
        system_prompt = """Bạn là một trợ lý AI chuyên tư vấn pháp luật Việt Nam.

Hướng dẫn:
1. Trả lời rõ ràng, chính xác và dễ hiểu bằng Tiếng Việt
2. Luôn trích dẫn các điều luật, khoản, điểm liên quan khi có
3. Nếu câu hỏi liên quan đến nhiều luật, hãy liệt kê tất cả các quy định có liên quan
4. Giải thích thuật ngữ pháp luật khi cần thiết
5. Nếu chưa rõ về tình huống cụ thể, hãy hỏi thêm chi tiết
6. Lưu ý: Đây là thông tin pháp luật tổng quát, không phải lời khuyên pháp lý chính thức. Các trường hợp cụ thể nên tham khảo luật sư chuyên môn."""

        # Get AI response
        try:
            gemini_response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                )
            )
            ai_response = gemini_response.text
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return {
                "status": "error",
                "message": f"AI service error: {str(e)}"
            }, 503
        
        if not ai_response:
            return {
                "status": "error",
                "message": "Failed to generate response"
            }, 500
        
        # Calculate tokens (approximate)
        api_response_time_ms = int((time.time() - start_time) * 1000)
        query_tokens = memory_manager.estimate_tokens(question)
        response_tokens = memory_manager.estimate_tokens(ai_response)
        
        # Get turn number
        session_obj = ConversationSession.get_by_id(db_session_id)
        turn_number = session_obj.message_count + 1
        
        # Save message to session
        message_id = session_manager.add_message_to_session(
            session_id=session_id,
            turn_number=turn_number,
            user_query=question,
            ai_response=ai_response,
            citations=citations,
            email=email,
            tokens_info={
                'query_tokens': query_tokens,
                'response_tokens': response_tokens,
                'api_response_time_ms': api_response_time_ms
            }
        )
        
        if not message_id:
            return {
                "status": "error",
                "message": "Failed to save message"
            }, 500
        
        # Check if summary is needed
        if memory_manager.should_create_summary(db_session_id):
            full_context, _, _ = memory_manager.get_conversation_context(
                session_id, db_session_id
            )
            summary_result = memory_manager.create_summary(
                session_id, db_session_id, full_context
            )
            if summary_result:
                logger.info(f"Created summary for session {session_id}")
        
        # Log security event
        security_manager.log_security_event(
            email=email,
            session=session_obj,
            action='message_sent',
            status='success'
        )
        
        response_data = {
            "status": "success",
            "data": {
                "message_id": message_id,
                "turn_number": turn_number,
                "user_query": question,
                "ai_response": ai_response,
                "citations": citations,
                "tokens_used": {
                    "query_tokens": query_tokens,
                    "response_tokens": response_tokens,
                    "total_tokens": query_tokens + response_tokens
                },
                "api_response_time_ms": api_response_time_ms
            }
        }
        
        return response_data, 200
    
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to send message: {str(e)}"
        }, 500


@chat_bp.route('/message/store', methods=['POST'])
def store_message():
    """
    Lưu một message vào session mà không gọi AI.
    Dùng cho flow legal_unclear (clarification) để vẫn giữ được hội thoại/memory.

    Request body:
    {
        "session_id": "uuid",
        "user_query": "...",
        "ai_response": "...",
        "citations": [] (optional)
    }
    """
    email, status_code, response = get_auth_email()
    if email is None:
        return response, status_code

    try:
        data = request.get_json()
        if not data:
            return {"status": "error", "message": "Request body is required"}, 400

        session_id = data.get('session_id')
        user_query = (data.get('user_query') or '').strip()
        ai_response = (data.get('ai_response') or '').strip()
        citations = data.get('citations') or []

        if not session_id:
            return {"status": "error", "message": "session_id is required"}, 400
        if not user_query:
            return {"status": "error", "message": "user_query cannot be empty"}, 400
        if not ai_response:
            return {"status": "error", "message": "ai_response cannot be empty"}, 400

        user_query = security_manager.sanitize_user_input(user_query)

        session = session_manager.get_session(session_id)
        if not session:
            return {"status": "error", "message": "Session not found"}, 404

        db_session_id = session.get('db_id')
        if not security_manager.validate_access(email, session_id, db_session_id):
            return {"status": "error", "message": "Unauthorized access"}, 403

        session_obj = ConversationSession.get_by_id(int(db_session_id))
        turn_number = session_obj.message_count + 1

        message_id = session_manager.add_message_to_session(
            session_id=session_id,
            turn_number=turn_number,
            user_query=user_query,
            ai_response=ai_response,
            citations=citations,
            email=email,
            tokens_info={
                'query_tokens': memory_manager.estimate_tokens(user_query),
                'response_tokens': memory_manager.estimate_tokens(ai_response),
                'api_response_time_ms': 0
            }
        )

        if not message_id:
            return {"status": "error", "message": "Failed to save message"}, 500

        security_manager.log_security_event(
            email=email,
            session=session_obj,
            action='message_stored',
            status='success'
        )

        return {
            "status": "success",
            "data": {
                "message_id": message_id,
                "turn_number": turn_number,
                "user_query": user_query,
                "ai_response": ai_response,
                "citations": citations
            }
        }, 200

    except Exception as e:
        logger.error(f"Error storing message: {str(e)}")
        return {"status": "error", "message": f"Failed to store message: {str(e)}"}, 500


@chat_bp.route('/session/<session_id>/memory', methods=['GET'])
def get_session_memory(session_id):
    """
    Lấy memory/summary của session
    
    Returns:
        {
            "status": "success",
            "data": {
                "version": 1,
                "summary": "...",
                "key_topics": [...],
                "important_facts": [...]
            }
        }
    """
    email, status_code, response = get_auth_email()
    if email is None:
        return response, status_code
    
    try:
        session = session_manager.get_session(session_id)
        if not session:
            return {
                "status": "error",
                "message": "Session not found"
            }, 404
        
        db_session_id = session.get('db_id')
        if not security_manager.validate_access(email, session_id, db_session_id):
            return {
                "status": "error",
                "message": "Unauthorized access"
            }, 403
        
        memory = memory_manager.get_memory(session_id, db_session_id)
        
        if not memory:
            return {
                "status": "success",
                "data": None,
                "message": "No memory created yet"
            }, 200
        
        return {
            "status": "success",
            "data": memory
        }, 200
    
    except Exception as e:
        logger.error(f"Error getting session memory: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get memory: {str(e)}"
        }, 500


@chat_bp.route('/session/<session_id>/clear', methods=['POST'])
def clear_session(session_id):
    """
    Clear messages trong session (giữ metadata)
    
    Returns:
        {
            "status": "success",
            "message": "Session cleared"
        }
    """
    email, status_code, response = get_auth_email()
    if email is None:
        return response, status_code
    
    try:
        session = session_manager.get_session(session_id)
        if not session:
            return {
                "status": "error",
                "message": "Session not found"
            }, 404
        
        db_session_id = session.get('db_id')
        if not security_manager.validate_access(email, session_id, db_session_id):
            return {
                "status": "error",
                "message": "Unauthorized access"
            }, 403
        
        success = session_manager.clear_session(session_id)
        
        if success:
            session_obj = ConversationSession.get_by_id(db_session_id)
            security_manager.log_security_event(
                email=email,
                session=session_obj,
                action='session_cleared',
                status='success'
            )
            
            return {
                "status": "success",
                "message": "Session cleared successfully"
            }, 200
        else:
            return {
                "status": "error",
                "message": "Failed to clear session"
            }, 500
    
    except Exception as e:
        logger.error(f"Error clearing session: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to clear session: {str(e)}"
        }, 500


@chat_bp.route('/session/<session_id>/delete', methods=['DELETE'])
def delete_session(session_id):
    """
    Xóa hoàn toàn một session
    
    Returns:
        {
            "status": "success",
            "message": "Session deleted"
        }
    """
    email, status_code, response = get_auth_email()
    if email is None:
        return response, status_code
    
    try:
        session = session_manager.get_session(session_id)
        if not session:
            return {
                "status": "error",
                "message": "Session not found"
            }, 404
        
        db_session_id = session.get('db_id')
        if not security_manager.validate_access(email, session_id, db_session_id):
            return {
                "status": "error",
                "message": "Unauthorized access"
            }, 403

        # Capture session object for audit logging BEFORE deletion.
        # After deletion, ConversationSession.get_by_id(db_session_id) will raise DoesNotExist.
        session_obj = None
        try:
            session_obj = ConversationSession.get_by_id(int(db_session_id))
        except Exception:
            session_obj = None

        success = session_manager.delete_session(session_id)

        if success:
            security_manager.log_security_event(
                email=email,
                session=session_obj,
                action='session_deleted',
                status='success'
            )

            return {
                "status": "success",
                "message": "Session deleted successfully"
            }, 200
        else:
            return {
                "status": "error",
                "message": "Failed to delete session"
            }, 500
    
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to delete session: {str(e)}"
        }, 500


@chat_bp.route('/security/logs', methods=['GET'])
def get_security_logs():
    """
    Lấy security logs của user
    
    Query params:
        limit: số logs cần lấy (default: 50)
    
    Returns:
        {
            "status": "success",
            "data": [...]
        }
    """
    email, status_code, response = get_auth_email()
    if email is None:
        return response, status_code
    
    try:
        limit = request.args.get('limit', default=50, type=int)
        limit = min(max(limit, 1), 500)
        
        logs = security_manager.get_security_logs(email, limit)
        
        return {
            "status": "success",
            "data": logs,
            "count": len(logs)
        }, 200
    
    except Exception as e:
        logger.error(f"Error getting security logs: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get logs: {str(e)}"
        }, 500
