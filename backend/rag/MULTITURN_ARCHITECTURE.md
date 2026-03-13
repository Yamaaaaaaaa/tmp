# Multi-Turn Conversation System Documentation

## Giới thiệu

Hệ thống đã được mở rộng để hỗ trợ **multi-turn conversations** (chat nhiều lần trong một session) và **AI memory** (LLM có thể nhớ ngữ cảnh cuộc trò chuyện). Điều này cho phép trải nghiệm tương tác tốt hơn khi thảo luận các vấn đề pháp luật phức tạp.

## Kiến trúc Hệ thống

### Backend Stack
- **Flask** (Python) - REST API server
- **MySQL** - Persistent storage cho conversations & metadata
- **Redis** - Cache layer cho performance
- **ChromaDB** - Vector database cho legal documents
- **Gemini API** - LLM cho generating responses

### Database Schema

#### 1. **ConversationSession**
Đại diện cho một phiên chat của user
```sql
- session_id (UUID)
- email (user identifier)
- session_name (tên phiên)
- message_count (số lần trò chuyện)
- total_tokens_used (tokens đã dùng)
- last_message_at (tin nhắn cuối)
- status (active/archived/deleted)
```

#### 2. **ConversationMessage**
Lưu trữ từng Q&A turn
```sql
- session_id (FK)
- turn_number (lượt 1, 2, 3...)
- user_query (câu hỏi)
- ai_response (câu trả lời)
- retrieved_context (văn bản pháp luật được lấy)
- citations (JSON: references)
- tokens_used (query_tokens, response_tokens)
- api_response_time_ms
```

#### 3. **ConversationMemory**
Lưu trữ summarized conversation context
```sql
- session_id (FK)
- conversation_summary (tóm tắt cuộc trò chuyện)
- key_topics (các chủ đề chính)
- important_facts (sự kiện quan trọng)
- current_context_length (token count)
- is_context_summarized (đã tóm tắt)
- version (phiên bản của memory)
```

#### 4. **SecurityLog**
Audit trail cho security monitoring
```sql
- email (user)
- action (message_sent, session_cleared, etc.)
- status (success/failed)
- ip_address
- timestamp
```

## API Endpoints

### Session Management

#### 1. Tạo Session Mới
```bash
POST /api/v2/chat/session/create
Authorization: Bearer <token>

Body:
{
  "session_name": "Tư vấn về hợp đồng lao động"
}

Response:
{
  "status": "success",
  "data": {
    "session_id": "uuid-xxx",
    "session_name": "Tư vấn về hợp đồng lao động",
    "created_at": "2024-03-13T10:30:00"
  }
}
```

#### 2. Lấy Danh Sách Sessions
```bash
GET /api/v2/chat/session/list
Authorization: Bearer <token>

Response:
{
  "status": "success",
  "data": [
    {
      "session_id": "uuid-1",
      "session_name": "Session 1",
      "message_count": 5,
      "total_tokens": 1200,
      "last_message_at": "timestamp"
    }
  ],
  "count": 1
}
```

### Message Exchange

#### 3. Gửi Message (Multi-turn)
```bash
POST /api/v2/chat/message/send
Authorization: Bearer <token>

Body:
{
  "session_id": "uuid-xxx",
  "question": "Hỏi gì đó về pháp luật",
  "use_memory": true
}

Response:
{
  "status": "success",
  "data": {
    "message_id": 123,
    "turn_number": 1,
    "user_query": "...",
    "ai_response": "...",
    "citations": [...],
    "tokens_used": {
      "query_tokens": 10,
      "response_tokens": 50,
      "total_tokens": 60
    },
    "api_response_time_ms": 3500
  }
}
```

#### 4. Lấy Messages Trong Session
```bash
GET /api/v2/chat/session/{session_id}/messages?limit=10
Authorization: Bearer <token>

Response:
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
  ],
  "count": 1
}
```

### Memory Management

