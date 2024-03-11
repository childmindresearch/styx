# Styx

<p align="center">
  <img src="docs/logo.png" width="500em">
</p>

[![Build](https://github.com/childmindresearch/styx/actions/workflows/test.yaml/badge.svg?branch=main)](https://github.com/childmindresearch/styx/actions/workflows/test.yaml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/childmindresearch/styx/branch/main/graph/badge.svg?token=22HWWFWPW5)](https://codecov.io/gh/childmindresearch/styx)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![stability-wip](https://img.shields.io/badge/stability-work_in_progress-lightgrey.svg)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/childmindresearch/styx/blob/main/LICENSE)
[![pages](https://img.shields.io/badge/api-docs-blue)](https://childmindresearch.github.io/styx)

Compile Python command line tool wrappers from Boutiques descriptors.

## Features

- [x] Target modern Python (3.11+)
- [x] Intellisense &amp; full static type checking for inputs and outputs
- [x] Documentation generation
- [x] Custom execution environments via dependency injection
- [x] Runtime input validation
- [ ] Integration test generation
- [ ] Default runners
  - [ ] Local
  - [ ] Docker
  - [ ] Singularity

## Boutiques descriptor implementation status: 77%

- [x] Documentation
- [x] Types (String, Numerical, File)
- [x] Flags
- [x] Lists
- [x] Enums
- [x] Constraints (Numeric ranges, Groups)
- [ ] (Conditional) outputs
- [x] Static metadata (Hash, name, container environment)
- [ ] Tests
