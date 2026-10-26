Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 1. Purane processes kill karein
WshShell.Run "cmd /c taskkill /F /IM python.exe /T 2>nul & taskkill /F /IM node.exe /T 2>nul", 0, True
WScript.Sleep 1000

' 2. FastAPI Backend start karein
WshShell.CurrentDirectory = "E:\raise india"
WshShell.Run "cmd /c set PYTHONPATH=E:\raise india && .\backend\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --timeout-keep-alive 60", 0, False
WScript.Sleep 2500

' 3. Next.js Frontend start karein (Port 3000)
WshShell.CurrentDirectory = "E:\raise india\frontend"
WshShell.Run "cmd /c npm run dev -- -p 3000", 0, False
WScript.Sleep 3500

' 4. Browser open karein (Clean string formatting bina quotes issue ke)
Dim targetUrl, chromePath, edgePath
targetUrl = "http://localhost:3000"
chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

If fso.FileExists(chromePath) Then
    WshShell.Run chr(34) & chromePath & chr(34) & " --app=" & targetUrl, 1, False
ElseIf fso.FileExists(edgePath) Then
    WshShell.Run chr(34) & edgePath & chr(34) & " --app=" & targetUrl, 1, False
Else
    WshShell.Run "cmd /c start " & targetUrl, 0, False
End If