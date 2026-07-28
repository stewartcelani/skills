#Requires -Version 5.1
<#
.SYNOPSIS
  Read-only Active Directory Group Policy inventory via LDAP (no RSAT required).

.DESCRIPTION
  Domain-agnostic: discovers the domain and configuration naming contexts from
  RootDSE. Lists GPOs, expands gPLink topology (domain/OU/site), finds unlinked
  GPOs, and can run gpresult for the current user. Read-only — never writes.

.PARAMETER Action
  list | unlinked | links | links-on | gpo | search | rsop-user | summary

.PARAMETER Name
  GPO display-name fragment, or OU name/DN fragment for links-on.

.PARAMETER Json
  Emit JSON instead of tables.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('list', 'unlinked', 'links', 'links-on', 'gpo', 'search', 'rsop-user', 'summary')]
    [string]$Action,

    [string]$Name = '',

    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-DomainDn {
    $root = [ADSI]'LDAP://RootDSE'
    return [string]$root.defaultNamingContext
}

function Get-ConfigDn {
    $root = [ADSI]'LDAP://RootDSE'
    return [string]$root.configurationNamingContext
}

function Decode-GpoFlags([int]$flags) {
    switch ($flags) {
        0 { 'Enabled (User+Computer)' }
        1 { 'User disabled' }
        2 { 'Computer disabled' }
        3 { 'Both disabled' }
        default { "flags=$flags" }
    }
}

function Decode-LinkOptions([int]$options) {
    switch ($options) {
        0 { [pscustomobject]@{ Enabled = $true;  Enforced = $false; Label = 'Enabled' } }
        1 { [pscustomobject]@{ Enabled = $false; Enforced = $false; Label = 'Disabled' } }
        2 { [pscustomobject]@{ Enabled = $true;  Enforced = $true;  Label = 'Enforced' } }
        3 { [pscustomobject]@{ Enabled = $false; Enforced = $true;  Label = 'Disabled+Enforced' } }
        default { [pscustomobject]@{ Enabled = $null; Enforced = $null; Label = "options=$options" } }
    }
}

function Get-PropFirst($props, [string]$name) {
    if (-not $props.PropertyNames.Contains($name)) { return $null }
    if ($props[$name].Count -lt 1) { return $null }
    return $props[$name][0]
}

function Get-AllGpos {
    $domainDn = Get-DomainDn
    $searcher = New-Object DirectoryServices.DirectorySearcher([ADSI]"LDAP://CN=Policies,CN=System,$domainDn")
    $searcher.Filter = '(objectClass=groupPolicyContainer)'
    $searcher.PageSize = 500
    [void]$searcher.PropertiesToLoad.AddRange(@(
        'displayName', 'cn', 'flags', 'gPCFileSysPath', 'whenChanged', 'whenCreated', 'versionNumber', 'distinguishedName'
    ))
    $list = foreach ($r in $searcher.FindAll()) {
        $cn = [string](Get-PropFirst $r.Properties 'cn')
        if ([string]::IsNullOrWhiteSpace($cn)) { continue }
        $guid = $cn.Trim('{}')
        $flagsVal = Get-PropFirst $r.Properties 'flags'
        $flags = if ($null -ne $flagsVal) { [int]$flagsVal } else { 0 }
        $display = Get-PropFirst $r.Properties 'displayname'
        $sysvol = Get-PropFirst $r.Properties 'gpcfilesyspath'
        $changed = Get-PropFirst $r.Properties 'whenchanged'
        $ver = Get-PropFirst $r.Properties 'versionnumber'
        $dn = Get-PropFirst $r.Properties 'distinguishedname'
        [pscustomobject]@{
            Name          = if ($display) { [string]$display } else { $cn }
            Guid          = $cn
            GuidBare      = $guid
            Flags         = $flags
            FlagsLabel    = Decode-GpoFlags $flags
            Sysvol        = if ($sysvol) { [string]$sysvol } else { '' }
            WhenChanged   = if ($changed) { [datetime]$changed } else { $null }
            VersionNumber = if ($null -ne $ver) { [int]$ver } else { $null }
            Dn            = if ($dn) { [string]$dn } else { $r.Path }
        }
    }
    return @($list | Sort-Object Name)
}

function Parse-GPLink([string]$gpLink) {
    if ([string]::IsNullOrWhiteSpace($gpLink)) { return @() }
    # Format: [LDAP://cn={guid},cn=policies,...;<options>][...]
    $matches = [regex]::Matches($gpLink, '\[LDAP://([^;]+);(\d+)\]', 'IgnoreCase')
    $i = 0
    foreach ($m in $matches) {
        $i++
        $path = $m.Groups[1].Value
        $options = [int]$m.Groups[2].Value
        $guid = $null
        if ($path -match 'cn=\{([0-9A-Fa-f-]+)\}') { $guid = '{' + $Matches[1] + '}' }
        $decoded = Decode-LinkOptions $options
        [pscustomobject]@{
            StorageOrder = $i   # 1 = first in gPLink string (LSF / lower precedence in GPMC UI often reversed)
            Guid         = $guid
            LinkPath     = $path
            Options      = $options
            Enabled      = $decoded.Enabled
            Enforced     = $decoded.Enforced
            LinkState    = $decoded.Label
        }
    }
}

