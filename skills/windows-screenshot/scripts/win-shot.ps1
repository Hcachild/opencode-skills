[CmdletBinding()]
param(
  [ValidateSet('screen', 'window', 'region', 'list')]
  [string]$Mode = 'screen',
  [string]$Title,
  [string]$Process,
  [string]$Rect,
  [string]$Out,
  [int]$Padding = 0,
  [switch]$Clipboard,
  [switch]$PrintWindow
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Drawing, System.Windows.Forms

if (-not ('Shot.Native' -as [type])) {
  Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;

namespace Shot {
  public class Native {
    public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder sb, int max);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowTextLength(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT r);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int cmd);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdc, uint flags);
    [DllImport("dwmapi.dll")] public static extern int DwmGetWindowAttribute(IntPtr hWnd, int attr, out RECT value, int size);
    [DllImport("user32.dll")] public static extern IntPtr SetProcessDpiAwarenessContext(IntPtr ctx);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    public static void MakeDpiAware() {
      try { SetProcessDpiAwarenessContext(new IntPtr(-4)); } catch { }
    }

    public static System.Collections.Generic.List<IntPtr> Windows() {
      var list = new System.Collections.Generic.List<IntPtr>();
      EnumWindows(delegate(IntPtr h, IntPtr l) {
        if (IsWindowVisible(h) && GetWindowTextLength(h) > 0) list.Add(h);
        return true;
      }, IntPtr.Zero);
      return list;
    }

    public static RECT Frame(IntPtr h) {
      RECT r;
      if (DwmGetWindowAttribute(h, 9, out r, Marshal.SizeOf(typeof(RECT))) == 0 &&
          r.Right - r.Left > 0 && r.Bottom - r.Top > 0) return r;
      GetWindowRect(h, out r);
      return r;
    }
  }
}
'@
}

[Shot.Native]::MakeDpiAware()

function Get-WindowInfo {
  foreach ($h in [Shot.Native]::Windows()) {
    $len = [Shot.Native]::GetWindowTextLength($h)
    $sb = New-Object System.Text.StringBuilder ($len + 2)
    [void][Shot.Native]::GetWindowText($h, $sb, $sb.Capacity)
    $pidRef = [uint32]0
    [void][Shot.Native]::GetWindowThreadProcessId($h, [ref]$pidRef)
    $pname = ''
    try { $pname = (Get-Process -Id $pidRef -ErrorAction Stop).ProcessName } catch { }
    $r = New-Object Shot.Native+RECT
    [void][Shot.Native]::GetWindowRect($h, [ref]$r)
    [pscustomobject]@{
      Handle    = ('0x{0:X}' -f $h.ToInt64())
      Process   = $pname
      PID       = $pidRef
      Title     = $sb.ToString()
      X         = $r.Left
      Y         = $r.Top
      Width     = $r.Right - $r.Left
      Height    = $r.Bottom - $r.Top
      Minimized = [Shot.Native]::IsIconic($h)
    }
  }
}

function Test-AllBlack {
  param([System.Drawing.Bitmap]$Bitmap)
  $dark = 0; $total = 0
  $sx = [Math]::Max(1, [int]($Bitmap.Width / 16))
  $sy = [Math]::Max(1, [int]($Bitmap.Height / 16))
  for ($x = 0; $x -lt $Bitmap.Width; $x += $sx) {
    for ($y = 0; $y -lt $Bitmap.Height; $y += $sy) {
      $c = $Bitmap.GetPixel($x, $y)
      $total++
      if (($c.R + $c.G + $c.B) -lt 24) { $dark++ }
    }
  }
  return ($total -gt 0 -and ($dark / $total) -gt 0.97)
}

function Set-ClipboardImage {
  param([string]$Path)
  $tmp = Join-Path $env:TEMP ('shot-clip-{0}.ps1' -f [guid]::NewGuid().ToString('N'))
  $lines = @(
    'Add-Type -AssemblyName System.Windows.Forms, System.Drawing',
    "`$b = New-Object System.Drawing.Bitmap('$Path')",
    '[System.Windows.Forms.Clipboard]::SetImage($b)',
    'if ([System.Windows.Forms.Clipboard]::ContainsImage()) { "clipboard-ok" } else { "clipboard-fail" }'
  )
  Set-Content -LiteralPath $tmp -Value $lines -Encoding UTF8
  $res = & powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File $tmp 2>&1
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
  return ($res | Out-String).Trim()
}

