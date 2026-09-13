$sshDir = "$env:USERPROFILE\.ssh"
$keyPath = "$sshDir\id_ed25519"

if (-not (Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir | Out-Null
}

if (Test-Path $keyPath) {
    Remove-Item $keyPath -Force
}
if (Test-Path "$keyPath.pub") {
    Remove-Item "$keyPath.pub" -Force
}

Write-Host "Generating SSH key..."
& ssh-keygen -t ed25519 -C "hanbingjiuxing@users.noreply.github.com" -f $keyPath -N `""`""

if (Test-Path "$keyPath.pub") {
    Write-Host "SSH key generated successfully!"
    Write-Host "Public key:"
    Get-Content "$keyPath.pub"
} else {
    Write-Host "Failed to generate SSH key"
}