@echo off
set API_KEY=AIzaSyCocFEwXvVWq63C1Sg2HXMgzanFDeaTKAM
curl https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=%API_KEY% ^
    -H "Content-Type: application/json" ^
    -d "{ \"contents\": [{ \"parts\":[{ \"text\": \"Hello\" }] }] }"
