; Installateur Windows de PrepaFlyPy (Inno Setup).
; Compilé par la CI GitHub à chaque tag : produit installer_out\PrepaFlyPy-Setup.exe.
; La version est passée par la ligne de commande : ISCC /DAppVersion=x.y.z installer.iss
; Installation par utilisateur (sans droits admin), raccourcis menu Démarrer + Bureau,
; désinstallation visible dans « Applications installées » de Windows.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "PrepaFlyPy"
#define AppExe "PrepaFlyPy.exe"

[Setup]
AppId={{B7B4B2E0-6E2A-4C3F-9A1D-0F3C2E5A7D91}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=M.G.I. - Maintenance Generale Industrielle
AppPublisherURL=https://github.com/paul-jnn/PrepaFlyPy
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExe}
OutputDir=installer_out
OutputBaseFilename=PrepaFlyPy-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
{ Marque l'installation comme faite pour que l'app ne repropose pas de créer des
  raccourcis (l'installateur s'en est déjà chargé). Chemin = dossier de données
  utilisateur de l'app (platformdirs : LocalAppData\MGI\PrepaFlyPy). }
procedure CurStepChanged(CurStep: TSetupStep);
var Dir: string;
begin
  if CurStep = ssPostInstall then
  begin
    Dir := ExpandConstant('{localappdata}\MGI\PrepaFlyPy');
    ForceDirectories(Dir);
    SaveStringToFile(Dir + '\.setup_done', '1', False);
  end;
end;
