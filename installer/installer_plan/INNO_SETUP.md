# Inno Setup Script Specification

## Overview
This document details the Inno Setup configuration for creating the Windows installer for the Cookie Clicker Auto-Clicker bot.

## Script Location
`installer.iss` (in repository root)

## Basic Setup

```isscript
[Setup]
AppId={{B8A1C7D2-E3F4-5678-9ABC-DEF012345678}
AppName=Cookie Clicker Auto-Clicker
AppVersion=1.0.0
AppVerName=Cookie Clicker Auto-Clicker 1.0.0
AppPublisher=Cookie Clicker Auto-Clicker
AppPublisherURL=https://github.com/auto-clicker-for-cookie-clicker
AppSupportURL=https://github.com/auto-clicker-for-cookie-clicker/issues
AppUpdatesURL=https://github.com/auto-clicker-for-cookie-clicker/releases
DefaultDirName={autopf}\Cookie Clicker Auto-Clicker
DefaultGroupName=Cookie Clicker Auto-Clicker
AllowNoIcons=yes
OutputDir=dist\installer
OutputBaseFilename=CookieClickerAutoClicker_Setup
SetupIconFile=
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
```

## License & Info

```isscript
[License]
File=LICENSE
InfoBeforeFile=
InfoAfterFile=

[CustomMessages]
LauncherCheckboxLabel=Launch Cookie Clicker Auto-Clicker after installation
```

## File Section

```isscript
[Files]
Source: "dist\main\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files
```

## Icons & Shortcuts

```isscript
[Icons]
Name: "{group}"; Filename: "{app}\CookieClickerAutoClicker.exe"; Comment: "Cookie Clicker Automation Bot"
Name: "{group}\Uninstall Cookie Clicker Auto-Clicker"; Filename: "{uninstallexe}"
Name: "{autodesktop}"; Filename: "{app}\CookieClickerAutoClicker.exe"; Comment: "Cookie Clicker Automation Bot"; Tasks: desktopicon
```

## Tasks (Optional Components)

```isscript
[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
```

## Run Post-Install

```isscript
[Run]
Filename: "{app}\CookieClickerAutoClicker.exe"; Description: "{cm:LauncherCheckboxLabel}"; Flags: postinstall nowait skipifsilent
```

## Uninstaller

```isscript
[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\CookieClickerAutoClicker"
```

## Build Command

```bash
iscc installer.iss
```

Or with custom output directory:
```bash
iscc installer.iss /Odist/installer
```

## Testing Checklist

1. Run `iscc installer.iss`
2. Execute `dist/installer/CookieClickerAutoClicker_Setup.exe`
3. Verify install location selection works
4. Test desktop shortcut creation (when enabled)
5. Test Start Menu shortcut creation
6. Verify "Launch bot" post-install option
7. Test uninstaller removes files
8. Verify config in `%LOCALAPPDATA%` is preserved (if exists)

## Version Information
- Created: 2026-04-13
- Updated: 2026-04-13