"""Check published source URLs against their recorded normalized hashes."""

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    records = {}
    for name in ("files.json", "files-lql.json", "files-pyrcel.json"):
        index = json.loads((root / "agent" / name).read_text(encoding="utf-8"))
        for record in index["files"]:
            if record["url"] in records:
                assert records[record["url"]]["sha256_lf"] == record["sha256_lf"]
            records[record["url"]] = record

    def verify(record):
        row = {"path": record["path"], "url": record["url"], "expected": record["sha256_lf"]}
        try:
            request = Request(record["url"], headers={"User-Agent": "WebSemantic-source-verification"})
            with urlopen(request, timeout=45) as response:
                data = response.read().replace(b"\r\n", b"\n")
                row["http_status"] = response.status
                row["actual"] = hashlib.sha256(data).hexdigest()
                row["match"] = row["actual"] == row["expected"]
        except (OSError, ValueError) as error:
            row["match"] = False
            row["error"] = str(error)
        return row

    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(verify, records.values()))
    report = {"checked_at": datetime.now(timezone.utc).isoformat(),
              "scope": "Published URLs and content hashes; no scientific or agent-performance claim",
              "files": results, "matched": sum(r["match"] for r in results), "total": len(results)}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report["matched"], "/", report["total"], "published sources match")
    return 0 if all(r["match"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
