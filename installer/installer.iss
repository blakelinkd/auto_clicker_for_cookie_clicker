; Inno Setup Script for Cookie Clicker Auto-Clicker
; Generates a Windows installer

#define MyAppName "Cookie Clicker Auto-Clicker"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Cookie Clicker Auto-Clicker"
#define MyAppURL "https://github.com/auto-clicker-for-cookie-clicker"
#define MyAppExeName "CookieClickerAutoClicker.exe"

[Setup]
AppId={{B8A1C7D2-E3F4-5678-9ABC-DEF012345678}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\Cookie Clicker Auto-Clicker
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist\installer
OutputBaseFilename=CookieClickerAutoClicker_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=..\docs\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\main\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Cookie Clicker Auto-Clicker"; Filename: "{app}\{#MyAppExeName}"; Comment: "Cookie Clicker Automation Bot"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Cookie Clicker Auto-Clicker"; Filename: "{app}\{#MyAppExeName}"; Comment: "Cookie Clicker Automation Bot"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Cookie Clicker Auto-Clicker"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\CookieClickerAutoClicker"
