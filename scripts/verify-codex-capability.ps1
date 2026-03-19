param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$SshKeyPath = (Join-Path $env:USERPROFILE ".ssh\id_ed25519_personal"),
    [string]$SubscriptionId = "ea9dd497-9980-40a6-9e63-024f2c54e2d6"
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

function Invoke-GitCapture {
    param(
        [string]$RepoPath,
        [string[]]$GitArgs
    )

    $output = & git -C $RepoPath @GitArgs 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ($output | Out-String).Trim()
    }

    return ($output | Out-String).Trim()
}

function Test-GitHubSsh {
    param([string]$KeyPath)

    $sshCommand = "ssh -i `"$KeyPath`" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1"
    $output = & cmd.exe /d /c $sshCommand
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) {
        throw ($output | Out-String).Trim()
    }

    $combined = ($output | Out-String)
    if ($combined -notmatch "successfully authenticated" -and $combined -notmatch "shell access is not provided") {
        throw "SSH handshake did not return the expected GitHub authentication message."
    }
}

Require-Command "git"
Require-Command "ssh"
Require-Command "gh"
Require-Command "az"

$repoRootResolved = (Resolve-Path $RepoRoot).Path

Write-Section "Verify GitHub SSH"
if (-not (Test-Path $SshKeyPath)) {
    throw "SSH key not found at '$SshKeyPath'."
}
Test-GitHubSsh -KeyPath $SshKeyPath
Write-Host "SSH key verified: $SshKeyPath"

Write-Section "Verify GitHub CLI auth"
gh auth status

Write-Section "Verify Azure subscription context"
az account set --subscription $SubscriptionId
$accountJson = az account show --subscription $SubscriptionId --output json | ConvertFrom-Json
Write-Host "Subscription: $($accountJson.name) [$($accountJson.id)]"
Write-Host "Tenant: $($accountJson.tenantId)"

Write-Section "Verify main repo remotes"
    $mainOrigin = Invoke-GitCapture -RepoPath $repoRootResolved -GitArgs @("remote", "get-url", "origin")
Write-Host "origin: $mainOrigin"
if ($mainOrigin -ne "git@github.com:dcava30/Talenti_MVP.git") {
    Write-Host "WARNING: expected origin git@github.com:dcava30/Talenti_MVP.git"
}

& git -C $repoRootResolved remote get-url upstream *> $null
if ($LASTEXITCODE -eq 0) {
    $mainUpstream = Invoke-GitCapture -RepoPath $repoRootResolved -GitArgs @("remote", "get-url", "upstream")
    Write-Host "upstream: $mainUpstream"
    if ($mainUpstream -ne "git@github.com:dcava30/Talenti_MVP.git") {
        Write-Host "WARNING: expected upstream git@github.com:dcava30/Talenti_MVP.git"
    }
}

foreach ($repo in @(
    @{
        Folder = "model-service-1"
        Remote = "git@github.com:dcava30/Talenti_model_culture.git"
    },
    @{
        Folder = "model-service-2"
        Remote = "git@github.com:dcava30/Talenti_model_skills.git"
    }
)) {
    $targetPath = Join-Path $repoRootResolved $repo.Folder
    Write-Section "Verify $($repo.Folder)"
    if (-not (Test-Path $targetPath)) {
        Write-Host "Missing: $targetPath"
        continue
    }

    $originUrl = Invoke-GitCapture -RepoPath $targetPath -GitArgs @("remote", "get-url", "origin")
    $headSha = Invoke-GitCapture -RepoPath $targetPath -GitArgs @("rev-parse", "--short", "HEAD")
    Write-Host "origin: $originUrl"
    Write-Host "head: $headSha"
    if ($originUrl -ne $repo.Remote) {
        Write-Host "WARNING: expected $($repo.Remote)"
    }
}
