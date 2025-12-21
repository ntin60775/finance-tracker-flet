# Build Check Script for Finance Tracker
# Checks project readiness for PyInstaller build

Write-Host "Checking Finance Tracker build readiness..." -ForegroundColor Cyan

$ErrorCount = 0

# 1. Test check
Write-Host "`nRunning tests..." -ForegroundColor Yellow
try {
    $testResult = pytest tests/ -q --tb=no
    if ($LASTEXITCODE -eq 0) {
        Write-Host "All tests pass" -ForegroundColor Green
    } else {
        Write-Host "Tests failed!" -ForegroundColor Red
        $ErrorCount++
    }
} catch {
    Write-Host "Test execution error: $_" -ForegroundColor Red
    $ErrorCount++
}

# 2. Entry points check for view=ft.AppView.FLET_APP
Write-Host "`nChecking entry points..." -ForegroundColor Yellow

$entryPoints = @(
    "src/finance_tracker/__main__.py",
    "main.py"
)

foreach ($file in $entryPoints) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        if ($content -match "view=ft\.AppView\.FLET_APP") {
            Write-Host ($file + ": correct launch mode") -ForegroundColor Green
        } else {
            Write-Host ($file + ": missing view=ft.AppView.FLET_APP") -ForegroundColor Red
            $ErrorCount++
        }
    } else {
        Write-Host ($file + ": file not found") -ForegroundColor Red
        $ErrorCount++
    }
}

# 3. PyInstaller spec check
Write-Host "`nChecking PyInstaller spec..." -ForegroundColor Yellow

if (Test-Path "finance_tracker.spec") {
    $specContent = Get-Content "finance_tracker.spec" -Raw
    
    # Check console=False
    if ($specContent -match "console=False") {
        Write-Host "Spec: console=False (GUI mode)" -ForegroundColor Green
    } else {
        Write-Host "Spec: console not set to False" -ForegroundColor Yellow
    }
    
    # Check icon
    if ($specContent -match "icon=\['assets") {
        Write-Host "Spec: icon configured" -ForegroundColor Green
    } else {
        Write-Host "Spec: icon not configured" -ForegroundColor Yellow
    }
    
    # Check datas
    if ($specContent -match "datas=.*assets") {
        Write-Host "Spec: resources included" -ForegroundColor Green
    } else {
        Write-Host "Spec: resources not included" -ForegroundColor Red
        $ErrorCount++
    }
} else {
    Write-Host "finance_tracker.spec not found" -ForegroundColor Red
    $ErrorCount++
}

# 4. Resources check
Write-Host "`nChecking resources..." -ForegroundColor Yellow

$resources = @(
    "assets/icon.ico",
    "assets/icon.png"
)

foreach ($resource in $resources) {
    if (Test-Path $resource) {
        Write-Host ($resource + ": found") -ForegroundColor Green
    } else {
        Write-Host ($resource + ": not found") -ForegroundColor Red
        $ErrorCount++
    }
}

# 5. Dependencies check
Write-Host "`nChecking dependencies..." -ForegroundColor Yellow

try {
    $pipList = pip list --format=freeze
    $requiredPackages = @("flet", "sqlalchemy", "pydantic", "pyinstaller")
    
    foreach ($package in $requiredPackages) {
        if ($pipList -match "^$package==") {
            Write-Host ($package + ": installed") -ForegroundColor Green
        } else {
            Write-Host ($package + ": not installed") -ForegroundColor Red
            $ErrorCount++
        }
    }
} catch {
    Write-Host ("Could not check dependencies: " + $_) -ForegroundColor Yellow
}

# Final result
Write-Host "`n============================================================" -ForegroundColor Cyan

if ($ErrorCount -eq 0) {
    Write-Host "ALL CHECKS PASSED!" -ForegroundColor Green
    Write-Host "Project ready for PyInstaller build" -ForegroundColor Green
    Write-Host "`nTo build, run:" -ForegroundColor Cyan
    Write-Host "pyinstaller finance_tracker.spec --clean --noconfirm" -ForegroundColor White
    exit 0
} else {
    Write-Host ("ISSUES FOUND: " + $ErrorCount) -ForegroundColor Red
    Write-Host "Fix errors before building!" -ForegroundColor Yellow
    Write-Host "`nSee documentation: .kiro/steering/build-deployment.md" -ForegroundColor Cyan
    exit 1
}