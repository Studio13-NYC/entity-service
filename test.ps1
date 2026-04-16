<#
.SYNOPSIS
  Live smoke checks against a running NER service (use the real client over HTTP).

.DESCRIPTION
  Start the API first, for example:
    uv run fastapi dev app\main.py

  Then from another terminal:
    .\test.ps1
    .\test.ps1 http://127.0.0.1:8000
#>
param(
  [string] $BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$env:NER_SERVICE_URL = $BaseUrl

Push-Location $PSScriptRoot
try {
  npm run smoke
} finally {
  Pop-Location
}