#### 5. Lấy Conversation Memory/Summary
```bash
GET /api/v2/chat/session/{session_id}/memory
Authorization: Bearer <token>

Response:
{
  "status": "success",
  "data": {
    "version": 1,
    "summary": "Tóm tắt cuộc trò chuyện...",
    "key_topics": ["Điều 36 - Luật Lao động", ...],
    "important_facts": ["Sự kiện quan trọng 1", ...]
  }
}
```

### Session Control

#### 6. Clear Session (Xóa messages nhưng giữ metadata)
```bash
POST /api/v2/chat/session/{session_id}/clear
Authorization: Bearer <token>

Response:
{
  "status": "success",
  "message": "Session cleared successfully"
}
```

#### 7. Delete Session (Xóa hoàn toàn)
```bash
DELETE /api/v2/chat/session/{session_id}/delete
Authorization: Bearer <token>

Response:
{
  "status": "success",
  "message": "Session deleted successfully"
}
```

## Xử lý Các Vấn Đề Chính

### 1. Quản Lý Trạng Thái (Session State Management)

#### Vấn đề
- Cần bảo tồn trạng thái cuộc trò chuyện qua nhiều requests
- Đảm bảo consistency của dữ liệu

#### Giải Pháp
```python
# SessionManager xử lý:
1. Cache session info vào Redis (high-speed access)
2. Persist session data vào MySQL (durability)
3. Auto-timeout sessions sau 24 giờ
4. Atomic operations để tránh race conditions

# Cấu trúc:
- Redis: Cache layer (TTL: 24h)
  - session:{session_id} → session metadata
  - session_messages:{session_id} → recent messages
  
- MySQL: Persistent storage
  - ConversationSession table
  - ConversationMessage table
```

### 2. Memory cho LLM (Token & Context Management)

#### Vấn Đề
- Gemini API có token limit (~1M tokens)
- Longer conversations = higher costs
- Need to balance context richness with efficiency

#### Giải Pháp
```python
# MemoryManager xử lý:

1. **Token Tracking**
   - Estimate tokens cho mỗi message
   - Track cumulative token usage
   - Alert when approaching limits

2. **Context Window Management**
   - Default max context: 4000 tokens
   - Keep recent messages in full
   - Summarize older messages

3. **Adaptive Summarization**
   - Create summary khi:
     - Message count > 15
     - Total tokens > 80% of max
   - Use Gemini để tạo intelligent summary
   - Preserve key topics & facts

4. **Cấu trúc**
   - Full messages: Last 10 turns
   - Summarized: Turns 1-N (summarized)
   - Key topics & facts: Indexed for quick reference
```

**Example:**
```
Turn 1-5: [Full conversation text] - 800 tokens
Turn 6-10: [Full conversation text] - 900 tokens
Turn 11-20: [SUMMARIZED] - 200 tokens
Key Topics: Điều 36 (Luật Lao động), Hợp đồng không xác định kỳ hạn
```

### 3. Bảo Mật & Riêng Tư (Security & Privacy)

#### Vấn Đề
- Conversations có thể chứa sensitive data
- Unauthorized access to conversations
- Data breaches

#### Giải Pháp
```python
# SecurityManager xử lý:

1. **Access Control**
   - Email-based access validation
   - JWT token verification
   - Per-session access checks
   - Return 403 Forbidden if unauthorized

2. **Data Encryption**
   - Encryption key: Set in env variables
   - Fernet (symmetric) encryption
   - Can be extended to field-level encryption

3. **Input Sanitization**
   - Remove dangerous characters
   - Limit input length (5000 chars)
   - Allow Vietnamese characters
   - Prevent injection attacks

4. **Audit Logging**
   - Log all sensitive actions:
     - message_sent
     - session_created/deleted
     - unauthorized_access_attempt
   - 12-month retention

5. **Rate Limiting**
   - 100 requests/hour per user
   - 500 requests/day per user
   - Check via SecurityLog

6. **Data Retention & Purge**
   - Conversations: 90 days
   - Backups: 180 days
   - Deleted data: 7-day purge
   - Security logs: 365 days
```

