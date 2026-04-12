"""
db/base.py

Defines the SQLAlchemy DeclarativeBase that all models inherit from.
This is the shared "parent class" that lets SQLAlchemy know which
Python classes represent database tables.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass