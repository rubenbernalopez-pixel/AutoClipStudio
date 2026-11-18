<#
.SYNOPSIS
    Build script for AutoClip Studio
.DESCRIPTION
    Compiles the WPF application, prepares Python backend, downloads dependencies,
    and creates the WiX installer package.
.NOTES
    Requires: .NET 8 SDK, WiX Toolset v4, Python 3.11+, FFmpeg
#>

param(
    [string]$Configuration = "Release",
    [string]$OutputDir = ".\artifacts",
    [switch]$SkipPythonDeps,
    [switch]$CreateInstaller,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$SolutionFile = Join-Path $ProjectRoot "AutoClipStudio.sln"
$WpfProject = Join-Path $ProjectRoot "src\AutoClipStudio.WPF\AutoClipStudio.WPF.csproj"
$PythonSource = Join-Path $ProjectRoot "src\AutoClipStudio.Python\auto_clip_studio"
$AssetsSource = Join-Path $ProjectRoot "assets"
$InstallerDir = Join-Path $ProjectRoot "installer\AutoClipStudio.Setup"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [$Level] $Message"
}

function Invoke-CommandWithLogging {
    param([string]$Command, [string]$WorkingDirectory = $ProjectRoot)
    Write-Log "Ejecutando: $Command"
    $process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c $Command" -WorkingDirectory $WorkingDirectory -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -ne 0) {
        throw "Comando falló con código $($process.ExitCode): $Command"
    }
}

# Clean previous builds
if ($Clean) {
    Write-Log "Limpiando builds anteriores..."
    Remove-Item -Path (Join-Path $ProjectRoot "artifacts") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path (Join-Path $ProjectRoot "src\AutoClipStudio.WPF\bin") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path (Join-Path $ProjectRoot "src\AutoClipStudio.WPF\obj") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path (Join-Path $ProjectRoot "src\AutoClipStudio.Core\bin") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path (Join-Path $ProjectRoot "src\AutoClipStudio.Core\obj") -Recurse -Force -ErrorAction SilentlyContinue
}

# Create output directory
$ArtifactsDir = Join-Path $ProjectRoot $OutputDir
New-Item -Path $ArtifactsDir -ItemType Directory -Force | Out-Null

# 1. Restore and build .NET projects
Write-Log "=== Restaurando paquetes NuGet ==="
Invoke-CommandWithLogging "dotnet restore \"$SolutionFile\""

Write-Log "=== Compilando solución ($Configuration) ==="
Invoke-CommandWithLogging "dotnet build \"$SolutionFile\" --configuration $Configuration --no-restore"

# 2. Publish WPF application (self-contained, single file not used due to Python)
Write-Log "=== Publicando aplicación WPF ==="
$PublishDir = Join-Path $ArtifactsDir "publish"
Invoke-CommandWithLogging "dotnet publish \"$WpfProject\" --configuration $Configuration --runtime win-x64 --self-contained false -o \"$PublishDir\""

# 3. Prepare Python backend
if (-not $SkipPythonDeps) {
    Write-Log "=== Preparando backend Python ==="

    # Check Python availability
    $pythonExe = "python"
    if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
        $pythonExe = "python3"
    }
    if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
        Write-Log "Python no encontrado en PATH. Se usará Python embebido." "WARN"
    } else {
        $pyVersion = & $pythonExe --version
        Write-Log "Python detectado: $pyVersion"
    }

    # Install Python dependencies
    $PythonTargetDir = Join-Path $PublishDir "Python"
    New-Item -Path $PythonTargetDir -ItemType Directory -Force | Out-Null

    Write-Log "Instalando dependencias Python..."
    if (Get-Command $pythonExe -ErrorAction SilentlyContinue) {
        Invoke-CommandWithLogging "$pythonExe -m pip install --upgrade pip" $PythonSource
        Invoke-CommandWithLogging "$pythonExe -m pip install -r \"$PythonSource\..\requirements.txt\" --target \"$PythonTargetDir\packages\" --no-deps" $PythonSource
    }

    # Copy Python source code
    Write-Log "Copiando código Python..."
    $PySrcTarget = Join-Path $PythonTargetDir "auto_clip_studio"
    Copy-Item -Path $PythonSource -Destination $PySrcTarget -Recurse -Force

    # Create requirements.txt if not exists
    $ReqFile = Join-Path $PythonSource "..\requirements.txt"
    if (-not (Test-Path $ReqFile)) {
        @"
faster-whisper==1.1.0
yt-dlp==2024.7.12
ffmpeg-python==0.2.0
numpy==1.26.4
torch==2.3.0
torchaudio==2.3.0
opencv-python==4.10.0.84
pillow==10.3.0
pydantic==2.7.1
pydantic-settings==2.3.3
python-json-logger==2.0.7
rich==13.7.1
click==8.1.7
tqdm==4.66.4
requests==2.32.3
aiofiles==23.2.1
"@ | Set-Content -Path $ReqFile -Encoding UTF8
    }
}

# 4. Copy assets
Write-Log "=== Copiando assets ==="
$AssetsTarget = Join-Path $PublishDir "Assets"
Copy-Item -Path $AssetsSource -Destination $AssetsTarget -Recurse -Force -ErrorAction SilentlyContinue

