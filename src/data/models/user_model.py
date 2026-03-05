from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, Enum
from src.data.clients.database import Base
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

class Role(PyEnum): 
    associate = "associate"
    manager = "manager"
    admin = "admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key = True, unique = True, autoincrement = True)
    name = Column(String(255), nullable = False)
    email = Column(String(255), unique = True, nullable = False)
    password = Column(String(255), nullable = False)
    role = Column(Enum(Role))
    is_active = Column(Boolean, server_default= "False")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
