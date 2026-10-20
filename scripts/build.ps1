param([string]$Compiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe")
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
if (-not (Test-Path -LiteralPath $Compiler)) { throw 'Install Inno Setup 6 or pass -Compiler with the ISCC.exe path.' }
& $Compiler (Join-Path $projectRoot 'installer\workflow.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
& python (Join-Path $PSScriptRoot 'package.py')
if ($LASTEXITCODE -ne 0) { throw 'ZIP packaging failed.' }
