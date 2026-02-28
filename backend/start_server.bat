@echo off
set TRANSFORMERS_NO_TF=1
set USE_TF=0
set TF_CPP_MIN_LOG_LEVEL=3
cd /d c:\Users\LENOVO\AgriSense\backend
py -c "import uvicorn; uvicorn.run('main:app', host='0.0.0.0', port=8000, log_level='info')"
