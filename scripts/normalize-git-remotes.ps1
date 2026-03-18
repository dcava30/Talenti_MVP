param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$EnsureMainUpstream
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=== $Title ==="
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Invoke-GitChecked {
    param(
        [string]$RepoPath,
        [string[]]$GitArgs
    )

    & git -C $RepoPath @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "git -C $RepoPath $($GitArgs -join ' ') failed."
    }
}

function Test-RemoteExists {
    param(
        [string]$RepoPath,
        [string]$RemoteName
    )

    & git -C $RepoPath remote get-url $RemoteName *> $null
    return $LASTEXITCODE -eq 0
}

Require-Command "git"

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$repoDefinitions = @(
    @{
        Path = $repoRootResolved
        Label = "main app"
        Remote = "git@github.com:dcava30/Talenti_MVP.git"
        EnsureUpstream = $true
    },
    @{
        Path = (Join-Path $repoRootResolved "model-service-1")
        Label = "model-service-1"
        Remote = "git@github.com:dcava30/Talenti_model_culture.git"
        EnsureUpstream = $false
    },
    @{
        Path = (Join-Path $repoRootResolved "model-service-2")
        Label = "model-service-2"
        Remote = "git@github.com:dcava30/Talenti_model_skills.git"
        EnsureUpstream = $false
    }
)

foreach ($repo in $repoDefinitions) {
    if (-not (Test-Path (Join-Path $repo.Path ".git"))) {
        continue
    }

    Write-Section "Normalize $($repo.Label) remotes"
    Invoke-GitChecked -RepoPath $repo.Path -GitArgs @("remote", "set-url", "origin", $repo.Remote)
    Write-Host "origin -> $($repo.Remote)"

    if ($repo.EnsureUpstream -and ($EnsureMainUpstream -or (Test-RemoteExists -RepoPath $repo.Path -RemoteName "upstream"))) {
        if (Test-RemoteExists -RepoPath $repo.Path -RemoteName "upstream") {
            Invoke-GitChecked -RepoPath $repo.Path -GitArgs @("remote", "set-url", "upstream", $repo.Remote)
        } else {
            Invoke-GitChecked -RepoPath $repo.Path -GitArgs @("remote", "add", "upstream", $repo.Remote)
        }
        Write-Host "upstream -> $($repo.Remote)"
    }
}
