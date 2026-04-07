"""module: user_model.py"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.data.clients.database import Base


class User(Base):
    """SQLAlchemy model representing a user in the system. This model defines the structure of the users table in the database, including fields for user ID, name, email, password, role, active status, and timestamps for creation and updates. The id is the primary key for this table and is set to auto-increment. The email field is unique to ensure that no two users can have the same email address. The role field can be used to define different levels of access or permissions for users (e.g., admin, regular user). The is_active field indicates whether the user's account is currently active. The created_at and updated_at fields automatically record when each user record is created and last updated, respectively. This model serves as the basis for managing user accounts and authentication within the system."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="False")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
