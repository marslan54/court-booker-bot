param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("setup", "run", "test", "lint", "ci", "docker-build", "docker-run")]
    [string]$Task
)

switch ($Task) {
    "setup" {
        python -m venv .venv
        .\.venv\Scripts\Activate.ps1
        python -m pip install -r requirements.txt
        playwright install chromium
    }
    "run" { python main.py }
    "test" { python -m pytest }
    "lint" { python -m flake8 . }
    "ci" {
        python -m flake8 .
        if ($LASTEXITCODE -eq 0) { python -m pytest }
    }
    "docker-build" { docker build -t courtbooker-bot . }
    "docker-run" { docker compose up --build }
}
