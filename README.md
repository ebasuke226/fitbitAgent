# python-ci-templates

2025年版 Python CI 比較（Flake8/Black/isort/mypy vs Ruff + mypy）。

## ローカル実行
```bash
pip install -r requirements-dev.txt

# 旧来スタック
black --check .
isort --check-only .
flake8 .
mypy .

# Ruff構成
ruff format --check .
ruff check . --fix --exit-non-zero-on-fix
mypy .
