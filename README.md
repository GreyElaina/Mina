# Mina Package Structure

[简体中文](README.md) | [English](README.en.md)

`Mina` 是基于 `pdm-backend` 的 "模块分包" 实现.

`Mina` 同样也是 `Mina Package Structure` 的实现, 作为一门独特的规范, 其具有以下特性:

 - 将整个项目作为工作区环境, 通过现有的设施统一管理所有分包使用的依赖树;
 - 分包各自声明自己的信息和工作区中引用的依赖;
 - 对 `pdm-backend` 构建发布时所读取的 `Metadata` 进行修补以复用其构建流程;
 - 通过提供完整的 `PEP-517` 构建后端 (`build backend`), 避免了一些潜在的问题.

`Mina` 提供了名为 [`mina-build`](https://pypi.org/project/mina-build/) 的 `PEP-517` 实现,
同时还提供作为 `PDM Plugin` 的简易 CLI 实现;

`mina-build` 仅在配置了需要构建的分包名称时才会注入 `pdm-pep517` 的构建流程,
其他情况下的行为与 `pdm-backend` 无异.

CLI 中虽提供了一个 `pdm mina build <package>` 指令,
但你也可以通过环境变量 `MINA_BUILD_TARGET` 或是 `config-setting` 中设置 `--mina-target` 指定需要打包的分包.

## Quick Start

### 安装 CLI

目前, Mina 仅支持将 `pdm` 作为主要的用户功能入口, 但或许 `poetry` 会在之后得到支持?

```bash
elaina@localhost $ pip install pdm-mina
# or pdm
elaina@localhost $ pdm add pdm-mina -d
```

### 引入 mina-build

在项目的 `pyproject.toml` 中配置以下项:

```toml
[build-system]
requires = ["mina-build>=0.2.5"]
build-backend = "mina.backend"
```

### 编辑 pyproject.toml

假设你有如下的目录结构:

```
mina-example/
├── avilla/
│   ├── core/
│   │   └── __init__.py
│   ├── io/
│   │   └── __init__.py
│   ├── onebot/
│   │   └── __init__.py
│   └── elizabeth/
│       └── __init__.py
└── pyproject.toml
```

如果需要将 `avilla` 下的模块发为多个包, 用 `Mina` 可以简单的做到,
比如上面这种我们就可以在 `pyproject.toml` 内填入以下几个表来声明分包:

```toml
[tool.mina.packages."core"]
[tool.mina.packages."io"]
[tool.mina.packages."onebot"]
[tool.mina.packages."elizabeth"]
```

`Mina` 的分包声明沿用了 `PEP-621` 中的声明方式.
我们这里以配置分包 `core` 举例.

```toml
[tool.mina.packages."core"]
includes = [
    "avilla/core"
]
# 相当于 tool.pdm.includes, 如果不填我不知道会发生什么, 可能就是普通的情况 -- 打包 name 所指向的模块.

# raw-dependencies = [...]
#    这一配置项会在处理完 project.dependencies 后直接排入依赖声明.
#    你可以用这个特性来声明分包之间的依赖.

# override = false

[tool.mina.packages."core".project]
name = "avilla-core"  # 分包在 `pypi` 上的名称, 必填
description = "..."
authors = ["..."]
version = "0.1.0"  # 版本, 不保证支持动态获取(因为我没用过也没试过)
requires-python = ">=3.9"
dependencies = [  # 建议填入
    "aiohttp",  # 这里虽然使用 `PEP-508` 规范, 但所有包都会被重定向至 project.dependencies 上的同名项.
    "starlette",
    "pydantic"
]
optional-dependencies = {
    "amnesia": ["graia-amnesia"]  # optional dependencies 示例
}
entry-points = {pdm = {mina = "mina.plugin:ensure_pdm"}}  # entry-points 的声明方式
```

填入后, 你可以通过 CLI 的 `pdm mina list` 简单的检查, 或是直接 `pdm mina build <pkg>` 测试;

### 构建发布包

使用 `pdm mina build <pkg>` 可以构建对应的分包.

如果你希望, 你可以使用 `pdm mina build -a/--all` 一次性构建所有的分包.

这里推荐使用 `twine` + `keyring` 发布到 PyPI 上, 当然 `pdm-publish`, 或是用 Github Actions 也是可以的.

## 覆盖工作区配置

如果你希望, 你可以让 Mina 在处理和注入分包的 `project` 定义时, 使用覆盖工作区配置的形式来获得 Project Spec; 本特性默认不启用:

```toml
[tool.mina]
override-global = true  # 全局启用该特性

[tool.mina.packages."core"]
override = true  # 仅在 core 分包启用该特性
```

# 开源协议

本项目使用 MIT 协议开源.