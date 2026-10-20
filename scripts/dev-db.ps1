# Start/stop the portable local PostgreSQL 16 for development (Windows).
# One-time setup (already done on this machine; for a new machine see README):
#   1. Download https://get.enterprisedb.com/postgresql/postgresql-16.15-1-windows-x64-binaries.zip
#   2. Extract to C:\Users\<you>\pgsql-portable-download\pgsql
#   3. pgsql\bin\initdb -D ..\data -U postgres -A trust -E UTF8
#   4. pgsql\bin\createdb -U postgres esports   (after starting)
#
# Usage:  .\scripts\dev-db.ps1 start | stop | status

param([Parameter(Mandatory = $true)][ValidateSet("start", "stop", "status")] [string]$Action)

$pgRoot = Join-Path $env:USERPROFILE "pgsql-portable-download"
$bin = Join-Path $pgRoot "pgsql\bin"
$data = Join-Path $pgRoot "data"
$log = Join-Path $pgRoot "pg.log"

switch ($Action) {
    "start"  { & "$bin\pg_ctl.exe" -D $data -l $log -o "-p 5432" start }
    "stop"   { & "$bin\pg_ctl.exe" -D $data stop }
    "status" { & "$bin\pg_isready.exe" -p 5432 }
}
