$ErrorActionPreference = "Stop"
$root = (Get-Location).Path

function Copy-TaskFolder {
    param([string]$Source, [string]$Destination)
    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        Write-Warning "Missing source folder: $Source"
        return
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $Source -Force) {
        if ($item.PSIsContainer) {
            if ($item.Name -in @(".git",".venv","venv","__pycache__",".pytest_cache","node_modules","raw","clean","rejected","logs","step5_backup") -or $item.Name -match '(?i)backup') { continue }
            Copy-TaskFolder -Source $item.FullName -Destination (Join-Path $Destination $item.Name)
        } else {
            if ($item.Name -match '^(?i)\.env($|\.)' -or $item.Name -match '(?i)\.(csv|log|bak|backup|py\.backup|xlsx|duckdb|db)$' -or $item.Name -match '(?i)\.before_') { continue }
            Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $Destination $item.Name) -Force
        }
    }
}

function Copy-Page {
    param([string]$Name,[string]$Destination)
    $source = Join-Path $root ("Task 5 - First Dashboard\pages\" + $Name)
    if (Test-Path -LiteralPath $source -PathType Leaf) {
        $folder = Join-Path $Destination "dashboard"
        New-Item -ItemType Directory -Force -Path $folder | Out-Null
        Copy-Item -LiteralPath $source -Destination (Join-Path $folder $Name) -Force
    } else { Write-Warning "Missing dashboard page: $Name" }
}

Write-Host "Creating phase-1, phase-2 and phase-3 folders..." -ForegroundColor Cyan
$phase1 = Join-Path $root "phase-1"
$phase2 = Join-Path $root "phase-2"
$phase3 = Join-Path $root "phase-3"
New-Item -ItemType Directory -Force -Path $phase1,$phase2,$phase3 | Out-Null

# Phase 1: Tasks 1-5
@("Task 1 - ETL","Task 2 - Warehouse","Task 3 - Dashboard","Task 3 - Data Quality Gatekeeper","Task 4 - Attendace","Task 4 - Attendance Anomalies","Task 4 - Governed Metric Layer") | ForEach-Object {
    Copy-TaskFolder (Join-Path $root $_) (Join-Path $phase1 $_)
}
$t5 = Join-Path $phase1 "Task 5 - First Dashboard"
New-Item -ItemType Directory -Force -Path $t5 | Out-Null
@("app.py","README.md","requirements.txt","Final_Dashboard.png",".env.example") | ForEach-Object {
    $p = Join-Path $root ("Task 5 - First Dashboard\" + $_)
    if (Test-Path -LiteralPath $p -PathType Leaf) { Copy-Item -LiteralPath $p -Destination (Join-Path $t5 $_) -Force }
}
Copy-Page "2_Attendance_Trends.py" $t5

# Phase 2: Tasks 6-10
@("Task 6 - Attendance and Leave Trends","Task 7 - Attrition Analytics","Task 8 - Team Productivity","Task 9 - Payroll Cost","Task 10 - Budget vs Actual and KPI Targets") | ForEach-Object {
    Copy-TaskFolder (Join-Path $root $_) (Join-Path $phase2 $_)
}
Copy-Page "2_Attendance_Trends.py" (Join-Path $phase2 "Task 6 - Attendance and Leave Trends")
Copy-Page "3_Attrition_Analytics.py" (Join-Path $phase2 "Task 7 - Attrition Analytics")
Copy-Page "4_Team_Productivity.py" (Join-Path $phase2 "Task 8 - Team Productivity")
Copy-Page "5_Payroll_Cost.py" (Join-Path $phase2 "Task 9 - Payroll Cost")
Copy-Page "6_Budget_vs_Actual.py" (Join-Path $phase2 "Task 10 - Budget vs Actual and KPI Targets")

# Phase 3: Tasks 11-15
@("Task 11 - Profit and Loss","Task 12 - Invoices Receivables and Cash Flow","Task 13 - Cross Department Impact View") | ForEach-Object {
    Copy-TaskFolder (Join-Path $root $_) (Join-Path $phase3 $_)
}
Copy-Page "5_Profit_Loss.py" (Join-Path $phase3 "Task 11 - Profit and Loss")
Copy-Page "8_Receivables_Cash_Flow.py" (Join-Path $phase3 "Task 12 - Invoices Receivables and Cash Flow")
Copy-Page "9_Cross_Department_Impact.py" (Join-Path $phase3 "Task 13 - Cross Department Impact View")

$t14 = Join-Path $phase3 "Task 14 - AI Signals"
$t15 = Join-Path $phase3 "Task 15 - Executive Scorecard"
New-Item -ItemType Directory -Force -Path $t14,$t15 | Out-Null
Copy-Page "10_AI_Signals.py" $t14
Copy-Page "11_Executive_Scorecard.py" $t15
$pdf = Join-Path $root "Task 5 - First Dashboard\pages\Executive KPI Scorecard.pdf"
if (Test-Path -LiteralPath $pdf -PathType Leaf) {
    New-Item -ItemType Directory -Force -Path (Join-Path $t15 "evidence") | Out-Null
    Copy-Item -LiteralPath $pdf -Destination (Join-Path $t15 "evidence\Executive KPI Scorecard.pdf") -Force
}

Write-Host "`nDone. Files were COPIED; original folders remain untouched." -ForegroundColor Green
Get-ChildItem -LiteralPath $root -Directory | Where-Object Name -in @("phase-1","phase-2","phase-3") | Select-Object Name
