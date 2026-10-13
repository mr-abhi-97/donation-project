# ==============================================================================
# Raise India Portal - Desktop Shortcut Creator
# Creates or updates "Raise India Portal.lnk" on the Windows Desktop
# Target: wscript.exe "E:\new try\launch_app.vbs"
# Icon: "E:\new try\app_icon.ico, 0"
# ==============================================================================

$WshShell = New-Object -ComObject WScript.Shell

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir -or -not (Test-Path $ScriptDir)) {
    $ScriptDir = 'E:\new try'
}

$LaunchVbsPath = Join-Path $ScriptDir 'launch_app.vbs'
$IconPath = Join-Path $ScriptDir 'app_icon.ico'

if (-not (Test-Path $LaunchVbsPath)) {
    Write-Error "Launcher script not found at $LaunchVbsPath"
    exit 1
}

# Resolve desktop locations (native + OneDrive synced desktop)
$DesktopPaths = @(
    $WshShell.SpecialFolders('Desktop'),
    [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

foreach ($Desktop in $DesktopPaths) {
    $ShortcutPath = Join-Path $Desktop 'Raise India Portal.lnk'
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = 'wscript.exe'
    $Shortcut.Arguments = '"' + $LaunchVbsPath + '"'
    $Shortcut.IconLocation = $IconPath + ', 0'
    $Shortcut.WorkingDirectory = $ScriptDir
    $Shortcut.Description = 'Raise India Foundation - Donation Reconciliation & OCR Portal'
    $Shortcut.Save()
    Write-Host "Desktop shortcut created at: $ShortcutPath"
}

Write-Host "Shortcut Name:     Raise India Portal.lnk"
Write-Host "Target:            wscript.exe ""$LaunchVbsPath"""
Write-Host "IconLocation:      $IconPath, 0"
Write-Host "WorkingDirectory:  $ScriptDir"
