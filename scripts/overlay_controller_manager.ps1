param(
    [switch]$NoBackup
)

$src = "install/bin/controller_manager.dll"
$dst = ".pixi/envs/default/Library/bin/controller_manager.dll"

if (!(Test-Path $src)) {
    Write-Host "[overlay] skip: install/bin/controller_manager.dll not built yet"
    exit 0
}

if (!(Test-Path $dst)) {
    # If conda has no copy yet, place the patched DLL in the expected load directory.
    Copy-Item -Force $src $dst
    Write-Host "[overlay] conda copy missing; placed patched controller_manager.dll in Library/bin"
    exit 0
}

if (!$NoBackup -and !(Test-Path ($dst + ".conda-backup"))) {
    Copy-Item $dst ($dst + ".conda-backup")
}

try {
    Copy-Item -Force $src $dst
    if ($NoBackup) {
        Write-Host "[overlay] patched controller_manager.dll in place"
    } else {
        Write-Host "[overlay] patched controller_manager.dll copied over conda copy"
    }
} catch {
    if ($NoBackup) {
        Write-Host "[overlay] skip: controller_manager.dll is locked (sim running?)"
        exit 0
    }
    throw
}
