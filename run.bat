@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto use_venv
python -c "import streamlit" >nul 2>nul
if errorlevel 1 goto check_py
python -m streamlit run app.py --browser.gatherUsageStats false
goto :eof

:check_py
py -c "import streamlit" >nul 2>nul
if errorlevel 1 goto missing
py -m streamlit run app.py --browser.gatherUsageStats false
goto :eof

:use_venv
".venv\Scripts\python.exe" -m streamlit run app.py --browser.gatherUsageStats false
goto :eof

:missing
echo Streamlit is not installed in the available Python environments.
echo Install project dependencies once with: python -m pip install -r requirements.txt
echo Or use the Python launcher environment: py -m pip install -r requirements.txt
pause
exit /b 1
