"""Build the HPC archive: project + reserved corpus, never secrets, virtual environments, runs or results."""

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # ...\Documents\websemantic
SKIP_DIRS = {".venv", ".git", "__pycache__", "work", "runs", "build", ".pytest_cache", ".ruff_cache", "Resultats", "hpc-results"}


def main(out):
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for top in ("semantic-sim-layer", "benchmark-reserve"):
            for p in (ROOT / top).rglob("*"):
                if not p.is_file() or set(p.parts) & SKIP_DIRS or p.name == ".env" or p.suffix == ".zip":
                    continue
                z.write(p, Path("websemantic") / p.relative_to(ROOT))
                n += 1
    print(n, "files ->", out)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
