#!/bin/sh
# usage: tools_dev/run.sh upgrade | shell <script.py>
cd /c/Users/Lenovo/Documents/odoo19
PY=./.venv_odoo19/Scripts/python.exe
CONF=odoo19_dma_field_reports.conf
case "$1" in
  upgrade) timeout 900 $PY -X utf8 odoo-19.0/odoo-bin -c $CONF -d dma_fr_dev -u dma_field_reports --stop-after-init --no-http 2>&1 | grep -E "ERROR|CRITICAL|Traceback|WARNING.*dma_fr|rror:" | grep -v "Postgres version" | head -30; echo "upgrade done";;
  shell) timeout 900 $PY -X utf8 odoo-19.0/odoo-bin shell -c $CONF -d dma_fr_dev --no-http < "$2" 2>&1 | grep -v -E "^2026.*INFO|py.warnings|UserWarning|warnings.warn";;
esac
