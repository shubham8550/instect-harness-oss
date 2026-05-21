set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

# --- Build ---

build: build-rust build-python build-ts
build-rust:
    cargo build --workspace
build-python:
    cd python && uv sync && uv build
build-ts:
    cd typescript && pnpm install && pnpm -r build

# --- Test ---

test: test-rust test-python test-ts
test-rust:
    cargo test --workspace
test-python:
    cd python && uv run pytest
test-ts:
    cd typescript && pnpm -r test

conformance:
    bash tests/conformance/run.sh

# --- Lint / Format ---

lint: lint-rust lint-python lint-ts
lint-rust:
    cargo fmt --all -- --check
    cargo clippy --workspace --all-targets -- -D warnings
lint-python:
    cd python && uv run ruff check . && uv run ruff format --check .
lint-ts:
    cd typescript && pnpm -r lint

fmt:
    cargo fmt --all
    cd python && uv run ruff format .
    cd typescript && pnpm -r format

# --- Codegen ---

# Regenerate Pydantic + Zod + Rust types from `schemas/`.
# First-time setup (per-machine):
#   uv pip install -r tools/codegen/requirements.txt
#   cargo install typify-cli              # for the Rust emitter
#   # Node 22 LTS + pnpm for the TS emitter (json-schema-to-zod via npx)
codegen:
    uv run --with-requirements tools/codegen/requirements.txt python tools/codegen/codegen.py \
      --mode=generate \
      --schemas-dir=schemas \
      --out-py=python/packages/instect_core/src/instect_core/_generated \
      --out-ts=typescript/packages/core/src/_generated \
      --out-rust=crates/insect-core/src/_generated

# Fail if committed `_generated/` outputs no longer match a fresh codegen run.
drift-check:
    bash tools/drift_check.sh

# --- Clean ---

clean:
    cargo clean
    rm -rf python/.venv typescript/node_modules typescript/.turbo
