import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from database import Base

class TestStatusEnum(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed" # Test execution failed
    ERROR = "error" # Error during test logic

class TestResultEnum(enum.Enum):
    NOT_RUN = "not_run"
    PASSED = "passed" # Vulnerability not found or check passed
    VULNERABLE = "vulnerable" # Vulnerability found
    INFO = "info" # Informational finding

class Website(Base):
    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_scan_at = Column(DateTime(timezone=True), nullable=True)

    scans = relationship("Scan", back_populates="website")

class TestDefinition(Base):
    __tablename__ = "test_definitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # e.g., "SQL Injection", "XSS"
    description = Column(Text, nullable=True)

    scan_results = relationship("ScanResult", back_populates="test_definition")


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    status = Column(SQLEnum(TestStatusEnum), default=TestStatusEnum.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    website = relationship("Website", back_populates="scans")
    results = relationship("ScanResult", back_populates="scan", cascade="all, delete-orphan")


class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    test_definition_id = Column(Integer, ForeignKey("test_definitions.id"), nullable=False)
    status = Column(SQLEnum(TestStatusEnum), default=TestStatusEnum.PENDING, nullable=False)
    result = Column(SQLEnum(TestResultEnum), default=TestResultEnum.NOT_RUN, nullable=False)
    summary = Column(Text, nullable=True) # Short summary or finding
    details = Column(Text, nullable=True) # Detailed output or evidence
    recommendations = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    scan = relationship("Scan", back_populates="results")
    test_definition = relationship("TestDefinition", back_populates="scan_results")