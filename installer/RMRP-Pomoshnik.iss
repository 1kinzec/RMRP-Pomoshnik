#define MyAppName "RMRP Помощник"
#define MyAppVersion "1.4.0"
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
WizardStyle=modern dark includetitlebar hidebevels
WizardSizePercent=120,120
WizardBackColor=#07111F
WizardBackImageFile=assets\setup-bg.bmp
WizardBackImageOpacity=255
WizardImageFile=
WizardSmallImageFile=
SetupIconFile=assets\rmrp.ico
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin
DisableWelcomePage=no
LanguageDetectionMethod=none

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "..\dist\RMRP_Pomoshnik.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Messages]
WelcomeLabel1=Добро пожаловать в RMRP Помощник
WelcomeLabel2=Установите современный помощник по законодательству RMRP версии 1.4.0.
SelectDirLabel3=Выберите папку для установки RMRP Помощника.
ReadyLabel1=Всё готово к установке
ReadyLabel2=Нажмите «Установить», чтобы начать установку RMRP Помощника.
FinishedHeadingLabel=Установка завершена
FinishedLabelNoIcons=RMRP Помощник версии 1.4.0 успешно установлен.
