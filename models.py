from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key = True, index = True)
    username = Column(String, unique = True, nullable = False, index = True)
    email = Column(String, unique = True, nullable = False, index = True)
    hashed_password = Column(String, nullable = False)
    sessions = relationship("ReviewSession", back_populates = "owner", cascade = "all, delete-orphan") # (one User to many ReviewSessions relationship)


class ReviewSession(Base):
    __tablename__ = "review_sessions"

    id = Column(Integer, primary_key = True, index = True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable = False)

    # Input fields
    language = Column(String, nullable = False)
    issue_description = Column(Text, nullable = False)

    # AI output fields
    ai_category = Column(String, nullable = True)
    ai_difficulty = Column(String, nullable = True)        # Beginner / Intermediate / Advanced
    ai_recommendation = Column(Text, nullable = True)

    # Telemetry status fields
    ai_status = Column(String, default = "PENDING")        # SUCCESS / FAILED / PENDING
    error_message = Column(Text, nullable = True)

    # Relationship back to User
    owner = relationship("User", back_populates = "sessions")
