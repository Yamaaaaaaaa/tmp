# Deployment & Implementation Checklist

## Phase 1: Preparation (Days 1-2)

### Database Preparation
- [ ] Backup existing MySQL database
  ```bash
  mysqldump -h qna-mysql -u root -p qna > backup_$(date +%Y%m%d).sql
  ```

- [ ] Review new database schema
  ```sql
  - ConversationSession
  - ConversationMessage
  - ConversationMemory
  - ConversationReference
  - SecurityLog
  ```

- [ ] Test schema creation in development environment
  ```python
  python3 -c "from models import *; print('Database initialized')"
  ```

### Environment Setup
- [ ] Generate encryption key
  ```bash
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

- [ ] Update .env.example with new variables
- [ ] Create .env file with production values
  ```bash
  ENCRYPTION_KEY=<generated-key>
  SESSION_TIMEOUT_HOURS=24
  MAX_CONTEXT_TOKENS=4000
  MAX_REQUESTS_PER_HOUR=100
  ```

- [ ] Verify all external services are accessible
  - [ ] MySQL database
  - [ ] Redis server
  - [ ] ChromaDB
  - [ ] Gemini API

### Dependency Updates
- [ ] Review new requirements
  ```bash
  pip install cryptography python-dateutil
  ```

- [ ] Test installation in dev environment
- [ ] Verify compatibility with existing code

## Phase 2: Code Deployment (Days 3-4)

### Backend Code
- [ ] Deploy new Python files
  - [ ] `session_manager.py`
  - [ ] `memory_manager.py`
  - [ ] `security_manager.py`
  - [ ] `chat_endpoints.py`

- [ ] Update `models.py` with new database models
- [ ] Update `app.py` to register new blueprint
- [ ] Update `requirements.txt`

### Testing
- [ ] Unit tests for SessionManager
  ```bash
  pytest tests/test_session_manager.py -v
  ```

- [ ] Unit tests for MemoryManager
  ```bash
  pytest tests/test_memory_manager.py -v
  ```

- [ ] Unit tests for SecurityManager
  ```bash
  pytest tests/test_security_manager.py -v
  ```

- [ ] Integration tests for API endpoints
  ```bash
  pytest tests/test_chat_endpoints.py -v
  ```

- [ ] Load testing (verify performance)
  ```bash
  artillery load tests/load-test.yml
  ```

### Frontend Code
- [ ] Create `chat.service.ts` in web/services
- [ ] Create React/Vue components for multi-turn UI
  - [ ] ChatSessionList
  - [ ] ChatWindow
  - [ ] MessageHistory
  - [ ] MemorySummary

- [ ] Update API base URLs if needed
- [ ] Test TypeScript compilation
  ```bash
  npm run build
  ```

## Phase 3: Database Migration (Days 5-6)

### Initial Setup
- [ ] Create new tables (if not exists)
  ```python
  python3 scripts/init_db.py
  ```

- [ ] Verify schema
  ```bash
  mysql -h qna-mysql -u root -p qna -e "SHOW TABLES;"
  ```

### Data Migration (Optional)
- [ ] Migrate existing QuestionModel to new schema
  ```python
  # For each Question:
  # 1. Create ConversationSession
  # 2. Create ConversationMessage
  # 3. Migrate References to ConversationReference
  ```

- [ ] Verify migration integrity
  - [ ] Total message count matches
  - [ ] No data loss
  - [ ] Proper foreign keys

#### Migration Script
```python
from models import *
from datetime import datetime

# For each old question
for old_question in QuestionModel.select():
    # Create session
    session = ConversationSession.create(
        email=old_question.email,
        session_name=f"Migrated on {datetime.now()}",
        status='archived'
    )
    
    # Create message
    message = ConversationMessage.create(
        session=session,
        email=old_question.email,
        turn_number=1,
        user_query=old_question.question,
        ai_response=old_question.response,
        citations='{}',
        model_used='legacy'
    )
    
    # Migrate references
    for ref in Reference.select().where(Reference.question_id == old_question.id):
        ConversationReference.create(
            message=message,
            mapc=ref.mapc,
            noidung=ref.noidung,
            ten=ref.ten
        )
```

## Phase 4: Staging Deployment (Days 7-8)

### Docker Build
- [ ] Build new Docker image
  ```bash
  docker build -f backend/rag/Dockerfile -t vnlawadvisor/rag:v2.0 .
  ```

- [ ] Test image locally
  ```bash
  docker run -e MYSQL_HOST=localhost vnlawadvisor/rag:v2.0
  ```

### Staging Environment
- [ ] Deploy to staging
  ```bash
  docker-compose -f docker-compose.staging.yml up -d
  ```

- [ ] Run smoke tests
  ```bash
  curl http://staging-api:5001/api/v2/chat/session/list \
    -H "Authorization: Bearer test_token"
  ```

- [ ] Test all endpoints
  - [ ] POST /api/v2/chat/session/create
  - [ ] POST /api/v2/chat/message/send
  - [ ] GET /api/v2/chat/session/list
  - [ ] GET /api/v2/chat/session/{id}/memory
  - etc.

- [ ] Performance testing
  - [ ] Response time < 4 seconds per message
  - [ ] Memory usage stable
  - [ ] Redis cache working

- [ ] Security testing
  - [ ] JWT validation works
  - [ ] Access control enforced
  - [ ] Rate limiting works
  - [ ] Encryption/decryption works

- [ ] Load testing
  - [ ] 10 concurrent users
  - [ ] 100 messages per user

## Phase 5: Production Deployment (Days 9-10)

### Pre-deployment
- [ ] Create rollback plan
  ```bash
  git tag pre-multiturn-v$(date +%Y%m%d)
  ```

- [ ] Final backup of production database
  ```bash
  mysqldump -h prod-mysql -u root -p qna > backup_production_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] Notify users about maintenance window (if needed)

