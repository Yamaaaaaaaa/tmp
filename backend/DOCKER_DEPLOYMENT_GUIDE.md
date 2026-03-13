# Docker Deployment Guide for Multi-turn System

## Tóm Tắt

Khi chạy trong Docker, **không cần thay đổi MySQL** - Docker sẽ tự động:
1. Tạo MySQL container với database `qna`
2. Persist data qua volume: `./rag/qna-sql:/var/lib/mysql`
3. Kết nối tất cả services qua `app-network`

## Bước 1: Sinh Encryption Key

```bash
cd e:\LegalChatbot\vnlawadvisor\backend
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Output:** Copy key này (ví dụ: `gAAAAABl...)` để dùng trong .env

## Bước 2: Cấu hình .env File

```bash
# Tại thư mục: e:\LegalChatbot\vnlawadvisor\backend\

# File: .env
ENCRYPTION_KEY=<paste-key-từ-bước-1>
HF_TOKEN=<your-huggingface-token>
GEMINI_API_KEY=<your-gemini-api-key>
```

## Bước 3: Verify Thay Đổi

### Đã Cập Nhật:
- ✅ `docker-compose.yml` - Thêm 9 environment variables mới
- ✅ `docker-compose.dev.yaml` - Thêm qna-service + environment variables
- ✅ `.env` - Template file để cấu hình
- ✅ `rag/requirements.txt` - Thêm cryptography
- ✅ `rag/models.py` - 5 bảng database mới
- ✅ `rag/session_manager.py` - Session management
- ✅ `rag/memory_manager.py` - Memory & context management
- ✅ `rag/security_manager.py` - Security & encryption
- ✅ `rag/chat_endpoints.py` - 11 API endpoints mới
- ✅ `rag/app.py` - Register chat blueprint

### MySQL - Không Cần Thay Đổi
```yaml
# Đã tồn tại trong docker-compose.yml
qna-mysql:
  image: mysql:latest
  volumes:
    - ./rag/qna-sql:/var/lib/mysql  # Database persisted here
  environment:
    MYSQL_ROOT_PASSWORD: 123456789
    MYSQL_DATABASE: qna
```

## Bước 4: Build & Run Docker

### Production (docker-compose.yml)
```bash
# Build lại Docker image
docker-compose build qna-service

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f qna-service

# Test API
curl -X GET http://localhost:8000/api/v2/chat/session/list \
  -H "Authorization: Bearer <token>"
```

### Development (docker-compose.dev.yaml)
```bash
# Build lại Docker image
docker-compose -f docker-compose.dev.yaml build qna-service

# Start all services
docker-compose -f docker-compose.dev.yaml up

# Test API (port 5001 exposed)
curl -X GET http://localhost:5001/api/v2/chat/session/list \
  -H "Authorization: Bearer <token>"
```

## Bước 5: Xác Minh Database Migration

Docker sẽ tự động:
1. Tạo MySQL container
2. Chạy Python code (models.py)
3. Tạo tất cả tables mới khi app.py start

**Kiểm tra tables:**
```bash
# Access MySQL inside container
docker exec -it qna-mysql mysql -uroot -p123456789 -D qna

# Lệnh SQL:
SHOW TABLES;

# Bảng mới sẽ xuất hiện:
# - conversationsession
# - conversationmessage
# - conversationmemory
# - conversationreference
# - securitylog
```

## Bước 6: Test Multi-turn API

### Create Session
```bash
curl -X POST http://localhost:5001/api/v2/chat/session/create \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_name": "Test Session"
  }'
```

### Send Message
```bash
curl -X POST http://localhost:5001/api/v2/chat/message/send \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "question": "Test question",
    "use_memory": true
  }'
```

## Troubleshooting

### Issue: "ENCRYPTION_KEY" not found
**Solution:**
```bash
# Check .env file exists
ls -la e:\LegalChatbot\vnlawadvisor\backend\.env

# Generate new key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Update .env with key
# ENCRYPTION_KEY=<generated-key>
```

### Issue: Database tables not created
**Solution:**
```bash
# Check app initialization logs
docker-compose logs qna-service | grep -i "create\|table"

# Manually run migration
docker exec qna-service python3 -c "from models import *"

# Verify tables exist
docker exec qna-mysql mysql -uroot -p123456789 -D qna -e "SHOW TABLES;"
```

### Issue: "No module named 'cryptography'"
**Solution:**
```bash
# Rebuild Docker image
docker-compose build --no-cache qna-service

