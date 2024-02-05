# Mina Package Structure

[简体中文](README.md) | [English](README.en.md)

`Mina` is a "modular subpackaging" implementation based on `pdm-backend`.

`Mina` is also an implementation of the `Mina Package Structure`, which is a unique specification with the following features:

 - The entire project is treated as a workspace environment, and the dependency tree used by all subpackages is managed uniformly through existing facilities;
 - Subpackages declare their own information and dependencies referenced in the workspace;
 - Patching the `Metadata` read by the `pdm-backend` build release to reuse its build process;
 - Avoids some potential problems by providing a complete `build backend` for `PEP-517`.

`Mina` provides a `PEP-517` implementation called [`mina-build`](https://pypi.org/project/mina-build/),
It also provides a simple CLI implementation as the `PDM Plugin`;

`mina-build` only works when the package to be packaged is defined, Otherwise the behavior is the same as `pdm-backend`.

The CLI does provide a `pdm mina build <package>` command,
but you can also specify the package to be packaged via the environment variable `MINA_BUILD_TARGET` or by setting `mina-target` in `config-setting`.

## Quick Start

### Installing the CLI

At the moment, Mina only supports `pdm` as the main user function entry, but perhaps `poetry` will be supported later?

```bash
elaina@localhost $ pipx inject pdm pdm-mina
# or pdm
elaina@localhost $ pdm self add pdm-mina
```

Or specify in `pyproject.toml`:

```toml
[tool.pdm]
plugins = ["pdm-mina"]
```

Then run:

```bash
elaina@localhost $ pdm install --plugins
```

This will enable `pdm-mina` plugin in the current project.

### Introduce mina-build

Configure the following in the project `pyproject.toml`:

```toml
[build-system]
requires = ["mina-build>=0.2.5"]
build-backend = "pdm.backend"
```

### Edit pyproject.toml

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
[tool.mina.packages."core"]
[tool.mina.packages."io"]
[tool.mina.packages."onebot"]
[tool.mina.packages."elizabeth"]
```

The declaration of subpackages for `Mina` follows `PEP-621`.
Here we take the example of the configuration subpackage `core`.

```toml
[tool.mina.packages."core"]
includes = [
    "avilla/core"
]
# Equivalent to tool.pdm.includes, I don't know what happens if you leave it out, it's probably just the normal case - packing the module that name refers to.

# override = false

[tool.mina.packages."core".project]
name = "avilla-core" # the name of the subpackage on `pypi`, required
description = "..."
authors = ["..."]
version = "0.1.0" # version, not guaranteed to support dynamic fetching (as I haven't used it or tried it)
requires-python = ">=3.9"
dependencies = [ # Suggest filling in
    "aiohttp", # Although the `PEP-508` specification is used here, all packages will be redirected to the same name in project.dependencies.
    "starlette",
    "pydantic"
]
optional-dependencies = {
    "amnesia": ["graia-amnesia"] # example of optional dependencies
}
entry-points = {pdm = {mina = "mina.plugin:ensure_pdm"}} # entry-points declaration method
```

Once filled in, you can simply check it via the CLI's `pdm mina list`, or test it directly with `pdm mina build <pkg>`;

### Building a release package

Use `pdm mina build <pkg>` to build the corresponding sub-packages.

If you wish, you can use `pdm mina build -a/--all` to build all the subpackages at once.

It is recommended to use `twine` + `keyring` to publish to PyPI, but of course `pdm-publish`, or use Github Actions is also possible.

## Overriding the workspace configuration

If you wish, you can have Mina use an override workspace configuration to get the Project Spec when processing and injecting subpackaged `project` definitions; this feature is not enabled by default:

```toml
[tool.mina]
override-global = true # Enable this feature globally

[tool.mina.packages. "core"]
override = true # Enable this feature only in core subpackages
```

# Open source license

This project is open source using the MIT.