function Get-LinkContainers {
    $domainDn = Get-DomainDn
    $configDn = Get-ConfigDn
    $results = [System.Collections.Generic.List[object]]::new()

    $searchDomain = New-Object DirectoryServices.DirectorySearcher([ADSI]"LDAP://$domainDn")
    $searchDomain.Filter = '(|(objectClass=organizationalUnit)(objectClass=domainDNS))'
    $searchDomain.PageSize = 500
    [void]$searchDomain.PropertiesToLoad.AddRange(@('distinguishedName', 'name', 'gPLink', 'gPOptions'))
    foreach ($r in $searchDomain.FindAll()) {
        $rawVal = Get-PropFirst $r.Properties 'gplink'
        if ([string]::IsNullOrWhiteSpace([string]$rawVal)) { continue }
        $raw = [string]$rawVal
        if ($raw -notmatch '\[LDAP://') { continue }
        $dn = [string](Get-PropFirst $r.Properties 'distinguishedname')
        $name = [string](Get-PropFirst $r.Properties 'name')
        $gpOptVal = Get-PropFirst $r.Properties 'gpoptions'
        $gpOptions = if ($null -ne $gpOptVal) { [int]$gpOptVal } else { 0 }
        $results.Add([pscustomobject]@{
            ScopeType         = if ($dn -eq $domainDn) { 'Domain' } else { 'OU' }
            Name              = $name
            DistinguishedName = $dn
            BlockInheritance  = [bool]($gpOptions -band 1)
            GPLinkRaw         = $raw
            Links             = @(Parse-GPLink $raw)
        }) | Out-Null
    }

    try {
        $searchSites = New-Object DirectoryServices.DirectorySearcher([ADSI]"LDAP://CN=Sites,$configDn")
        $searchSites.Filter = '(objectClass=site)'
        $searchSites.PageSize = 100
        [void]$searchSites.PropertiesToLoad.AddRange(@('distinguishedName', 'name', 'gPLink', 'gPOptions'))
        foreach ($r in $searchSites.FindAll()) {
            $rawVal = Get-PropFirst $r.Properties 'gplink'
            if ([string]::IsNullOrWhiteSpace([string]$rawVal)) { continue }
            $raw = [string]$rawVal
            if ($raw -notmatch '\[LDAP://') { continue }
            $dn = [string](Get-PropFirst $r.Properties 'distinguishedname')
            $name = [string](Get-PropFirst $r.Properties 'name')
            $gpOptVal = Get-PropFirst $r.Properties 'gpoptions'
            $gpOptions = if ($null -ne $gpOptVal) { [int]$gpOptVal } else { 0 }
            $results.Add([pscustomobject]@{
                ScopeType         = 'Site'
                Name              = $name
                DistinguishedName = $dn
                BlockInheritance  = [bool]($gpOptions -band 1)
                GPLinkRaw         = $raw
                Links             = @(Parse-GPLink $raw)
            }) | Out-Null
        }
    } catch {
        Write-Warning "Site gPLink scan failed: $_"
    }

    return @($results)
}

function Get-LinkedGuidSet($containers) {
    $set = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($c in $containers) {
        foreach ($l in $c.Links) {
            if ($l.Guid) { [void]$set.Add($l.Guid.Trim('{}')) }
        }
    }
    return $set
}

function Expand-Links($containers, $gpoByGuid) {
    foreach ($c in $containers) {
        # GPMC UI shows link order with highest precedence first = reverse of storage order
        $uiOrder = $c.Links.Count
        foreach ($l in $c.Links) {
            $bare = if ($l.Guid) { $l.Guid.Trim('{}') } else { '' }
            $gpoName = $null
            if ($bare -and $gpoByGuid.ContainsKey($bare)) { $gpoName = $gpoByGuid[$bare].Name }
            [pscustomobject]@{
                ScopeType         = $c.ScopeType
                ScopeName         = $c.Name
                ScopeDn           = $c.DistinguishedName
                BlockInheritance  = $c.BlockInheritance
                Precedence        = $uiOrder   # 1 = highest precedence (GPMC-style)
                StorageOrder      = $l.StorageOrder
                GpoName           = $gpoName
                GpoGuid           = $l.Guid
                LinkState         = $l.LinkState
                Enabled           = $l.Enabled
                Enforced          = $l.Enforced
            }
            $uiOrder--
        }
    }
}

function Emit($objects) {
    $arr = @($objects)
    if ($Json) {
        $arr | ConvertTo-Json -Depth 6
    } else {
        $arr | Format-Table -AutoSize | Out-String -Width 220 | Write-Output
        Write-Output "Count: $($arr.Count)"
    }
}