# Verify requirements.txt has cryptography
grep cryptography e:\LegalChatbot\vnlawadvisor\backend\rag\requirements.txt
```

### Issue: Redis connection error
**Solution:**
```bash
# Check Redis is running
docker-compose ps redis

# If not running, start it
docker-compose up -d redis

# Check connection
docker exec redis redis-cli ping
# Should output: PONG
```

## Production Deployment Steps

### 1. Pre-deployment Checks
- [ ] .env file has ENCRYPTION_KEY, HF_TOKEN, GEMINI_API_KEY
- [ ] docker-compose.yml has all environment variables
- [ ] All new files present in rag/ directory

### 2. Build Docker Image
```bash
docker-compose build qna-service
```

### 3. Start Services
```bash
docker-compose up -d
```

### 4. Verify Services
```bash
# Check all running
docker-compose ps

# Check qna-service logs
docker-compose logs qna-service -f --tail=50

# Test endpoint
curl http://localhost:5001/api/v2/chat/session/list \
  -H "Authorization: Bearer <test-token>"
```

### 5. Monitor
```bash
# Watch logs in real-time
docker-compose logs -f qna-service

# Check database size
docker exec qna-mysql mysql -uroot -p123456789 -D qna -e "
  SELECT 
    TABLE_NAME,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
  FROM information_schema.tables
  WHERE table_schema = 'qna'
  ORDER BY size_mb DESC;
"

# Check Redis memory
docker exec redis redis-cli info memory
```

## Backup Strategy (Docker)

```bash
# Backup MySQL volume
docker-compose exec qna-mysql mysqldump -uroot -p123456789 qna > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup entire volume
docker run --rm -v vnlawadvisor-backend_qna-sql:/data -v $(pwd):/backup alpine tar czf /backup/qna-sql-backup.tar.gz -C /data .

# Restore from backup
docker exec qna-mysql mysql -uroot -p123456789 qna < backup_YYYYMMDD_HHMMSS.sql
```

## Volume Cleanup (if needed)

```bash
# Remove all volumes (WARNING: Data loss!)
docker-compose down -v

# Remove only qna-sql volume
docker volume rm vnlawadvisor-backend_qna-sql

# Recreate everything
docker-compose up -d
```

## Environment Variables Reference

| Variable | Value | Purpose |
|----------|-------|---------|
| ENCRYPTION_KEY | Generated key | Encrypt sensitive data |
| SESSION_TIMEOUT_HOURS | 24 | Auto-expire sessions |
| MAX_CONTEXT_TOKENS | 4000 | Max context length |
| MAX_REQUESTS_PER_HOUR | 100 | Rate limiting |
| CONVERSATION_RETENTION_DAYS | 90 | Data retention |
| SECURITY_LOG_RETENTION_DAYS | 365 | Audit log retention |
| MYSQL_HOST | qna-mysql | Docker service name |
| REDIS_HOST | redis | Docker service name |

## Files Changed for Docker Compatibility

### docker-compose.yml
```yaml
qna-service:
  environment:
    # Added 9 new variables
    SESSION_TIMEOUT_HOURS: 24
    MAX_CONTEXT_TOKENS: 4000
    ENCRYPTION_KEY: ${ENCRYPTION_KEY}  # Load from .env
    ...
```

### docker-compose.dev.yaml
```yaml
# Added entire qna-service section with port 5001 exposed
qna-service:
  build: ./rag
  ports:
    - '5001:5001'  # Expose for local testing
  environment: ...
```

### .env
```
# New file at backend/.env
ENCRYPTION_KEY=...
HF_TOKEN=...
GEMINI_API_KEY=...
```

## Next Steps

1. ✅ Generate ENCRYPTION_KEY
2. ✅ Update .env file
3. ✅ Run `docker-compose build qna-service`
4. ✅ Run `docker-compose up -d`
5. ✅ Test API endpoints
6. ✅ Monitor logs
7. ✅ Setup alerts

---

**Important:** 
- All database schema changes happen automatically when Docker starts
- No manual SQL migrations needed
- MySQL data persists in `./rag/qna-sql` volume
- Restart containers if .env changes: `docker-compose restart qna-service`

---

**Last Updated:** March 13, 2024
**Version:** 1.0
