#define MyAppName "RMRP Помощник"
#define MyAppVersion "1.1.1"
#define MyAppPublisher "Kinzec X WOLF"
#define MyAppExeName "RMRP_Pomoshnik.exe"

[Setup]
AppId={{8E1B0E6A-8C0B-4A4E-A2B7-9D0F7A8D7B11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\RMRP Помощник
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=RMRP-Pomoshnik-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin

[Files]
Source: "..\dist\RMRP_Pomoshnik.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent
