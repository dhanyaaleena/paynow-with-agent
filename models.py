from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone
import enum

Base = declarative_base()


class PaymentDecisionEnum(str, enum.Enum):
    allow = "allow"
    review = "review"
    block = "block"


class Customer(Base):
    __tablename__ = "customers"
    id = Column(String, primary_key=True)
    name = Column(String)
    balance = Column(Float, default=0.0)


class Payee(Base):
    __tablename__ = "payees"
    id = Column(String, primary_key=True)
    name = Column(String)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String, ForeignKey("customers.id"))
    payee_id = Column(String, ForeignKey("payees.id"))
    amount = Column(Float)
    currency = Column(String)
    decision = Column(Enum(PaymentDecisionEnum))
    reasons = Column(String)  # Comma-separated reasons
    agent_trace = Column(String)  # JSON string
    request_id = Column(String, unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    idempotency_key = Column(String)
    __table_args__ = (
        UniqueConstraint(
            'customer_id',
            'idempotency_key',
            name='_customer_idem_uc'),
    )


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String)
    idempotency_key = Column(String)
    payment_id = Column(Integer, ForeignKey("payments.id"))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        UniqueConstraint(
            'customer_id',
            'idempotency_key',
            name='_idempotency_uc'),
    )
