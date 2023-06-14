# PEP-517 implementation for Mina Package Structure

`mina-build` 是 `Mina Package Structure` 的具体实现, 基于 `pdm-backend` 的现有建构.

你需要在 `pyproject.toml` 内将 `tool.mina.enabled` 设为 `true` 才能使用 Mina 的相关功能,
否则 `mina-build` 的行为与 `pdm-backend` 一致.

若是需要关于 `Mina` 的更多信息, 请参阅其他的文稿.