$ErrorActionPreference = "Stop"

$GameData = "C:\Program Files (x86)\Steam\steamapps\common\Baldurs Gate 3\Data"
$Module = "WeaponMastery_7a1a5ee1-3060-4c0a-a896-6833734c6617"

$Paths = @(
  "Projects\$Module",
  "Editor\Mods\$Module",
  "Mods\$Module",
  "Public\$Module",
  "Generated\Public\$Module"
)

foreach ($Path in $Paths) {
  $Source = Join-Path $PSScriptRoot $Path
  $Target = Join-Path $GameData $Path

  New-Item -ItemType Directory -Force -Path $Source | Out-Null
  New-Item -ItemType Directory -Force -Path (Split-Path $Target) | Out-Null

  if (Test-Path -LiteralPath $Target) {
    $Item = Get-Item -LiteralPath $Target -Force
    if ($Item.LinkType -eq "Junction" -and $Item.Target -eq $Source) {
      Write-Host "Already linked: $Path"
      continue
    }

    throw "Cannot link '$Path': '$Target' already exists and is not our junction."
  }

  New-Item -ItemType Junction -Path $Target -Target $Source | Out-Null
  Write-Host "Linked: $Path"
}
