' ==============================================================================
' Raise India Portal - Silent Desktop Application Launcher
' Launches FastAPI Backend and Next.js Frontend hidden in background,
' then opens the Portal in dedicated native application window mode.
' ==============================================================================
Option Explicit

Dim WshShell, fso, scriptDir
Dim backendCmd, frontendCmd, browserCmd
Dim chromePath, edgePath, localChrome, localEdge
Dim targetUrl

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Dynamically determine root repository directory
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
targetUrl = "http://localhost:3000"

' 1. Launch FastAPI Backend completely hidden (WindowStyle = 0)
backendCmd = "cmd.exe /c ""cd /d """ & scriptDir & """ && .\backend\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"""
WshShell.Run backendCmd, 0, False

' 2. Launch Next.js Frontend completely hidden (WindowStyle = 0)
frontendCmd = "cmd.exe /c ""cd /d """ & scriptDir & "\frontend"" && npm run dev"""
WshShell.Run frontendCmd, 0, False

' 3. Wait for servers to initialize (5 seconds)
WScript.Sleep 5000

' 4. Detect Browser for Dedicated Application Mode (--app)
chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
localChrome = WshShell.ExpandEnvironmentStrings("%LocalAppData%") & "\Google\Chrome\Application\chrome.exe"
localEdge = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"

If fso.FileExists(chromePath) Then
    browserCmd = """" & chromePath & """ --app=" & targetUrl
ElseIf fso.FileExists(localChrome) Then
    browserCmd = """" & localChrome & """ --app=" & targetUrl
ElseIf fso.FileExists(edgePath) Then
    browserCmd = """" & edgePath & """ --app=" & targetUrl
ElseIf fso.FileExists(localEdge) Then
    browserCmd = """" & localEdge & """ --app=" & targetUrl
Else
    ' Fallback to system default browser
    browserCmd = "cmd.exe /c start " & targetUrl
End If

' 5. Ensure Desktop Shortcut exists with official Raise India icon
Dim desktopPath, shortcutPath, oShortcut, iconFile
desktopPath = WshShell.SpecialFolders("Desktop")
shortcutPath = desktopPath & "\Raise India Portal.lnk"
iconFile = scriptDir & "\app_icon.ico"
If Not fso.FileExists(shortcutPath) Then
    Set oShortcut = WshShell.CreateShortcut(shortcutPath)
    oShortcut.TargetPath = "wscript.exe"
    oShortcut.Arguments = """" & WScript.ScriptFullName & """"
    If fso.FileExists(iconFile) Then
        oShortcut.IconLocation = iconFile & ", 0"
    End If
    oShortcut.WorkingDirectory = scriptDir
    oShortcut.Description = "Raise India Foundation - Donation Reconciliation & OCR Portal"
    oShortcut.Save
    Set oShortcut = Nothing
End If

' 6. Open Dedicated App Window
WshShell.Run browserCmd, 1, False

Set WshShell = Nothing
Set fso = Nothing
