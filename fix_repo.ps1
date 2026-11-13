# Green Spine: move to a clean branch with no large files in history.
$ErrorActionPreference = "Stop"
Set-Location "C:\Users\Win11\Documents\green-spine"

Write-Host "`n== Creating clean branch ==" -ForegroundColor Cyan
git checkout --orphan clean
git rm -r --cached . -q
git add .

Write-Host "`n== Files to be committed ==" -ForegroundColor Cyan
$n = (git diff --cached --name-only | Measure-Object -Line).Lines
Write-Host "$n files"
git diff --cached --name-only | Select-Object -First 25
if ($n -gt 500) {
  Write-Host "`nSTOP: $n files is too many - .gitignore is not catching something." -ForegroundColor Red
  Write-Host "Run 'git status' and check before pushing." -ForegroundColor Red
  exit 1
}

git commit -m "Green Spine: app, backend and processed data"
Write-Host "`n== Pushing ==" -ForegroundColor Cyan
git push -u origin clean
Write-Host "`nDone. Set 'clean' as the default branch on GitHub." -ForegroundColor Green
