import os
import hashlib
import nbformat

DOCS_NOTEBOOK_DIR = "docs-repo/tutorials/klusterai-api"
COOKBOOK_NOTEBOOK_DIR = "cookbook-repo/examples"


def hash_notebook(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)
    content = nbformat.writes(nb, version=4)
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def collect_notebook_hashes(folder):
    hashes = {}
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".ipynb"):
                full_path = os.path.join(root, file)
                hash_val = hash_notebook(full_path)
                hashes[file] = hash_val
    return hashes


def main():
    docs_hashes = collect_notebook_hashes(DOCS_NOTEBOOK_DIR)
    cookbook_hashes = collect_notebook_hashes(COOKBOOK_NOTEBOOK_DIR)

    mismatches = []
    for name, docs_hash in docs_hashes.items():
        if name in cookbook_hashes:
            if docs_hash != cookbook_hashes[name]:
                mismatches.append(name)

    if mismatches:
        print("🔴 Hash mismatches found in the following notebooks:")
        for name in mismatches:
            print(f" - {name}")
        exit(1)  # ❌ Causes the job to fail
    else:
        print("✅ All notebook hashes match.")
        # No exit needed; script ends, job passes

if __name__ == "__main__":
    main()