function Save-Shot {
  param([System.Drawing.Bitmap]$Bitmap, [string]$Path, [string]$Method, [string]$Target)
  $dir = Split-Path -Parent $Path
  if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  $Bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
  $result = [ordered]@{
    path   = $Path
    width  = $Bitmap.Width
    height = $Bitmap.Height
    method = $Method
    target = $Target
    bytes  = (Get-Item -LiteralPath $Path).Length
  }
  $Bitmap.Dispose()
  if ($Clipboard) { $result.clipboard = Set-ClipboardImage -Path $Path }
  $result | ConvertTo-Json -Compress
}

if ($Mode -eq 'list') {
  Get-WindowInfo | Where-Object {
    ($Width -ne 0) -and
    (-not $Title -or $_.Title -match $Title) -and
    (-not $Process -or $_.Process -match $Process)
  } | Sort-Object Minimized, Process | Format-Table -AutoSize | Out-String -Width 200
  return
}

if (-not $Out) {
  $Out = Join-Path $env:TEMP ('shot-{0:yyyyMMdd-HHmmss}.png' -f (Get-Date))
}

if ($Mode -eq 'region') {
  if (-not $Rect) { throw 'region 模式需要 -Rect "x,y,w,h"' }
  $p = $Rect -split ','
  $x = [int]$p[0]; $y = [int]$p[1]; $w = [int]$p[2]; $h = [int]$p[3]
  if ($w -le 0 -or $h -le 0) { throw "非法区域: $Rect" }
  $bmp = New-Object System.Drawing.Bitmap $w, $h
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($x, $y, 0, 0, $bmp.Size)
  $g.Dispose()
  Save-Shot -Bitmap $bmp -Path $Out -Method 'region' -Target $Rect
  return
}

if ($Mode -eq 'screen') {
  $vs = [System.Windows.Forms.SystemInformation]::VirtualScreen
  $bmp = New-Object System.Drawing.Bitmap $vs.Width, $vs.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($vs.Left, $vs.Top, 0, 0, $bmp.Size)
  $g.Dispose()
  Save-Shot -Bitmap $bmp -Path $Out -Method 'screen' -Target ("{0},{1} {2}x{3}" -f $vs.Left, $vs.Top, $vs.Width, $vs.Height)
  return
}

if (-not $Title -and -not $Process) { throw 'window 模式需要 -Title <正则> 和/或 -Process <正则>' }
$match = Get-WindowInfo | Where-Object {
  ($_.Width -gt 0 -and $_.Height -gt 0) -and
  (-not $Title -or $_.Title -match $Title) -and
  (-not $Process -or $_.Process -match $Process)
} | Sort-Object Minimized | Select-Object -First 1
if (-not $match) { throw "没找到匹配窗口（Title='$Title' Process='$Process'），先运行 -Mode list 查看" }

$hWnd = [IntPtr]([Convert]::ToInt64($match.Handle, 16))

if ([Shot.Native]::IsIconic($hWnd)) {
  [void][Shot.Native]::ShowWindow($hWnd, 9)
  Start-Sleep -Milliseconds 400
}

$frame = [Shot.Native]::Frame($hWnd)
$w = $frame.Right - $frame.Left
$h = $frame.Bottom - $frame.Top
if ($w -le 0 -or $h -le 0) { throw "窗口尺寸异常: ${w}x${h}" }

$bmp = $null
$method = ''
if ($PrintWindow) {
  $bmp = New-Object System.Drawing.Bitmap $w, $h
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $hdc = $g.GetHdc()
  $ok = [Shot.Native]::PrintWindow($hWnd, $hdc, 2)
  $g.ReleaseHdc($hdc)
  $g.Dispose()
  if ($ok -and -not (Test-AllBlack -Bitmap $bmp)) {
    $method = 'printwindow'
  } else {
    $bmp.Dispose()
    $bmp = $null
  }
}

if (-not $bmp) {
  [void][Shot.Native]::SetForegroundWindow($hWnd)
  Start-Sleep -Milliseconds 350
  $frame = [Shot.Native]::Frame($hWnd)
  $x = $frame.Left - $Padding
  $y = $frame.Top - $Padding
  $w = $frame.Right - $frame.Left + 2 * $Padding
  $h = $frame.Bottom - $frame.Top + 2 * $Padding
  $bmp = New-Object System.Drawing.Bitmap $w, $h
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($x, $y, 0, 0, $bmp.Size)
  $g.Dispose()
  $method = 'screen-blt'
}

Save-Shot -Bitmap $bmp -Path $Out -Method $method -Target $match.Title
