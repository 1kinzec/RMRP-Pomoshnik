#define MyAppName "RMRP Помощник"
#ifndef MyAppVersion
  #define MyAppVersion "2.5.0"
#endif
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
WizardSizePercent=110,110
WizardImageFile=assets\wizard-164x314.bmp,assets\wizard-192x366.bmp,assets\wizard-246x459.bmp,assets\wizard-328x628.bmp
WizardSmallImageFile=assets\small-55.bmp,assets\small-64.bmp,assets\small-80.bmp,assets\small-110.bmp
SetupIconFile=assets\rmrp.ico
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin
DisableWelcomePage=no
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}
AppCopyright=© {#MyAppPublisher}
UsePreviousAppDir=yes
LanguageDetectionMethod=none

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Files]
Source: "..\dist\RMRP_Pomoshnik.exe"; DestDir: "{app}"; Flags: ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"
Name: "autostart"; Description: "Запускать вместе с Windows"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{commonstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent
; после тихого обновления из приложения — сразу запускаем новую версию
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: WizardSilent

[Messages]
WelcomeLabel1=Добро пожаловать в RMRP Помощник
WelcomeLabel2=Помощник по законодательству RMRP: законы и поиск по статьям, ИИ-помощник, тесты, оверлей по F10 и Discord.%n%nВерсия {#MyAppVersion}. Дальше приложение обновляется само.
SelectDirLabel3=Выберите папку для установки RMRP Помощника.
ReadyLabel1=Всё готово к установке
ReadyLabel2=Нажмите «Установить», чтобы начать установку RMRP Помощника.
FinishedHeadingLabel=Установка завершена
FinishedLabelNoIcons=RMRP Помощник версии {#MyAppVersion} успешно установлен.
FinishedLabel=RMRP Помощник версии {#MyAppVersion} успешно установлен. Нажмите «Завершить», чтобы закрыть мастер.
