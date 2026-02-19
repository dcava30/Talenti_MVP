param(
    [string]$BackendUrl = "http://localhost:8000",
    [string]$Model1Url = "http://localhost:8001",
    [string]$Model2Url = "http://localhost:8002",
    [string]$Token = ""
)

$ErrorActionPreference = "Stop"

function Assert-Condition {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) {
        throw $Message
    }
}

function Assert-HasProperty {
    param(
        [object]$Obj,
        [string]$Prop,
        [string]$Context
    )
    Assert-Condition ($null -ne $Obj) "$Context is null"
    $props = $Obj.PSObject.Properties.Name
    Assert-Condition ($props -contains $Prop) "$Context missing '$Prop'"
}

$headers = @{ "Content-Type" = "application/json" }
if ($Token) {
    $headers["Authorization"] = "Bearer $Token"
}

$transcript = @(
    @{ speaker = "interviewer"; content = "Tell me about a time you made a decision quickly." },
    @{ speaker = "candidate"; content = "I gathered key data, aligned stakeholders, and made the call under a tight deadline." }
)

$jobDescription = "We are hiring a backend engineer with strong problem solving and collaboration."
$resumeText = "5 years of Python and API development. Led multiple backend projects."

try {
    Write-Host "1) Model service 1: /predict"
    $model1Payload = @{
        transcript = $transcript
        candidate_id = "cand_smoke"
        role_id = "role_smoke"
        department_id = "dept_smoke"
        interview_id = "int_smoke"
    } | ConvertTo-Json -Depth 8

    $model1Resp = Invoke-RestMethod -Method Post -Uri "$Model1Url/predict" -Headers $headers -Body $model1Payload
    Assert-HasProperty $model1Resp "scores" "Model1 response"
    Assert-HasProperty $model1Resp "summary" "Model1 response"
    Assert-Condition ($model1Resp.scores -is [System.Collections.IDictionary]) "Model1 scores is not an object"

    if ($model1Resp.scores.Count -gt 0) {
        $firstKey = $model1Resp.scores.Keys | Select-Object -First 1
        $scoreObj = $model1Resp.scores[$firstKey]
        Assert-HasProperty $scoreObj "score" "Model1 score[$firstKey]"
        Assert-HasProperty $scoreObj "confidence" "Model1 score[$firstKey]"
        Assert-HasProperty $scoreObj "rationale" "Model1 score[$firstKey]"
    }

    Write-Host "2) Model service 2: /predict/transcript"
    $model2Payload = @{
        job_description = $jobDescription
        resume_text = $resumeText
        transcript = $transcript
        role_title = "Backend Engineer"
        seniority = "mid"
    } | ConvertTo-Json -Depth 8

    $model2Resp = Invoke-RestMethod -Method Post -Uri "$Model2Url/predict/transcript" -Headers $headers -Body $model2Payload
    Assert-HasProperty $model2Resp "overall_score" "Model2 response"
    Assert-HasProperty $model2Resp "scores" "Model2 response"
    Assert-HasProperty $model2Resp "summary" "Model2 response"
    Assert-Condition ($model2Resp.scores -is [System.Collections.IDictionary]) "Model2 scores is not an object"

    Write-Host "3) Backend scoring: /api/v1/scoring/analyze"
    $backendPayload = @{
        interview_id = "smoke-" + (Get-Date -Format "yyyyMMddHHmmss")
        transcript = $transcript
        job_description = $jobDescription
        resume_text = $resumeText
        role_title = "Backend Engineer"
        seniority = "mid"
    } | ConvertTo-Json -Depth 8

    $scoreResp = Invoke-RestMethod -Method Post -Uri "$BackendUrl/api/v1/scoring/analyze" -Headers $headers -Body $backendPayload
    Assert-HasProperty $scoreResp "interview_id" "Scoring response"
    Assert-HasProperty $scoreResp "overall_score" "Scoring response"
    Assert-HasProperty $scoreResp "dimensions" "Scoring response"
    Assert-HasProperty $scoreResp "summary" "Scoring response"
    Assert-Condition ($scoreResp.dimensions -is [System.Collections.IEnumerable]) "Scoring dimensions is not a list"

    if ($scoreResp.dimensions.Count -gt 0) {
        $dim = $scoreResp.dimensions | Select-Object -First 1
        Assert-HasProperty $dim "name" "Scoring dimension"
        Assert-HasProperty $dim "score" "Scoring dimension"
    }

    Write-Host "Smoke test OK."
} catch {
    Write-Error $_
    exit 1
}
