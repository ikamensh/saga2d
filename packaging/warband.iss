#ifndef AppVersion
  #error AppVersion must be supplied by tools/build_warband.py
#endif

[Setup]
AppId={{B51768BC-40A4-4705-BE86-D55131C7B414}
AppName=Warband
AppVersion={#AppVersion}
VersionInfoVersion={#AppNumericVersion}
AppPublisher=Saga2D contributors
AppPublisherURL=https://github.com/ikamensh/saga2d
DefaultDirName={localappdata}\Programs\Warband
DefaultGroupName=Warband
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=Warband-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Warband.exe
CloseApplications=yes
RestartApplications=no

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Icons]
Name: "{group}\Warband"; Filename: "{app}\Warband.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Warband"; Filename: "{app}\Warband.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\Warband.exe"; Description: "Play Warband"; Flags: nowait postinstall skipifsilent
