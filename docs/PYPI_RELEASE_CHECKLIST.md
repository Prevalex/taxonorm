# PyPI Release Checklist

This project is technically prepared for a future PyPI upload, but the first
real publication should still be deliberate.

## Before Upload

- Review the public API exported from `taxonorm.__all__`.
- Review public exception types and stable diagnostic `code` values.
- Run the full local verification checklist.
- Build a fresh distribution from a clean working tree.
- Inspect wheel and sdist contents.
- Upload to TestPyPI first if the project name is still available there.

## License

The project uses the MIT License. The license text is stored in `LICENSE` and
declared in `pyproject.toml`.

## Local Verification

```shell
pytest -q
mypy
python -m build
twine check dist/*
```

## Optional Extras

- `taxonorm[excel]`: XLS/XLSX read/write support.
- `taxonorm[xml]`: XML read support.
- `taxonorm[view]`: terminal and HTML tree viewers.
- `taxonorm[graph]`: `networkx` adapter.
- `taxonorm[tree]`: `bigtree` adapter.
- `taxonorm[pandas]`: `pandas.DataFrame` import support.
