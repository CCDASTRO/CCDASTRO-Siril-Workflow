#define AppVersion "0.3.0"
[Setup]
AppId=CCDASTRO.siril.Workflow
AppName=CCDASTRO Siril Workflow
AppVersion={#AppVersion}
AppPublisher=CCDASTRO, Inc.
AppPublisherURL=https://ccdastro.com/
AppSupportURL=https://github.com/CCDASTRO/CCDASTRO-Siril-Workflow/issues
AppUpdatesURL=https://github.com/CCDASTRO/CCDASTRO-Siril-Workflow/releases
DefaultDirName={localappdata}\CCDASTRO\SirilWorkflow
DisableDirPage=yes
DefaultGroupName=CCDASTRO Siril Workflow
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=CCDASTRO-Siril-Workflow-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
#ifdef TestBuild
UninstallFilesDir={app}\.uninstall
#else
UninstallFilesDir={localappdata}\CCDASTRO\SirilWorkflowInstaller
#endif
CloseApplications=no
RestartApplications=no
SetupLogging=yes
#ifdef TestBuild
Uninstallable=yes
CreateUninstallRegKey=no
#endif
[Files]
Source: "..\CCDASTRO_Siril_Workflow.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\ccdastro_siril\*.py"; DestDir: "{app}\ccdastro_siril"; Flags: ignoreversion
Source: "..\presets\*.json"; DestDir: "{app}\presets"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\INSTALL.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\INSTALL-WINDOWS.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
#ifndef TestBuild
Name: "{group}\Installation guide"; Filename: "{app}\INSTALL-WINDOWS.txt"
Name: "{group}\Downloads and updates"; Filename: "https://github.com/CCDASTRO/CCDASTRO-Siril-Workflow/releases"
Name: "{group}\Uninstall"; Filename: "{uninstallexe}"
#endif
[Run]
Filename: "{app}\INSTALL-WINDOWS.txt"; Description: "Read installation and launch instructions"; Flags: postinstall shellexec skipifsilent
[Code]
function HostIsRunning(): Boolean;
var Locator, Service, Processes: Variant;
begin
#ifdef TestBuild
  Result := False;
#else
  try
    Locator := CreateOleObject('WbemScripting.SWbemLocator');
    Service := Locator.ConnectServer('', 'root\CIMV2');
    Processes := Service.ExecQuery('SELECT Name FROM Win32_Process WHERE Name = ''siril.exe'' OR Name = ''siril-cli.exe''');
    Result := Processes.Count > 0;
  except
    RaiseException('Unable to check whether the host is running. Close the host and try the installer again.');
  end;
#endif
end;
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if HostIsRunning() then
    Result := 'Close Siril and its workflow windows, then click Install again. No application will be closed automatically.';
end;
function InitializeUninstall(): Boolean;
begin
  Result := not HostIsRunning();
  if not Result then MsgBox('Close Siril before uninstalling this workflow.', mbInformation, MB_OK);
end;

function SirilConfig(): String;
begin
#ifdef TestBuild
  Result := ExpandConstant('{app}\test-siril.ini');
#else
  Result := ExpandConstant('{localappdata}\siril\config.1.4.ini');
#endif
end;
procedure RegisterScriptPath(Removing: Boolean);
var Config, Encoded, Value, Backup: String; Lines: TArrayOfString; I: Integer;
begin
  Config := SirilConfig();
  if not FileExists(Config) then begin
    Log('No Siril 1.4 configuration yet. See installation guide for manual script-folder registration.');
    Exit;
  end;
  if not LoadStringsFromFile(Config, Lines) then RaiseException('Could not read Siril configuration.');
  Encoded := ExpandConstant('{app}');
  StringChangeEx(Encoded, '\', '\\', True);
  for I := 0 to GetArrayLength(Lines)-1 do begin
    if Pos('script_path=', Lines[I]) = 1 then begin
      Value := Copy(Lines[I], 13, Length(Lines[I]));
      if (Value <> '') and (Value[Length(Value)] <> ';') then Value := Value + ';';
      if Removing then begin
        Value := ';' + Value;
        if StringChangeEx(Value, ';'+Encoded+';', ';', True) = 0 then Exit;
        Delete(Value,1,1);
      end else begin
        if Pos(';'+Encoded+';', ';'+Value) > 0 then Exit;
        Value := Value + Encoded + ';';
      end;
      Backup := Config + '.ccdastro-' + GetDateTimeString('yyyymmdd-hhnnss', '-', ':') + '.bak';
      if not FileCopy(Config, Backup, True) then RaiseException('Could not back up Siril settings. Registration was not changed.');
      Lines[I] := 'script_path='+Value;
      if not SaveStringsToUTF8FileWithoutBOM(Config+'.ccdastro-new', Lines, False) then RaiseException('Could not prepare updated Siril settings.');
      if not FileCopy(Config+'.ccdastro-new', Config, False) then RaiseException('Could not save Siril script-folder setting. Backup retained.');
      DeleteFile(Config+'.ccdastro-new');
      Exit;
    end;
  end;
  Log('Siril script_path entry not found; follow the manual registration steps.');
end;
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then RegisterScriptPath(False);
end;
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then RegisterScriptPath(True);
end;
