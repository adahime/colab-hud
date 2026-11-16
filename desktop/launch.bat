@echo off
setlocal
set "TOOL_PYTHONW=%USERPROFILE%\AppData\Roaming\uv\tools\google-colab-cli\Scripts\pythonw.exe"
if exist "%TOOL_PYTHONW%" (
  start "" "%TOOL_PYTHONW%" "%~dp0launch.pyw"
) else (
  start "" pythonw "%~dp0launch.pyw"
)
