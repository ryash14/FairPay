"""The one engine and the one session factory the whole project uses.

Importing this module creates no table and writes nothing; run_database_setup.py
creates the tables.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import config

database_engine = create_engine(config.APPLICATION_DATABASE_URL, connect_args={"check_same_thread": False})
session_factory = sessionmaker(bind=database_engine)
