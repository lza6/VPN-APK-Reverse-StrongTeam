#!/usr/bin/env pwsh
# Sync tools from apk-analysis workspace into this repo (single source of truth stays in repo).
param()
Copy-Item D:\apk-analysis\tools\lsparanoid_deobf.py tools\ -Force
Copy-Item D:\apk-analysis\REVERSE_REPORT.md docs\REVERSE_REPORT.md -Force
Write-Host 'synced'
