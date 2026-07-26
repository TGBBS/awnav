$ErrorActionPreference = "Stop"

$root = "E:\awnav\awnav.com"
$blogSource = Join-Path $root "blog-site"
$blogDest = Join-Path $root "static\blog"
$hugo = Join-Path $root ".tmp-hugo\hugo.exe"

if (-not (Test-Path $hugo)) {
    throw "Hugo executable not found: $hugo"
}

if (-not (Test-Path $blogSource)) {
    throw "Blog source not found: $blogSource"
}

$resolvedRoot = (Resolve-Path $root).Path
$resolvedDestParent = (Resolve-Path (Split-Path $blogDest -Parent)).Path
if ($resolvedDestParent -ne (Join-Path $resolvedRoot "static")) {
    throw "Unexpected blog destination parent: $resolvedDestParent"
}

if (Test-Path $blogDest) {
    Get-ChildItem -LiteralPath $blogDest -Force | Remove-Item -Recurse -Force
} else {
    New-Item -ItemType Directory -Path $blogDest | Out-Null
}

& $hugo --source $blogSource --destination $blogDest
