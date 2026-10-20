param([string]$Compiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe")
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$testRoot=Join-Path $env:TEMP ('CCDASTRO-Siril-InstallerTest-'+[guid]::NewGuid().ToString('N'))
$target=Join-Path $testRoot 'installed'
New-Item -ItemType Directory -Path $target -Force | Out-Null
& $Compiler /Q /DTestBuild "/O$testRoot" /FInstallerTest (Join-Path $projectRoot 'installer\workflow.iss')
if ($LASTEXITCODE -ne 0) { throw 'Test installer compilation failed' }
$fixture="[gui]`r`nscript_path=C:\\ExistingScripts;`r`nother_setting=keep`r`n"
if ('siril' -eq 'siril') { [IO.File]::WriteAllText((Join-Path $target 'test-siril.ini'),$fixture,[Text.UTF8Encoding]::new($false)) }
[IO.File]::WriteAllText((Join-Path $target 'personal-preset.json'),'{"keep":true}')
foreach ($pass in @('install','upgrade')) {
 $run=Start-Process -FilePath (Join-Path $testRoot 'InstallerTest.exe') -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',"/DIR=`"$target`"","/LOG=`"$testRoot\$pass.log`"") -WindowStyle Hidden -Wait -PassThru
 if ($run.ExitCode -ne 0) { throw "Installer $pass failed: $($run.ExitCode)" }
 if (-not (Test-Path -LiteralPath (Join-Path $target 'ccdastro_siril\_updates.py'))) { throw 'Installed package incomplete' }
}
if ('siril' -eq 'siril') {
 $config=[IO.File]::ReadAllText((Join-Path $target 'test-siril.ini'))
 $encoded=$target.Replace('\','\\')
 $expected=$fixture.Replace('C:\\ExistingScripts;','C:\\ExistingScripts;'+$encoded+';')
 if ($config -ne $expected) { throw 'Siril settings modified unexpectedly or path duplicated' }
 if (-not (Get-ChildItem -LiteralPath $target -Filter '*.bak')) { throw 'Settings backup missing' }
}
$uninstall=Start-Process -FilePath (Join-Path $target '.uninstall\unins000.exe') -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -WindowStyle Hidden -Wait -PassThru
if ($uninstall.ExitCode -ne 0) { throw 'Uninstall failed' }
if (Test-Path -LiteralPath (Join-Path $target 'ccdastro_siril\_updates.py')) { throw 'Package was not uninstalled' }
if ([IO.File]::ReadAllText((Join-Path $target 'personal-preset.json')) -ne '{"keep":true}') { throw 'Personal preset changed' }
if ('siril' -eq 'siril' -and [IO.File]::ReadAllText((Join-Path $target 'test-siril.ini')) -ne $fixture) { throw 'Uninstall did not restore script paths' }
Write-Output 'Siril: isolated install, repeated upgrade, uninstall and personal-file preservation passed.'