**Security Flow:**
```
1. User sends request → JWT validation
2. Extract email from token
3. Check session ownership (email match)
4. Validate rate limits
5. Sanitize inputs
6. Log security event
7. Execute operation
8. Return response
```

### 4. Hiệu Suất (Performance Optimization)

#### Vấn Đề
- Longer context → slower API calls
- Database queries могут bị slow
- Memory usage с large conversations

#### Giải Pháp
```python
# Architecture:

1. **Multi-layer Caching**
   - Redis L1: Session metadata (fast retrieval)
   - Redis L2: Recent messages (fast history)
   - MySQL L3: Full persistent storage
   - ChromaDB: Vector search index

2. **Query Optimization**
   - Index on: email, session_id, turn_number
   - Limit query results (pagination)
   - Use compound indexes

3. **Response Time Optimization**
   - Track API response time for each message
   - Implement connection pooling
   - Use async operations where possible
   - Batch database operations

4. **Memory Optimization**
   - Summarize old messages periodically
   - Compress stored context
   - Archive old sessions (move to archive table)
   - Clean up expired cache entries
```

**Performance Metrics**
```
Expected response times:
- Create session: ~50ms
- Send message: 3-5 seconds (API call time)
- Get messages: ~100-200ms
- Create summary: ~2-3 seconds

Token efficiency:
- Without summary: 800+ tokens per turn
- With summary: 300-500 tokens per turn
- Savings: ~40-50% tokens từ older messages
```

### 5. Xử Lý Ngữ Cảnh Dài (Long Context Handling)

#### Vấn Đề
- LLM token limits (1M for Gemini)
- Cost increases with context length
- Quality may degrade with very long context

#### Giải Pháp
```python
# Token Management Strategy:

1. **Progressive Summarization**
   - First 5 turns: Full context (provide detail)
   - Turns 6-10: Full context (still important)
   - Turns 11+: Summarized context (save tokens)
   - Key facts: Always included

2. **Context Truncation**
   - If context > max_tokens:
     - Keep recent messages (full)
     - Summarize older messages
     - If still over limit, use only summary + recent

3. **Smart Context Selection**
   ```python
   context = []
   
   # Add conversation summary (if exists)
   if memory:
       context.append(f"[SUMMARY]\n{memory.summary}\n\n")
   
   # Add recent messages (full)
   for msg in recent_messages:
       context.append(f"[Turn {msg.turn}]\nUser: ...\nAssistant: ...\n")
   
   # Add current query
   context.append(f"[Current Query]\n{current_query}")
   ```

4. **Monitoring**
   - Alert at 80% token usage
   - Auto-summarize at 85%
   - Reject at 95%

## Frontend Integration

### Using ChatService

```typescript
import chatService from '@/services/chat.service';

// Create new session
const response = await chatService.createSession("My Legal Issue");
const sessionId = response.data.session_id;

// Send first message
const msg1 = await chatService.sendMessage(
  sessionId,
  "I have a question about labor law",
  true // useMemory
);

// Follow-up question (AI remembers context)
const msg2 = await chatService.sendMessage(
  sessionId,
  "Can you explain Article 36 in more detail?",
  true
);

// Get all messages in session
const messages = await chatService.getSessionMessages(sessionId);

// Get conversation summary
const memory = await chatService.getSessionMemory(sessionId);
```

## Configuration

### Environment Variables
```bash
# Session Management
SESSION_TIMEOUT_HOURS=24
MAX_CONTEXT_TOKENS=4000

# Rate Limiting
MAX_REQUESTS_PER_HOUR=100
MAX_REQUESTS_PER_DAY=500

# Security
ENCRYPTION_KEY=<generated-key>

