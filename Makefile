# isort . && black . && bandit -r . && pylint && pre-commit run --all-files

FILES := $(wildcard **/*.py)

# if you wrap everything in poetry run, it runs slower.
ifeq ($(origin VIRTUAL_ENV),undefined)
    VENV := uv run
else
    VENV :=
endif

uv.lock: pyproject.toml
	echo "Installing dependencies"
	uv sync --all-extras


.PHONY: test
test: uv.lock
	@echo "Running tests"
	$(VENV) pytest --doctest-modules git_mirror -n 2
	# $(VENV) python -m unittest discover
	$(VENV) py.test tests -vv -n 2 --cov=git_mirror --cov-report=html --cov-fail-under 50
	$(VENV) bash basic_help.sh

.PHONY: isort
isort:
	@echo "Formatting imports"
	$(VENV) isort .

.PHONY: isort-llm
isort-llm:
	@echo "Skipping isort (LLM mode)"

.PHONY: black
black:
	@echo "Formatting code"
	$(VENV) black git_mirror --exclude .venv
	$(VENV) black tests --exclude .venv

.PHONY: black-llm
black-llm:
	@echo "Skipping black (LLM mode)"

.PHONY: pre-commit
pre-commit:
	@echo "Pre-commit checks"
	$(VENV) pre-commit run --all-files

.PHONY: pre-commit-llm
pre-commit-llm:
	@echo "Pre-commit checks (no fix)"
	SKIP=no-commit-to-branch,black,isort,ruff $(VENV) pre-commit run --all-files

.PHONY: bandit
bandit:
	@echo "Security checks"
	$(VENV)  bandit git_mirror -r

.PHONY: pylint
pylint:
	@echo "Linting with pylint"
	$(VENV) ruff check --fix
	$(VENV) pylint git_mirror --fail-under 9.8

.PHONY: pylint-llm
pylint-llm:
	@echo "Linting with pylint (no fix)"
	$(VENV) ruff check
	$(VENV) pylint git_mirror --fail-under 9.8

.PHONY: check
check: mypy test pylint bandit pre-commit

.PHONY: check-llm
check-llm: mypy-llm test pylint-llm bandit-llm pre-commit-llm

.PHONY: publish_test
publish_test:
	rm -rf dist && uv build && uv publish --repository testpypi

.PHONY: publish
publish: test
	rm -rf dist && uv build && uv publish

.PHONY: mypy
mypy:
	@echo "Running mypy"
	$(VENV) mypy git_mirror --ignore-missing-imports --check-untyped-defs

.PHONY: mypy-llm
mypy-llm:
	@echo "Running mypy (LLM mode)"
	$(VENV) mypy git_mirror --ignore-missing-imports --check-untyped-defs

.PHONY: ty
ty:
	@echo "Running ty"
	$(VENV) ty check git_mirror

.PHONY: ty-llm
ty-llm:
	@echo "Running ty (LLM mode)"
	$(VENV) ty check git_mirror

.PHONY: bandit-llm
bandit-llm:
	@echo "Running bandit (LLM mode)"
	$(VENV) bandit git_mirror -r

.PHONY: pip-audit
pip-audit:
	@echo "Running pip-audit"
	$(VENV) pip-audit

.PHONY: pre-release
pre-release: check_all check bandit interrogate pip-audit
	@echo "Pre-release checks complete"

.PHONY: docker
docker:
	docker build -t git_mirror -f Dockerfile .

.PHONY: check_docs
check_docs:
	$(VENV) interrogate git_mirror --verbose
	$(VENV) pydoctest --config .pydoctest.json | grep -v "__init__" | grep -v "__main__" | grep -v "Unable to parse"

.PHONY: make_docs
make_docs:
	pdoc git_mirror --html -o docs --force

.PHONY: check_md
check_md:
	$(VENV) mdformat README.md docs/*.md
	# $(VENV) linkcheckMarkdown README.md # it is attempting to validate ssl certs
	$(VENV) markdownlint README.md --config .markdownlintrc

.PHONY: check_spelling
check_spelling:
	$(VENV) pylint git_mirror --enable C0402 --rcfile=.pylintrc_spell
	$(VENV) codespell README.md --ignore-words=private_dictionary.txt
	$(VENV) codespell git_mirror --ignore-words=private_dictionary.txt

.PHONY: check_changelog
check_changelog:
	# pipx install keepachangelog-manager
	$(VENV) changelogmanager validate

.PHONY: check_all
check_all: check_docs check_md check_spelling check_changelog

.PHONY: check_all-llm
check_all-llm: check_docs check_md check_spelling check_changelog
