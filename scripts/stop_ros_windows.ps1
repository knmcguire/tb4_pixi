# Stop lingering ROS/Gazebo processes for this workspace on Windows.
# Targets known launch/task command lines and kills full process trees.

$ErrorActionPreference = "Stop"

function Get-DescendantPids {
    param(
        [Parameter(Mandatory = $true)]
        [int]$ParentPid,
        [Parameter(Mandatory = $true)]
        [System.Collections.Generic.HashSet[int]]$Visited
    )

    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ParentPid" |
        Select-Object -ExpandProperty ProcessId

    foreach ($child in $children) {
        if ($Visited.Add([int]$child)) {
            Get-DescendantPids -ParentPid ([int]$child) -Visited $Visited
        }
    }
}

$cmdRegex = '(turtlebot4_gz\.launch\.py|turtlebot4_gz_bringup|teleop_twist_keyboard|cmd_vel_unstamped|create3_sim|irobot_create|\bgz\s+sim\b)'
$exeNames = @(
    'gz.exe',
    'gz-sim.exe',
    'ruby.exe'
)

$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$workspaceEscaped = [Regex]::Escape($workspaceRoot)

$matches = Get-CimInstance Win32_Process | Where-Object {
    $cmd = $_.CommandLine
    $inWorkspace = $cmd -and $cmd -match $workspaceEscaped
    ($cmd -and $cmd -match $cmdRegex -and $inWorkspace) -or
    ($exeNames -contains $_.Name -and $inWorkspace)
}

if (-not $matches) {
    Write-Host '[stop] no matching ROS/Gazebo processes found'
    exit 0
}

$allPids = New-Object 'System.Collections.Generic.HashSet[int]'

foreach ($proc in $matches) {
    [void]$allPids.Add([int]$proc.ProcessId)
    Get-DescendantPids -ParentPid ([int]$proc.ProcessId) -Visited $allPids
}

# Kill deepest descendants first for cleaner teardown.
$killList = $allPids | Sort-Object -Descending

foreach ($procId in $killList) {
    try {
        $p = Get-Process -Id $procId -ErrorAction Stop
        Stop-Process -Id $procId -Force -ErrorAction Stop
        Write-Host "[stop] killed $($p.ProcessName) (PID $procId)"
    }
    catch {
        # Process may already have exited; ignore.
    }
}

Write-Host "[stop] done (terminated $($killList.Count) process(es))"
