param(
    [Parameter(Mandatory = $true)]
    [string]$Repo,

    [string]$MainBranch = "main",

    [string[]]$UatReviewerLogins = @(),
    [string[]]$ProdReviewerLogins = @(),

    [switch]$EnableShaPinning,
    [switch]$RestrictAllowedActions
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Resolve-ReviewerSpecs {
    param([string[]]$Logins)

    $reviewers = @()
    foreach ($login in $Logins) {
        $user = gh api "users/$login" | ConvertFrom-Json
        if (-not $user.id) {
            throw "Unable to resolve GitHub user id for '$login'."
        }
        $reviewers += @{ type = "User"; id = [int]$user.id }
    }
    return $reviewers
}

function Set-EnvironmentPolicy {
    param(
        [string]$EnvironmentName,
        [object[]]$Reviewers,
        [bool]$CustomBranchPolicies
    )

    $body = @{
        wait_timer = 0
        reviewers = $Reviewers
        can_admins_bypass = $false
        deployment_branch_policy = @{
            protected_branches = $false
            custom_branch_policies = $CustomBranchPolicies
        }
    } | ConvertTo-Json -Depth 8

    $tmp = Join-Path $env:TEMP ("gh-env-policy-" + [guid]::NewGuid().ToString("N") + ".json")
    [System.IO.File]::WriteAllText($tmp, $body, (New-Object System.Text.UTF8Encoding($false)))
    try {
        gh api --method PUT "repos/$Repo/environments/$EnvironmentName" --input $tmp | Out-Null
    } catch {
        if ($_.Exception.Message -like "*required reviewers protection rule*") {
            Write-Warning "Required reviewers are not supported on the current GitHub billing plan for '$EnvironmentName'. Applying fallback policy without reviewers."
            $fallbackBody = @{
                can_admins_bypass = $false
            } | ConvertTo-Json -Depth 5
            [System.IO.File]::WriteAllText($tmp, $fallbackBody, (New-Object System.Text.UTF8Encoding($false)))
            gh api --method PUT "repos/$Repo/environments/$EnvironmentName" --input $tmp | Out-Null
        } else {
            throw
        }
    } finally {
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    }
}

function Ensure-EnvBranchPolicy {
    param(
        [string]$EnvironmentName,
        [string]$BranchName
    )

    $policiesRaw = gh api "repos/$Repo/environments/$EnvironmentName/deployment-branch-policies" 2>$null
    if (-not $policiesRaw) {
        Write-Warning "Unable to query deployment branch policies for '$EnvironmentName'."
        return
    }
    $policies = $policiesRaw | ConvertFrom-Json
    $exists = $false
    if ($policies -and $policies.branch_policies) {
        foreach ($policy in $policies.branch_policies) {
            if ($policy.name -eq $BranchName) {
                $exists = $true
                break
            }
        }
    }

    if (-not $exists) {
        gh api --method POST "repos/$Repo/environments/$EnvironmentName/deployment-branch-policies" -f name="$BranchName" | Out-Null
    }
}

Require-Command "gh"

$null = gh auth status

Write-Host "Configuring GitHub Actions token defaults..."
gh api --method PUT "repos/$Repo/actions/permissions/workflow" -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false | Out-Null

if ($RestrictAllowedActions) {
    Write-Host "Restricting allowed actions to local + GitHub owned actions..."
    gh api --method PUT "repos/$Repo/actions/permissions" `
        -f enabled=true `
        -f allowed_actions=selected `
        -f github_owned_allowed=true `
        -f verified_allowed=true `
        -f patterns_allowed[]="actions/*" `
        -f patterns_allowed[]="github/*" | Out-Null
}

if ($EnableShaPinning) {
    Write-Host "Enabling SHA pinning requirement for workflow actions..."
    gh api --method PUT "repos/$Repo/actions/permissions" -f enabled=true -f allowed_actions=all -F sha_pinning_required=true | Out-Null
}

$uatReviewers = Resolve-ReviewerSpecs -Logins $UatReviewerLogins
$prodReviewers = Resolve-ReviewerSpecs -Logins $ProdReviewerLogins

Write-Host "Applying environment protections..."
Set-EnvironmentPolicy -EnvironmentName "dev" -Reviewers @() -CustomBranchPolicies $true
Set-EnvironmentPolicy -EnvironmentName "uat" -Reviewers $uatReviewers -CustomBranchPolicies $false
Set-EnvironmentPolicy -EnvironmentName "prod" -Reviewers $prodReviewers -CustomBranchPolicies $false

Ensure-EnvBranchPolicy -EnvironmentName "dev" -BranchName $MainBranch

Write-Host "Done."
Write-Host "- dev: protected deployment branch policy on '$MainBranch'"
Write-Host "- uat: required reviewers = $($UatReviewerLogins -join ', ')"
Write-Host "- prod: required reviewers enabled = $($ProdReviewerLogins -join ', ')"
