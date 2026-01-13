@echo off
setlocal enabledelayedexpansion

REM ====== 配置：把 RAW 改成你机器上真实存在的 jpg ======
set RAW=D:\workspace\image-pipeline\app\data\swim.jpg

echo [smoke] 1) health
curl -s http://localhost:9002/pipeline/v1/health
echo.

echo [smoke] 2) process
curl -s -X POST "http://localhost:9002/pipeline/v1/process" ^
  -H "Content-Type: application/json" ^
  -d "{\"requestId\":\"req_smoke_001\",\"sessionId\":\"sess_smoke_001\",\"attemptIndex\":0,\"rawPath\":\"%RAW:\=\\\\%\",\"template\":{\"templateId\":\"tpl_test\",\"outputWidth\":1800,\"outputHeight\":1200,\"backgroundPath\":\"D:\\\\no_such_bg.jpg\",\"overlayPath\":\"D:\\\\no_such_ov.png\",\"safeArea\":{\"x\":0.1,\"y\":0.1,\"w\":0.8,\"h\":0.8},\"cropMode\":\"FILL\"},\"options\":{\"bgMode\":\"STATIC\",\"segmentation\":\"AUTO\",\"featherPx\":6,\"strength\":0.6},\"output\":{\"previewWidth\":900,\"finalWidth\":1800}}"
echo.

echo [smoke] done. now open:
echo   http://localhost:9002/files/preview/sess_smoke_001/0.jpg
echo   http://localhost:9002/files/final/sess_smoke_001/0.jpg
