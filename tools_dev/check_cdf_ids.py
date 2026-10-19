"""Compare the CDF_ID texts used by the old EORE code with IMSMA's customdefinedfield (name, datatype, entity)."""
import csv
import sys

sys.path.insert(0, r"C:/Users/Lenovo/Documents/dma_field_reports/addons/dma_field_reports/services")
import refdata  # noqa: E402

out, _m = refdata.read_package(open(r"C:/Users/Lenovo/Documents/dma_field_reports/local/imsma_ref_20250302.zip", "rb").read())
cdfs = {r["cdf_id"]: r for r in out["cdfs.csv"]}
for r in csv.DictReader(open(r"C:/Users/Lenovo/Documents/imsma-importer/analysis/mappings/MRE_MDC.csv", encoding="utf8")):
    if not r["cdf_guid"]:
        continue
    c = cdfs.get(r["cdf_guid"])
    if not c:
        print("MISSING", r["cdf_guid"], r["cdf_id"])
        continue
    composed = f"{r['cdf_id'].split('.')[0]}.{c['datatype']}.{c['name']}"
    flag = "" if composed == r["cdf_id"] else "   <-- differs"
    print(f"{r['source_column_letter']:3} {r['cdf_id']!r:75} imsma name={c['name']!r} type={c['datatype']} entity={c['entity']} active={c['active']}{flag}")
