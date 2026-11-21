# Post-deployment smoke test against the real local release stack.
#
#   scripts/smoke-test.ps1
#   scripts/smoke-test.ps1 -BaseUrl http://localhost:18080 -ProjectName usa-phase16-fresh
#
# Checks health, static/SPA serving, student/admin/professor logins, permissions,
# a student read endpoint, course selection, notifications + conversations
# persistence across a backend restart, and (unless -SkipAI) a grounded AI
# answer. Real-provider and mock-provider runs are labelled explicitly.
[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8080",
    [string]$EnvFile = ".env",
    [string]$ProjectName = "university-assistant",
    [switch]$SkipAI,
    [switch]$SkipPersistenceRestart
)

$ErrorActionPreference = "Continue"
. "$PSScriptRoot\_common.ps1"

$envPath = Resolve-EnvPath $EnvFile
$envMap = Get-DotEnv $envPath
$demoPassword = Get-RequiredEnv $envMap "DEMO_PASSWORD"
$aiProvider = if ($envMap["AI_PROVIDER"]) { $envMap["AI_PROVIDER"] } else { "mock" }
$base = $BaseUrl.TrimEnd("/")

$script:passed = 0
$script:failed = 0
$results = [System.Collections.Generic.List[string]]::new()

function Check {
    param([string]$Name, [bool]$Ok, [string]$Detail = "")
    if ($Ok) {
        $script:passed++
        $line = "PASS  $Name"
    } else {
        $script:failed++
        $line = "FAIL  $Name"
    }
    if ($Detail) { $line = "$line  -  $Detail" }
    Write-Host $line
    $results.Add($line)
}

function Get-ResponseText {
    param($Response)
    try {
        $bytes = $Response.RawContentStream.ToArray()
        return [System.Text.Encoding]::UTF8.GetString($bytes)
    } catch {
        return [string]$Response.Content
    }
}

function Convert-JsonSafe {
    param([string]$Text)
    try { return ($Text | ConvertFrom-Json) } catch { return $null }
}

function Invoke-Api {
    param(
        [string]$Method,
        [string]$Path,
        [string]$Token = "",
        $Body = $null
    )
    $uri = "$base$Path"
    $splat = @{
        Method = $Method
        Uri = $uri
        UseBasicParsing = $true
        TimeoutSec = 30
    }
    if ($Token) { $splat["Headers"] = @{ Authorization = "Bearer $Token" } }
    if ($null -ne $Body) {
        $json = $Body | ConvertTo-Json -Compress -Depth 10
        $splat["ContentType"] = "application/json; charset=utf-8"
        $splat["Body"] = [System.Text.Encoding]::UTF8.GetBytes($json)
    }
    try {
        $response = Invoke-WebRequest @splat
        $text = Get-ResponseText $response
        return [pscustomobject]@{
            Status = [int]$response.StatusCode
            Text = $text
            Json = (Convert-JsonSafe $text)
        }
    } catch {
        $response = $_.Exception.Response
        if ($null -eq $response) { throw }
        $reader = New-Object System.IO.StreamReader($response.GetResponseStream(), [System.Text.Encoding]::UTF8)
        $text = $reader.ReadToEnd()
        return [pscustomobject]@{
            Status = [int]$response.StatusCode
            Text = $text
            Json = (Convert-JsonSafe $text)
        }
    }
}

function Get-PageText {
    param([string]$Path)
    $response = Invoke-WebRequest -Uri "$base$Path" -UseBasicParsing -TimeoutSec 20
    return [pscustomobject]@{
        Status = [int]$response.StatusCode
        Text = (Get-ResponseText $response)
    }
}

