#define MyAppName "RMRP Помощник"
#define MyAppVersion "1.3.0"
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
WizardImageFile=wizard.bmp
WizardSmallImageFile=wizard-small.bmp
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

[Code]
procedure SetLabelStyle(L: TLabel; Size: Integer; Bold: Boolean; Color: TColor);
begin
  L.Font.Name := 'Segoe UI';
  L.Font.Size := Size;
  L.Font.Color := Color;
  if Bold then
    L.Font.Style := [fsBold]
  else
    L.Font.Style := [];
end;

procedure InitializeWizard;
begin
  { Deep RMRP blue palette }
  WizardForm.Color := $00180B05;
  WizardForm.MainPanel.Color := $00180B05;
  WizardForm.InnerPage.Color := $00180B05;
  WizardForm.WizardBitmapImage.ParentColor := False;
  WizardForm.WizardBitmapImage.BackColor := $001E0D06;
  WizardForm.WizardSmallBitmapImage.ParentColor := False;
  WizardForm.WizardSmallBitmapImage.BackColor := $00180B05;

  SetLabelStyle(WizardForm.WelcomeLabel1, 18, True, $00FFFFFF);
  SetLabelStyle(WizardForm.WelcomeLabel2, 10, False, $00B8C9E6);
  SetLabelStyle(WizardForm.SelectDirLabel, 10, True, $00FFFFFF);
  SetLabelStyle(WizardForm.SelectStartMenuFolderLabel, 10, True, $00FFFFFF);
  SetLabelStyle(WizardForm.ReadyLabel1, 18, True, $00FFFFFF);
  SetLabelStyle(WizardForm.ReadyLabel2, 10, False, $00B8C9E6);
  SetLabelStyle(WizardForm.FinishedLabel, 10, False, $00B8C9E6);
  SetLabelStyle(WizardForm.FinishedHeadingLabel, 18, True, $00FFFFFF);

  WizardForm.NextButton.Font.Name := 'Segoe UI';
  WizardForm.NextButton.Font.Style := [fsBold];
  WizardForm.BackButton.Font.Name := 'Segoe UI';
  WizardForm.CancelButton.Font.Name := 'Segoe UI';

end;
