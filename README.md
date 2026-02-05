# isweep-backend Dependency Management

## Installing dependencies

```sh
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Optional: Lock dependencies with pip-tools

```sh
pip install pip-tools
pip-compile requirements.in -o requirements.lock.txt
pip-compile requirements-dev.in -o requirements-dev.lock.txt
```

- Do NOT commit venv folders or lock files unless needed for reproducibility.
- _venv/ and .venv/ are ignored by .gitignore.