Push-Location $script:RepoRoot
try {
    $compose = Get-ComposeArgs -EnvFile $EnvFile -ProjectName $ProjectName
    Write-Host "Smoke test against $base (AI provider: $aiProvider)"
    Write-Host ""

    # --- health -------------------------------------------------------------
    $live = Invoke-Api GET "/health/live"
    Check "health live returns 200" ($live.Status -eq 200) "status=$($live.Status)"
    Check "health live payload ok" ($live.Json.status -eq "ok")

    $ready = Invoke-Api GET "/health/ready"
    Check "health ready returns 200" ($ready.Status -eq 200) "status=$($ready.Status)"
    Check "health ready database ok" ($ready.Json.checks.database -eq "ok")

    $deep = Invoke-Api GET "/health/deep"
    Check "health deep returns 200" ($deep.Status -eq 200) "status=$($deep.Status)"
    Check "health deep status ok" ($deep.Json.status -eq "ok")
    $deepAi = $deep.Json.checks.ai_provider.status
    Check "health deep AI state is explicit" ($deepAi -in @("mock", "configured", "not_configured")) "ai=$deepAi"

    $apiHealth = Invoke-Api GET "/api/v1/health/"
    Check "versioned API health returns 200" ($apiHealth.Status -eq 200)

    # --- frontend / SPA routes ---------------------------------------------
    $root = Get-PageText "/"
    Check "frontend root served" ($root.Status -eq 200 -and $root.Text -match 'id="root"')
    foreach ($route in @("/selection", "/admin/users", "/assistant")) {
        $page = Get-PageText $route
        Check "SPA route $route serves index.html" ($page.Status -eq 200 -and $page.Text -match 'id="root"')
    }

    # --- logins -------------------------------------------------------------
    $studentLogin = Invoke-Api POST "/api/v1/auth/login/" "" @{ email = "student@semnan.local"; password = $demoPassword }
    Check "student login" ($studentLogin.Status -eq 200 -and $studentLogin.Json.user.role -eq "STUDENT") "status=$($studentLogin.Status)"
    $adminLogin = Invoke-Api POST "/api/v1/auth/login/" "" @{ email = "admin@semnan.local"; password = $demoPassword }
    Check "admin login" ($adminLogin.Status -eq 200 -and $adminLogin.Json.user.role -eq "ADMIN") "status=$($adminLogin.Status)"
    $professorLogin = Invoke-Api POST "/api/v1/auth/login/" "" @{ email = "professor@semnan.local"; password = $demoPassword }
    Check "professor login" ($professorLogin.Status -eq 200 -and $professorLogin.Json.user.role -eq "PROFESSOR") "status=$($professorLogin.Status)"

    $studentToken = $studentLogin.Json.access
    $adminToken = $adminLogin.Json.access
    Check "student token issued" ([bool]$studentToken)
    Check "admin token issued" ([bool]$adminToken)
    if (-not $studentToken -or -not $adminToken) { throw "Login did not issue tokens; later checks cannot run." }

    $me = Invoke-Api GET "/api/v1/auth/me/" $studentToken
    Check "student /auth/me" ($me.Status -eq 200 -and $me.Json.role -eq "STUDENT")

    # --- permissions --------------------------------------------------------
    $adminUsers = Invoke-Api GET "/api/v1/admin/users/?page_size=1" $adminToken
    Check "admin endpoint accessible to admin" ($adminUsers.Status -eq 200) "status=$($adminUsers.Status)"
    $studentOnAdmin = Invoke-Api GET "/api/v1/admin/users/?page_size=1" $studentToken
    Check "admin endpoint denied to student" ($studentOnAdmin.Status -eq 403) "status=$($studentOnAdmin.Status)"

    # --- student read + course selection -----------------------------------
    $studentMe = Invoke-Api GET "/api/v1/students/me/" $studentToken
    Check "student read endpoint" ($studentMe.Status -eq 200) "status=$($studentMe.Status)"

    $selection = Invoke-Api POST "/api/v1/students/me/course-selection/" $studentToken @{ course_query = "1916003" }
    Check "course selection by code" ($selection.Status -eq 200 -and $selection.Json.status -eq "resolved" -and $selection.Json.course.code -eq "1916003") "status=$($selection.Status)"
    $selectionName = Invoke-Api POST "/api/v1/students/me/course-selection/" $studentToken @{ course_query = "مدارهای الکتریکی" }
    Check "course selection by Persian name" ($selectionName.Status -eq 200 -and $selectionName.Json.course.code -eq "1916003") "status=$($selectionName.Status)"

    # --- persistence --------------------------------------------------------
    $notifications = Invoke-Api GET "/api/v1/notifications/" $studentToken
    $notificationCount = $notifications.Json.count
    Check "notifications list" ($notifications.Status -eq 200) "count=$notificationCount"
    Check "demo notification exists" ([int]$notificationCount -ge 1) "count=$notificationCount"

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $conversation = Invoke-Api POST "/api/v1/conversations/" $studentToken @{ title = "Smoke test $stamp" }
    $conversationId = $conversation.Json.id
    Check "conversation create" ($conversation.Status -eq 201 -and [bool]$conversationId) "status=$($conversation.Status) id=$conversationId"

    if (-not $SkipPersistenceRestart) {
        Write-Host "Restarting backend to verify persistence..."
        & docker @compose restart backend | Out-Null
        Assert-ExitCode "docker compose restart backend"
        if (-not (Wait-HttpOk -Url "$base/health/ready" -TimeoutSeconds 90)) {
            throw "Backend did not become ready after restart."
        }
    }

    $conversationAfter = Invoke-Api GET "/api/v1/conversations/$conversationId/" $studentToken
    Check "conversation survives restart" ($conversationAfter.Status -eq 200 -and $conversationAfter.Json.id -eq $conversationId) "status=$($conversationAfter.Status)"
    $notificationsAfter = Invoke-Api GET "/api/v1/notifications/" $studentToken
    Check "notifications survive restart" ($notificationsAfter.Status -eq 200 -and [int]$notificationsAfter.Json.count -eq [int]$notificationCount) "before=$notificationCount after=$($notificationsAfter.Json.count)"

    # --- AI -----------------------------------------------------------------
    if ($SkipAI) {
        Write-Host "AI checks skipped (-SkipAI)."
    } else {
        $grounded = Invoke-Api POST "/api/v1/ai/ask/" $studentToken @{ question = "پیش‌نیاز درس مدارهای الکتریکی چیست؟" }
        Check "grounded AI answer" ($grounded.Status -eq 200 -and -not [string]::IsNullOrWhiteSpace($grounded.Json.answer)) "status=$($grounded.Status) mode=$($grounded.Json.mode)"

        if ($aiProvider -eq "groq") {
            # Real-provider path: a general question reaches Groq (structured
            # university answers may be composed without an LLM).
            $general = Invoke-Api POST "/api/v1/ai/ask/" $studentToken @{ question = "عدد پی را با دو رقم اعشار توضیح بده." }
            Check "real provider answer (groq)" ($general.Status -eq 200 -and -not [string]::IsNullOrWhiteSpace($general.Json.answer)) "status=$($general.Status)"
        } else {
            Check "mock provider labelled (no external LLM)" ($aiProvider -eq "mock") "provider=$aiProvider"
        }
    }

    # --- logs ---------------------------------------------------------------
    $logText = (& docker @compose logs --no-color --tail 300 backend worker 2>&1) -join "`n"
    $badLogs = @(($logText -split "`n") | Where-Object { $_ -match 'Traceback|level=ERROR|level=CRITICAL' })
    Check "no critical backend/worker log errors" (@($badLogs).Count -eq 0) $(if ($badLogs) { $badLogs[0] } else { "clean" })

    Write-Host ""
    Write-Host "$($script:passed)/$($script:passed + $script:failed) smoke checks passed"
    if ($script:failed -gt 0) {
        foreach ($line in $results | Where-Object { $_ -like "FAIL*" }) { Write-Host $line }
        exit 1
    }
} finally {
    Pop-Location
}
