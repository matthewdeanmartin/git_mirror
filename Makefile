FILES := $(wildcard **/*.py)

UV_CACHE_DIR ?= $(CURDIR)/.uv-cache
UV_RUN = UV_CACHE_DIR=$(UV_CACHE_DIR) uv run
PYTEST_BASETEMP = $(CURDIR)/.pytest-tmp

uv.lock: pyproject.toml
	@echo "Installing dependencies"
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv sync --all-extras

.PHONY: test
test: uv.lock smoke-py smoke-bash
	@echo "Running tests"
	$(UV_RUN) pytest --basetemp=$(PYTEST_BASETEMP) --doctest-modules git_mirror -n 2
	$(UV_RUN) pytest --basetemp=$(PYTEST_BASETEMP) tests -vv -n 2 --cov=git_mirror --cov-report=html --cov-fail-under 50

.PHONY: smoke-py
smoke-py:
	@echo "Running CLI smoke tests"
	$(UV_RUN) pytest --basetemp=$(PYTEST_BASETEMP) tests/tests_human/test_cli_smoke.py -q

.PHONY: smoke-bash
smoke-bash:
	@echo "Running bash smoke scripts"
	@if [ "$(OS)" = "Windows_NT" ]; then \
		echo "Skipping bash smoke scripts on Windows; they run in GitHub Actions."; \
	else \
		bash scripts/basic_help.sh; \
		bash scripts/basic_test.sh; \
		bash scripts/basic_test_dry.sh; \
		bash scripts/entrypoint_help.sh; \
	fi

.PHONY: isort
isort:
	@echo "Formatting imports"
	$(UV_RUN) isort .

.PHONY: isort-llm
isort-llm:
	@echo "Skipping isort (LLM mode)"

.PHONY: black
black:
	@echo "Formatting code"
	$(UV_RUN) black git_mirror --exclude .venv
	$(UV_RUN) black tests --exclude .venv

.PHONY: black-llm
black-llm:
	@echo "Skipping black (LLM mode)"

.PHONY: pre-commit
pre-commit:
	@echo "Pre-commit checks"
	$(UV_RUN) pre-commit run --all-files

.PHONY: pre-commit-llm
pre-commit-llm:
	@echo "Pre-commit checks (no fix)"
	SKIP=no-commit-to-branch,black,isort,ruff $(UV_RUN) pre-commit run --all-files

.PHONY: bandit
bandit:
	@echo "Security checks"
	$(UV_RUN) bandit git_mirror -r

.PHONY: pylint
pylint:
	@echo "Linting with pylint"
	$(UV_RUN) ruff check --fix
	$(UV_RUN) pylint git_mirror --fail-under 9.8

.PHONY: pylint-llm
pylint-llm:
	@echo "Linting with pylint (no fix)"
	$(UV_RUN) ruff check
	$(UV_RUN) pylint git_mirror --fail-under 9.8

.PHONY: check
check: mypy test pylint bandit pre-commit

.PHONY: check-llm
check-llm: mypy-llm test pylint-llm bandit-llm pre-commit-llm

.PHONY: build-package
build-package:
	rm -rf dist
	$(UV_RUN) uv build

.PHONY: publish_test
publish_test: build-package
	$(UV_RUN) uv publish --repository testpypi

.PHONY: publish
publish: pre-publication
	$(UV_RUN) uv publish

.PHONY: mypy
mypy:
	@echo "Running mypy"
	$(UV_RUN) mypy git_mirror --ignore-missing-imports --check-untyped-defs

.PHONY: mypy-llm
mypy-llm:
	@echo "Running mypy (LLM mode)"
	$(UV_RUN) mypy git_mirror --ignore-missing-imports --check-untyped-defs

.PHONY: ty
ty:
	@echo "Running ty"
	$(UV_RUN) ty check git_mirror

.PHONY: ty-llm
ty-llm:
	@echo "Running ty (LLM mode)"
	$(UV_RUN) ty check git_mirror

.PHONY: bandit-llm
bandit-llm:
	@echo "Running bandit (LLM mode)"
	$(UV_RUN) bandit git_mirror -r

.PHONY: pip-audit
pip-audit:
	@echo "Running pip-audit"
	$(UV_RUN) pip-audit

.PHONY: lint-actions
lint-actions:
	@UV_CACHE_DIR=$(UV_CACHE_DIR) uv run zizmor . --config .zizmor.yml --min-severity informational --persona pedantic
	@UV_CACHE_DIR=$(UV_CACHE_DIR) uv run check-jsonschema --schemafile https://json.schemastore.org/github-workflow.json .github/workflows/*.yml

.PHONY: fix-actions
fix-actions:
	@UV_CACHE_DIR=$(UV_CACHE_DIR) uv run gha-update

.PHONY: pre-publication
pre-publication: check-llm check_all-llm lint-actions build-package
	@echo "Pre-publication checks complete"

.PHONY: docker
docker:
	docker build -t git_mirror -f Dockerfile .

.PHONY: check_docs
check_docs:
	$(UV_RUN) interrogate git_mirror --verbose
	$(UV_RUN) pydoctest --config .pydoctest.json | grep -v "__init__" | grep -v "__main__" | grep -v "Unable to parse"

.PHONY: make_docs
make_docs:
	$(UV_RUN) pdoc git_mirror --html -o docs --force

.PHONY: check_md
check_md:
	$(UV_RUN) mdformat --check README.md docs/*.md
	$(UV_RUN) markdownlint README.md --config .markdownlintrc

.PHONY: check_spelling
check_spelling:
	$(UV_RUN) pylint git_mirror --enable C0402 --rcfile=.pylintrc_spell
	$(UV_RUN) codespell README.md --ignore-words=private_dictionary.txt
	$(UV_RUN) codespell git_mirror --ignore-words=private_dictionary.txt

.PHONY: check_changelog
check_changelog:
	$(UV_RUN) changelogmanager validate

.PHONY: check_all
check_all: check_docs check_md check_spelling check_changelog

.PHONY: check_all-llm
check_all-llm: check_docs check_md check_spelling check_changelog
