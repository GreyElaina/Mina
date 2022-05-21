# Mina Package Structure

[简体中文](README.md) | [English](README.en.md)

`Mina` is a "modular subpackaging" implementation based on `pdm-pep517`.

`Mina` is also an implementation of the `Mina Package Structure`, which is a unique specification with the following features:

 - The entire project is treated as a workspace environment, and the dependency tree used by all subpackages is managed uniformly through existing facilities;
 - Subpackages declare their own information and dependencies referenced in the workspace;
 - Patching the `Metadata` read by the `pdm-pep517` build release to reuse its build process;
 - Avoids some potential problems by providing a complete `build backend` for `PEP-517`.

`Mina` provides a `PEP-517` implementation called [`mina-build`](https://pypi.org/project/mina-build/),
It also provides a simple CLI implementation as the `PDM Plugin`;

`mina-build` only works when `tool.mina.enabled` is set to `true` in `pyproject.toml`,
Otherwise the behavior is the same as `pdm-pep517`.

The CLI does provide a `pdm mina build <package>` command,
but you can also specify the package to be packaged via the environment variable `MINA_BUILD_TARGET` or by setting `--mina-target` in `config-setting`.

## Quick Start

Configure the following in the project `pyproject.toml`:

```toml
[build-system]
requires = ["mina-build>=0.2.5"]
build-backend = "mina.backend"

[tool.mina]
enabled = true
```

If you wish, you can have Mina use an override of the workspace configuration to get project spec when processing and injecting subpackage's `project` definitions; this feature is not enabled by default:

```toml
[tool.mina]
enabled = true
override-global = true # Enable this feature globally

[tool.mina.packages. "core"]
override = true # Enable this feature only in core subpackages
```

Although the CLI is optional, and only `pdm` is supported so far, it's a good idea to install it:

```bash
elaina@localhost $ pdm add pdm-mina
```

Suppose you have the following directory structure:

```
mina-example/
├── avilla/
│ ├── core/
│ │ └── __init__.py
│ ├── io/
│ │ └── __init__.py
│ ├── onebot/
│ │ └── __init__.py
│ └── elizabeth/
│ └── __init__.py
└── pyproject.toml
```

If you need to publish these modules, or subpackages, under `avilla` as multiple packages, you can do it easily with `Mina`,
For example, in the above case we can declare a sub-package in `pyproject.toml` by filling in the following configs:

```toml
[tool.mina.packages. "core"]
[tool.mina.packages. "io"]
[tool.mina.packages. "onebot"]
[tool.mina.packages. "elizabeth"]
```

The declaration of subpackages for `Mina` follows `PEP-621`.
Here we take the example of the configuration subpackage `core`.

```toml
[tool.mina.packages. "core"]
includes = [
    "avilla/core"
]
# Equivalent to tool.pdm.includes, I don't know what happens if you leave it out, it's probably just follow the default behaviour - packing the module that name refers to.

# raw-dependencies = [...]
# This configuration item will be queued directly into the dependency declaration after project.dependencies has been processed.
# You can use this feature to declare dependencies between subpackages.

# override = false

[tool.mina.packages. "core".project]
name = "avilla-core" # the name of the subpackage on `pypi`, required
description = "..."
authors = ["..."]
version = "0.1.0" # version, not guaranteed to support dynamic fetching (as I haven't used it or tried it)
requires-python = ">=3.9"
dependencies = [ # Suggest filling in
    "aiohttp", # Although the `PEP-518` specification is used here, all packages will be redirected to the same name in project.dependencies.
    "starlette",
    "pydantic"
]
optional-dependencies = {
    "amnesia": ["graia-amnesia"] # example of optional dependencies
}
entry-points = {pdm = {mina = "mina.plugin:ensure_pdm"}} # entry-points declaration method, a table may be better.
```

Once filled in, you can simply check it with the CLI's `pdm mina list`, or test it directly with `pdm mina build <pkg>`;
It is recommended to use `twine` + `keyring` to publish to PyPI, but `pdm-publish` is also possible.

# Open Source License

This project is open source under MIT.

