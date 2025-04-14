# LLM Documentation Generation Scripts

This repository provides a set of Python scripts to automatically compile your project’s Markdown documentation into files that are more easily consumed by large language models (LLMs). This helps you build advanced developer assistance and in-depth context for ChatGPT or similar AI tools.

## Contents

- **`llms_config.json`**  
  Contains project configuration (name, URL, base paths, doc categories, etc.). Update the values to match your project.

- **`generate_llms.py`**  
  A master script that invokes the two main generation steps:
  1. **Standard Generation** (gathers all documentation into `llms-full.txt` and a structural `llms.txt`)
  2. **Category Generation** (splits docs by categories defined in `llms_config.json`)

- **`generate_llms_standard.py`**  
  Crawls your documentation folder (by default `docs/`), processes any snippet includes, and builds:
  - `llms-full.txt`: A single, large text file containing all doc content.
  - `llms.txt`: A simpler outline of pages.

- **`generate_llms_by_category.py`**  
  Further organizes your documentation by product or feature “categories.”  
  - Reads metadata from frontmatter in `.md` files (e.g., `categories: someCategory`).
  - Produces `llms-somecategory.txt` for each category, optionally merging in any “sharedCategories” (e.g., “basics,” “reference”).

- **`transform_tables.py`**  
  A utility for converting HTML `<table>` elements in your Markdown files into raw Markdown tables.

## Prerequisites

- Python 3.x

## Usage

1. **Adjust `llms_config.json`**  
   - Set `projectName`, `projectUrl`, `raw_base_url`, etc
   - Define any “categories” or “sharedCategories” you plan to use

2. **Update `generate_llms_standard.py`**  
   - Point `docs_repo` to the folder where your Markdown files live
   - Adjust `docs_url` if you have a public docs site

3. **Prepare Your Documentation**  
   - In the metadata of your `.md` or `.mdx` pages include a "categories:" line, you can add one or more category tags
   - Each category tags should be separated by a comma, and if the category name is two or more words use a hyphen - 
   - snippet files called with (`--8<-- 'path/to/snippet'`), should be places in the `.snippets` folder

4. **Workflow modification**
   - If you use the `transfor_tables` script, make sure to update your workflow to install `beautifulsoup4`
   - `pip install pyyaml requests beautifulsoup4`

5. **Run the Scripts**  
   - From the repository root (or wherever the scripts are located), run:
     ```bash
     python3 generate_llms.py
     ```
   - The script will:
     - Build `llms-full.txt` and `llms.txt` in your docs folder (via **generate_llms_standard**).
     - Build category-based `.txt` files in `docs/llms-files` (via **generate_llms_by_category**).

6. **Review Outputs**  
   - `llms-full.txt`: All docs in one file, suitable for uploading to an LLM context window (or an embedding pipeline).
   - `llms-<category>.txt`: Each top-level category you defined in `llms_config.json` gets a dedicated file.

## Customization

Feel free to modify any of these scripts to suit your directory structure or naming conventions. If you don’t need categories, you can omit `generate_llms_by_category.py` or skip calling `generate_all_categories()` in `generate_llms.py`.

