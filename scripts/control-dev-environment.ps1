<#
.SYNOPSIS
Starts, stops, or inspects the Talenti DEV Azure environment.

.DESCRIPTION
This script manages the current DEV deployment topology documented in
documentation/DEPLOYMENT_DEV_V2.md and infra/dev/main.bicep:

- Azure Container Apps:
  - ca-backend-dev
  - ca-backend-worker-dev
  - ca-model1-dev
  - ca-model2-dev
  - ca-acs-worker-dev
- Azure Database for PostgreSQL Flexible Server:
  - psql-talenti-dev-aue
- Azure Static Web App:
  - swa-talenti-dev-aue

Stop behavior:
- Saves the current container app scale settings to a local state file
- Disables Azure Monitor web tests and alerts unless -SkipAlertToggle is used
- Disables backend ingress
- Scales all container apps to min replicas 0
- Stops the PostgreSQL flexible server

Start behavior:
- Starts the PostgreSQL flexible server
- Restores container app scale settings from the saved state file, or from
  DEV infra defaults if no state file exists
- Re-enables backend ingress
- Optionally waits for backend /health to return 200
- Re-enables Azure Monitor web tests and alerts unless -SkipAlertToggle is used

Azure Static Web Apps does not expose a stop/start operation via az CLI, so the
frontend remains provisioned. When the environment is "stopped", the static app
can still serve assets, but the backend and database are intentionally offline.

.EXAMPLE
.\scripts\control-dev-environment.ps1 -Action status

.EXAMPLE
.\scripts\control-dev-environment.ps1 -Action stop -SubscriptionId <sub-id>

.EXAMPLE
.\scripts\control-dev-environment.ps1 -Action start -SubscriptionId <sub-id>

.EXAMPLE
.\scripts\control-dev-environment.ps1 -Action stop -DryRun
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("start", "stop", "status")]
    [string]$Action,

    [string]$SubscriptionId = "",
    [string]$ResourceGroup = "rg-talenti-dev-aue",
    [string]$EnvironmentName = "dev",

    [string]$StaticWebApp = "swa-talenti-dev-aue",
    [string]$BackendApp = "ca-backend-dev",
    [string]$BackendWorkerApp = "ca-backend-worker-dev",
    [string]$Model1App = "ca-model1-dev",
    [string]$Model2App = "ca-model2-dev",
    [string]$AcsWorkerApp = "ca-acs-worker-dev",
    [string]$PostgresServer = "psql-talenti-dev-aue",

    [string]$StatePath = ".tmp/azure-dev-power-state.json",
    [string]$AzureConfigDir = "",

    [switch]$SkipAlertToggle,
    [switch]$SkipHealthCheck,
    [switch]$DryRun,

    [int]$PostgresStartTimeoutSeconds = 900,
    [int]$BackendHealthTimeoutSeconds = 300
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script:ResolvedStatePath = if ([System.IO.Path]::IsPathRooted($StatePath)) {
    $StatePath
} else {
    Join-Path $script:RepoRoot $StatePath
}

$script:ResolvedAzureConfigDir = ""
$script:ResolvedSubscriptionId = ""
$script:AzCliPath = ""
$script:AzCliTempDir = Join-Path $script:RepoRoot ".tmp\azure-cli-runner"

$script:ContainerAppDefinitions = @(
    [pscustomobject]@{
        Name = $BackendApp
        DefaultMinReplicas = 1
        DefaultMaxReplicas = 2
        IngressEnabled = $true
        IngressType = "external"
        TargetPort = 8000
        Transport = "auto"
    },
    [pscustomobject]@{
        Name = $BackendWorkerApp
        DefaultMinReplicas = 1
        DefaultMaxReplicas = 1
        IngressEnabled = $false
        IngressType = ""
        TargetPort = $null
        Transport = ""
    },
    [pscustomobject]@{
        Name = $Model1App
        DefaultMinReplicas = 1
        DefaultMaxReplicas = 2
        IngressEnabled = $true
        IngressType = "internal"
        TargetPort = 8001
        Transport = "auto"
    },
    [pscustomobject]@{
        Name = $Model2App
        DefaultMinReplicas = 1
        DefaultMaxReplicas = 2
        IngressEnabled = $true
        IngressType = "internal"
        TargetPort = 8002
        Transport = "auto"
    },
    [pscustomobject]@{
        Name = $AcsWorkerApp
        DefaultMinReplicas = 1
        DefaultMaxReplicas = 1
        IngressEnabled = $true
        IngressType = "internal"
        TargetPort = 8000
        Transport = "auto"
    }
)

