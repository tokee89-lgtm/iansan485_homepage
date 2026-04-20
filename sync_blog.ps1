# sync_blog.ps1
$dataFile = "js/newsData.js"
$imageDir = "images/blog"
$rssUrl = "https://rss.blog.naver.com/iansan485.xml"

Write-Host "Creating directories..."
if (!(Test-Path $imageDir)) { New-Object -TypeName System.IO.DirectoryInfo -ArgumentList $imageDir | ForEach-Object { $_.Create() } }

Write-Host "Setting security protocol..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host "Fetching RSS..."
$wc = New-Object System.Net.WebClient
$wc.Headers.Add("User-Agent", "Mozilla/5.0")
try {
    $rssContent = $wc.DownloadString($rssUrl)
    Write-Host "RSS content received."
} catch {
    Write-Error "Failed to fetch RSS: $($_.Exception.Message)"
    exit
}

$xml = [xml]$rssContent

Write-Host "Loading existing newsData.js..."
$realPath = (Resolve-Path $dataFile).Path
$content = [System.IO.File]::ReadAllText($realPath, [System.Text.Encoding]::UTF8)
$jsonMatch = [regex]::Match($content, 'const newsData = (\[[\s\S]*?\]);')
if (!$jsonMatch.Success) {
    Write-Error "Could not find newsData array in $dataFile"
    exit
}
$existingData = $jsonMatch.Groups[1].Value | ConvertFrom-Json

$existingLinks = New-Object System.Collections.Generic.HashSet[string]
foreach ($item in $existingData) {
    if ($item.link) { 
        $link = $item.link -replace '\?.*$', ''
        [void]$existingLinks.Add($link) 
    }
}

$maxId = 0
foreach ($item in $existingData) {
    if ($item.id -gt $maxId) { $maxId = $item.id }
}

$items = @($xml.rss.channel.item)
[array]::Reverse($items)

$newPostsCount = 0
$updatedDataList = New-Object System.Collections.Generic.List[PSObject]

foreach ($item in $items) {
    $link = $item.link -replace '\?.*$', ''
    if ($existingLinks.Contains($link)) { continue }
    
    $title = $item.title
    Write-Host "Processing new post: $title"
    
    $dateStr = $item.pubDate
    try {
        $dt = [DateTime]::Parse($dateStr)
        $formattedDate = $dt.ToString("yyyy.MM.dd")
    } catch {
        $formattedDate = "Unknown"
    }
    
    $category = $item.category.'#cdata-section'
    if (!$category) { $category = $item.category }
    if (!$category) { $category = "알림마당" }
    
    $descRaw = $item.description.'#cdata-section'
    if (!$descRaw) { $descRaw = $item.description }

    # Handle image
    $imgMatch = [regex]::Match($descRaw, 'src=["''](https?://[^"'']+(?:jpg|jpeg|png|gif|JPEG|JPG|PNG)[^"'']*)["'']')
    $imgUrl = $imgMatch.Groups[1].Value
    $localImgRelPath = "images/static/notice_placeholder.png"
    
    if ($imgUrl) {
        $cleanImgUrl = $imgUrl -replace '\?.*$', ''
        $md5 = [System.Security.Cryptography.MD5]::Create()
        $hashBytes = $md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($cleanImgUrl))
        $hash12 = (($hashBytes | ForEach-Object { $_.ToString("x2") }) -join "").Substring(0, 12)
        $filename = "blog_$($hash12).jpg"
        $localImgPath = "$imageDir/$filename"
        $localImgRelPath = "images/blog/$filename"
        
        if (!(Test-Path $localImgPath)) {
            Write-Host "  Downloading image: $filename"
            try {
                $optUrl = $imgUrl -replace 'type=s3', 'type=w800' -replace 'type=w1', 'type=w800'
                $wc.DownloadFile($optUrl, $localImgPath)
            } catch {
                Write-Warning "  Failed download: $imgUrl"
            }
        }
    }

    $descText = $descRaw -replace '&lt;', '<' -replace '&gt;', '>' -replace '&quot;', '"' -replace '&amp;', '&'
    $textOnly = $descText -replace '<[^>]+>', ''
    $summary = if ($textOnly.Length -gt 120) { $textOnly.Substring(0, 120) + "..." } else { $textOnly }

    $maxId++
    $newPost = [PSCustomObject]@{
        id = $maxId
        category = $category
        title = $title
        date = $formattedDate
        image = $localImgRelPath
        summary = $summary
        content = $descText
        link = $item.link
    }
    $updatedDataList.Add($newPost)
    $newPostsCount++
}

if ($newPostsCount -gt 0) {
    # Combine (newest at front)
    $updatedDataList.Reverse()
    $finalArray = $updatedDataList + $existingData
    $json = ConvertTo-Json $finalArray -Depth 10
    
    # Write files
    $newJsContent = "const newsData = $json;`n"
    [System.IO.File]::WriteAllText($realPath, $newJsContent, [System.Text.Encoding]::UTF8)
    
    if (Test-Path "dist") {
        $distPath = (New-Object System.IO.FileInfo -ArgumentList "dist/js/newsData.js").FullName
        [System.IO.File]::WriteAllText($distPath, $newJsContent, [System.Text.Encoding]::UTF8)
        if (!(Test-Path "dist/images/blog")) { New-Item -ItemType Directory -Path "dist/images/blog" -Force }
        Copy-Item "$imageDir/*" "dist/images/blog/" -Force -ErrorAction SilentlyContinue
    }
    Write-Host "DONE! Added $newPostsCount items."
} else {
    Write-Host "No new items found."
}
