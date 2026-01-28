# 🚀 Quick Deploy Script for HF Spaces
# This script automates the deployment process

Write-Host "🛡️ CyberGuard - HF Spaces Deployment" -ForegroundColor Cyan
Write-Host "===================================`n" -ForegroundColor Cyan

# Step 1: Clone HF Space
Write-Host "📥 Step 1: Cloning HF Space repository..." -ForegroundColor Yellow
Set-Location ~\Desktop
if (Test-Path "CyberGuard") {
    Write-Host "⚠️  Directory already exists. Removing..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force CyberGuard
}

Write-Host "Enter your HF access token when prompted for password!" -ForegroundColor Green
git clone https://huggingface.co/spaces/Sidhartha2004/CyberGuard

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to clone repository" -ForegroundColor Red
    exit 1
}

# Step 2: Copy backend files
Write-Host "`n📦 Step 2: Copying backend files..." -ForegroundColor Yellow
$sourcePath = "c:\Users\Sidhartha Vyas\Desktop\CM\backend"
$destPath = "~\Desktop\CyberGuard"

Copy-Item "$sourcePath\*" $destPath -Recurse -Force

# Step 3: Clean up
Write-Host "`n🧹 Step 3: Cleaning unnecessary files..." -ForegroundColor Yellow
Set-Location ~\Desktop\CyberGuard

# Remove files that shouldn't be deployed
Remove-Item .env -ErrorAction SilentlyContinue
Remove-Item render.yaml -ErrorAction SilentlyContinue
Remove-Item test_*.py -ErrorAction SilentlyContinue
Remove-Item __pycache__ -Recurse -Force -ErrorAction SilentlyContinue

# Step 4: Verify files
Write-Host "`n✅ Step 4: Verifying deployment files..." -ForegroundColor Yellow
$requiredFiles = @("Dockerfile", "requirements.txt", "README.md", "main.py", "models.py", "auth.py", "poller.py")
$allPresent = $true

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "   ✓ $file" -ForegroundColor Green
    }
    else {
        Write-Host "   ✗ $file (MISSING!)" -ForegroundColor Red
        $allPresent = $false
    }
}

if (-not $allPresent) {
    Write-Host "`n❌ Some required files are missing!" -ForegroundColor Red
    exit 1
}

# Step 5: Git configuration
Write-Host "`n📝 Step 5: Configuring git..." -ForegroundColor Yellow
git config user.email "sidhartha@example.com"
git config user.name "Sidhartha Vyas"

# Step 6: Commit and push
Write-Host "`n📤 Step 6: Pushing to HF Spaces..." -ForegroundColor Yellow
git add .
git commit -m "Deploy full FastAPI backend with ML moderation and Twitter integration"
git push

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Successfully deployed to HF Spaces!" -ForegroundColor Green
    Write-Host "`n🔗 Your Space: https://huggingface.co/spaces/Sidhartha2004/CyberGuard" -ForegroundColor Cyan
    Write-Host "🌐 API URL: https://sidhartha2004-cyberguard.hf.space" -ForegroundColor Cyan
    Write-Host "`n⚠️  IMPORTANT: Don't forget to add environment secrets in Space settings!" -ForegroundColor Yellow
    Write-Host "   Go to: https://huggingface.co/spaces/Sidhartha2004/CyberGuard/settings" -ForegroundColor Yellow
}
else {
    Write-Host "`n❌ Push failed. Please check the error above." -ForegroundColor Red
    exit 1
}

Write-Host "`n✨ Deployment complete! Monitor build at your Space URL." -ForegroundColor Green
