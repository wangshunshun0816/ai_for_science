"""Write or check generated R02 component bundles."""

import argparse
from pathlib import Path

from danus_ai.contracts.export_schema import Format, schema_bytes

OUTPUTS: tuple[tuple[str, Format], ...] = (
    ("r02.schema.json", "json-schema"),
    ("r02.openapi.json", "openapi"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "schemas"
    if not args.check:
        root.mkdir(exist_ok=True)
    bad = []
    for filename, format in OUTPUTS:
        target = root / filename
        generated = schema_bytes(format)
        if args.check:
            if not target.is_file() or target.read_bytes() != generated:
                bad.append(filename)
        else:
            target.write_bytes(generated)
    if bad:
        print("Stale R02 schema bundles:", ", ".join(bad))
        return 1
    print("R02 schema bundles:", "verified" if args.check else "generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
