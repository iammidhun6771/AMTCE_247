@echo off
:restart
echo [%date% %time%] Starting AMTCE Bot... >> D:\AMTCE\logs\bot_restart.log
cd /d D:\AMTCE
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
D:\AMTCE\venv\Scripts\python.exe -X utf8 main.py >> D:\AMTCE\logs\bot.log 2>&1
echo [%date% %time%] Bot stopped. Restarting in 10 seconds... >> D:\AMTCE\logs\bot_restart.log
timeout /t 10
goto restart