# Create placeholder background videos if they don't exist
$BgDir = Join-Path $AssetsTarget "backgrounds"
New-Item -Path $BgDir -ItemType Directory -Force | Out-Null

# 5. Copy FFmpeg (bundled)
Write-Log "=== Verificando FFmpeg ==="
$FfmpegDir = Join-Path $PublishDir "ffmpeg"
if (-not (Test-Path (Join-Path $FfmpegDir "ffmpeg.exe"))) {
    Write-Log "FFmpeg no encontrado en build output. Se espera que esté en PATH o se descargue en primer uso." "WARN"
}

# 6. Create installer if requested
if ($CreateInstaller) {
    Write-Log "=== Creando instalador WiX ==="

    # Check WiX
    $wixCmd = "dotnet wix"
    if (-not (Get-Command "dotnet" -ErrorAction SilentlyContinue)) {
        throw "dotnet no encontrado. Instale .NET 8 SDK."
    }

    # Install WiX toolset if not present
    try {
        Invoke-CommandWithLogging "dotnet tool list -g | findstr wix"
    } catch {
        Write-Log "Instalando WiX Toolset..."
        Invoke-CommandWithLogging "dotnet tool install --global wix"
    }

    # Build MSI
    $MsiOutput = Join-Path $ArtifactsDir "AutoClipStudio.msi"
    $WixProject = Join-Path $InstallerDir "AutoClipStudio.Setup.wixproj"

    # Create WiX project file if not exists
    if (-not (Test-Path $WixProject)) {
        @"
<Project Sdk="WixToolset.Sdk/4.0.5">
  <PropertyGroup>
    <OutputType>Package</OutputType>
    <DefineConstants>BuildOutput=$PublishDir;PythonSource=$PythonSource;AssetsSource=$AssetsSource</DefineConstants>
  </PropertyGroup>
  <ItemGroup>
    <Content Include="Product.wxs" />
  </ItemGroup>
</Project>
"@ | Set-Content -Path $WixProject -Encoding UTF8
    }

    Invoke-CommandWithLogging "dotnet build \"$WixProject\" --configuration $Configuration -p:DefineConstants=\"BuildOutput=$PublishDir;PythonSource=$PythonSource;AssetsSource=$AssetsSource\"" $InstallerDir

    # Copy MSI to artifacts
    $BuiltMsi = Join-Path $InstallerDir "bin\$Configuration\AutoClipStudio.msi"
    if (Test-Path $BuiltMsi) {
        Copy-Item -Path $BuiltMsi -Destination $MsiOutput -Force
        Write-Log "MSI creado: $MsiOutput"
    }

    # Build Bootstrapper (Bundle)
    $BundleProject = Join-Path $InstallerDir "AutoClipStudio.Bundle.wixproj"
    if (-not (Test-Path $BundleProject)) {
        @"
<Project Sdk="WixToolset.Sdk/4.0.5">
  <PropertyGroup>
    <OutputType>Bundle</OutputType>
    <DefineConstants>BuildOutput=$PublishDir;PythonSource=$PythonSource;AssetsSource=$AssetsSource;PrereqsDir=$ProjectRoot\prereqs</DefineConstants>
  </PropertyGroup>
  <ItemGroup>
    <Content Include="Bundle.wxs" />
  </ItemGroup>
</Project>
"@ | Set-Content -Path $BundleProject -Encoding UTF8
    }

    $BundleOutput = Join-Path $ArtifactsDir "AutoClipStudio_Setup.exe"
    Invoke-CommandWithLogging "dotnet build \"$BundleProject\" --configuration $Configuration -p:DefineConstants=\"BuildOutput=$PublishDir;PythonSource=$PythonSource;AssetsSource=$AssetsSource;PrereqsDir=$ProjectRoot\prereqs\"" $InstallerDir

    $BuiltBundle = Join-Path $InstallerDir "bin\$Configuration\AutoClipStudio_Setup.exe"
    if (Test-Path $BuiltBundle) {
        Copy-Item -Path $BuiltBundle -Destination $BundleOutput -Force
        Write-Log "Instalador creado: $BundleOutput"
    }
}

# 7. Create ZIP distribution
Write-Log "=== Creando distribución ZIP ==="
$ZipName = "AutoClipStudio_v1.0.0_win-x64.zip"
$ZipPath = Join-Path $ArtifactsDir $ZipName
Compress-Archive -Path (Join-Path $PublishDir "*") -DestinationPath $ZipPath -Force
Write-Log "ZIP creado: $ZipPath"

# 8. Generate checksums
Write-Log "=== Generando checksums ==="
$FilesToHash = @($ZipPath)
if ($CreateInstaller -and (Test-Path (Join-Path $ArtifactsDir "AutoClipStudio_Setup.exe"))) {
    $FilesToHash += Join-Path $ArtifactsDir "AutoClipStudio_Setup.exe"
}

foreach ($file in $FilesToHash) {
    $hash = Get-FileHash -Path $file -Algorithm SHA256
    $hash.Hash | Set-Content -Path "$file.sha256"
    Write-Log "SHA256: $($hash.Hash)  $($hash.Path)"
}

Write-Log "=== Build completado ==="
Write-Log "Artefactos en: $ArtifactsDir"
Get-ChildItem -Path $ArtifactsDir | ForEach-Object { Write-Log "  - $($_.Name) ($([math]::Round($_.Length/1MB, 2)) MB)" }