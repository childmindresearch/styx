# Styx

<img src="docs/logo.png" width="500em" style="display: block; margin-left: auto; margin-right: auto"> </img>


[![Build](https://github.com/cmi-dair/styx/actions/workflows/test.yaml/badge.svg?branch=main)](https://github.com/cmi-dair/styx/actions/workflows/test.yaml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/cmi-dair/styx/branch/main/graph/badge.svg?token=22HWWFWPW5)](https://codecov.io/gh/cmi-dair/styx)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![stability-wip](https://img.shields.io/badge/stability-work_in_progress-lightgrey.svg)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/cmi-dair/styx/blob/main/LICENSE)
[![pages](https://img.shields.io/badge/api-docs-blue)](https://cmi-dair.github.io/styx)

Compile Python command line tool wrappers from Boutiques descriptors.

## Features

- [x] Modern Python 3.11+ target
- [x] Intellisense &amp; full static type checking for inputs and outputs
- [x] Documentation generation
- [x] Custom execution environments via dependency injection
- [x] Runtime input validation
- [ ] Unit test generation

## Boutiques descriptor implementation status: 66%

- [x] Documentation
- [x] Types (String, Numerical, File)
- [x] Flags
- [x] Lists
- [x] Enums
- [x] Constraints (Numeric ranges, Groups)
- [ ] (Conditional) outputs
- [ ] Execution meta data
- [ ] Tests
