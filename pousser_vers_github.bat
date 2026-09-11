@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ================================================================
echo   PrepaFlyPy - envoi vers GitHub (depot paul-jnn/PrepaFlyPy)
echo   Dossier : %cd%
echo ================================================================
echo.

git --version >nul 2>&1
if errorlevel 1 (
  echo [X] Git n'est pas accessible. Ouvre "Git Bash" a la place, ou installe Git.
  pause
  exit /b 1
)

if not exist ".git" (
  echo [1/6] Initialisation du depot local...
  git init
  git branch -M main
) else (
  echo [1/6] Depot local deja initialise.
)

echo [2/6] Ajout des fichiers...
git add .

echo [3/6] Commit...
git commit -m "PrepaFlyPy 0.3.0 : coeur SORA/regimes/DJI, API, UI web, CLI, tests, CI"

echo [4/6] Configuration du depot distant...
git remote get-url origin >nul 2>&1
if errorlevel 1 (
  git remote add origin https://github.com/paul-jnn/PrepaFlyPy.git
) else (
  git remote set-url origin https://github.com/paul-jnn/PrepaFlyPy.git
)

echo [5/6] Envoi sur la branche main (une fenetre de connexion GitHub peut s'ouvrir)...
git push -u origin main
if errorlevel 1 (
  echo.
  echo [X] L'envoi a echoue. Verifie ta connexion GitHub, puis relance ce fichier.
  pause
  exit /b 1
)

echo [6/6] Tag de version v0.3.0 (declenche la construction des .exe)...
git tag v0.3.0
git push origin v0.3.0

echo.
echo ================================================================
echo   Termine. Va voir l'onglet "Actions" du depot sur GitHub :
echo   les executables Windows/Linux se construisent tout seuls.
echo ================================================================
pause
