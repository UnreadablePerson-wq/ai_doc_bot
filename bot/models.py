# bot/models.py

from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, Index
from datetime import datetime

from bot.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index('idx_user_telegram_id', 'telegram_id'),
    )
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    language = Column(String, default="ru")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<User {self.telegram_id}>"

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index('idx_document_user_id', 'user_id'),
        Index('idx_document_created', 'created_at'),
    )
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    file_name = Column(String, nullable=False)
    file_id = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Document {self.id}: {self.file_name}>"

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index('idx_message_user_id', 'user_id'),
        Index('idx_message_created', 'created_at'),
        Index('idx_message_document', 'document_id'),
    )
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    document_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Message {self.id}: {self.role}>"