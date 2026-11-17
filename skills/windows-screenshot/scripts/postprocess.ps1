[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$In,
  [string]$Out,
  [string]$Crop,
  [string]$Box,
  [string]$Zoom,
  [double]$Scale = 0,
  [switch]$Clipboard
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Drawing, System.Windows.Forms

if (-not (Test-Path -LiteralPath $In)) { throw "输入不存在: $In" }
if (-not $Out) {
  $dir = Split-Path -Parent (Resolve-Path -LiteralPath $In)
  $name = [IO.Path]::GetFileNameWithoutExtension($In)
  $Out = Join-Path $dir ("{0}-edit-{1:HHmmss}.png" -f $name, (Get-Date))
}

$src = [System.Drawing.Bitmap]::FromFile((Resolve-Path -LiteralPath $In))
$current = $src

if ($Crop) {
  $p = $Crop -split ','
  $r = New-Object System.Drawing.Rectangle ([int]$p[0]), ([int]$p[1]), ([int]$p[2]), ([int]$p[3])
  $r.Intersect((New-Object System.Drawing.Rectangle 0, 0, $current.Width, $current.Height))
  if ($r.Width -le 0 -or $r.Height -le 0) { throw "Crop 区域无效: $Crop" }
  $cropped = $current.Clone($r, $current.PixelFormat)
  if ($current -ne $src) { $current.Dispose() }
  $current = $cropped
}

$canvas = New-Object System.Drawing.Bitmap $current.Width, $current.Height
$g = [System.Drawing.Graphics]::FromImage($canvas)
$g.SmoothingMode = 'AntiAlias'
$g.TextRenderingHint = 'ClearTypeGridFit'
$g.DrawImage($current, 0, 0, $current.Width, $current.Height)

$red = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 255, 45, 85)), 4
$font = New-Object System.Drawing.Font "Microsoft YaHei UI", 13, ([System.Drawing.FontStyle]::Bold)

if ($Box) {
  foreach ($item in ($Box -split ';')) {
    if (-not $item.Trim()) { continue }
    $parts = $item -split ':'
    $c = $parts[0] -split ','
    $label = if ($parts.Count -gt 1) { $parts[1] } else { '' }
    $x = [int]$c[0]; $y = [int]$c[1]; $w = [int]$c[2]; $h = [int]$c[3]
    $g.DrawRectangle($red, $x, $y, $w, $h)
    if ($label) {
      $size = $g.MeasureString($label, $font)
      $ty = $y - $size.Height - 8
      if ($ty -lt 0) { $ty = $y + 4 }
      $g.FillRectangle((New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 255, 45, 85))), $x, $ty, ($size.Width + 16), ($size.Height + 4))
      $g.DrawString($label, $font, [System.Drawing.Brushes]::White, ($x + 8), ($ty + 2))
    }
  }
}

if ($Zoom) {
  $parts = $Zoom -split ':'
  $c = $parts[0] -split ','
  $factor = if ($parts.Count -gt 1) { [double]$parts[1] } else { 2 }
  $r = New-Object System.Drawing.Rectangle ([int]$c[0]), ([int]$c[1]), ([int]$c[2]), ([int]$c[3])
  $r.Intersect((New-Object System.Drawing.Rectangle 0, 0, $canvas.Width, $canvas.Height))
  if ($r.Width -le 0 -or $r.Height -le 0) { throw "Zoom 区域无效: $Zoom" }

  $margin = 16
  $maxW = $canvas.Width - 2 * $margin
  $zw = [int]($r.Width * $factor)
  $zh = [int]($r.Height * $factor)
  if ($zw -gt $maxW) {
    $factor = $maxW / $r.Width
    $zw = $maxW
    $zh = [int]($r.Height * $factor)
  }

  $zoomBmp = New-Object System.Drawing.Bitmap $zw, $zh
  $zoomG = [System.Drawing.Graphics]::FromImage($zoomBmp)
  $zoomG.InterpolationMode = 'HighQualityBicubic'
  $zoomG.PixelOffsetMode = 'HighQuality'
  $zoomG.DrawImage($canvas, (New-Object System.Drawing.Rectangle 0, 0, $zw, $zh), $r, [System.Drawing.GraphicsUnit]::Pixel)
  $zoomG.Dispose()

  $pad = 12
  $panelH = $zh + 2 * $pad + 30
  $panelX = [int](($canvas.Width - $zw) / 2 - $pad)
  $panelY = [int]($canvas.Height - $panelH - 20)
  $panelW = $zw + 2 * $pad
  $g.FillRectangle((New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 28, 28, 30))), $panelX, $panelY, $panelW, $panelH)
  $g.DrawImage($zoomBmp, ($panelX + $pad), ($panelY + $pad), $zw, $zh)
  $g.DrawRectangle($red, ($panelX + $pad), ($panelY + $pad), $zw, $zh)
  $caption = ('放大 {0:0.##}x' -f [Math]::Round($factor, 2))
  $g.DrawString($caption, $font, [System.Drawing.Brushes]::White, ($panelX + $pad), ($panelY + $pad + $zh + 2))

  $arrowPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 255, 45, 85)), 3
  $arrowPen.CustomEndCap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap 5, 7
  $startX = [int]($r.X + $r.Width / 2)
  $startY = [int]($r.Y + $r.Height)
  $g.DrawLine($arrowPen, $startX, ($startY + 4), [int]($panelX + $panelW / 2), ($panelY - 8))

  $zoomBmp.Dispose()
}

$g.Dispose()
if ($current -ne $src) { $current.Dispose() }
$src.Dispose()

$final = $canvas
if ($Scale -gt 0 -and $Scale -ne 1) {
  $nw = [int]([Math]::Round($canvas.Width * $Scale))
  $nh = [int]([Math]::Round($canvas.Height * $Scale))
  $scaled = New-Object System.Drawing.Bitmap $nw, $nh
  $sg = [System.Drawing.Graphics]::FromImage($scaled)
  $sg.InterpolationMode = 'HighQualityBicubic'
  $sg.DrawImage($canvas, 0, 0, $nw, $nh)
  $sg.Dispose()
  $canvas.Dispose()
  $final = $scaled
}

$dir = Split-Path -Parent $Out
if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
$final.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$result = [ordered]@{
  path   = $Out
  width  = $final.Width
  height = $final.Height
  bytes  = (Get-Item -LiteralPath $Out).Length
}
$final.Dispose()

if ($Clipboard) {
  $tmp = Join-Path $env:TEMP ('shot-clip-{0}.ps1' -f [guid]::NewGuid().ToString('N'))
  $lines = @(
    'Add-Type -AssemblyName System.Windows.Forms, System.Drawing',
    "`$b = New-Object System.Drawing.Bitmap('$Out')",
    '[System.Windows.Forms.Clipboard]::SetImage($b)',
    'if ([System.Windows.Forms.Clipboard]::ContainsImage()) { "clipboard-ok" } else { "clipboard-fail" }'
  )
  Set-Content -LiteralPath $tmp -Value $lines -Encoding UTF8
  $result.clipboard = ((& powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File $tmp 2>&1) | Out-String).Trim()
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}

$result | ConvertTo-Json -Compress

