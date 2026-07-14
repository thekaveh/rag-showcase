from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .build_docs import WIKI_SRC, build

REPO = "git@github.com:thekaveh/rag-showcase.wiki.git"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Push generated/wiki to the GitHub wiki master branch.")
    parser.add_argument("--push", action="store_true", help="Actually push; otherwise only build and report.")
    args = parser.parse_args()

    build(site=False, wiki=True, mkdocs=False)
    if not args.push:
        print(f"generated wiki at {WIKI_SRC}")
        return

    os.environ.setdefault("GIT_AUTHOR_NAME", "rag-showcase docs bot")
    os.environ.setdefault("GIT_AUTHOR_EMAIL", "docs@rag-showcase.local")
    os.environ.setdefault("GIT_COMMITTER_NAME", os.environ["GIT_AUTHOR_NAME"])
    os.environ.setdefault("GIT_COMMITTER_EMAIL", os.environ["GIT_AUTHOR_EMAIL"])

    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / "wiki"
        run(["git", "clone", REPO, str(work)])
        for child in work.iterdir():
            if child.name == ".git":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        for src in WIKI_SRC.iterdir():
            dst = work / src.name
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        run(["git", "add", "."], cwd=work)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=work, check=True, text=True, capture_output=True)
        if not status.stdout.strip():
            print("wiki already up to date")
            return
        run(["git", "commit", "-m", "docs: sync generated wiki"], cwd=work)
        run(["git", "push", "origin", "HEAD:master"], cwd=work)


if __name__ == "__main__":
    main()
