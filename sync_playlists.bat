@echo off
chcp 65001 > nul
echo ===================================================
echo [YouTube Playlists Sync] 동기화 작업을 시작합니다...
echo ===================================================
echo.

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe sync_playlists.py %*
) else (
    python sync_playlists.py %*
)

echo.
echo 작업이 완료되었습니다. 아무 키나 누르면 종료됩니다.
pause > nul
