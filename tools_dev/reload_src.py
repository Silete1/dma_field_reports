import base64
src = env["dma.fr.source"].search([], limit=1)
src.package_file = base64.b64encode(open(r"C:/Users/Lenovo/Documents/dma_field_reports/local/imsma_ref_20250302.zip", "rb").read())
src.action_refresh()
print(src.stats)
env.cr.commit()
