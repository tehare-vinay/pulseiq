$ErrorActionPreference = "Stop"

$ProjectRoot = (Get-Location).Path
$Task2 = Join-Path $ProjectRoot "Task 2 - Warehouse"
if (-not (Test-Path $Task2)) {
    throw "Project root galat hai. PowerShell ko PulseIQ_Analytics folder me kholkar script run karein."
}

$required = @(
    "schema.sql",
    "load_warehouse.py",
    "star_schema.md",
    "star_schema.mmd",
    "task2_business_questions.md",
    "task2_validation_queries.sql",
    "task2_row_count_reconciliation.sql",
    "task2_employee_history_validation_final.sql",
    "task2_orphan_check_results.md",
    "task2_history_and_orphans_notes.md",
    "README.md"
)
$missing = @()
foreach ($f in $required) {
    if (-not (Test-Path (Join-Path $Task2 $f))) { $missing += $f }
}
if ($missing.Count -gt 0) {
    Write-Host "STOP: Ye required files missing hain:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host " - $_" }
    throw "Files missing; final package nahi banaya."
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportPath = Join-Path $Task2 "TASK2_FINAL_STATUS.md"
$report = @"
# PulseIQ Analytics — Task 2 Final Status

Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Deliverables
- PostgreSQL warehouse schema and loader
- Star-schema diagram and join-map documentation
- Business questions and validation SQL
- Row-count reconciliation and employee-history validation evidence
- Orphan-check and exception documentation

## Latest recorded reconciliation
| Fact table | Expected accepted rows | Warehouse rows | Result |
|---|---:|---:|---|
| fact_attendance_monthly | 7343 | 7343 | PASS |
| fact_headcount_monthly | 891 | 891 | PASS |
| fact_leave | 3439 | 3439 | PASS; 2 invalid source rows quarantined |
| fact_payroll | 7344 | 7344 | PASS |

## Exceptions — do not silently alter source data
1. Four attendance history records (FA-X0001 to FA-X0004) have fact months outside the linked employee dimension validity period. Pending source-owner review.
2. Two payroll records (PI-X0003, PI-X0004) refer to EMP-9001 and EMP-9002, absent from the supplied employee dimension; employee_key remains -1. Pending source-owner review.
3. Two invalid leave rows are quarantined with reason leave_end_before_start.

## Sign-off
Warehouse row-count reconciliation is recorded as PASS for all four fact tables. Task 2 is **substantially complete with documented source exceptions**, not exception-free. Do not change or delete source rows or invent employee keys without written source-owner confirmation.

Before submission, run the current validation SQL against the local database and confirm the official updated task instructions and submission form requirements.
"@
Set-Content -Path $reportPath -Value $report -Encoding UTF8

$docsRoot = Join-Path $ProjectRoot "docs"
$include = @($Task2)
if (Test-Path $docsRoot) { $include += $docsRoot }

$zipPath = Join-Path $ProjectRoot "Task2_Final_Package_$stamp.zip"
$stage = Join-Path $env:TEMP "PulseIQ_Task2_Final_$stamp"
New-Item -ItemType Directory -Path $stage | Out-Null
try {
    Copy-Item -Path $Task2 -Destination $stage -Recurse
    if (Test-Path $docsRoot) { Copy-Item -Path $docsRoot -Destination $stage -Recurse }
    Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -CompressionLevel Optimal
}
finally {
    Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "`nTASK 2 PACKAGE CREATED" -ForegroundColor Green
Write-Host "Status report: $reportPath"
Write-Host "ZIP package:   $zipPath"
Write-Host "`nIMPORTANT: This packages the existing Task 2 files and documents known exceptions; it does not change the database or clear source-data exceptions."
