# Mina Package Structure

`Mina` 是基于 `pdm-pep517` 的 "模块分包" 实现.

`Mina` 同样也是 `Mina Package Structure` 的实现, 作为一门独特的规范, 其具有以下特性:

 - 将整个项目作为工作区环境, 通过现有的设施统一管理所有分包使用的依赖树;
 - 分包各自声明自己的信息和工作区中引用的依赖;
 - 对 `pdm-pep517` 构建发布时所读取的 `Metadata` 进行修补以复用其构建流程;
 - 通过提供完整的 `PEP-517` 构建后端 (`build backend`), 避免了一些潜在的问题.

`Mina` 提供了名为 [`mina-build`](https://pypi.org/project/mina-build/) 的 `PEP-517` 实现,
同时还提供作为 `PDM Plugin` 的简易 CLI 实现;

`mina-build` 仅在 `pyproject.toml` 中 `tool.mina.enabled` 被设为 `true` 时起作用,
其他情况下的行为与 `pdm-pep517` 无异.

CLI 中虽提供了一个 `pdm mina build <package>` 指令,
但你也可以通过环境变量 `MINA_BUILD_TARGET` 或是 `config-setting` 中设置 `--package` 指定需要打包的分包.

## Quick Start

在项目的 `pyproject.toml` 中配置以下项:

```toml
[build-system]
requires = ["mina-build>=0.1.7"]
build-backend = "mina.backend"

[tool.mina]
enabled = true
```

虽然 CLI 是可选的, 并且到现在还只支持 `pdm`, 但还是装上吧:

```bash
elaina@localhost $ pdm add pdm-mina
```

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

`Mina` 的分包声明沿用了 `PEP-621` 中的声明方式, 但并非完全都是, 所以有时候你或许会被 pdm/otherpkg 的检查阻拦下, 这个问题后续会得到解决.
我们这里以配置分包 `core` 举例.

```toml
[tool.mina.packages."core"]
name = "avilla-core"  # 分包在 `pypi` 上的名称, 必填
description = "..."
authors = ["..."]
includes = ["avilla/core"]  # 相当于 tool.pdm.includes, 必填
version = "0.1.0"  # 版本, 后续会提供动态获取的支持, 当然是 pdm 同款. 必填(目前).
requires-python = ">=3.9"  # 建议填入
dependencies = [  # 建议填入
    "aiohttp",  # 这里虽然使用 `PEP-508` 规范, 但所有包都会被重定向至 project.dependencies 上的同名项.
    "starlette",  # 后续会加入其他的支持.
    "pydantic"
]
optional-dependencies = {
    "amnesia": ["graia-amnesia"]  # optional dependencies 示例
}
entry-points = {
    "mina": "mina.plugin:ensure_pdm"  # entry point 实例
}
```

填入后, 你可以通过 CLI 的 `pdm mina list` 简单的检查, 或是直接 `pdm mina build <pkg>` 测试.

因为未知原因, 我没法测试 `pdm-publish`, 但理论上支持, `twine` 倒是可以用, 我试过了.

当然如果你真的要 `--no-clean` 我也没办法...

# 开源协议

本项目使用 MIT 协议开源.