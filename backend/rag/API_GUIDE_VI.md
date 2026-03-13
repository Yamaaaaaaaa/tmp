# Hướng Dẫn Sử Dụng API Multi-turn Chat

## Tổng Quan

Hệ thống đã được nâng cấp để hỗ trợ:
- ✅ **Chat nhiều lần** trong một session
- ✅ **AI Memory** - LLM nhớ context của cuộc trò chuyện
- ✅ **Token Management** - Tự động quản lý độ dài context
- ✅ **Security** - Mã hóa dữ liệu, audit logging
- ✅ **Performance** - Cache tối ưu, summarization thông minh

## Quick Start

### 1. Tạo Session Mới
```bash
curl -X POST http://localhost:5001/api/v2/chat/session/create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_name": "Tư vấn Luật Lao Động"
  }'
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "session_name": "Tư vấn Luật Lao Động",
    "created_at": "2024-03-13T10:30:00.000Z"
  }
}
```

### 2. Gửi Câu Hỏi (Lần 1)
```bash
curl -X POST http://localhost:5001/api/v2/chat/message/send \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "question": "Tôi bị sa thải không có lý do, tôi có thể kiện được không?",
    "use_memory": true
  }'
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "message_id": 1,
    "turn_number": 1,
    "user_query": "Tôi bị sa thải không có lý do, tôi có thể kiện được không?",
    "ai_response": "Theo Luật Lao động 2020... [chi tiết]",
    "citations": [
      {
        "mapc": "Điều 36",
        "ten": "Luật Lao động 2020",
        "noidung": "Quyền bảo vệ khi sa thải..."
      }
    ],
    "tokens_used": {
      "query_tokens": 15,
      "response_tokens": 280,
      "total_tokens": 295
    },
    "api_response_time_ms": 3500
  }
}
```

### 3. Gửi Câu Hỏi Follow-up (Lần 2)
```bash
curl -X POST http://localhost:5001/api/v2/chat/message/send \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "question": "Mức bồi thường tối thiểu là bao nhiêu?",
    "use_memory": true
  }'
```

**AI sẽ nhớ context từ câu hỏi trước và trả lời liên quan hơn!**

### 4. Xem Lịch Sử Chat
```bash
curl -X GET "http://localhost:5001/api/v2/chat/session/123e4567-e89b-12d3-a456-426614174000/messages?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. Xem Tóm Tắt Cuộc Trò Chuyện
```bash
curl -X GET "http://localhost:5001/api/v2/chat/session/123e4567-e89b-12d3-a456-426614174000/memory" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "version": 1,
    "summary": "Người dùng tìm hiểu về quyền bảo vệ khi bị sa thải...",
    "key_topics": ["Điều 36 - Luật Lao động", "Bồi thường"],
    "important_facts": ["Mức bồi thường tối thiểu", "Thủ tục khiếu nại"]
  }
}
```

## Các Endpoint Chính

### Session Management

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/v2/chat/session/create` | Tạo session mới |
| GET | `/api/v2/chat/session/list` | Lấy danh sách sessions |
| GET | `/api/v2/chat/session/{id}/messages` | Lấy messages trong session |
| GET | `/api/v2/chat/session/{id}/memory` | Lấy tóm tắt cuộc trò chuyện |
| POST | `/api/v2/chat/session/{id}/clear` | Xóa messages (giữ metadata) |
| DELETE | `/api/v2/chat/session/{id}/delete` | Xóa session hoàn toàn |

### Chat

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/v2/chat/message/send` | Gửi message |

### Security

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/v2/chat/security/logs` | Xem security logs |

## Tính Năng Chính

### 1. Multi-turn Conversation
```
Turn 1: User: "Tôi bị sa thải không?"
        AI: "Có nhiều cách..."
        
Turn 2: User: "Mức bồi thường là?"
        AI: "Dựa vào câu trò chuyện trước, mức bồi thường..."
        
Turn 3: User: "Tôi cần làm gì?"
        AI: "Bước 1..., Bước 2..., ..."
```

### 2. Automatic Memory Management
- **Tự động tóm tắt** khi cuộc trò chuyện dài (>15 turns)
- **Giữ context quan trọng** suốt cuộc trò chuyện
- **Giảm token cost** đến 40-50%

### 3. Security Features
- 🔒 **Encryption** - Dữ liệu được mã hóa
- 🛡️ **Access Control** - Chỉ chủ session mới xem được
- 📝 **Audit Logs** - Tất cả hoạt động được ghi lại
- 🚫 **Rate Limiting** - Giới hạn request

### 4. Performance Optimization
- ⚡ **Redis Caching** - High-speed session access
- 📊 **Token Tracking** - Monitor chi phí API
- ⏱️ **Response Timing** - Track hiệu suất

## Các Lỗi Thường Gặp

### 401 - Unauthorized
```
Lỗi: "Missing or invalid authorization token"
Giải pháp: Kiểm tra JWT token, chắc chắn nó còn hiệu lực
```

