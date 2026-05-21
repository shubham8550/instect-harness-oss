# Instect Harness

Open-source LLM evaluation and agent harness. Apache-2.0.

This is the engine that powers Instect's bug-detection and code-review tooling. It is also a standalone library you can use to build, run, and score LLM evals — locally, in CI, or as a long-running daemon.

> Status: pre-release. Schema `insect.eval.v1` is being frozen.

## Workspaces

- `crates/` — Rust core (`insectd` daemon, gRPC, sandbox runtime)
- `python/` — Python SDK and CLI (`uv` workspace)
- `typescript/` — TypeScript SDK (`pnpm` workspace)
- `schemas/` — JSON Schema source of truth for cross-language types
- `examples/` — runnable examples per SDK
- `docs/` — design docs and user-facing docs
- `tests/conformance/` — cross-SDK conformance suite

## Quick start

```sh
# tool versions are pinned in mise.toml
mise install

# top-level recipes
just                # list recipes
just build          # build all workspaces
just test           # run unit + conformance tests
just lint           # rustfmt + clippy + ruff + biome
just codegen        # regenerate types from schemas/
```

## License

Apache-2.0. See `LICENSE`. Contributions require a DCO sign-off (`git commit -s`); see `CONTRIBUTING.md`.
