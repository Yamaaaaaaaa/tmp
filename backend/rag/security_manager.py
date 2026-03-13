"""
Security Manager - Xử lý bảo mật, encryption, và audit logging
Đảm bảo dữ liệu nhạy cảm được bảo vệ
"""

import hashlib
import json
import hmac
import time
from typing import Optional, Dict, Any
from datetime import datetime
from cryptography.fernet import Fernet
from models import SecurityLog, ConversationSession, ConversationMessage
import logging
import os
from dotenv import load_dotenv

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

class SecurityManager:
    """Quản lý security, encryption, và audit"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize SecurityManager
        
        Args:
            encryption_key: Encryption key (if None, use env variable)
        """
        # Get encryption key từ environment
        key = encryption_key or os.getenv("ENCRYPTION_KEY")
        
        if not key:
            # Generate a default key (KHÔNG nên dùng cho production)
            logger.warning("No encryption key provided, generating default key")
            key = Fernet.generate_key().decode()
        
        # Strip whitespace and quotes
        key = key.strip().strip('"').strip("'")
        
        # Keep key as string for Fernet - it expects base64 string, not bytes
        if isinstance(key, bytes):
            key = key.decode()
        
        try:
            self.cipher = Fernet(key)
            self.encryption_key = key
            self.encryption_key_bytes = key.encode()
            logger.info("SecurityManager initialized successfully")
        except ValueError as e:
            logger.error(f"Invalid encryption key format: {str(e)}")
            logger.info("Generating new encryption key...")
            key = Fernet.generate_key().decode()
            self.cipher = Fernet(key)
            self.encryption_key = key
            self.encryption_key_bytes = key.encode()
    
    def encrypt_message(self, message: str) -> str:
        """
        Encrypt một message
        
        Args:
            message: Message cần encrypt
            
        Returns:
            Encrypted message (base64 string)
        """
        try:
            encrypted = self.cipher.encrypt(message.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Error encrypting message: {str(e)}")
            raise
    
    def decrypt_message(self, encrypted_message: str) -> str:
        """
        Decrypt một message
        
        Args:
            encrypted_message: Encrypted message
            
        Returns:
            Decrypted message
        """
        try:
            decrypted = self.cipher.decrypt(encrypted_message.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Error decrypting message: {str(e)}")
            raise
    
    def hash_email(self, email: str) -> str:
        """
        Hash email (for privacy)
        
        Args:
            email: Email address
            
        Returns:
            Hashed email
        """
        return hashlib.sha256(email.encode()).hexdigest()[:16]
    
    def validate_access(self, email: str, session_id: str, db_session_id: int) -> bool:
        """
        Validate nếu user có access tới session
        
        Args:
            email: Email của user
            session_id: Redis session ID
            db_session_id: Database session ID
            
        Returns:
            True nếu user có access
        """
        try:
            session = ConversationSession.select().where(
                ConversationSession.id == db_session_id
            ).first()
            
            if not session:
                logger.warning(f"Session {db_session_id} not found")
                return False
            
            # Kiểm tra nếu email của user match với session email
            if session.email != email:
                logger.warning(
                    f"Unauthorized access attempt: {email} tried to access "
                    f"session {session_id} owned by {session.email}"
                )
                self.log_security_event(
                    email=email,
                    session=session,
                    action='unauthorized_access_attempt',
                    status='failed',
                    details=f"Attempted to access session owned by {session.email}"
                )
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating access: {str(e)}")
            return False
    
    def sanitize_user_input(self, text: str, max_length: int = 5000) -> str:
        """
        Sanitize user input để tránh injection attacks
        
        Args:
            text: User input
            max_length: Maximum length allowed
            
        Returns:
            Sanitized text
        """
        try:
            # Limit length
            text = text[:max_length]
            
            # Remove potentially dangerous characters
            # Allow Vietnamese characters, alphanumeric, and basic punctuation
            import re
            # Allow unicode letters (including Vietnamese), numbers, basic punctuation
            text = re.sub(r'[^\w\s\.\,\?\!\-\(\)\:\;\u0100-\u01B0\u1E00-\u1EFF]', '', text)
            
            # Remove multiple spaces
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
        except Exception as e:
            logger.error(f"Error sanitizing input: {str(e)}")
            return text[:max_length]
    
    def validate_session_token(self, token: str, session_id: str) -> bool:
        """
        Validate session token (basic HMAC validation)
        
        Args:
            token: Session token
            session_id: Session ID
            
        Returns:
            True nếu token valid
        """
        try:
            # Generate expected token
            expected_token = hmac.new(
                self.encryption_key_bytes,
                session_id.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Constant-time comparison để tránh timing attacks
            return hmac.compare_digest(token, expected_token)
        except Exception as e:
            logger.error(f"Error validating session token: {str(e)}")
            return False
    
    def generate_session_token(self, session_id: str) -> str:
        """
        Generate session token
        
        Args:
            session_id: Session ID
            
        Returns:
            Session token
        """
        try:
            token = hmac.new(
                self.encryption_key_bytes,
                session_id.encode(),
                hashlib.sha256
            ).hexdigest()
            return token
        except Exception as e:
            logger.error(f"Error generating session token: {str(e)}")
            raise
    
    def log_security_event(self, email: str, session: ConversationSession = None,
                          action: str = None, status: str = None,
                          details: str = None, ip_address: str = None) -> bool:
        """
        Log security event
        
        Args:
            email: User email
            session: ConversationSession instance
            action: Action type
            status: Status (success/failed)
            details: Additional details
            ip_address: User IP address
            
        Returns:
            Success status
        """
        try:
            SecurityLog.create(
                email=email,
                session=session if session else None,
                action=action or "unknown",
                status=status or "unknown",
                ip_address=ip_address,
                details=details
            )
            
            logger.info(f"Security event logged: {email} - {action} - {status}")
            return True
        except Exception as e:
            logger.error(f"Error logging security event: {str(e)}")
            return False

    def log_activity(self, email: str, action: str,
                     metadata: Optional[Dict[str, Any]] = None,
                     session: ConversationSession = None,
                     status: str = "success",
                     ip_address: str = None) -> bool:
        """
        Compatibility wrapper for audit logging.

        Args:
            email: User email
            action: Activity action
            metadata: Optional metadata to serialize into details
            session: ConversationSession instance (optional)
            status: Status (default: success)
            ip_address: User IP address (optional)

        Returns:
            Success status
        """
        details = None
        if metadata is not None:
            try:
                details = json.dumps(metadata, ensure_ascii=False)
            except Exception:
                details = str(metadata)

        return self.log_security_event(
            email=email,
            session=session,
            action=action,
            status=status,
            details=details,
            ip_address=ip_address
        )
    
    def mask_sensitive_data(self, data: Dict[str, Any], 
                           sensitive_keys: list = None) -> Dict[str, Any]:
        """
        Mask sensitive data trong dictionary
        
        Args:
            data: Data dictionary
            sensitive_keys: List of keys to mask
            
        Returns:
            Data với sensitive info masked
        """
        if not sensitive_keys:
            sensitive_keys = ['email', 'password', 'token', 'api_key']
        
        masked_data = {}
        for key, value in data.items():
            if key.lower() in sensitive_keys:
                if isinstance(value, str) and len(value) > 4:
                    masked_data[key] = value[:2] + "***" + value[-2:]
                else:
                    masked_data[key] = "***"
            else:
                masked_data[key] = value
        
        return masked_data
    
    def get_security_logs(self, email: str, limit: int = 100) -> list:
        """
        Get security logs cho user
        
        Args:
            email: User email
            limit: Number of logs
            
        Returns:
            List of security logs
        """
        try:
            logs = SecurityLog.select().where(
                SecurityLog.email == email
            ).order_by(
                SecurityLog.createdAt.desc()
            ).limit(limit)
            
            result = []
            for log in logs:
                result.append({
                    'id': log.id,
                    'action': log.action,
                    'status': log.status,
                    'ip_address': log.ip_address,
                    'details': log.details,
                    'timestamp': log.createdAt.isoformat()
                })
            
            return result
        except Exception as e:
            logger.error(f"Error getting security logs: {str(e)}")
            return []
    
    def check_rate_limit(self, email: str, action: str, 
                        max_attempts: int = 100, 
                        time_window_seconds: int = 3600) -> bool:
        """
        Check rate limiting (simple version using database)
        
        Args:
            email: User email
            action: Action type
            max_attempts: Maximum attempts allowed
            time_window_seconds: Time window in seconds
            
        Returns:
            True nếu under limit, False nếu exceeded
        """
        try:
            # Count recent logs
            import datetime as dt
            recent_time = dt.datetime.now() - dt.timedelta(seconds=time_window_seconds)
            
            count = SecurityLog.select().where(
                (SecurityLog.email == email) &
                (SecurityLog.action == action) &
                (SecurityLog.createdAt >= recent_time)
            ).count()
            
            return count < max_attempts
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return True  # Default to allow on error
    
    def get_data_retention_policy(self) -> Dict[str, Any]:
        """
        Get data retention policy
        
        Returns:
            Retention policy information
        """
        return {
            'conversation_retention_days': _get_env_int("CONVERSATION_RETENTION_DAYS", 90),
            'backup_retention_days': 180,
            'deleted_data_purge_days': 7,
            'security_logs_retention_days': _get_env_int("SECURITY_LOG_RETENTION_DAYS", 365),
            'description': 'Data retention policy for legal advisor system'
        }


# Initialize singleton
security_manager = SecurityManager()
