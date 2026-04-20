$dataFile = "js/newsData.js"
$imageDir = "images/blog"
$distDir = "dist"

if (!(Test-Path $imageDir)) { New-Item -ItemType Directory -Path $imageDir -Force }

# Force TLS 1.2 for modern web requests
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
} catch {}

Write-Host "Reading $dataFile..."
$realPath = (Resolve-Path $dataFile).Path
$content = [System.IO.File]::ReadAllText($realPath, [System.Text.Encoding]::UTF8)
$newContent = $content

# 1. Update main image fields
$regex = [regex]'"image":\s*"(https?://blogthumb\.pstatic\.net/[^"]+)"'
$matches = $regex.Matches($content)

Write-Host "Found $($matches.Count) remote images."

$count = 0
foreach ($m in $matches) {
    $fullUrl = $m.Groups[1].Value
    $cleanUrl = $fullUrl.Split('?')[0]
    
    $md5 = [System.Security.Cryptography.MD5]::Create()
    $hashBytes = $md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($cleanUrl))
    $hashString = ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""
    $hash12 = $hashString.Substring(0, 12)
    
    $ext = "jpg"
    if ($fullUrl -like "*png*") { $ext = "png" }
    elseif ($fullUrl -like "*gif*") { $ext = "gif" }
    
    $filename = "blog_$($hash12).$ext"
    $localPath = "$imageDir/$filename"
    $relPath = "images/blog/$filename"
    
    $success = $false
    if (!(Test-Path $localPath)) {
        Write-Host "Downloading [$($filename)] from [$($fullUrl)]"
        try {
            $headers = @{
                "User-Agent" = "Mozilla/5.0"
                "Referer" = "https://blog.naver.com/"
            }
            # Use the URL directly from RSS feed
            Invoke-WebRequest -Uri $fullUrl -OutFile $localPath -Headers $headers -TimeoutSec 15 -ErrorAction Stop
            if (Test-Path $localPath) {
                Write-Host "  OK"
                $success = $true
                Start-Sleep -Milliseconds 200
            }
        } catch {
            Write-Warning "  FAIL: $($_.Exception.Message)"
        }
    } else {
        $success = $true
    }
    
    if ($success) {
        $newContent = $newContent.Replace($fullUrl, $relPath)
        $count++
    }
}

# 2. Update inline content images
$regex2 = [regex]'src=\\"(https?://blogthumb\.pstatic\.net/[^"]+)\\"'
$matches2 = $regex2.Matches($newContent)
foreach ($m in $matches2) {
    $fullUrl = $m.Groups[1].Value
    $cleanUrl = $fullUrl.Split('?')[0]
    
    $md5 = [System.Security.Cryptography.MD5]::Create()
    $hashBytes = $md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($cleanUrl))
    $hashString = ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""
    $hash12 = $hashString.Substring(0, 12)
    
    $ext = "jpg"
    if ($fullUrl -like "*png*") { $ext = "png" }
    $filename = "blog_$($hash12).$ext"
    $localPath = "$imageDir/$filename"
    $relPath = "images/blog/$filename"
    
    if (Test-Path $localPath) {
        $newContent = $newContent.Replace($fullUrl, $relPath)
    }
}

if ($count -gt 0) {
    Write-Host "Saving changes ($count updates)..."
    [System.IO.File]::WriteAllText($realPath, $newContent, [System.Text.Encoding]::UTF8)

    $distDataPath = "$distDir/$dataFile"
    if (Test-Path (Split-Path $distDataPath)) {
        [System.IO.File]::WriteAllText($distDataPath, $newContent, [System.Text.Encoding]::UTF8)
    }
    # Also sync all images to dist
    if (Test-Path $distDir) {
        Copy-Item "$imageDir/*" "$distDir/$imageDir/" -Force -ErrorAction SilentlyContinue
    }
    Write-Host "DONE!"
} else {
    Write-Host "No changes were made."
}
