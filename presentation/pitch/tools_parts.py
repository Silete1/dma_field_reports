"""Fold exhibit parts into the engine files (idempotent).   (ANU sector-pitch kit)

    py -3.11 tools_parts.py

Every parts/<name>.css is folded at the end of anu-ex.css and every parts/<name>.js at the end of exhibits.js, each
between its own markers (/* PART <name> START */ … /* PART <name> END */), replaced on every run. Edit a part, run this,
then build.py. The kit ships parts/ex-dlv.* (the delivery edition's exhibits: Iraq maps, manifest sheet, street run,
cash chain, merchant bars, chat→tickets, vehicles, week strip, hand-written paper objects) already folded in.
"""
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
PARTS = HERE / "parts"


def fold(target, ext):
    t = HERE / target
    s = t.read_text(encoding="utf-8")
    for part in sorted(PARTS.glob(f"*.{ext}")):
        name = part.stem
        a, b = f"/* PART {name} START (tools_parts.py) */", f"/* PART {name} END */"
        s = re.sub(re.escape(a) + r".*?" + re.escape(b) + r"\n?", "", s, flags=re.S)
        # an edition-specific fold of the same part (older marker form) is replaced too
        s = re.sub(r"/\* DLV-START \(tools_parts\.py\) \*/.*?/\* DLV-END \*/\n?", "", s, flags=re.S) if name == "ex-dlv" else s
        s = s.rstrip() + "\n" + a + "\n" + part.read_text(encoding="utf-8").strip() + "\n" + b + "\n"
    t.write_text(s, encoding="utf-8")
    print(f"{target}: {len(s) // 1024} KB")


if __name__ == "__main__":
    fold("anu-ex.css", "css")
    fold("exhibits.js", "js")
