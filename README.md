<div align="center">

# Instect Harness

**The polyglot LLM evaluation harness — Rust core, Python / TypeScript / Go SDKs, OTLP-native, reproducible from CI to production.**

[![Build](https://github.com/shubham8550/instect-harness-oss/actions/workflows/build.yml/badge.svg)](https://github.com/shubham8550/instect-harness-oss/actions/workflows/build.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/badge/pypi-soon-orange.svg)](#status)
[![npm](https://img.shields.io/badge/npm-soon-orange.svg)](#status)
[![crates.io](https://img.shields.io/badge/crates.io-soon-orange.svg)](#status)
[![Status](https://img.shields.io/badge/status-pre--release-yellow.svg)](#status)

[Why Instect](#why-instect) · [Quick start](#quick-start) · [Architecture](#architecture) · [vs. the alternatives](#vs-the-alternatives) · [Roadmap](#roadmap) · [Contributing](#contributing)

</div>

---

## What is this

Instect Harness is an open-source evaluation and agent harness for LLMs. It is designed to be **the same engine** that:

- runs your evals locally during dev,
- gates your PRs in CI,
- powers the production code-review bot ([Instect Bugbot](https://instect.dev) — closed-source, built on this engine),
- and lets you replay your production traces back through your model to catch silent regressions.

One engine. Three SDKs. Zero forks. Apache 2.0 forever.

## Why Instect

Five things you cannot do well with anything else today:

### 1. Polyglot SDKs from a single spec

Most eval harnesses are Python-only. That breaks the moment you want to eval a TypeScript LangChain agent or a Go inference service.

Instect defines `insect.eval.v1` as a versioned JSON Schema and a gRPC contract. The `insectd` daemon is written in Rust. Python, TypeScript, and Go SDKs sit on top — same evals run unchanged across every language.

### 2. Hierarchical budget tree as a first-class scheduler primitive

Cost is not a passive metric. In Instect, `$` and `tokens-per-minute` are **nodes** in the scheduler's concurrency tree, alongside `max_inflight`. Trials park on exhaustion instead of crashing. `BudgetExceeded` is a Trace event you can react to.

```python
@eval(name="my-eval", budget=Budget(dollars=10, tokens_per_minute=50_000))
def my_eval(): ...
```

### 3. OTLP-native traces + WAL-journaled runs

Every Trial is an OpenTelemetry trace. Export to Phoenix, Datadog, Langfuse, or any OTel-compatible backend with zero glue.

Runs are journaled via a write-ahead log. Crash mid-run? `insect resume`. Want to time-travel? `insect replay`. Want statistical regression detection against last week's baseline? `insect diff` ships a paired-bootstrap test that exits non-zero in CI.

### 4. Production-trace ingest + live-target evals

```sh
# Turn last week's prod traffic into a Dataset.
insect ingest --otlp https://traces.yourcompany.com --since=7d

# Eval a running service directly. Not a model — a service.
insect live --target=https://staging.api/v1/chat
```

This is the one nobody else does. Eval your *behavior*, not just your model outputs.

### 5. Time-travel agent debugger + visual run-diff

```sh
# Drop into a REPL at any span boundary mid-trial.
insect debug <trial_id> --at "agent.step[7]"

# Diff two runs visually. Statistical regression detection built in.
insect diff <run_a> <run_b>
```

If you have ever tried to debug a 30-step agent loop by re-running it and adding `print` statements — you know why this matters.

## Quick start

```sh
# Install tool versions (Rust 1.84, Python 3.12, Node 22, pnpm, uv) — all pinned in mise.toml
mise install

# Build everything
just build

# Run the example eval
just example
```

### Python SDK

```python
from instect import eval, scorers

@eval(name="capital-cities", scorer=scorers.exact_match)
def capitals():
    return [
        {"input": "Capital of France?", "target": "Paris"},
        {"input": "Capital of Japan?", "target": "Tokyo"},
    ]

# Run via CLI:
#   insect run capital-cities --provider openai/gpt-4o
#   insect diff capital-cities --against last-week
```

### TypeScript SDK

```ts
import { defineEval, scorers } from "@instect/sdk";

export default defineEval({
  name: "capital-cities",
  dataset: [
    { input: "Capital of France?", target: "Paris" },
    { input: "Capital of Japan?", target: "Tokyo" },
  ],
  scorers: [scorers.exactMatch()],
});
```

### Rust crate

```rust
use insect_core::{Eval, Scorer};

let eval = Eval::builder("capital-cities")
    .dataset(vec![("Capital of France?", "Paris")])
    .scorer(Scorer::exact_match())
    .build();
```

## Architecture

```
        ┌────────────────────────────────────────────────────┐
        │                  instect CLI                       │
        │   eval · run · resume · replay · diff · ingest     │
        │                live · debug                        │
        └────────────────────────┬───────────────────────────┘
                                 │ gRPC
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│                       insectd (Rust)                          │
│                                                              │
│  scheduler    │  WAL journal  │  cache     │  OTLP exporter  │
│  budget tree  │  sandbox      │  providers │  judge calibr.  │
└──────────────────────────────────────────────────────────────┘
        ▲                ▲                  ▲              ▲
        │                │                  │              │
    Python SDK       TypeScript SDK      Go SDK        any HTTP
   (instect)       (@instect/sdk)        (soon)         client
```

Key crates: `insect-core` (types, schema bindings), `insect-proto` (gRPC), `insect-eval` (solver/scorer/judge primitives), `insect-runtime` (run orchestration, WAL), `insect-sandbox` (sandbox abstraction), `insect-providers` (LLM provider adapters: OpenAI, Anthropic, NVIDIA NIM, Bedrock, vLLM, local).

## vs. the alternatives

|                                  | Instect | Inspect AI | OpenAI Evals | DeepEval | Promptfoo |
| -------------------------------- | :-----: | :--------: | :----------: | :------: | :-------: |
| Polyglot SDKs (Py/TS/Go)         |   yes   |     no     |      no      |    no    |    no     |
| OTLP-native traces               |   yes   |     no     |      no      |  partial |    no     |
| Hierarchical budget primitive    |   yes   |     no     |      no      |    no    |    no     |
| Production-trace ingest          |   yes   |     no     |      no      |    no    |    no     |
| Live-target eval (run real svc)  |   yes   |     no     |      no      |    no    |    no     |
| Built-in statistical engine      |   yes   |     no     |      no      |  partial |    no     |
| Time-travel agent debugger       |   yes   |     no     |      no      |    no    |    no     |
| Visual run-diff w/ regression    |   yes   |     no     |      no      |    no    |    no     |
| Resumable runs (WAL)             |   yes   |  partial   |      no      |    no    |    no     |
| Apache-2.0 / open spec           |   yes   |    yes     |     yes      |   yes    |    yes    |

We respect Inspect AI immensely — it set the bar for what a serious eval harness looks like. Instect inherits the abstractions (Solver / Scorer / Sandbox) and goes further on polyglot, production-coupling, and reproducibility. See [`docs/vs-inspect-ai.md`](docs/vs-inspect-ai.md) for a deeper, honest comparison.

## Status

**Pre-release.** The `insect.eval.v1` schema is being frozen. Expect breaking changes until v0.5.

| Milestone | What ships | Target |
| --- | --- | --- |
| **v0.1** | foundation, OpenAI + Anthropic adapters, Python SDK MVP, `insect run` / `insect report` | week 6 |
| **v0.5** | Inspect-AI parity — full Solver/Agent/Scorer/Judge, sandboxes, TS SDK, NIM + Bedrock, conformance suite | week 12 |
| **v1.0** | the differentiators ship — `insect diff` / `ingest` / `live`, time-travel debug, statistical engine, judge calibration, GitHub Action | week 26 |

Want to track progress? [Watch this repo](https://github.com/shubham8550/instect-harness-oss/subscription). Want to influence the v1 spec? [Open a discussion](https://github.com/shubham8550/instect-harness-oss/discussions).

## Workspaces

```
crates/                    Rust workspace (insectd, core, eval, runtime, sandbox, providers)
python/                    uv workspace — instect / instect_sdk / instect_cli
typescript/                pnpm workspace — @instect/core / @instect/sdk / @instect/cli
schemas/                   JSON Schema source of truth for insect.eval.v1
examples/                  runnable examples per SDK
docs/                      design docs and user guides
tests/conformance/         cross-SDK conformance suite
```

## Contributing

Contributions are very welcome — especially **new scorers**, **provider adapters that pass the conformance suite**, and **sandbox backends**.

We use the [Developer Certificate of Origin](https://developercertificate.org/) (DCO) — sign off every commit with `-s`:

```sh
git commit -s -m "feat: my contribution"
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full PR checklist (tests, lint, schema drift-check) and what we are / aren't looking for at this stage.

## Community

- [GitHub Discussions](https://github.com/shubham8550/instect-harness-oss/discussions) — questions, feature requests, design conversations
- [Issues](https://github.com/shubham8550/instect-harness-oss/issues) — bug reports
- Discord — coming with v0.1 release

## License

Apache-2.0. See [`LICENSE`](LICENSE).

The **harness core, all provider adapters, all sandboxes, and the conformance suite are Apache-2.0 forever.** No CLA. No bait-and-switch. Advanced solvers, RL-trained scorers, premium SAST rule packs, and the DinD exploit playbooks that power the closed-source [Instect](https://instect.dev) product are commercially licensed and live in a separate repository.

---

<div align="center">

Built by [@shubham8550](https://github.com/shubham8550) and contributors · Powered by Rust, Python, and TypeScript

</div>
