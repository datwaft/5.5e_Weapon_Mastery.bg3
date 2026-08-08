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

  if (-not (Test-Path -LiteralPath $Target)) {
    Write-Host "Not linked: $Path"
    continue
  }

  $Item = Get-Item -LiteralPath $Target -Force
  if ($Item.LinkType -ne "Junction" -or $Item.Target -ne $Source) {
    throw "Refusing to remove '$Target': it is not our junction."
  }

  Remove-Item -LiteralPath $Target
  Write-Host "Unlinked: $Path"
}
