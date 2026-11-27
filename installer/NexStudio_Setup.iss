; NexStudio 1.5 Final Inno Setup taslak dosyası
#define MyAppName "NexStudio"
#define MyAppVersion "1.5.10"
#define MyAppPublisher "Ali Mert Taşcı / NexHub"
#define MyAppExeName "NexStudio.exe"

[Setup]
AppId={{B9E9D60E-6E6E-4C9B-9A9A-NEXSTUDIO15FINAL}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputBaseFilename=NexStudio_Setup_1_5_Final
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\NexStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Ek kısayollar:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} uygulamasını başlat"; Flags: nowait postinstall skipifsilent
