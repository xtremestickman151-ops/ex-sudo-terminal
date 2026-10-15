#define MyVer "1.1.1"
[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EXSUDO000001}}
AppName=EX SUDO TERMINAL
AppVersion={#MyVer}
AppVerName=EX SUDO TERMINAL {#MyVer}
AppPublisher=EX Inc.
AppPublisherURL=https://github.com/xtremestickman151-ops/ex-sudo-terminal
AppCopyright=©2026 EX Inc.
VersionInfoVersion={#MyVer}.0
VersionInfoCompany=EX Inc.
VersionInfoCopyright=©2026 EX Inc.
VersionInfoProductName=EX SUDO TERMINAL
VersionInfoDescription=EX SUDO TERMINAL Setup
DefaultDirName={localappdata}\Programs\EX SUDO TERMINAL
DefaultGroupName=EX SUDO TERMINAL
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=EX SUDO TERMINAL Setup {#MyVer}
SetupIconFile=logo.ico
UninstallDisplayIcon={app}\EX SUDO TERMINAL.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\EX SUDO TERMINAL\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\EX SUDO TERMINAL"; Filename: "{app}\EX SUDO TERMINAL.exe"
Name: "{group}\Uninstall EX SUDO TERMINAL"; Filename: "{uninstallexe}"
Name: "{userdesktop}\EX SUDO TERMINAL"; Filename: "{app}\EX SUDO TERMINAL.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\EX SUDO TERMINAL.exe"; Description: "Launch EX SUDO TERMINAL now"; Flags: nowait postinstall skipifsilent
