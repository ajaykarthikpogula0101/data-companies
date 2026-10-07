<#
.SYNOPSIS
  Find regions where this subscription can actually create a 4-vCPU VM.

.DESCRIPTION
  Azure refuses a VM for three different reasons and only reports one at a time:
  the size has no capacity in that region, the region is closed to new
  customers, or your vCPU quota there is used up. This checks all three.

  Only the Standard_D4* families are fetched (server-side filter), so it runs in
  a couple of minutes rather than downloading every SKU in every region.

  A size counts as usable unless it is blocked for the whole location, or every
  availability zone is blocked. Zone-level restrictions on SOME zones are fine --
  we do not pin a zone when creating.

.EXAMPLE
  .\deploy\find_vm_capacity.ps1
  .\deploy\find_vm_capacity.ps1 -Regions eastus,westus3,japaneast
#>
[CmdletBinding()]
param(
  [string[]]$Regions = @(
    "centralindia", "southindia", "westindia",
    "eastus", "eastus2", "centralus", "southcentralus", "westus2", "westus3",
    "canadacentral", "northeurope", "uksouth", "swedencentral",
    "germanywestcentral", "francecentral", "polandcentral",
    "uaenorth", "japaneast", "koreacentral", "southeastasia",
    "australiaeast", "brazilsouth"
  ),
  # 4 vCPU / 16 GB, x86 only. ARM sizes (D4ps_v5 and friends) are deliberately
  # excluded: the Camoufox browser build we install is x86-64.
  [string[]]$Sizes = @(
    "Standard_D4as_v5", "Standard_D4ads_v5", "Standard_D4s_v5",
    "Standard_D4ds_v5", "Standard_D4as_v4", "Standard_D4a_v4",
    "Standard_D4s_v4", "Standard_D4s_v3"
  ),
  [int]$NeedVcpu = 4
)

$ErrorActionPreference = "Continue"
$rows = @()

foreach ($region in $Regions) {
  Write-Host ("{0,-20}" -f $region) -NoNewline

  # --- quota ---------------------------------------------------------------
  $freeTotal = -1
  try {
    $usage = az vm list-usage -l $region -o json 2>$null | ConvertFrom-Json
    $total = $usage | Where-Object { $_.name.value -eq "cores" } | Select-Object -First 1
    if ($total) { $freeTotal = [int]$total.limit - [int]$total.currentValue }
  } catch { }

  if ($freeTotal -lt 0) {
    Write-Host "region closed / no access" -ForegroundColor DarkGray
    $rows += [pscustomobject]@{ Region = $region; FreeVcpu = "-"; Sizes = "region closed"; CanCreate = "no" }
    continue
  }

  # --- which D4 sizes are actually offered here ----------------------------
  $available = @()
  try {
    $skus = az vm list-skus -l $region --size Standard_D4 --all -o json 2>$null | ConvertFrom-Json
    foreach ($sku in $skus) {
      if ($Sizes -notcontains $sku.name) { continue }
      $blocked = $false
      foreach ($r in @($sku.restrictions)) {
        if ($r.type -eq "Location") { $blocked = $true; break }
        # every zone blocked == effectively unavailable
        if ($r.type -eq "Zone" -and @($r.restrictionInfo.zones).Count -ge 3) { $blocked = $true; break }
      }
      if (-not $blocked) { $available += $sku.name }
    }
  } catch { }
  $available = $available | Select-Object -Unique

  $usable = ($freeTotal -ge $NeedVcpu) -and ($available.Count -gt 0)
  $rows += [pscustomobject]@{
    Region    = $region
    FreeVcpu  = $freeTotal
    Sizes     = if ($available) { ($available -join ", ") } else { "none" }
    CanCreate = if ($usable) { "YES" } else { "no" }
  }

  $msg = "free vCPU=$freeTotal  " + $(if ($available) { $available[0] } else { "no D4 size available" })
  Write-Host $msg -ForegroundColor $(if ($usable) { "Green" } else { "DarkGray" })
}

Write-Host "`n=== USE THESE: regions that will accept a $NeedVcpu-vCPU VM ===" -ForegroundColor Cyan
$good = $rows | Where-Object { $_.CanCreate -eq "YES" }
if ($good) { $good | Format-Table -AutoSize } else { Write-Host "none found" -ForegroundColor Red }

Write-Host "=== everything checked ===" -ForegroundColor DarkGray
$rows | Format-Table -AutoSize
