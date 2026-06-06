#define MyAppName "NexDeck"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "NexHub / Ali Mert Taşcı"
#define MyAppURL "https://www.youtube.com/@NexHubCo"
#define MyAppExeName "NexDeck.exe"

[Setup]
; Inno Setup'ta Tools > Generate GUID ile yeni GUID üretip AppId değerini değiştirebilirsin.
AppId={{B3F2D1A1-54C7-4C85-91A2-8A9F7E1D2026}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

DefaultDirName={localappdata}\Programs\NexHub\NexDeck
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

OutputDir=..\output
OutputBaseFilename=NexDeck_Setup_v{#MyAppVersion}

SetupIconFile=..\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

LicenseFile=..\build_assets\license.txt

Compression=lzma
SolidCompression=yes
WizardStyle=modern

PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Ek seçenekler:"; Flags: unchecked
Name: "startupicon"; Description: "Windows açılışında NexDeck'i başlat"; GroupDescription: "Ek seçenekler:"; Flags: unchecked

[Files]
Source: "..\dist\NexDeck\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build_assets\license.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\NexDeck"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\NexDeck Lisansı"; Filename: "{app}\license.txt"
Name: "{autodesktop}\NexDeck"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\NexDeck"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "NexDeck'i başlat"; Flags: nowait postinstall skipifsilent
