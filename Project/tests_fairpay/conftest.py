"""Shared fixtures for the team's own test suite (the SRS marking suite stays in tests.py).

Unit tests need only the code and the PDFs. The end-to-end tests also need the
built pipeline (steps 1 to 4) and run the agents on the offline rehearsal
model, so they never spend a Gemini call.
"""
import os
import sys

import pytest

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT)
os.chdir(PROJECT)

from config import config  # noqa: E402


class DocumentStore:
    """A stand-in for the Chroma collection that serves whole documents, for tests of the readers."""

    def __init__(self, chunks):
        self.chunks = chunks

    def get(self, where):
        name = where["document_name"]["$eq"]
        return {"documents": [c["chunk_text"] for c in self.chunks if c["document_name"] == name]}


@pytest.fixture(scope="session")
def chunks():
    from knowledge.chunk_splitting import build_chunk_records, split_documents_into_sections
    from knowledge.pdf_extraction import extract_text_from_directory
    if not os.path.isdir(config.DOCS_DIRECTORY):
        pytest.skip("data/docs is missing: run python devkit/bootstrap_demo.py")
    sections = split_documents_into_sections(extract_text_from_directory(config.DOCS_DIRECTORY))
    return build_chunk_records(sections, config.CHUNK_SIZE_CHARACTERS, config.CHUNK_OVERLAP_CHARACTERS)


@pytest.fixture(scope="session")
def store(chunks):
    return DocumentStore(chunks)


@pytest.fixture(scope="session")
def schedules(store):
    from knowledge.schedule_reading import read_pay_schedule
    return {name: read_pay_schedule(store, name) for name in config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION}


@pytest.fixture(scope="session")
def open_queries():
    from data_pipeline.dataset_loader import load_raw_dataset
    if not os.path.exists(config.OPEN_QUERIES_FILE):
        pytest.skip("the live queue is missing")
    return load_raw_dataset(config.OPEN_QUERIES_FILE, config.NULL_TOKENS)


@pytest.fixture(scope="session")
def service():
    needed = [config.CORRECTION_MODEL_FILE, config.VECTOR_STORE_DIRECTORY, config.APPLICATION_DATABASE_FILE]
    if not all(os.path.exists(path) for path in needed):
        pytest.skip("run steps 1 to 4 before the end-to-end tests")
    os.environ["FAIRPAY_OFFLINE_LLM"] = "1"
    from fastapi.testclient import TestClient
    from api.routes import service_application
    return TestClient(service_application, raise_server_exceptions=False)


def sign_in(client, username):
    account = next(a for a in config.SEED_USER_ACCOUNTS if a["username"] == username)
    reply = client.post("/auth/signin", json={"username": username, "password": account["password"]})
    assert reply.status_code == 200, reply.text
    return {config.SESSION_TOKEN_HEADER: reply.json()["session_token"]}


def first_user(role):
    return next(a["username"] for a in config.SEED_USER_ACCOUNTS if a["role"] == role)


def second_user(role):
    return [a["username"] for a in config.SEED_USER_ACCOUNTS if a["role"] == role][1]
