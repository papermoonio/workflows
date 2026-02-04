# Workflows Repository

This repository contains scripts and resources designed to streamline workflow tasks across PaperMoon documentation projects. It serves as a centralized hub for shared tools and utilities used throughout documentation workflows.

License: Evaluation-only. You may download/build/run this software solely for internal evaluation. Any production or commercial use (including SaaS/hosting) requires a separate commercial license agreement with PaperMoon Dev SL.
## Structure

- **`llms_scripts/`**: Scripts for generating llms files.
- **`requirements.txt`**: Python dependencies for MkDocs-based documentation projects.
- **`utility_scripts/`**: General-purpose scripts, including `redirect_tester.py` (validates redirects and optional site targets).
- **`.github/workflows/`**: CI workflows used across documentation repos.

## Utility scripts (quick usage)

- `utility_scripts/redirect_tester.py`
	- Validates redirects from `redirects.json` and (optionally) checks built site targets.
	- Minimal run:
		- `python3 utility_scripts/redirect_tester.py --mkdocs-dir /path/to/mkdocs-repo`
	- Skip static target checks:
		- `python3 utility_scripts/redirect_tester.py --mkdocs-dir /path/to/mkdocs-repo --skip-static-check`
	- Write report to `redirect_report.json` in the mkdocs repo:
		- `python3 utility_scripts/redirect_tester.py --mkdocs-dir /path/to/mkdocs-repo --report`

## License

See the LICENSE file for details.
