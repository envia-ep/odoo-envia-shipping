import io
import sys

zip_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/envia.zip"
with open(zip_path, "rb") as f:
    zip_data = f.read()
_, names = env["ir.module.module"]._import_zipfile(io.BytesIO(zip_data))
print("Imported:", names)
envia = env["ir.module.module"].search([("name", "=", "envia")])
print("envia before install:", envia.state, "imported=", envia.imported)
envia.button_immediate_install()
env.cr.commit()
print("envia after install:", envia.state)
http = env["ir.module.module"].search([("name", "=", "envia_http")])
print("envia_http:", http.state, "imported=", http.imported)
