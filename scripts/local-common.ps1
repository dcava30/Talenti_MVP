function Write-Section {
    param([string]$Title)
    Write-Host "`n=== $Title ==="
}

function Invoke-Checked {
    param(
        [string]$Exe,
        [string[]]$Args,
        [string]$Workdir = ""
    )

    if ($Workdir) {
        Push-Location $Workdir
    }

    try {
        & $Exe @Args
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $Exe $($Args -join ' ')"
        }
    } finally {
        if ($Workdir) {
            Pop-Location
        }
    }
}

function Wait-ForComposePostgres {
    param(
        [string]$Workdir,
        [string]$User,
        [string]$Database,
        [int]$TimeoutSec = 180
    )

    $start = Get-Date
    while ((Get-Date) - $start -lt [TimeSpan]::FromSeconds($TimeoutSec)) {
        Push-Location $Workdir
        try {
            & docker compose exec -T postgres pg_isready -U $User -d $Database *> $null
            if ($LASTEXITCODE -eq 0) {
                return
            }
        } finally {
            Pop-Location
        }
        Start-Sleep -Seconds 2
    }

    throw "Timed out waiting for local PostgreSQL readiness."
}

function Get-DatabaseNameFromUrl {
    param([string]$DatabaseUrl)

    $match = [regex]::Match($DatabaseUrl, "/([^/?]+)(\?.*)?$")
    if (-not $match.Success) {
        throw "Could not determine database name from URL: $DatabaseUrl"
    }

    return $match.Groups[1].Value
}

function Ensure-ComposePostgresDatabase {
    param(
        [string]$Workdir,
        [string]$User,
        [string]$Database
    )

    $escapedDatabaseForLiteral = $Database.Replace("'", "''")
    $escapedDatabaseForIdentifier = $Database.Replace('"', '""')
    $existsQuery = "SELECT 1 FROM pg_database WHERE datname = '$escapedDatabaseForLiteral';"

    Push-Location $Workdir
    try {
        $exists = & docker compose exec -T postgres psql -U $User -d postgres -tAc $existsQuery
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to query PostgreSQL databases."
        }

        if (-not $exists.Trim()) {
            & docker compose exec -T postgres psql -U $User -d postgres -c "CREATE DATABASE `"$escapedDatabaseForIdentifier`";" *> $null
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to create PostgreSQL database '$Database'."
            }
        }
    } finally {
        Pop-Location
    }
}

function Ensure-Venv {
    param(
        [string]$VenvPath,
        [string]$PythonExe = "python"
    )

    if (-not (Test-Path $VenvPath)) {
        Write-Host "Creating venv at $VenvPath"
        & $PythonExe -m venv $VenvPath
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create venv at $VenvPath"
        }
    }

    $pythonPath = Join-Path $VenvPath "Scripts\python.exe"
    if (-not (Test-Path $pythonPath)) {
        throw "Python executable not found at $pythonPath"
    }

    return $pythonPath
}

function Require-RepoDirectory {
    param(
        [string]$Path,
        [string]$Label
    )

    if (-not (Test-Path $Path)) {
        throw "Missing $Label at $Path. Run .\scripts\setup-model-repos.ps1 first."
    }
}

function Set-Or-AppendEnvKey {
    param(
        [string]$EnvPath,
        [string]$Key,
        [string]$Value
    )

    if (-not (Test-Path $EnvPath)) {
        New-Item -ItemType File -Path $EnvPath -Force | Out-Null
    }

    $lines = Get-Content $EnvPath -ErrorAction SilentlyContinue
    if ($null -eq $lines) {
        $lines = @()
    }

    $pattern = "^$([regex]::Escape($Key))="
    $updated = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) {
            $lines[$i] = "$Key=$Value"
            $updated = $true
            break
        }
    }

    if (-not $updated) {
        $lines += "$Key=$Value"
    }

    Set-Content -Path $EnvPath -Value $lines -Encoding ASCII
}

function Resolve-DatabaseUrl {
    param(
        [ValidateSet("compose", "external")]
        [string]$DatabaseMode,
        [string]$ExternalDatabaseUrl,
        [int]$PostgresPort,
        [string]$PostgresUser,
        [string]$PostgresPassword,
        [string]$PostgresDb
    )

    if ($DatabaseMode -eq "external") {
        if (-not $ExternalDatabaseUrl) {
            throw "External mode requires -ExternalDatabaseUrl."
        }

        return $ExternalDatabaseUrl
    }

    return "postgresql+psycopg://${PostgresUser}:$PostgresPassword@localhost:$PostgresPort/$PostgresDb"
}

function Resolve-PythonCommand {
    param(
        [string]$RepoPath,
        [string]$FallbackPython = "python"
    )

    $venvPython = Join-Path $RepoPath ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }

    return $FallbackPython
}
