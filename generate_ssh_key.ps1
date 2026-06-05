$sshDir = "$env:USERPROFILE\.ssh"
$keyPath = "$sshDir\id_ed25519"

if (-not (Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir | Out-Null
}

if (-not (Test-Path $keyPath)) {
    Write-Host "Generating SSH key..."
    $null = & ssh-keygen -t ed25519 -C "hanbingjiuxing@users.noreply.github.com" -f $keyPath
    Write-Host "SSH key generated successfully!"
} else {
    Write-Host "SSH key already exists."
}

if (Test-Path "$keyPath.pub") {
    Get-Content "$keyPath.pub"
} else {
    Write-Host "Public key file not found"
}