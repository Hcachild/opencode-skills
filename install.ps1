# install.ps1 — Install opencode-skills to ~/.config/opencode/skills/
# Usage:
#   .\install.ps1              # install all skills (symlink)
#   .\install.ps1 -Copy        # install all skills (copy)
#   .\install.ps1 -Project     # install to .opencode\skills\ (project-local)
#   .\install.ps1 -List        # list available skills
#   .\install.ps1 -Skill tdd   # install a single skill

param(
    [switch]$Copy,
    [switch]$Project,
    [switch]$List,
    [string]$Skill,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsDir = Join-Path $ScriptDir "skills"

if ($Help) {
    Write-Host "Usage: .\install.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Copy        Copy files instead of symlinking"
    Write-Host "  -Project     Install to .opencode\skills\ (project-local)"
    Write-Host "  -List        List available skills"
    Write-Host "  -Skill NAME  Install a single skill"
    Write-Host "  -Help        Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\install.ps1                    # Install all skills globally (symlink)"
    Write-Host "  .\install.ps1 -Copy              # Install all skills globally (copy)"
    Write-Host "  .\install.ps1 -Project           # Install to current project"
    Write-Host "  .\install.ps1 -Skill tdd         # Install only the 'tdd' skill"
    exit 0
}

if ($List) {
    Write-Host "Available skills:"
    Get-ChildItem $SkillsDir -Directory | Select-Object -ExpandProperty Name | Sort-Object
    exit 0
}

# Determine destination
if ($Project) {
    $Dest = ".opencode\skills"
} else {
    $Dest = Join-Path $env:USERPROFILE ".config\opencode\skills"
}

if (!(Test-Path $Dest)) {
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
}

# Gather skills to install
if ($Skill) {
    $src = Join-Path $SkillsDir $Skill
    if (!(Test-Path $src)) {
        Write-Host "Error: Skill '$Skill' not found in $SkillsDir" -ForegroundColor Red
        Write-Host "Run '.\install.ps1 -List' to see available skills."
        exit 1
    }
    $SkillsToInstall = @($Skill)
} else {
    $SkillsToInstall = Get-ChildItem $SkillsDir -Directory | Select-Object -ExpandProperty Name | Sort-Object
}

$mode = if ($Copy) { "copy" } else { "symlink" }
Write-Host "Installing $($SkillsToInstall.Count) skill(s) to $Dest (mode: $mode)"
Write-Host ""

$installed = 0
$skipped = 0

foreach ($s in $SkillsToInstall) {
    $src = Join-Path $SkillsDir $s
    $dst = Join-Path $Dest $s

    if (Test-Path $dst) {
        if ($Copy) {
            Remove-Item $dst -Recurse -Force
        } else {
            Write-Host "  SKIP  $s (already exists)"
            $skipped++
            continue
        }
    }

    if ($Copy) {
        Copy-Item $src $dst -Recurse -Force
        Write-Host "  COPY  $s"
    } else {
        # On Windows, symlinks require admin or Developer Mode
        try {
            New-Item -ItemType SymbolicLink -Path $dst -Target $src -ErrorAction Stop | Out-Null
            Write-Host "  LINK  $s"
        } catch {
            # Fallback to copy if symlink fails
            Copy-Item $src $dst -Recurse -Force
            Write-Host "  COPY  $s (symlink failed, copied instead)"
        }
    }
    $installed++
}

Write-Host ""
Write-Host "Done: $installed installed, $skipped skipped."

# Install Node.js dependencies for feishu-doc
$feishuDoc = Join-Path $Dest "feishu-doc-1.2.7"
if (Test-Path (Join-Path $feishuDoc "package.json")) {
    Write-Host ""
    Write-Host "Installing Node.js dependencies for feishu-doc-1.2.7..."
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($npm) {
        Push-Location $feishuDoc
        try { npm install --production } catch { Write-Host "  Warning: npm install failed" -ForegroundColor Yellow }
        Pop-Location
    } else {
        Write-Host "  Warning: npm not found. Run 'npm install' in $feishuDoc manually." -ForegroundColor Yellow
    }
}

# Remind about Python dependencies
Write-Host ""
Write-Host "NOTE: Some skills require Python dependencies."
Write-Host "  pip install -r requirements.txt"
Write-Host ""
Write-Host "Restart OpenCode for skills to take effect."