# --- Actions ---

switch ($Action) {
    'rsop-user' {
        $text = & gpresult.exe /r /scope user 2>&1 | Out-String
        if ($Json) {
            [pscustomobject]@{ Action = 'rsop-user'; Output = $text } | ConvertTo-Json -Depth 4
        } else {
            $text
        }
        break
    }

    'summary' {
        $gpos = Get-AllGpos
        $containers = Get-LinkContainers
        $linked = Get-LinkedGuidSet $containers
        $unlinkedCount = @($gpos | Where-Object { -not $linked.Contains($_.GuidBare) }).Count
        $obj = [pscustomobject]@{
            Domain            = Get-DomainDn
            GpoTotal          = $gpos.Count
            ContainersWithLinks = $containers.Count
            DistinctLinkedGpos = $linked.Count
            UnlinkedGpos      = $unlinkedCount
            QueriedAt         = Get-Date
        }
        if ($Json) { $obj | ConvertTo-Json } else { $obj | Format-List | Out-String | Write-Output }
        break
    }

    'list' {
        Emit (Get-AllGpos | Select-Object Name, Guid, Flags, FlagsLabel, WhenChanged, Sysvol)
        break
    }

    'search' {
        if ([string]::IsNullOrWhiteSpace($Name)) { throw '-Name is required for search' }
        $gpos = Get-AllGpos | Where-Object { $_.Name -like "*$Name*" }
        Emit ($gpos | Select-Object Name, Guid, Flags, FlagsLabel, WhenChanged, Sysvol)
        break
    }

    'unlinked' {
        $gpos = Get-AllGpos
        $linked = Get-LinkedGuidSet (Get-LinkContainers)
        $unlinked = $gpos | Where-Object { -not $linked.Contains($_.GuidBare) }
        Emit ($unlinked | Select-Object Name, Guid, Flags, FlagsLabel, WhenChanged)
        break
    }

    'links' {
        $gpos = Get-AllGpos
        $byGuid = @{}
        foreach ($g in $gpos) { $byGuid[$g.GuidBare] = $g }
        $rows = Expand-Links (Get-LinkContainers) $byGuid
        Emit ($rows | Sort-Object ScopeDn, Precedence)
        break
    }

    'links-on' {
        if ([string]::IsNullOrWhiteSpace($Name)) { throw '-Name is required for links-on (OU name or DN fragment)' }
        $gpos = Get-AllGpos
        $byGuid = @{}
        foreach ($g in $gpos) { $byGuid[$g.GuidBare] = $g }
        $containers = Get-LinkContainers | Where-Object {
            $_.DistinguishedName -like "*$Name*" -or $_.Name -like "*$Name*"
        }
        if (-not $containers) {
            Write-Warning "No containers with gPLink matched '$Name'. (OUs with zero direct links are omitted.)"
        }
        $rows = Expand-Links $containers $byGuid
        Emit ($rows | Sort-Object ScopeDn, Precedence)
        break
    }

    'gpo' {
        if ([string]::IsNullOrWhiteSpace($Name)) { throw '-Name is required for gpo' }
        $gpos = Get-AllGpos | Where-Object {
            $_.Name -like "*$Name*" -or $_.Guid -like "*$Name*" -or $_.GuidBare -like "*$Name*"
        }
        if (-not $gpos) { throw "No GPO matched '$Name'" }
        $byGuid = @{}
        foreach ($g in Get-AllGpos) { $byGuid[$g.GuidBare] = $g }
        $allLinks = @(Expand-Links (Get-LinkContainers) $byGuid)
        $payload = foreach ($g in $gpos) {
            $links = @($allLinks | Where-Object { $_.GpoGuid -and $_.GpoGuid.Trim('{}') -eq $g.GuidBare })
            [pscustomobject]@{
                Name       = $g.Name
                Guid       = $g.Guid
                Flags      = $g.Flags
                FlagsLabel = $g.FlagsLabel
                Sysvol     = $g.Sysvol
                WhenChanged = $g.WhenChanged
                LinkCount  = $links.Count
                Links      = $links
            }
        }
        if ($Json) {
            $payload | ConvertTo-Json -Depth 6
        } else {
            foreach ($p in $payload) {
                Write-Output "==== $($p.Name)  $($p.Guid) ===="
                Write-Output "Flags: $($p.FlagsLabel) ($($p.Flags))"
                Write-Output "Sysvol: $($p.Sysvol)"
                Write-Output "WhenChanged: $($p.WhenChanged)"
                Write-Output "LinkCount: $($p.LinkCount)"
                if ($p.LinkCount -eq 0) {
                    Write-Output "(not linked on any domain/OU/site scanned)"
                } else {
                    $p.Links | Select-Object Precedence, LinkState, Enabled, Enforced, ScopeType, ScopeName, ScopeDn |
                        Format-Table -AutoSize | Out-String -Width 220 | Write-Output
                }
            }
        }
        break
    }
}
