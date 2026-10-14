from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class RegulatoryRule(Base):
    __tablename__ = "regulatory_rules"

    id = Column(Integer, primary_key=True, index=True)
    jurisdiction = Column(String(10), index=True, nullable=False)  # e.g., "BD", "US", "UK"
    entity_type = Column(String(50), nullable=False)  # e.g., "PRIVATE_LTD", "LLC"
    title = Column(String(255), nullable=False)
    description = Column(Text)
    frequency = Column(String(50), nullable=False)  # "ANNUAL", "QUARTERLY", "MONTHLY"
    governing_body = Column(String(100))  # e.g., "RJSC", "NBR", "SEC"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
