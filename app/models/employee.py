from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class Employee(Base):
    __tablename__ = "employee"

    KPK: Mapped[str] = mapped_column(String(6), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dob: Mapped[str | None] = mapped_column(String(8), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supervisor: Mapped[str | None] = mapped_column(String(6), nullable=True)
    join_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
