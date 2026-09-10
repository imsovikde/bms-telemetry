$dll = Join-Path (Get-Location) 'bin\LibreHardwareMonitorLib.dll'
[System.Reflection.Assembly]::LoadFrom($dll) | Out-Null

$computer = New-Object LibreHardwareMonitor.Hardware.Computer
$computer.IsCpuEnabled = $true
$computer.IsGpuEnabled = $true
$computer.IsMotherboardEnabled = $true
$computer.IsBatteryEnabled = $false
$computer.IsMemoryEnabled = $false
$computer.IsStorageEnabled = $false
$computer.Open()

foreach ($h in $computer.Hardware) {
    $h.Update()
    foreach ($sub in $h.SubHardware) {
        $sub.Update()
        foreach ($s in $sub.Sensors) {
            if ($null -ne $s.Value) {
                Write-Output "$($h.Name) / $($sub.Name) | $($s.Name) [$($s.SensorType)]: $($s.Value)"
            }
        }
    }
    foreach ($s in $h.Sensors) {
        if ($null -ne $s.Value) {
            Write-Output "$($h.Name) | $($s.Name) [$($s.SensorType)]: $($s.Value)"
        }
    }
}
$computer.Close()

