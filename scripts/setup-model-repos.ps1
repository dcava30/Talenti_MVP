param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$SshKeyPath = (Join-Path $env:USERPROFILE ".ssh\id_ed25519_personal"),
    [switch]$Fetch,
    [switch]$ForceReclone
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
        [string[]]$GitArgs,
        [string]$Workdir = ""
    )

    if ($Workdir) {
        Push-Location $Workdir
    }

    try {
        & git @GitArgs
        if ($LASTEXITCODE -ne 0) {
            throw "git $($GitArgs -join ' ') failed."
        }
    } finally {
        if ($Workdir) {
            Pop-Location
        }
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

function Ensure-CleanWorkingTree {
    param([string]$RepoPath)

    $status = Invoke-GitCapture -RepoPath $RepoPath -GitArgs @("status", "--short")
    if ($status) {
        throw "Refusing to replace '$RepoPath' because it has uncommitted changes."
    }
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

$repoRootResolved = (Resolve-Path $RepoRoot).Path
if (-not (Test-Path $SshKeyPath)) {
    throw "SSH key not found at '$SshKeyPath'."
}

Require-Command "git"
Require-Command "ssh"

$env:GIT_SSH_COMMAND = "ssh -i `"$SshKeyPath`" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"

$repoDefinitions = @(
    @{
        Folder = "model-service-1"
        Label = "culture model"
        Remote = "git@github.com:dcava30/Talenti_model_culture.git"
    },
    @{
        Folder = "model-service-2"
        Label = "skills model"
        Remote = "git@github.com:dcava30/Talenti_model_skills.git"
    }
)

Write-Section "Verify GitHub SSH access"
Test-GitHubSsh -KeyPath $SshKeyPath

foreach ($repo in $repoDefinitions) {
    $targetPath = Join-Path $repoRootResolved $repo.Folder

    if (-not (Test-Path $targetPath)) {
        Write-Section "Clone $($repo.Label)"
        Invoke-GitChecked -GitArgs @("clone", $repo.Remote, $repo.Folder) -Workdir $repoRootResolved
    } else {
        $gitDirPath = Join-Path $targetPath ".git"
        if (-not (Test-Path $gitDirPath)) {
            throw "Path '$targetPath' exists but is not a git repository. Move it aside or remove it, then rerun this script."
        }

        $originUrl = Invoke-GitCapture -RepoPath $targetPath -GitArgs @("remote", "get-url", "origin")
        if ($originUrl -ne $repo.Remote) {
            if (-not $ForceReclone) {
                throw "Repository '$targetPath' points at '$originUrl' instead of '$($repo.Remote)'. Rerun with -ForceReclone after confirming the folder is disposable."
            }

            Ensure-CleanWorkingTree -RepoPath $targetPath
            Remove-Item -Path $targetPath -Recurse -Force

            Write-Section "Reclone $($repo.Label)"
            Invoke-GitChecked -GitArgs @("clone", $repo.Remote, $repo.Folder) -Workdir $repoRootResolved
        }
    }

    if ($Fetch) {
        Write-Section "Fetch $($repo.Label)"
        Invoke-GitChecked -GitArgs @("-C", $targetPath, "fetch", "--prune", "--tags", "origin")
    }

    $headSha = Invoke-GitCapture -RepoPath $targetPath -GitArgs @("rev-parse", "--short", "HEAD")
    $branchName = Invoke-GitCapture -RepoPath $targetPath -GitArgs @("rev-parse", "--abbrev-ref", "HEAD")
    $originUrl = Invoke-GitCapture -RepoPath $targetPath -GitArgs @("remote", "get-url", "origin")

    Write-Host "$($repo.Folder): $branchName @ $headSha"
    Write-Host "origin: $originUrl"
}

Write-Section "Done"
Write-Host "Model repositories are available under:"
Write-Host "- $(Join-Path $repoRootResolved 'model-service-1')"
Write-Host "- $(Join-Path $repoRootResolved 'model-service-2')"
