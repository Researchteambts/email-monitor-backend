from sqlalchemy import (
    Column, Integer, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Account(Base):
    __tablename__ = "accounts"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(Text, unique=True, nullable=False, index=True)
    password   = Column(Text, nullable=False)
    provider   = Column(Text, nullable=False, default="gmail")
    is_active  = Column(Boolean, default=True, nullable=False)  # ← added
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    emails = relationship("Email", back_populates="account_rel",
                          cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Account email={self.email} provider={self.provider}>"


class Email(Base):
    __tablename__ = "emails"

    __table_args__ = (
        UniqueConstraint("account_id", "uid", name="uq_account_uid"),  # ← fixed
    )

    id           = Column(Integer, primary_key=True, index=True)
    uid          = Column(Text, nullable=False)
    account_id   = Column(Integer, ForeignKey("accounts.id",             # ← fixed
                          ondelete="CASCADE"), nullable=False, index=True)
    from_address = Column(Text)
    subject      = Column(Text)
    body         = Column(Text)
    received_at = Column(DateTime(timezone=True), nullable=True)
    folder = Column(Text, default="inbox") 
    forwarded_at = Column(DateTime(timezone=True), server_default=func.now())
    status       = Column(Text, default="forwarded")
    is_read = Column(Boolean, default=False, server_default='false', nullable=False)
    account_rel = relationship("Account", back_populates="emails")

    def __repr__(self):
        return f"<Email uid={self.uid} account_id={self.account_id} subject={self.subject}>"