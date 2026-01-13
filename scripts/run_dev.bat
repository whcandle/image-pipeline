@echo off
setlocal

REM 进入项目根目录（脚本所在目录的上一级）
cd /d %~dp0..
echo [run_dev] cwd=%cd%

uvicorn app.main:app --host 0.0.0.0 --port 9002 --reload