$script:MetricAlertNames = @(
    "alert-backend-5xx-$EnvironmentName",
    "alert-backend-latency-$EnvironmentName",
    "alert-$BackendApp-restarts",
    "alert-$BackendWorkerApp-restarts",
    "alert-$Model1App-restarts",
    "alert-$Model2App-restarts",
    "alert-$AcsWorkerApp-restarts"
)

$script:ScheduledQueryAlertNames = @(
    "alert-backend-availability-$EnvironmentName",
    "alert-frontend-availability-$EnvironmentName",
    "alert-job-queue-backlog-$EnvironmentName",
    "alert-job-queue-age-$EnvironmentName"
)

$script:WebTestNames = @(
    "wt-talenti-backend-$EnvironmentName",
    "wt-talenti-frontend-$EnvironmentName"
)

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

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Get-AzCliPath {
    if ($script:AzCliPath) {
        return $script:AzCliPath
    }

    $azCommand = Get-Command "az.cmd" -ErrorAction SilentlyContinue
    if (-not $azCommand) {
        $azCommand = Get-Command "az" -ErrorAction SilentlyContinue
    }
    if (-not $azCommand) {
        throw "Azure CLI executable not found."
    }

    $script:AzCliPath = $azCommand.Source
    return $script:AzCliPath
}