### 403 - Forbidden
```
Lỗi: "Unauthorized access"
Giải pháp: Bạn không sở hữu session này, dùng session của riêng bạn
```

### 404 - Not Found
```
Lỗi: "Session not found"
Giải pháp: Session đã hết hạn (24 giờ) hoặc đã bị xóa, tạo session mới
```

### 429 - Too Many Requests
```
Lỗi: "Rate limit exceeded"
Giải pháp: Bạn gửi quá nhiều request, chờ trước khi gửi tiếp

Giới hạn:
- 100 requests/hour
- 500 requests/day
```

### 503 - Service Unavailable
```
Lỗi: "AI service error"
Giải pháp: Gemini API không khả dụng, thử lại sau vài phút
```

## Best Practices

### ✅ Nên Làm

1. **Tạo session để mỗi vấn đề khác nhau**
   ```
   Session 1: Tư vấn Luật Lao Động
   Session 2: Tư vấn Luật Dân Sự
   Session 3: Tư vấn Luật Hình Sự
   ```

2. **Dùng memory cho conversation liên tục**
   ```javascript
   use_memory: true // Bật để AI nhớ context
   ```

3. **Kiểm tra message history trước khi xóa**
   ```bash
   # Lấy messages trước khi clear
   GET /api/v2/chat/session/{id}/messages
   
   # Sau đó clear nếu chắc chắn
   POST /api/v2/chat/session/{id}/clear
   ```

4. **Monitor token usage**
   - Kiểm tra `tokens_used` trong response
   - Thường ~100-300 tokens per message
   - Over 400 tokens = nên archive session

### ❌ Không Nên Làm

1. ❌ Reuse session cho vấn đề khác nhau
   ```javascript
   // SAI
   chatService.sendMessage(sessionId, "Hỏi về luật hôn nhân");
   chatService.sendMessage(sessionId, "Hỏi về luật đất đai"); // Sai!
   
   // ĐÚNG
   session1 = createSession("Hôn nhân");
   session2 = createSession("Đất đai");
   ```

2. ❌ Ignore security logs
   - Luôn check logs để phát hiện unauthorized access

3. ❌ Store sensitive data in memory
   - Conversation có thể được archive
   - Không nên đưa số CMT, tài khoản ngân hàng, etc.

4. ❌ Forget to handle rate limits
   - Implement retry logic with exponential backoff

## TypeScript Frontend Example

```typescript
import chatService from '@/services/chat.service';

export default function LegalAdvisor() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  // Create session when component mounts
  useEffect(() => {
    const createNewSession = async () => {
      const resp = await chatService.createSession('Legal Consultation');
      setSessionId(resp.data.session_id);
    };
    createNewSession();
  }, []);

  // Send message
  const handleSendMessage = async (question: string) => {
    if (!sessionId) return;
    
    setLoading(true);
    try {
      const resp = await chatService.sendMessage(
        sessionId,
        question,
        true // use memory
      );
      
      if (resp.status === 'success') {
        const newMessage = resp.data;
        setMessages(prev => [...prev, {
          role: 'user',
          content: newMessage.user_query
        }, {
          role: 'assistant',
          content: newMessage.ai_response,
          citations: newMessage.citations
        }]);
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {messages.map((msg, idx) => (
        <div key={idx} className={msg.role}>
          {msg.content}
          {msg.citations && (
            <div className="citations">
              {msg.citations.map(citation => (
                <p key={citation.mapc}>📄 {citation.ten}</p>
              ))}
            </div>
          )}
        </div>
      ))}
      <input
        onKeyPress={(e) => {
          if (e.key === 'Enter') {
            handleSendMessage(e.currentTarget.value);
            e.currentTarget.value = '';
          }
        }}
        placeholder="Hỏi gì đó..."
        disabled={loading}
      />
    </div>
  );
}
```

## Configuration

### Environment Variables
```bash
# .env file
SESSION_TIMEOUT_HOURS=24
MAX_CONTEXT_TOKENS=4000
MAX_REQUESTS_PER_HOUR=100
ENCRYPTION_KEY=your-encryption-key
```

### Generate Encryption Key
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Monitoring

### Check Token Usage
```python
from models import ConversationSession

session = ConversationSession.get_by_id(1)
print(f"Total tokens: {session.total_tokens_used}")
print(f"Messages: {session.message_count}")
print(f"Avg per message: {session.total_tokens_used / session.message_count}")
```

### View Security Logs
```bash
curl -X GET "http://localhost:5001/api/v2/chat/security/logs?limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Support

Nếu gặp vấn đề:
1. Kiểm tra error message từ API
2. Xem security logs
3. Check application logs: `/var/log/qna-service.log`
4. Contact: support@vnlawadvisor.com

---

**Version**: 1.0  
**Last Updated**: March 13, 2024
