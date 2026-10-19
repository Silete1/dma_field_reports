"""Stored values per year for some CDFs (did the Access tool's values arrive?)."""
import sys
from collections import Counter

EX = "C:/Users/Lenovo/Documents/dma_imsma_data/extract/copy_cdfvalue.txt"
WATCH = {
    "c0a8-429c-15240423292-575ac7de-e86-ec": "Magazin (typo GUID in old tool)",
    "c0a8-429c-15240426832-2130ec27-e87-aa": "Folders",
    "c0a8-cc01-160e6ac65d2-2fbf5fc1-1d-ab3": "Funded by",
    "c0a7-f58e-1773eacedb7-ef3a9ab4-10-dff": "MAC owner",
}
c = Counter()
with open(EX, encoding="utf8") as f:
    cols = f.readline().split("(", 1)[1].split(")", 1)[0].split(", ")
    ix = {k: i for i, k in enumerate(cols)}
    for line in f:
        p = line.split("\t")
        if len(p) < len(cols):
            continue
        name = WATCH.get(p[ix["cdf_id"]])
        if name:
            c[(name, p[ix["dataentrydate"]][:4], p[ix["dataenterer"]] == "Dummy Data Enterer")] += 1
for k in sorted(c):
    print(k, c[k])
