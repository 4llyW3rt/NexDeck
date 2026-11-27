; NexStudio Inno Setup betiği (2.6.4+: kullanıcı klasörüne kurulur, yönetici izni istemez)
; Önce build.bat çalıştırın, sonra bu dosyayı Inno Setup Compiler ile derleyin.
#define MyAppName "NexStudio"
#define MyAppVersion "2.6.4"
#define MyAppPublisher "Ali Mert Taşcı / NexHub"
#define MyAppExeName "NexStudio.exe"

[Setup]
; 1.5.x ile aynı AppId: kurulum eski sürümün üzerine güncelleme olarak yapılır.
AppId={{B9E9D60E-6E6E-4C9B-9A9A-NEXSTUDIO158}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; 2.6.4: Kullanıcı başına kurulum -> %LOCALAPPDATA%\Programs\NexStudio.
; Yönetici izni (UAC) gerekmez; otomatik güncelleme sessizce kurabilir (Chrome/Discord/VS Code gibi).
PrivilegesRequired=lowest
DefaultDirName={autopf}\{#MyAppName}
; Eski yönetici kurulumunun (Program Files) yolunu kullanma; o kopyayı uygulama ayrıca kaldırmayı önerir.
UsePreviousAppDir=no
DefaultGroupName={#MyAppName}
OutputDir=..\output
OutputBaseFilename=NexStudio_Setup_2_6_4
SetupIconFile=..\src\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; 64-bit uygulama: Program Files (x86) yerine Program Files'a kurulur
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Çalışan NexStudio'yu kapatıp güncellemeye izin ver
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\NexStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