# Data Retention
CONVERSATION_RETENTION_DAYS=90
SECURITY_LOG_RETENTION_DAYS=365
```

### Generate Encryption Key
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Monitoring & Maintenance

### Key Metrics to Monitor
1. **Token Usage**
   - Avg tokens per session
   - Trending token growth
   - Cost estimation

2. **Performance**
   - API response time
   - Database query time
   - Cache hit rate

3. **Security**
   - Failed login attempts
   - Unauthorized access attempts
   - Rate limit violations

4. **Storage**
   - Database size growth
   - Redis memory usage
   - Conversation archive size

### Maintenance Tasks
```bash
# Backup conversations
mysqldump -h qna-mysql -u root -p qna > backup.sql

# Archive old sessions (90+ days)
UPDATE ConversationSession 
SET status = 'archived' 
WHERE DATEDIFF(NOW(), last_message_at) > 90;

# Clean up expired cache
redis-cli FLUSHDB ASYNC

# Review security logs
SELECT COUNT(*), action, status 
FROM SecurityLog 
GROUP BY action, status;
```

## Testing

### Unit Tests
```python
# Test SessionManager
def test_create_session():
    session_id = session_manager.create_session("test@example.com")
    assert session_id is not None

# Test MemoryManager
def test_context_truncation():
    context, tokens, info = memory_manager.get_conversation_context(
        session_id, db_session_id
    )
    assert tokens <= 4000

# Test SecurityManager
def test_access_validation():
    is_valid = security_manager.validate_access(
        email, session_id, db_session_id
    )
    assert is_valid == True
```

### Integration Tests
```bash
# Create session & send messages
curl -X POST http://localhost:5001/api/v2/chat/session/create \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"session_name": "Test"}'

# Send message
curl -X POST http://localhost:5001/api/v2/chat/message/send \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "...", "question": "..."}'
```

## Migration from Single-turn to Multi-turn

### For Existing Users
- Old `/api/v1/question` endpoint still works
- New `/api/v2/chat` endpoints available in parallel
- Support both for backward compatibility

### Migration Steps
1. Update frontend to use new ChatService
2. Create sessions for each user
3. Map old questions to new message format
4. Test with sample conversations

## Troubleshooting

### Common Issues

**1. Token limit exceeded**
```
Solution: Summary was not created in time
Fix: Manually trigger summary creation
  memory_manager.create_summary(session_id, db_session_id, context)
```

**2. Session not found (404)**
```
Solution: Session expired (>24 hours) or deleted
Fix: Create new session
```

**3. Rate limit exceeded (429)**
```
Solution: Too many requests in time window
Fix: Wait before sending new requests
     Or increase MAX_REQUESTS_PER_HOUR in config
```

**4. Unauthorized access (403)**
```
Solution: Accessing someone else's session
Fix: Verify session_id belongs to authenticated user
```

## Future Enhancements

1. **Advanced Summarization**
   - Extractive + abstractive summaries
   - Legal-specific summary templates
   - Multi-language support

2. **Conversation Analytics**
   - Most asked questions
   - User interaction patterns
   - Legal topic trends

3. **Persistent Memory**
   - User preferences
   - Favorite legal references
   - Custom knowledge base

4. **Collaborative Features**
   - Share conversations with lawyers
   - Threaded discussions
   - Real-time collaboration

5. **Enhanced Search**
   - Full-text search in conversations
   - Semantic search across sessions
   - Citation-based retrieval

## Support & Best Practices

### Best Practices
1. Always set `use_memory=true` for contextual conversations
2. Create new session for new legal issue
3. Check session memory before complex questions
4. Monitor token usage in admin panel
5. Archive sessions periodically

### Getting Help
- Check logs: `/var/log/qna-service.log`
- Review API responses for error details
- Check security logs for access issues
- Contact system administrator

---

**Version**: 1.0  
**Last Updated**: March 13, 2024  
**Maintained by**: VNLawAdvisor Team
