"""Step 5: start the REST service, after checking every earlier stage has run.

    python run_api_service.py
"""
import os
import sys

from config import config

REQUIRED_BEFORE_STARTING = [
    (config.CORRECTION_MODEL_FILE, "run_model_training.py"),
    (config.EFFORT_MODEL_FILE, "run_model_training.py"),
    (config.CATEGORY_MODEL_FILE, "run_model_training.py"),
    (config.CORRECTION_SCHEMA_FILE, "run_model_training.py"),
    (config.EFFORT_SCHEMA_FILE, "run_model_training.py"),
    (config.OPEN_QUERIES_FILE, "the supplied data folder"),
    (config.OPEN_QUERY_NOTES_FILE, "the supplied data folder"),
    (config.VECTOR_STORE_DIRECTORY, "run_knowledge_indexing.py"),
    (config.APPLICATION_DATABASE_FILE, "run_database_setup.py"),
]


def main():
    missing = [(path, source) for path, source in REQUIRED_BEFORE_STARTING if not os.path.exists(path)]
    if missing:
        print("The service cannot start.")
        for path, source in missing:
            print(f"{path} is missing; it comes from {source}")
        return 1
    import uvicorn
    from api.routes import service_application
    print(f"Starting {config.API_TITLE} on port {config.API_PORT}. Interactive documentation: "
          f"http://localhost:{config.API_PORT}/docs")
    uvicorn.run(service_application, host=config.API_HOST, port=config.API_PORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
