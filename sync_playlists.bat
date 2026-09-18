@echo off
chcp 65001 > nul
echo ===================================================
echo [YouTube Playlists Sync] 
echo ===================================================
echo.

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe sync_playlists.py %*
) else (
    python sync_playlists.py %*
)

echo.
echo completed
pause > nul
