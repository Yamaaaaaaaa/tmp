import pymysql
import os
import datetime

import peewee as pw
from dotenv import load_dotenv

load_dotenv()
db_name = os.getenv("MYSQL_DATABASE")
db_host = os.getenv("MYSQL_HOST")
db_password = os.getenv("MYSQL_ROOT_PASSWORD")
db_port = int(os.getenv("MYSQL_PORT"))

conn = pymysql.connect(host=db_host, port=db_port, user='root', password=db_password)
cursor = conn.cursor()
cursor.execute(f"SHOW DATABASES LIKE '{db_name}'")
result = cursor.fetchall()
if result:
    print("Database exists")
else:
    print("Database not exists")
    cursor.execute(f'CREATE DATABASE {db_name}')
conn.close()

myDB = pw.MySQLDatabase(
    host=db_host,
    port=db_port,
    user="root",
    passwd=db_password,
    database=db_name
)

class MySQLModel(pw.Model):
    """A base model that will use our MySQL database"""
    id = pw.PrimaryKeyField(null=False)
    createdAt = pw.DateTimeField(default=datetime.datetime.now)
    updatedAt = pw.DateTimeField()
    
    def save(self, *args, **kwargs):
        self.updatedAt = datetime.datetime.now()
        return super(MySQLModel, self).save(*args, **kwargs)

    class Meta:
        database = myDB
        legacy_table_names = False

class QuestionModel(MySQLModel):
    email = pw.CharField(50)
    question = pw.TextField()
    response = pw.TextField()

class Reference(MySQLModel):
    question_id = pw.ForeignKeyField(QuestionModel)
    mapc = pw.CharField(255)
    noidung = pw.TextField()
    ten = pw.TextField()


# ===== Multi-turn Conversation Models =====

class ConversationSession(MySQLModel):
    """Quản lý một phiên chat với nhiều lần trò chuyện"""
    email = pw.CharField(50, index=True)
    session_name = pw.CharField(255)  # Tên session (optional)
    status = pw.CharField(20, default='active')  # active, archived, deleted
    total_messages = pw.IntegerField(default=0)
    message_count = pw.IntegerField(default=0)  # Số lượng messages trong session
    total_tokens_used = pw.IntegerField(default=0)  # Tổng tokens đã dùng
    is_archived = pw.BooleanField(default=False)
    last_message_at = pw.DateTimeField(null=True)  # Message cuối cùng
    

class ConversationMessage(MySQLModel):
    """Lưu trữ từng message trong cuộc trò chuyện"""
    session = pw.ForeignKeyField(ConversationSession, backref='messages')
    email = pw.CharField(50, index=True)
    turn_number = pw.IntegerField()  # Số lượt trò chuyện (1, 2, 3...)
    
    # Message content
    user_query = pw.TextField()  # Câu hỏi từ user
    ai_response = pw.TextField()  # Câu trả lời từ AI
    
    # Context & References
    retrieved_context = pw.TextField()  # Context được lấy từ vector DB
    citations = pw.TextField()  # JSON: danh sách citation references
    
    # Metadata
    query_tokens = pw.IntegerField(default=0)  # Tokens của query
    response_tokens = pw.IntegerField(default=0)  # Tokens của response
    total_tokens = pw.IntegerField(default=0)  # Tổng tokens
    api_response_time_ms = pw.IntegerField(default=0)  # Response time
    model_used = pw.CharField(100, default='gemini-2.5-flash')  # Model được dùng


class ConversationMemory(MySQLModel):
    """Lưu trữ memory/context cho conversation (summarized info)"""
    session = pw.ForeignKeyField(ConversationSession, backref='memories')
    email = pw.CharField(50, index=True)
    
    # Summarized context
    conversation_summary = pw.TextField()  # Tóm tắt cuộc trò chuyện
    key_topics = pw.TextField()  # JSON: danh sách các topic chính
    important_facts = pw.TextField()  # JSON: những fact quan trọng
    
    # Context management
    current_context_length = pw.IntegerField(default=0)  # Độ dài context hiện tại
    max_context_length = pw.IntegerField(default=4000)  # Max tokens cho context
    is_context_summarized = pw.BooleanField(default=False)  # Đã tóm tắt chưa
    
    # Version control
    version = pw.IntegerField(default=1)  # Version của memory
    truncated_from_turn = pw.IntegerField(null=True)  # Bắt đầu truncate từ turn nào


class ConversationReference(MySQLModel):
    """Lưu trữ references cho mỗi message (optimization)"""
    message = pw.ForeignKeyField(ConversationMessage, backref='references')
    mapc = pw.CharField(255)
    noidung = pw.TextField()
    ten = pw.CharField(255)
    demuc_id = pw.CharField(100, null=True)
    chude_id = pw.CharField(100, null=True)
    relevance_score = pw.FloatField(default=1.0)  # Điểm liên quan


class SecurityLog(MySQLModel):
    """Log cho security & audit purposes"""
    email = pw.CharField(50, index=True)
    session = pw.ForeignKeyField(ConversationSession, null=True)
    action = pw.CharField(100)  # 'message_sent', 'message_deleted', 'session_cleared'
    status = pw.CharField(20)  # 'success', 'failed'
    ip_address = pw.CharField(50, null=True)
    details = pw.TextField(null=True)


# ===== Initialize Database =====

myDB.connect()
myDB.create_tables([
    QuestionModel, 
    Reference,
    ConversationSession,
    ConversationMessage,
    ConversationMemory,
    ConversationReference,
    SecurityLog
])