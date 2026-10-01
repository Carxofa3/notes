; Notes Workstation NSIS Setup Script
; Packages the full standalone Python server + GUI binary into a native Windows Setup Wizard

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

Function .onInit
  ; Clean up legacy lowercase Tauri installation if present
  ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\notes-workstation" "UninstallString"
  ${If} $0 != ""
    ExecWait '$0 /S'
  ${EndIf}

  ; Clean up previous Notes Workstation installation if present
  ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NotesWorkstation" "UninstallString"
  ${If} $0 != ""
    ExecWait '$0 /S _?=$INSTDIR'
  ${EndIf}
FunctionEnd

!ifndef ROOT_DIR
  !define ROOT_DIR ".."
!endif

; General Settings
Name "Notes Workstation"
OutFile "${ROOT_DIR}\dist\Notes-Workstation-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\NotesWorkstation"
InstallDirRegKey HKCU "Software\NotesWorkstation" "Install_Dir"
RequestExecutionLevel user

; Interface Settings
!define MUI_ABORTWARNING
!define MUI_ICON "icon.ico"
!define MUI_UNICON "icon.ico"
!define MUI_HEADERIMAGE
!define MUI_WELCOMEFINISHPAGE_BITMAP_NOSTRETCH

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\Notes-Workstation-Windows.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Notes Workstation"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; Installer Section
Section "Notes Workstation (required)" SecCore
  SetOutPath "$INSTDIR"
  
  ; Write the standalone server + GUI executable
  File "${ROOT_DIR}\dist\Notes-Workstation-Windows.exe"
  File "icon.ico"

  ; Store installation folder in registry
  WriteRegStr HKCU "Software\NotesWorkstation" "Install_Dir" "$INSTDIR"

  ; Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Windows Add/Remove Programs integration
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NotesWorkstation" "DisplayName" "Notes Workstation"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NotesWorkstation" "DisplayIcon" "$INSTDIR\icon.ico"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NotesWorkstation" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NotesWorkstation" "Publisher" "Notes Team"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NotesWorkstation" "DisplayVersion" "2.1.10"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NotesWorkstation" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NotesWorkstation" "NoRepair" 1

  ; Create Start Menu Shortcuts
  CreateDirectory "$SMPROGRAMS\Notes Workstation"
  CreateShortcut "$SMPROGRAMS\Notes Workstation\Notes Workstation.lnk" "$INSTDIR\Notes-Workstation-Windows.exe" "" "$INSTDIR\icon.ico" 0
  CreateShortcut "$SMPROGRAMS\Notes Workstation\Uninstall Notes Workstation.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0

  ; Create Desktop Shortcut
  CreateShortcut "$DESKTOP\Notes Workstation.lnk" "$INSTDIR\Notes-Workstation-Windows.exe" "" "$INSTDIR\icon.ico" 0
SectionEnd

; Uninstaller Section
Section "Uninstall"
  Delete "$DESKTOP\Notes Workstation.lnk"
  Delete "$SMPROGRAMS\Notes Workstation\Notes Workstation.lnk"
  Delete "$SMPROGRAMS\Notes Workstation\Uninstall Notes Workstation.lnk"
  RMDir "$SMPROGRAMS\Notes Workstation"

  Delete "$INSTDIR\Notes-Workstation-Windows.exe"
  Delete "$INSTDIR\icon.ico"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"

  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\NotesWorkstation"
  DeleteRegKey HKCU "Software\NotesWorkstation"
SectionEnd
