import uuid
from datetime import datetime
import json
from sqlalchemy import create_engine, Column, String, Float, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./vigilai_proxy.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ProxyLog(Base):
    __tablename__ = "proxy_logs"

    id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    model_used = Column(String, index=True)
    original_prompt = Column(Text)
    processed_prompt = Column(Text)
    response = Column(Text)
    status = Column(String, index=True)  # ALLOWED, BLOCKED_PII, BLOCKED_INJECTION, etc.
    latency_ms = Column(Float)
    cost_usd = Column(Float)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    violated_rules = Column(Text)  # JSON-encoded list of strings
    client_ip = Column(String, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper functions to record logs
def add_proxy_log(
    model_used: str,
    original_prompt: str,
    processed_prompt: str,
    response: str,
    status: str,
    latency_ms: float,
    cost_usd: float,
    input_tokens: int,
    output_tokens: int,
    violated_rules: list,
    client_ip: str = None
) -> ProxyLog:
    db = SessionLocal()
    try:
        log_entry = ProxyLog(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            model_used=model_used,
            original_prompt=original_prompt,
            processed_prompt=processed_prompt,
            response=response,
            status=status,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            violated_rules=json.dumps(violated_rules),
            client_ip=client_ip
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
    finally:
        db.close()
