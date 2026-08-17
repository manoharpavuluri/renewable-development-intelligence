.PHONY: demo test smoke trace synthesize stability mlflow-ui help

VENV := .venv/bin
export PYTHONPATH := src
# Defaults to the frozen, committed example so `make demo` works
# from a fresh clone with no live evidence collection or Foundry
# calls. Point RESULT_DIR at a live data/spikes/<run>/ directory
# (gitignored - see README) to see a real, uncommitted run instead.
RESULT_DIR ?= data/examples/rdi-wok-250-001
RDI_THREAD_ID ?= RDI-WOK-250-001:screening:v1

help:
	@echo "make demo        - show the completed screening + draft recommendation (frozen example, no re-run)"
	@echo "make test        - run the offline evaluation harness"
	@echo "make smoke       - live-network check of every external evidence source"
	@echo "make synthesize  - re-run gate synthesis / G6 / G7 / recommendation draft (calls Foundry)"
	@echo "make trace       - log one full pipeline trace to MLflow (calls Foundry)"
	@echo "make stability   - recommendation-stability eval, N live Foundry runs (default 20)"
	@echo "make mlflow-ui   - open the MLflow trace viewer"

demo:
	@echo "=== RDI-WOK-250-001: western Oklahoma 250 MW wind screening ==="
	@echo
	@echo "--- Executive assessment ---"
	@echo "See docs/reports/executive_assessment.md for the full report."
	@echo
	@$(VENV)/python -c "\
import json; \
d = json.load(open('$(RESULT_DIR)/screening/project_assessment_draft.json')); \
rec = d['recommendation_draft']; \
print('Recommendation:', rec['recommendation'], '(', rec['status'], ')'); \
print('COD feasibility:', d['cod_feasibility']['status'], '-', d['cod_feasibility']['years_to_target_cod'], 'years to target'); \
print('Evidence sufficiency:', d['evidence_sufficiency']['status']); \
print(); \
print('Gates:'); \
[print(f\"  {g['gate_id']} {g['status']:<24} confidence={g['confidence']:<6} risks={len(g['material_risks'])}\") for g in d['gate_synthesis']]; \
"
	@echo
	@echo "--- Evaluation harness ---"
	@$(VENV)/python -m pytest tests/ -q 2>&1 | tail -3
	@echo
	@echo "Full docs: README.md | docs/architecture/overview.md | docs/reports/executive_assessment.md"

test:
	$(VENV)/python -m pytest tests/ -v

smoke:
	$(VENV)/python scripts/smoke_live_sources.py

synthesize:
	RESULT_DIR=$(RESULT_DIR) $(VENV)/python scripts/synthesize_project_assessment.py

trace:
	RDI_THREAD_ID=$(RDI_THREAD_ID) $(VENV)/python scripts/trace_project_run.py

stability:
	RDI_THREAD_ID=$(RDI_THREAD_ID) $(VENV)/python scripts/eval_recommendation_stability.py

mlflow-ui:
	$(VENV)/mlflow ui --backend-store-uri sqlite:///data/runtime/mlflow.db
