Set WshShell = CreateObject("WScript.Shell")
strCurDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strCurDir
WshShell.Run chr(34) & strCurDir & "\start_windows.bat" & chr(34), 0, False
Set WshShell = Nothing
