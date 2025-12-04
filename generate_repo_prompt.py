#!/usr/bin/env python3
"""
generate_repo_prompt.py
──────────────────────────────────────────────────────────────────────────────
Create a markdown file that contains

  • a pretty Unicode directory tree
  • the full contents of every readable text-like file

Skips helper artifacts (this script, the Dockerfile, the report itself) and
ignores heavy/binary directories like .git or node_modules.

Usage
─────
    python generate_repo_prompt.py [PATH] [OUTFILE] [--verbose]

    PATH     : directory to scan  (default: /app)
    OUTFILE  : markdown report    (default: repo_prompt.txt)

Example inside container
────────────────────────
    docker run --rm -v "$PWD":/app repo-prompt       # writes /app/repo_prompt.txt
"""
from __future__ import annotations
import argparse, os, sys, textwrap
from pathlib import Path
from typing import Iterable

# ───── configuration ─────────────────────────────────────────────────────────
EXCLUDE_DIRS  = {".git", "node_modules", ".venv", ".idea", "__pycache__"}
SKIP_FILES    = {  # names, *not* patterns
    "generate_repo_prompt.py",
    "repo_prompt.dockerfile",
    "Dockerfile",
    "repo_prompt.txt",
    "package-lock.json",
    ".gitignore",
}
TEXT_EXTS = {
    # source / config / docs
    ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml", ".toml",
    ".md", ".markdown", ".txt", ".rst",
    ".html", ".htm", ".css", ".scss",
    ".xml", ".svg",
    ".c", ".cpp", ".h", ".hpp", ".java", ".go", ".rs", ".rb", ".php", ".sh",
    ".ini", ".cfg", ".conf", ".csv", ".tsv", ".sql",
}
UTF8_SAMPLE = 8192
# ─────────────────────────────────────────────────────────────────────────────


def is_probably_text(path: Path) -> bool:
    """Fast heuristic: (1) extension whitelist → (2) utf-8 sniff of first 8 KB."""
    if path.suffix.lower() in TEXT_EXTS:
        return True
    try:
        with path.open("rb") as fh:
            fh.read(UTF8_SAMPLE).decode("utf-8")
        return True
    except Exception:
        return False


def iter_files(root: Path) -> Iterable[Path]:
    """Yield every file below *root* that isn't excluded."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            if name in SKIP_FILES:
                continue
            yield Path(dirpath) / name


def print_tree(root: Path, out, prefix: str = "") -> None:
    """Write a pretty tree to *out*, respecting EXCLUDE_DIRS."""
    kids = [
        p for p in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        if p.name not in EXCLUDE_DIRS and p.name not in SKIP_FILES
    ]
    last = len(kids) - 1
    for idx, child in enumerate(kids):
        joint = "└──" if idx == last else "├──"
        out.write(f"{prefix}{joint} {child.name}\n")
        if child.is_dir():
            next_prefix = prefix + ("    " if idx == last else "│   ")
            print_tree(child, out, next_prefix)


def dump_repo(root: Path, outfile: Path, verbose: bool = False) -> None:
    SKIP_FILES.add(outfile.name)          # never include the report itself

    with outfile.open("w", encoding="utf-8") as out:
        # ─ directory tree ─
        out.write("## directory structure\n")
        out.write(f"{root.name}\n")
        print_tree(root, out)

        # ─ file contents ─
        for f in iter_files(root):
            if not is_probably_text(f):
                if verbose:
                    print(f"skip binary  : {f.relative_to(root)}", file=sys.stderr)
                continue

            rel = f.relative_to(root)
            if verbose:
                print(f"include text : {rel}", file=sys.stderr)

            out.write(f"\n## {rel}\n\n")
            try:
                out.write(f.read_text(errors="replace"))
            except Exception as e:
                out.write(f"[unable to read: {e}]\n")
            out.write("\n")

    print(f"✓ Report written to {outfile}")


def main() -> None:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(__doc__),
        add_help=False,
    )
    parser.add_argument("path",    nargs="?", default="/app")
    parser.add_argument("outfile", nargs="?", default="repo_prompt.txt")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    outfile = Path(args.outfile).resolve()

    if not root.is_dir():
        sys.exit(f"Error: '{root}' is not a directory")

    dump_repo(root, outfile, args.verbose)


if __name__ == "__main__":
    main()
