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
WizardBackImageOpacity=165

WizardImageFile=
WizardSmallImageFile=

SetupIconFile=assets\rmrp.ico

ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

PrivilegesRequired=admin
DisableWelcomePage=no

[Files]
Source: "..\dist\RMRP_Pomoshnik.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Messages]
WelcomeLabel1=Добро пожаловать в {#MyAppName}
WelcomeLabel2=Установка версии {#MyAppVersion}\n\nСовременный помощник по законодательству RMRP.\n\nНажмите «Далее», чтобы продолжить установку.
SelectDirLabel3=Выберите папку, в которую будет установлен {#MyAppName}.
ReadyLabel1=Всё готово к установке
ReadyLabel2=Нажмите «Установить», чтобы установить {#MyAppName} на компьютер.
FinishedHeadingLabel=Установка завершена
FinishedLabelNoIcons=Установка {#MyAppName} успешно завершена.