### Deployment
- [ ] Stop existing service
  ```bash
  docker-compose stop qna-service
  ```

- [ ] Deploy new version
  ```bash
  docker-compose up -d qna-service
  ```

- [ ] Verify service is running
  ```bash
  docker-compose logs qna-service
  curl http://localhost:5001/api/v2/chat/session/list \
    -H "Authorization: Bearer $(get_test_token)"
  ```

- [ ] Monitor logs for errors
  - [ ] No database errors
  - [ ] No API errors
  - [ ] Normal request rate

### Post-deployment
- [ ] Run end-to-end tests
  ```bash
  pytest tests/e2e/ -v
  ```

- [ ] Verify backward compatibility
  - [ ] Old /api/v1/question endpoint still works
  - [ ] Existing users unaffected

- [ ] Monitor metrics
  - [ ] Response times
  - [ ] Error rates
  - [ ] Token usage
  - [ ] User activity

- [ ] Update documentation
  - [ ] API docs
  - [ ] User guide
  - [ ] Admin guide

## Phase 6: Post-Deployment (Days 11-14)

### Monitoring
- [ ] Set up alerts
  - [ ] API error rate > 1%
  - [ ] Response time > 5 seconds
  - [ ] Database connection errors
  - [ ] Redis connection errors

- [ ] Daily checks
  - [ ] Review security logs
  - [ ] Check database size growth
  - [ ] Monitor token usage trends
  - [ ] Review error logs

### Optimization
- [ ] Analyze performance data
  - [ ] Identify slow endpoints
  - [ ] Optimize queries if needed
  - [ ] Tune cache settings

- [ ] User feedback
  - [ ] Gather feedback from early users
  - [ ] Fix bugs
  - [ ] Improve UX

- [ ] Documentation updates
  - [ ] Add FAQ based on user questions
  - [ ] Update troubleshooting guide
  - [ ] Create video tutorials

## Rollback Plan

If issues occur during deployment:

### Immediate Rollback
```bash
# Stop new version
docker-compose stop qna-service

# Restore old version
git checkout pre-multiturn-v<date>
docker-compose up -d qna-service

# Restore database (if needed)
mysql -h prod-mysql -u root -p qna < backup_production_<date>.sql
```

### Communication
- [ ] Notify users of the issue
- [ ] Provide ETA for fix
- [ ] Post incident report after resolution

## Success Criteria

- ✅ All endpoints responding correctly (HTTP 200/201)
- ✅ Session creation and message sending works
- ✅ Memory is created automatically
- ✅ Security checks pass (JWT, access control)
- ✅ API response time < 5 seconds (including LLM call)
- ✅ No data loss from migration
- ✅ Backward compatibility maintained
- ✅ Security logs recording events
- ✅ Rate limiting working
- ✅ No critical errors in logs

## Testing Checklist

### Functional Testing
```bash
# Create session
SESSION_ID=$(curl -X POST http://localhost:5001/api/v2/chat/session/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_name":"Test"}' | jq -r '.data.session_id')

# Send message
curl -X POST http://localhost:5001/api/v2/chat/message/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"question\":\"Test question\",\"use_memory\":true}"

# Get messages
curl -X GET "http://localhost:5001/api/v2/chat/session/$SESSION_ID/messages" \
  -H "Authorization: Bearer $TOKEN"

# Get memory
curl -X GET "http://localhost:5001/api/v2/chat/session/$SESSION_ID/memory" \
  -H "Authorization: Bearer $TOKEN"
```

### Security Testing
```bash
# Test unauthorized access
curl -X GET "http://localhost:5001/api/v2/chat/session/$SESSION_ID/messages" \
  -H "Authorization: Bearer INVALID_TOKEN"
# Should return 401

# Test access to other user's session
curl -X GET "http://localhost:5001/api/v2/chat/session/$OTHER_USER_SESSION/messages" \
  -H "Authorization: Bearer YOUR_TOKEN"
# Should return 403
```

### Performance Testing
```bash
# Using Apache Bench
ab -n 100 -c 10 -H "Authorization: Bearer $TOKEN" \
  http://localhost:5001/api/v2/chat/session/list

# Using hey
hey -n 100 -c 10 -H "Authorization: Bearer $TOKEN" \
  http://localhost:5001/api/v2/chat/session/list
```

## Support Contacts

- **DevOps**: devops@vnlawadvisor.com
- **Database**: dba@vnlawadvisor.com
- **QA**: qa@vnlawadvisor.com
- **Security**: security@vnlawadvisor.com

---

**Status**: Ready for Deployment  
**Last Updated**: March 13, 2024  
**Approved By**: [Name]