function Invoke-AzCommand {
    param(
        [string[]]$AzArgs,
        [switch]$AllowFailure
    )

    $azPath = Get-AzCliPath
    Ensure-Directory -Path $script:AzCliTempDir

    $effectiveArgs = @($AzArgs)
    if ($effectiveArgs -notcontains "--only-show-errors") {
        $effectiveArgs += "--only-show-errors"
    }

    $token = [guid]::NewGuid().Guid
    $stdoutPath = Join-Path $script:AzCliTempDir "$token.stdout.txt"
    $stderrPath = Join-Path $script:AzCliTempDir "$token.stderr.txt"

    try {
        $process = Start-Process `
            -FilePath $azPath `
            -ArgumentList $effectiveArgs `
            -WorkingDirectory $script:RepoRoot `
            -NoNewWindow `
            -Wait `
            -PassThru `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath

        $stdoutText = if (Test-Path $stdoutPath) { [System.IO.File]::ReadAllText($stdoutPath) } else { "" }
        $stderrText = if (Test-Path $stderrPath) { [System.IO.File]::ReadAllText($stderrPath) } else { "" }

        if ($null -eq $stdoutText) { $stdoutText = "" }
        if ($null -eq $stderrText) { $stderrText = "" }

        if ($process.ExitCode -ne 0 -and -not $AllowFailure) {
            $stderrRendered = $stderrText.Trim()
            $stdoutRendered = $stdoutText.Trim()
            throw "Azure CLI command failed: az $($effectiveArgs -join ' ')`nSTDERR:`n$stderrRendered`nSTDOUT:`n$stdoutRendered"
        }

        return [pscustomobject]@{
            ExitCode = $process.ExitCode
            StdOut = $stdoutText
            StdErr = $stderrText
        }
    } finally {
        foreach ($path in @($stdoutPath, $stderrPath)) {
            if (Test-Path $path) {
                Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function Invoke-AzJson {
    param([string[]]$AzArgs)
    $result = Invoke-AzCommand -AzArgs $AzArgs
    $rendered = $result.StdOut.Trim()
    if (-not $rendered) {
        return $null
    }
    return $rendered | ConvertFrom-Json
}

function Invoke-AzTsv {
    param(
        [string[]]$AzArgs,
        [switch]$AllowFailure
    )

    $result = Invoke-AzCommand -AzArgs $AzArgs -AllowFailure:$AllowFailure
    return $result.StdOut.Trim()
}

function Invoke-AzMutation {
    param(
        [string]$Description,
        [string[]]$AzArgs
    )

    if ($DryRun) {
        Write-Host "[dry-run] $Description"
        Write-Host "          az $($AzArgs -join ' ')"
        return
    }

    Write-Host $Description
    Invoke-AzCommand -AzArgs $AzArgs | Out-Null
}

function Initialize-AzContext {
    Write-Section "Azure context"

    Require-Command "az"
    $null = Get-AzCliPath

    $env:AZURE_CORE_ONLY_SHOW_ERRORS = "True"
    Ensure-Directory -Path $script:AzCliTempDir

    if ($AzureConfigDir) {
        $script:ResolvedAzureConfigDir = if ([System.IO.Path]::IsPathRooted($AzureConfigDir)) {
            $AzureConfigDir
        } else {
            Join-Path $script:RepoRoot $AzureConfigDir
        }
        Ensure-Directory -Path $script:ResolvedAzureConfigDir
        $env:AZURE_CONFIG_DIR = $script:ResolvedAzureConfigDir
        Write-Host "AZURE_CONFIG_DIR=$script:ResolvedAzureConfigDir"
    }

    Invoke-AzCommand -AzArgs @(
        "config", "set",
        "core.only_show_errors=yes",
        "extension.use_dynamic_install=yes_without_prompt",
        "extension.dynamic_install_allow_preview=true"
    ) | Out-Null

    try {
        Invoke-AzCommand -AzArgs @("extension", "add", "--name", "containerapp", "--upgrade") -AllowFailure | Out-Null
    } catch {
        Write-Warning "Unable to proactively install/upgrade the containerapp extension. Continuing."
    }

    try {
        Invoke-AzCommand -AzArgs @("extension", "add", "--name", "staticwebapp", "--upgrade") -AllowFailure | Out-Null
    } catch {
        Write-Warning "Unable to proactively install/upgrade the staticwebapp extension. Continuing."
    }

    if ($SubscriptionId) {
        Write-Host "Selecting Azure subscription $SubscriptionId"
        Invoke-AzCommand -AzArgs @(
            "account", "set",
            "--subscription", $SubscriptionId
        ) | Out-Null
        $script:ResolvedSubscriptionId = $SubscriptionId
    } else {
        $script:ResolvedSubscriptionId = Invoke-AzTsv -AzArgs @(
            "account", "show",
            "--query", "id",
            "-o", "tsv"
        )
        if (-not $script:ResolvedSubscriptionId) {
            throw "Unable to resolve the active Azure subscription. Pass -SubscriptionId explicitly after running az login."
        }
        Write-Host "Using active Azure subscription $script:ResolvedSubscriptionId"
    }

    Invoke-AzCommand -AzArgs @(
        "group", "show",
        "--name", $ResourceGroup
    ) | Out-Null
}

function Get-ContainerAppDefinition {
    param([string]$Name)

    $definition = $script:ContainerAppDefinitions | Where-Object { $_.Name -eq $Name } | Select-Object -First 1
    if (-not $definition) {
        throw "Unknown container app definition for '$Name'."
    }
    return $definition
}

function Get-ContainerAppRuntimeState {
    param([string]$Name)

    $app = Invoke-AzJson -AzArgs @(
        "containerapp", "show",
        "--name", $Name,
        "--resource-group", $ResourceGroup,
        "-o", "json"
    )

    $definition = Get-ContainerAppDefinition -Name $Name
    $ingress = $app.properties.configuration.ingress
    $scale = $app.properties.template.scale

    return [pscustomobject]@{
        name = $Name
        minReplicas = if ($null -ne $scale.minReplicas) { [int]$scale.minReplicas } else { [int]$definition.DefaultMinReplicas }
        maxReplicas = if ($null -ne $scale.maxReplicas) { [int]$scale.maxReplicas } else { [int]$definition.DefaultMaxReplicas }
        ingressEnabled = ($null -ne $ingress)
        ingressType = if ($null -eq $ingress) { "" } elseif ($ingress.external) { "external" } else { "internal" }
        targetPort = if ($null -ne $ingress -and $null -ne $ingress.targetPort) { [int]$ingress.targetPort } else { $null }
        transport = if ($null -ne $ingress -and $ingress.transport) { ([string]$ingress.transport).ToLowerInvariant() } else { "" }
        fqdn = if ($null -ne $ingress -and $ingress.fqdn) { [string]$ingress.fqdn } else { "" }
        latestRevisionName = [string]$app.properties.latestRevisionName
        latestReadyRevisionName = [string]$app.properties.latestReadyRevisionName
    }
}

function Get-AllContainerAppRuntimeState {
    return @($script:ContainerAppDefinitions | ForEach-Object {
        Get-ContainerAppRuntimeState -Name $_.Name
    })
}

function Get-PostgresState {
    $server = Invoke-AzJson -AzArgs @(
        "postgres", "flexible-server", "show",
        "--name", $PostgresServer,
        "--resource-group", $ResourceGroup,
        "-o", "json"
    )

    if ($server.state) {
        return [string]$server.state
    }
    if ($server.userVisibleState) {
        return [string]$server.userVisibleState
    }
    return ""
}

function Get-StaticWebAppHostname {
    return Invoke-AzTsv -AzArgs @(
        "staticwebapp", "show",
        "--name", $StaticWebApp,
        "--resource-group", $ResourceGroup,
        "--query", "defaultHostname",
        "-o", "tsv"
    ) -AllowFailure
}

function Test-LooksStopped {
    param(
        [object[]]$ContainerState,
        [string]$PostgresState
    )

    $allScaledToZero = $true
    foreach ($app in $ContainerState) {
        if ([int]$app.minReplicas -ne 0) {
            $allScaledToZero = $false
            break
        }
    }

    $backend = $ContainerState | Where-Object { $_.name -eq $BackendApp } | Select-Object -First 1
    $backendIngressDisabled = $null -ne $backend -and -not [bool]$backend.ingressEnabled
    $postgresStopped = -not $PostgresState -or $PostgresState -notmatch "Ready|Starting"

    return ($allScaledToZero -and $backendIngressDisabled -and $postgresStopped)
}

function Save-RunningState {
    param(
        [object[]]$ContainerState,
        [string]$PostgresState
    )

    if (Test-LooksStopped -ContainerState $ContainerState -PostgresState $PostgresState) {
        if (Test-Path $script:ResolvedStatePath) {
            Write-Host "Environment already appears stopped; keeping existing state file at $script:ResolvedStatePath"
        } else {
            Write-Warning "Environment already appears stopped; no state snapshot was written because it would only capture the stopped configuration."
        }
        return
    }

    $parent = Split-Path -Parent $script:ResolvedStatePath
    if ($parent) {
        Ensure-Directory -Path $parent
    }

    $payload = [ordered]@{
        savedAt = (Get-Date).ToString("o")
        subscriptionId = $script:ResolvedSubscriptionId
        resourceGroup = $ResourceGroup
        environmentName = $EnvironmentName
        postgresServer = $PostgresServer
        apps = @($ContainerState | ForEach-Object {
            [ordered]@{
                name = $_.name
                minReplicas = [int]$_.minReplicas
                maxReplicas = [int]$_.maxReplicas
                ingressEnabled = [bool]$_.ingressEnabled
                ingressType = [string]$_.ingressType
                targetPort = if ($null -ne $_.targetPort) { [int]$_.targetPort } else { $null }
                transport = [string]$_.transport
            }
        })
    }

    ($payload | ConvertTo-Json -Depth 6) | Set-Content -Path $script:ResolvedStatePath -Encoding ASCII
    Write-Host "Saved running-state snapshot to $script:ResolvedStatePath"
}

function Get-SavedState {
    if (-not (Test-Path $script:ResolvedStatePath)) {
        return $null
    }

    $raw = Get-Content -Path $script:ResolvedStatePath -Raw
    if (-not $raw.Trim()) {
        return $null
    }

    return $raw | ConvertFrom-Json
}

function Get-DesiredAppState {
    param(
        [string]$Name,
        [object]$SavedState
    )

    if ($SavedState -and $SavedState.apps) {
        $match = @($SavedState.apps | Where-Object { $_.name -eq $Name }) | Select-Object -First 1
        if ($match) {
            return [pscustomobject]@{
                name = $Name
                minReplicas = [int]$match.minReplicas
                maxReplicas = [int]$match.maxReplicas
                ingressEnabled = [bool]$match.ingressEnabled
                ingressType = [string]$match.ingressType
                targetPort = if ($null -ne $match.targetPort) { [int]$match.targetPort } else { $null }
                transport = [string]$match.transport
            }
        }
    }

    $definition = Get-ContainerAppDefinition -Name $Name
    return [pscustomobject]@{
        name = $Name
        minReplicas = [int]$definition.DefaultMinReplicas
        maxReplicas = [int]$definition.DefaultMaxReplicas
        ingressEnabled = [bool]$definition.IngressEnabled
        ingressType = [string]$definition.IngressType
        targetPort = if ($null -ne $definition.TargetPort) { [int]$definition.TargetPort } else { $null }
        transport = [string]$definition.Transport
    }
}

function Set-ContainerAppScale {
    param(
        [string]$Name,
        [int]$MinReplicas,
        [int]$MaxReplicas
    )

    $effectiveMax = [Math]::Max($MinReplicas, $MaxReplicas)

    Invoke-AzMutation -Description "Setting $Name scale to min=$MinReplicas max=$effectiveMax" -AzArgs @(
        "containerapp", "update",
        "--name", $Name,
        "--resource-group", $ResourceGroup,
        "--min-replicas", [string]$MinReplicas,
        "--max-replicas", [string]$effectiveMax
    )
}

function Disable-BackendIngress {
    Invoke-AzMutation -Description "Disabling ingress for $BackendApp" -AzArgs @(
        "containerapp", "ingress", "disable",
        "--name", $BackendApp,
        "--resource-group", $ResourceGroup
    )
}

function Enable-BackendIngress {
    param([object]$DesiredState)

    if (-not $DesiredState.ingressEnabled) {
        Write-Host "Desired backend state keeps ingress disabled; skipping ingress enable."
        return
    }

    $targetPort = if ($null -ne $DesiredState.targetPort) { [int]$DesiredState.targetPort } else { 8000 }
    $transport = if ($DesiredState.transport) { ([string]$DesiredState.transport).ToLowerInvariant() } else { "auto" }
    $ingressType = if ($DesiredState.ingressType) { ([string]$DesiredState.ingressType).ToLowerInvariant() } else { "external" }

    Invoke-AzMutation -Description "Enabling $ingressType ingress for $BackendApp on port $targetPort" -AzArgs @(
        "containerapp", "ingress", "enable",
        "--name", $BackendApp,
        "--resource-group", $ResourceGroup,
        "--type", $ingressType,
        "--target-port", [string]$targetPort,
        "--transport", $transport
    )
}

function Set-WebTestEnabled {
    param(
        [string]$Name,
        [bool]$Enabled
    )

    $value = $Enabled.ToString().ToLowerInvariant()
    try {
        Invoke-AzMutation -Description "Setting web test $Name enabled=$value" -AzArgs @(
            "resource", "update",
            "--resource-group", $ResourceGroup,
            "--namespace", "Microsoft.Insights",
            "--resource-type", "webtests",
            "--name", $Name,
            "--api-version", "2022-06-15",
            "--set", "properties.Enabled=$value"
        )
    } catch {
        Write-Warning "Unable to update web test '$Name': $($_.Exception.Message)"
    }
}

function Set-ScheduledQueryAlertEnabled {
    param(
        [string]$Name,
        [bool]$Enabled
    )

    $value = $Enabled.ToString().ToLowerInvariant()
    try {
        Invoke-AzMutation -Description "Setting scheduled query alert $Name enabled=$value" -AzArgs @(
            "resource", "update",
            "--resource-group", $ResourceGroup,
            "--namespace", "Microsoft.Insights",
            "--resource-type", "scheduledQueryRules",
            "--name", $Name,
            "--api-version", "2023-03-15-preview",
            "--set", "properties.enabled=$value"
        )
    } catch {
        Write-Warning "Unable to update scheduled query alert '$Name': $($_.Exception.Message)"
    }
}

function Set-MetricAlertEnabled {
    param(
        [string]$Name,
        [bool]$Enabled
    )

    $value = $Enabled.ToString().ToLowerInvariant()
    try {
        Invoke-AzMutation -Description "Setting metric alert $Name enabled=$value" -AzArgs @(
            "monitor", "metrics", "alert", "update",
            "--name", $Name,
            "--resource-group", $ResourceGroup,
            "--enabled", $value
        )
    } catch {
        Write-Warning "Unable to update metric alert '$Name': $($_.Exception.Message)"
    }
}

function Set-AlertingState {
    param([bool]$Enabled)

    $label = if ($Enabled) { "Enable" } else { "Disable" }
    Write-Section "$label monitor resources"

    foreach ($name in $script:WebTestNames) {
        Set-WebTestEnabled -Name $name -Enabled:$Enabled
    }
    foreach ($name in $script:ScheduledQueryAlertNames) {
        Set-ScheduledQueryAlertEnabled -Name $name -Enabled:$Enabled
    }
    foreach ($name in $script:MetricAlertNames) {
        Set-MetricAlertEnabled -Name $name -Enabled:$Enabled
    }
}

function Start-PostgresServer {
    Write-Section "Start PostgreSQL"

    $state = Get-PostgresState
    Write-Host "Current PostgreSQL state: $state"

    if ($state -match "Ready|Starting") {
        Write-Host "PostgreSQL is already running or starting."
    } else {
        Invoke-AzMutation -Description "Starting PostgreSQL server $PostgresServer" -AzArgs @(
            "postgres", "flexible-server", "start",
            "--name", $PostgresServer,
            "--resource-group", $ResourceGroup
        )
    }

    if ($DryRun) {
        return
    }

    $deadline = (Get-Date).AddSeconds($PostgresStartTimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $current = Get-PostgresState
        Write-Host "PostgreSQL state: $current"
        if ($current -match "Ready") {
            return
        }
        Start-Sleep -Seconds 15
    }

    throw "Timed out waiting for PostgreSQL server '$PostgresServer' to become Ready."
}

function Stop-PostgresServer {
    Write-Section "Stop PostgreSQL"

    $state = Get-PostgresState
    Write-Host "Current PostgreSQL state: $state"

    if ($state -and $state -notmatch "Ready|Starting") {
        Write-Host "PostgreSQL already appears stopped."
        return
    }

    Invoke-AzMutation -Description "Stopping PostgreSQL server $PostgresServer" -AzArgs @(
        "postgres", "flexible-server", "stop",
        "--name", $PostgresServer,
        "--resource-group", $ResourceGroup
    )
}

function Wait-For-BackendHealth {
    if ($SkipHealthCheck) {
        Write-Host "Skipping backend health check because -SkipHealthCheck was used."
        return
    }

    if ($DryRun) {
        Write-Host "[dry-run] Would wait for backend /health to return 200."
        return
    }

    Write-Section "Wait for backend health"

    $backend = Get-ContainerAppRuntimeState -Name $BackendApp
    if (-not $backend.fqdn) {
        throw "Backend ingress FQDN is not available after start."
    }

    $healthUrl = "https://$($backend.fqdn)/health"
    $deadline = (Get-Date).AddSeconds($BackendHealthTimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 20
            if ($response.StatusCode -eq 200) {
                Write-Host "Backend health check passed: $healthUrl"
                return
            }
        } catch {
            Write-Host "Backend not healthy yet: $healthUrl"
        }

        Start-Sleep -Seconds 10
    }

    throw "Timed out waiting for backend health check to pass: $healthUrl"
}

function Show-EnvironmentStatus {
    Write-Section "Environment status"

    $postgresState = Get-PostgresState
    $staticHostname = Get-StaticWebAppHostname
    $containerState = Get-AllContainerAppRuntimeState
    $savedState = Get-SavedState

    $overall = if (Test-LooksStopped -ContainerState $containerState -PostgresState $postgresState) {
        "stopped"
    } else {
        "running-or-partial"
    }

    Write-Host "Subscription: $script:ResolvedSubscriptionId"
    Write-Host "Resource group: $ResourceGroup"
    Write-Host "Environment: $EnvironmentName"
    Write-Host "Overall status: $overall"
    Write-Host "PostgreSQL: $postgresState"
    Write-Host "Static Web App: $StaticWebApp"
    Write-Host "Static Web App hostname: $staticHostname"
    Write-Host "State snapshot: $(if ($savedState) { $script:ResolvedStatePath } else { '<none>' })"

    Write-Host ""
    Write-Host "Container Apps"

    $containerState |
        Select-Object `
            @{ Name = "Name"; Expression = { $_.name } }, `
            @{ Name = "Min"; Expression = { $_.minReplicas } }, `
            @{ Name = "Max"; Expression = { $_.maxReplicas } }, `
            @{ Name = "Ingress"; Expression = {
                if (-not $_.ingressEnabled) { "disabled" }
                elseif ($_.ingressType) { $_.ingressType }
                else { "enabled" }
            } }, `
            @{ Name = "FQDN"; Expression = { $_.fqdn } } |
        Format-Table -AutoSize
}

function Stop-Environment {
    Write-Section "Capture current state"

    $containerState = Get-AllContainerAppRuntimeState
    $postgresState = Get-PostgresState
    Save-RunningState -ContainerState $containerState -PostgresState $postgresState

    if (-not $SkipAlertToggle) {
        Set-AlertingState -Enabled:$false
    } else {
        Write-Host "Skipping alert toggles because -SkipAlertToggle was used."
    }

    Write-Section "Scale down container apps"
    Disable-BackendIngress

    foreach ($definition in $script:ContainerAppDefinitions) {
        $current = $containerState | Where-Object { $_.name -eq $definition.Name } | Select-Object -First 1
        $max = if ($current) { [int]$current.maxReplicas } else { [int]$definition.DefaultMaxReplicas }
        Set-ContainerAppScale -Name $definition.Name -MinReplicas 0 -MaxReplicas $max
    }

    Stop-PostgresServer

    Write-Section "Stopped"
    Write-Host "DEV backend, worker, model services, ACS worker, and PostgreSQL have been powered down."
    Write-Host "The Static Web App remains provisioned because Azure Static Web Apps does not support stop/start via az CLI."
}

function Start-Environment {
    $savedState = Get-SavedState
    if ($savedState) {
        Write-Host "Using saved state from $script:ResolvedStatePath"
    } else {
        Write-Warning "No saved state file found. Falling back to DEV infra defaults from infra/dev/main.bicep."
    }

    Start-PostgresServer

    Write-Section "Restore internal services"
    foreach ($name in @($BackendWorkerApp, $Model1App, $Model2App, $AcsWorkerApp)) {
        $desired = Get-DesiredAppState -Name $name -SavedState $savedState
        Set-ContainerAppScale -Name $name -MinReplicas $desired.minReplicas -MaxReplicas $desired.maxReplicas
    }

    Write-Section "Restore backend"
    $backendDesired = Get-DesiredAppState -Name $BackendApp -SavedState $savedState
    Set-ContainerAppScale -Name $BackendApp -MinReplicas $backendDesired.minReplicas -MaxReplicas $backendDesired.maxReplicas
    Enable-BackendIngress -DesiredState $backendDesired

    Wait-For-BackendHealth

    if (-not $SkipAlertToggle) {
        Set-AlertingState -Enabled:$true
    } else {
        Write-Host "Skipping alert toggles because -SkipAlertToggle was used."
    }

    Write-Section "Started"
    Write-Host "DEV backend, worker, model services, ACS worker, and PostgreSQL have been restored."
}

Initialize-AzContext

switch ($Action) {
    "status" { Show-EnvironmentStatus }
    "stop" { Stop-Environment }
    "start" { Start-Environment }
    default { throw "Unsupported action: $Action" }
}
