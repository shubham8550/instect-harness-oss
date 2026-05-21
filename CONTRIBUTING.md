# Contributing to Instect Harness

Thanks for your interest in contributing.

## License and DCO

Instect Harness is licensed under Apache-2.0. By contributing, you license your contributions under the same terms.

We use the [Developer Certificate of Origin](https://developercertificate.org/) (DCO) rather than a CLA. Sign off every commit with `-s`:

```sh
git commit -s -m "your message"
```

This adds a `Signed-off-by:` line that asserts you have the right to submit the contribution under the project license.

## Setup

```sh
mise install
just build
just test
```

## Pull request checklist

- [ ] Tests pass: `just test`
- [ ] Lint clean: `just lint`
- [ ] Schema drift-check passes: `just drift-check`
- [ ] SPDX header present on every new source file
- [ ] DCO sign-off on every commit (`git commit -s`)
- [ ] Linked to an issue if non-trivial

## What we are interested in

- Solvers, scorers, and judges (with tests)
- Provider adapters that pass the conformance suite
- Sandbox backends
- Bug fixes with regression tests
- Docs and examples

## What we are not interested in (yet)

- Large architectural rewrites without prior discussion
- Adding dependencies without an issue describing the need
- Style-only refactors

If you have a substantial change in mind, open an issue first.
