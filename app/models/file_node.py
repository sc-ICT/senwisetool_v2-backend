from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import FileNodeType

if TYPE_CHECKING:
    from app.models.user import User


class FileNode(Base):
    __tablename__ = "file_nodes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("file_nodes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    type: Mapped[FileNodeType] = mapped_column(
        Enum(FileNodeType, name="file_node_type"),
        nullable=False,
    )

    # Identifiant du fichier dans le système de stockage physique.
    # Exemple futur :
    # users/42/550e8400-e29b-41d4-a716-446655440000
    #
    # Pour un dossier : NULL
    storage_key: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        unique=True,
    )

    mime_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    extension: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    size: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ─────────────────────────────────────────────────────────────
    # Relations
    # ─────────────────────────────────────────────────────────────

    user: Mapped["User"] = relationship(
        "User",
        back_populates="file_nodes",
    )

    parent: Mapped["FileNode | None"] = relationship(
        "FileNode",
        remote_side=[id],
        back_populates="children",
    )

    children: Mapped[list["FileNode"]] = relationship(
        "FileNode",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
