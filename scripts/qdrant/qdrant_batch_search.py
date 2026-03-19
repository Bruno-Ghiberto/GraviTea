#!/usr/bin/env python3
"""
Batch RAG Search — runs multiple queries and saves results to files.
====================================================================
Reads queries from a file (one per line) or from CLI arguments,
runs each through the RAG pipeline, and writes results to individual
.txt files in the output directory.

Usage:
    # From a queries file:
    .venv/bin/python scripts/qdrant/qdrant_batch_search.py -f queries.txt

    # From CLI arguments:
    .venv/bin/python scripts/qdrant/qdrant_batch_search.py \
        -q "acopio software market competitors" \
        -q "acopiador pain points regulatory" \
        -q "market sizing geographic distribution"

    # Custom output directory and collection:
    .venv/bin/python scripts/qdrant/qdrant_batch_search.py \
        -f queries.txt -o Docs/RAG_results -c acopio_research -l 5

    # JSON output:
    .venv/bin/python scripts/qdrant/qdrant_batch_search.py \
        -f queries.txt --json

Output files are named: {NN}_{sanitized_query}.txt
Example: 01_acopio_software_market_competitors.txt
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


DEFAULT_OUTPUT_DIR = "Docs/RAG_results"
SEARCH_SCRIPT = os.path.join(os.path.dirname(__file__), "qdrant_search.py")


def sanitize_filename(query: str, max_len: int = 60) -> str:
    """Convert a query string into a safe filename fragment."""
    # Lowercase, replace non-alnum with underscore, collapse multiples
    s = re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")
    return s[:max_len].rstrip("_")


def load_queries_from_file(filepath: str) -> list[str]:
    """Read queries from a text file, one per line. Skips blank/comment lines."""
    queries = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                queries.append(line)
    return queries


def run_query(
    query: str,
    output_path: str,
    python: str,
    collection: str | None,
    limit: int,
    json_output: bool,
    no_expand: bool,
) -> tuple[bool, str]:
    """Run a single query via qdrant_search.py and save to file."""
    cmd = [python, SEARCH_SCRIPT, "-q", query, "-l", str(limit), "-o", output_path]
    if collection:
        cmd.extend(["-c", collection])
    if json_output:
        cmd.append("--json")
    if no_expand:
        cmd.append("--no-expand")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        return False, result.stderr.strip()

    return True, result.stderr.strip()


def main():
    parser = argparse.ArgumentParser(
        description="Batch RAG search: run multiple queries, save results to files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-q", "--query",
        action="append",
        dest="queries",
        metavar="QUERY",
        help="Search query (repeatable). Alternative to --file.",
    )
    parser.add_argument(
        "-f", "--file",
        metavar="QUERIES_FILE",
        help="Path to a text file with one query per line.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        metavar="DIR",
        help=f"Output directory for result files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument("-c", "--collection", default=None, help="Force specific collection")
    parser.add_argument("-l", "--limit", type=int, default=5, help="Results per query (default: 5)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Save results as JSON")
    parser.add_argument("--no-expand", action="store_true", help="Disable query expansion")
    parser.add_argument(
        "--python",
        default=None,
        help="Python interpreter path (default: auto-detect .venv)",
    )

    args = parser.parse_args()

    # Collect queries
    queries: list[str] = []
    if args.file:
        queries.extend(load_queries_from_file(args.file))
    if args.queries:
        queries.extend(args.queries)
    if not queries:
        parser.error("No queries provided. Use -q QUERY or -f QUERIES_FILE.")

    # Resolve Python interpreter
    python = args.python
    if not python:
        # Auto-detect .venv in project root
        project_root = Path(__file__).resolve().parent.parent.parent
        venv_python = project_root / ".venv" / "bin" / "python"
        if venv_python.exists():
            python = str(venv_python)
        else:
            python = sys.executable

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Determine file extension
    ext = ".json" if args.json_output else ".txt"

    print(f"=== Batch RAG Search ===")
    print(f"Queries: {len(queries)}")
    print(f"Output:  {os.path.abspath(args.output_dir)}")
    print(f"Limit:   {args.limit} results/query")
    if args.collection:
        print(f"Collection: {args.collection}")
    print()

    # Run each query
    success_count = 0
    for i, query in enumerate(queries, 1):
        filename = f"{i:02d}_{sanitize_filename(query)}{ext}"
        output_path = os.path.join(args.output_dir, filename)

        ok, msg = run_query(
            query=query,
            output_path=output_path,
            python=python,
            collection=args.collection,
            limit=args.limit,
            json_output=args.json_output,
            no_expand=args.no_expand,
        )

        status = "OK" if ok else "FAIL"
        print(f"  [{status}] Q{i:02d}: {query[:70]}")
        if msg:
            # Print routing/expansion info indented
            for line in msg.split("\n"):
                print(f"         {line}")
        if ok:
            success_count += 1

    print(f"\n=== Done: {success_count}/{len(queries)} queries saved to {args.output_dir}/ ===")

    # Write a summary index file
    index_path = os.path.join(args.output_dir, "_index.txt")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f"# RAG Batch Search Results\n")
        f.write(f"# Generated by qdrant_batch_search.py\n")
        f.write(f"# Limit: {args.limit} results/query\n")
        if args.collection:
            f.write(f"# Collection: {args.collection}\n")
        f.write(f"#\n")
        for i, query in enumerate(queries, 1):
            filename = f"{i:02d}_{sanitize_filename(query)}{ext}"
            f.write(f"{filename}\t{query}\n")

    return 0 if success_count == len(queries) else 1


if __name__ == "__main__":
    sys.exit(main())
