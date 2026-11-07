"""Print the P0 reuse manifest with its upstream observations recomputed."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


MANIFEST = Path(__file__).resolve().parents[1] / "docs/implementation/reuse_manifest.json"
LINE_COUNT_METHOD = (
    "Count LF, CRLF or CR as one line terminator and count any final "
    "unterminated line. Empty files have zero lines."
)


def git_read(root: Path, *args: str) -> str:
    return subprocess.check_output(
        [
            "git", "--no-optional-locks",
            "-c", f"safe.directory={root.as_posix()}",
            "-c", "core.fsmonitor=false",
            "-C", str(root), *args,
        ],
        encoding="utf-8",
    )


def line_count(path: Path) -> int:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data.count(b"\n") + int(bool(data) and not data.endswith(b"\n"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, help="Override the checkout used for observation")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    baseline = manifest["baseline"]
    root = (args.upstream or Path(baseline["local_path"])).resolve(strict=True)
    if Path(git_read(root, "rev-parse", "--show-toplevel").strip()).resolve() != root:
        parser.error("--upstream must be the root of the upstream Git checkout")

    head, committed_at = git_read(root, "log", "-1", "--format=%H %cI").strip().split()
    status = git_read(root, "status", "--porcelain", "--untracked-files=all").splitlines()
    baseline.update(
        observed_head=head,
        observed_head_committed_at=committed_at,
        head_matches_design=head == baseline["expected_commit"],
        working_tree_matches_head=not status,
        working_tree_porcelain=status,
    )

    license_info = manifest["license"]
    license_info["sha256"] = hashlib.sha256((root / license_info["source_path"]).read_bytes()).hexdigest()
    notice_paths = []
    for directory, subdirs, files in os.walk(root):
        subdirs[:] = [name for name in subdirs if name != ".git"]
        notice_paths.extend(
            (Path(directory) / name).relative_to(root).as_posix()
            for name in files if name.startswith("NOTICE")
        )
    license_info["notice_candidate_paths"] = sorted(notice_paths)
    manifest["line_count_method"] = LINE_COUNT_METHOD
    source_paths = sorted(
        (path for path in (root / "danus").rglob("*.py") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    manifest["source_files"] = [
        {"path": path.relative_to(root).as_posix(), "lines": line_count(path)}
        for path in source_paths
    ]
    output = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.buffer.write(output.encode("utf-8"))


if __name__ == "__main__":
    main()
