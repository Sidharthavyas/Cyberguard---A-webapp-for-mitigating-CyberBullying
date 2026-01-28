@echo off
echo ======================================
echo HF Spaces Deployment - With Auth Setup
echo ======================================
echo.

cd /d %USERPROFILE%\Desktop\CyberGuard

echo Step 1: Configuring Git Credentials...
git config credential.helper store
echo.

echo Step 2: Pushing to HF Spaces...
echo IMPORTANT: When prompted, enter:
echo   Username: Sidhartha2004
echo   Password: YOUR_HF_ACCESS_TOKEN
echo.
echo Get your token from: https://huggingface.co/settings/tokens
echo.

git push origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo SUCCESS! Backend deployed to HF Spaces
    echo ========================================
    echo.
    echo Your Space: https://huggingface.co/spaces/Sidhartha2004/CyberGuard
    echo API URL: https://sidhartha2004-cyberguard.hf.space
    echo.
    echo NEXT STEPS:
    echo 1. Go to Space Settings and add environment secrets
    echo 2. Monitor build logs
    echo 3. Test the deployed API
    echo.
) else (
    echo.
    echo ========================================
    echo FAILED - Please check the error above
    echo ========================================
    echo.
)

pause
