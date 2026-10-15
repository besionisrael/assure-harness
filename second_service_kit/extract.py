"""Extract the files of a model's answer (format "### FILE: <name>" + fenced block).

  python extract.py answer.txt output_folder

Writes every file into output_folder, overwriting files with the same name, and
lists them. Run validate.py from output_folder afterwards."""
import re
import sys
from pathlib import Path

FILE = re.compile(r"^###\s*FILE:\s*`?([\w.\-]+)`?\s*$", re.M)
FENCE = re.compile(r"^```[\w-]*[^\n]*\n(.*?)^```\s*$", re.S | re.M)


def main(answer, out_dir):
    text = Path(answer).read_text(encoding="utf-8")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    heads = list(FILE.finditer(text))
    if not heads:
        raise SystemExit("no '### FILE: <name>' line found")
    for i, h in enumerate(heads):
        chunk = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        block = FENCE.search(chunk)
        if block is None:
            print(f"!! {h.group(1)}: no fenced block found, skipped")
            continue
        (out / h.group(1)).write_text(block.group(1), encoding="utf-8")
        print(f"wrote {out / h.group(1)} ({len(block.group(1).splitlines())} lines)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
