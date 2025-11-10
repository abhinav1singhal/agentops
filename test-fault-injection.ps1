# Complete Fault Injection Test Script
# This script tests the end-to-end incident detection and remediation flow

$SUPERVISOR_URL = "https://supervisor-api-668107958735.us-central1.run.app"
$DEMO_APP_URL = "https://demo-app-a-668107958735.us-central1.run.app"

Write-Host ""
Write-Host "=== FAULT INJECTION TEST SCRIPT ===" -ForegroundColor Cyan
Write-Host "Start time: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
Write-Host ""

# Step 1: Lower MIN_REQUEST_COUNT threshold
Write-Host "[Step 1/6] Updating supervisor-api MIN_REQUEST_COUNT to 10..." -ForegroundColor Yellow
gcloud run services update supervisor-api --region=us-central1 --update-env-vars MIN_REQUEST_COUNT=10

Write-Host "Waiting 45 seconds for deployment to complete..." -ForegroundColor Gray
Start-Sleep -Seconds 45
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host ""

# Step 2: Disable any previous faults
Write-Host "[Step 2/6] Disabling previous faults..." -ForegroundColor Yellow
try {
    $disableResult = Invoke-RestMethod -Method Post -Uri "$DEMO_APP_URL/fault/disable"
    Write-Host "Previous faults disabled" -ForegroundColor Green
} catch {
    Write-Host "Disable fault skipped" -ForegroundColor Gray
}
Write-Host ""

# Step 3: Enable fault injection
Write-Host "[Step 3/6] Enabling 20% error rate fault..." -ForegroundColor Yellow
$enableResult = Invoke-RestMethod -Method Post -Uri "$DEMO_APP_URL/fault/enable?type=5xx&error_rate=20&duration=900"
Write-Host "Fault enabled: $($enableResult.message)" -ForegroundColor Green
Write-Host "Config: error_rate=$($enableResult.config.error_rate)%, duration=$($enableResult.config.duration)s" -ForegroundColor Gray
Write-Host ""

# Step 4: Generate traffic
Write-Host "[Step 4/6] Generating 200 requests (20% will be 500 errors)..." -ForegroundColor Yellow
$trafficStartTime = Get-Date
Write-Host "Traffic start: $($trafficStartTime.ToString('HH:mm:ss'))" -ForegroundColor Gray

$successCount = 0
$errorCount = 0

for ($i = 1; $i -le 200; $i++) {
    try {
        Invoke-RestMethod -Method Get -Uri "$DEMO_APP_URL/" -ErrorAction Stop | Out-Null
        $successCount++
    } catch {
        $errorCount++
    }
    if ($i % 50 -eq 0) {
        Write-Host "  Sent $i requests... (Success: $successCount, Errors: $errorCount)" -ForegroundColor Gray
    }
}

Write-Host "Traffic generation complete!" -ForegroundColor Green
Write-Host "  Total: 200 | Success: $successCount | Errors: $errorCount" -ForegroundColor Green
Write-Host "  Expected errors: ~40 (20% of 200)" -ForegroundColor Gray
Write-Host "  Traffic end: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# Step 5: Wait for Cloud Monitoring metrics to propagate
Write-Host "[Step 5/6] Waiting 10 minutes for Cloud Monitoring metrics to propagate..." -ForegroundColor Yellow
Write-Host "  This is normal for Cloud Run - metrics can take 5-10 minutes to appear" -ForegroundColor Gray
Write-Host "  Start wait: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Gray

# Show countdown
for ($min = 10; $min -gt 0; $min--) {
    Write-Host "  $min minutes remaining..." -ForegroundColor Gray
    Start-Sleep -Seconds 60
}

Write-Host "  Wait complete: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Green
Write-Host ""

# Step 6: Trigger health scan
Write-Host "[Step 6/6] Triggering health scan..." -ForegroundColor Yellow
$scanResult = Invoke-RestMethod -Method Post -Uri "$SUPERVISOR_URL/health/scan"

Write-Host ""
Write-Host "=== HEALTH SCAN RESULTS ===" -ForegroundColor Cyan
$scanResult | ConvertTo-Json -Depth 5

Write-Host ""
Write-Host "=== TEST SUMMARY ===" -ForegroundColor Cyan
Write-Host "Traffic generated: 200 requests" -ForegroundColor White
Write-Host "Actual errors: $errorCount" -ForegroundColor White

$anomalyColor = if ($scanResult.anomalies_detected -gt 0) { "Green" } else { "Red" }
Write-Host "Anomalies detected: $($scanResult.anomalies_detected)" -ForegroundColor $anomalyColor

if ($scanResult.anomalies_detected -gt 0) {
    Write-Host ""
    Write-Host "TEST PASSED - Anomaly detection working!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Check Firestore for incident document" -ForegroundColor White
    Write-Host "2. Verify Pub/Sub message was published to remediation-actions" -ForegroundColor White
    Write-Host "3. Check fixer-agent logs for remediation execution" -ForegroundColor White
    Write-Host "4. View incident in dashboard" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "TEST FAILED - No anomalies detected" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Check demo-app-a metrics in Cloud Console" -ForegroundColor White
    Write-Host "2. Verify metrics are showing in Cloud Monitoring (may need more time)" -ForegroundColor White
    Write-Host "3. Check supervisor-api logs for details" -ForegroundColor White
    Write-Host ""
}

Write-Host "End time: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Cyan
Write-Host "=== TEST COMPLETE ===" -ForegroundColor Cyan
Write-Host ""
