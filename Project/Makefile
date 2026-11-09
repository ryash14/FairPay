# FairPay AI - every command runs from the Project folder.
PY ?= python

.PHONY: help bootstrap setup pipeline train index build api dashboard test lint gate monitor experiments clean fresh

help:
	@echo "make bootstrap    add demo config/data/docs only where missing"
	@echo "make build        steps 1-4: database, pipeline, models, knowledge base"
	@echo "make api          step 5: REST service on :8081"
	@echo "make dashboard    step 6: dashboard on :8080"
	@echo "make test         team tests (offline model, no Gemini cost)"
	@echo "make gate         fail if a model is under its minimum"
	@echo "make monitor      runs, budgets, latency and alerts"
	@echo "make experiments  baselines vs chosen models"
	@echo "make fresh        empty the database for the marking suite"

bootstrap: ; $(PY) devkit/bootstrap_demo.py
setup: ; $(PY) run_database_setup.py
pipeline: ; $(PY) run_data_pipeline.py
train: ; $(PY) run_model_training.py
index: ; $(PY) run_knowledge_indexing.py
build: setup pipeline train index gate
api: ; $(PY) run_api_service.py
dashboard: ; streamlit run run_dashboard.py
test: ; FAIRPAY_OFFLINE_LLM=1 $(PY) -m pytest tests_fairpay -q
lint: ; ruff check .
gate: ; $(PY) -m ops.model_gate
monitor: ; $(PY) -m ops.monitor
experiments: ; $(PY) -m experiments.compare_baselines
fresh:
	rm -f database/fairpay.db database/checkpoint.db
	$(PY) run_database_setup.py
clean:
	rm -rf processed output database/chroma_store database/*.db
