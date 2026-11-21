param([string]$Package = "custom-world-package")
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    $source = (Resolve-Path -LiteralPath $Package).Path
    $customBuild = Join-Path $PSScriptRoot "src-tauri/target/custom-world"
    New-Item -ItemType Directory -Force $customBuild | Out-Null
    $archive = Join-Path $customBuild "custom-world.ofm"
    & cargo run --locked --release --manifest-path src-tauri/Cargo.toml -p ofm-cli -- pack $source --output $archive
    if ($LASTEXITCODE -ne 0) { throw "Package validation or packing failed" }
    $config = @{
        bundle = @{
            resources = @{ "target/custom-world/custom-world.ofm" = "data/custom-world.ofm" }
            windows = @{ nsis = @{ installerHooks = "windows/custom-world.nsh" } }
        }
    }
    $configFile = Join-Path $customBuild "tauri.custom.json"
    [IO.File]::WriteAllText($configFile, ($config | ConvertTo-Json -Depth 8))
    & npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }
    & npm.cmd run tauri -- build --bundles nsis --config $configFile
    if ($LASTEXITCODE -ne 0) { throw "Tauri build failed" }
} finally {
    Pop-Location
}
