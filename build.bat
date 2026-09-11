@echo off
REM Usa o python do venv: o PyInstaller do PATH pode apontar para outra instalacao
REM e empacotar uma versao de flet diferente da fixada em requirements.txt.
venv\Scripts\python.exe -m PyInstaller --noconfirm tke_chamada_antecipada.spec
