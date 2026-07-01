$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Tools = Join-Path $Root "portable-tools"
$SdkRoot = Join-Path $Tools "android-sdk"
$Downloads = Join-Path $Tools "downloads"
$JdkDir = Join-Path $Tools "jdk17"
$GradleDir = Join-Path $Tools "gradle"

New-Item -ItemType Directory -Force -Path $Tools, $Downloads, $SdkRoot | Out-Null

function Download-File($Url, $OutFile) {
    if (Test-Path $OutFile) {
        Write-Host "Using cached $OutFile"
        return
    }
    Write-Host "Downloading $Url"
    Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
}

function Expand-Fresh($Zip, $Destination) {
    if (Test-Path $Destination) {
        Write-Host "Using existing $Destination"
        return
    }
    $tmp = "$Destination.tmp"
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    Expand-Archive -Path $Zip -DestinationPath $tmp -Force
    $child = Get-ChildItem -Path $tmp | Select-Object -First 1
    if ($child -and $child.PSIsContainer) {
        Move-Item -Path $child.FullName -Destination $Destination
        Remove-Item -Recurse -Force $tmp
    } else {
        Move-Item -Path $tmp -Destination $Destination
    }
}

$JdkZip = Join-Path $Downloads "jdk17.zip"
$GradleZip = Join-Path $Downloads "gradle.zip"
$CmdlineZip = Join-Path $Downloads "android-commandlinetools.zip"

Download-File "https://api.adoptium.net/v3/binary/latest/17/ga/windows/x64/jdk/hotspot/normal/eclipse?project=jdk" $JdkZip
Download-File "https://services.gradle.org/distributions/gradle-8.10.2-bin.zip" $GradleZip
Download-File "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip" $CmdlineZip

Expand-Fresh $JdkZip $JdkDir
Expand-Fresh $GradleZip $GradleDir

$CmdlineRoot = Join-Path $SdkRoot "cmdline-tools"
$Latest = Join-Path $CmdlineRoot "latest"
if (!(Test-Path $Latest)) {
    New-Item -ItemType Directory -Force -Path $CmdlineRoot | Out-Null
    $tmpCmd = Join-Path $Tools "cmdline-tools-tmp"
    if (Test-Path $tmpCmd) { Remove-Item -Recurse -Force $tmpCmd }
    New-Item -ItemType Directory -Force -Path $tmpCmd | Out-Null
    Expand-Archive -Path $CmdlineZip -DestinationPath $tmpCmd -Force
    $inner = Join-Path $tmpCmd "cmdline-tools"
    Move-Item -Path $inner -Destination $Latest
    Remove-Item -Recurse -Force $tmpCmd
}

$env:JAVA_HOME = $JdkDir
$env:ANDROID_HOME = $SdkRoot
$env:ANDROID_SDK_ROOT = $SdkRoot
$env:Path = "$JdkDir\bin;$GradleDir\bin;$Latest\bin;$SdkRoot\platform-tools;$env:Path"

Write-Host "Java:"
& "$JdkDir\bin\java.exe" -version

Write-Host "Installing Android SDK packages..."
$yes = "y`n" * 200
$yes | & "$Latest\bin\sdkmanager.bat" --sdk_root=$SdkRoot --licenses | Out-Host
& "$Latest\bin\sdkmanager.bat" --sdk_root=$SdkRoot "platform-tools" "platforms;android-35" "build-tools;35.0.0"

Write-Host "Building APK..."
Set-Location $Root
& "$GradleDir\bin\gradle.bat" assembleDebug --no-daemon

$Apk = Join-Path $Root "app\build\outputs\apk\debug\app-debug.apk"
if (!(Test-Path $Apk)) {
    throw "APK was not generated."
}

Write-Host ""
Write-Host "APK ready:"
Write-Host $Apk
