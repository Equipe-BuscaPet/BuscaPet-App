<#
Sobe o BuscaPet inteiro em Docker com um comando e deixa pronto para a demonstração:
banco, núcleo OpenCL, API e interface, migrações, dados de demonstração e descritores das fotos.

Uso (PowerShell, na pasta do projeto):    .\iniciar-demo.ps1
Para parar:                               docker compose down      (os dados ficam guardados)

Pode rodar de novo quando quiser: o que já existe é mantido.
#>
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Passo($texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }
# O Docker escreve o progresso em stderr; no PowerShell 5.1 isso viraria erro, então só o código de saída vale.
function Executar {
    $ErrorActionPreference = "Continue"
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Falhou: docker $($args -join ' ')" }
}

Passo "Conferindo o Docker"
$ErrorActionPreference = "Continue"
& docker info *> $null
$ErrorActionPreference = "Stop"
if ($LASTEXITCODE -ne 0) { throw "O Docker não está rodando. Abra o Docker Desktop, espere ele ficar verde e rode de novo." }

if (-not (Test-Path .env)) {
    Passo "Criando o arquivo .env (não vai para o Git)"
    $segredo = -join ((48..57) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
    @(
        "DATABASE_URL=postgresql+psycopg://buscapet:buscapet@db:5432/buscapet",
        "JWT_SECRET=$segredo",
        "NUCLEO_OPENCL_URL=http://nucleo-opencl:8001"
    ) | Set-Content -Encoding ascii .env
}

Passo "Subindo banco, núcleo OpenCL, API e interface (a primeira vez demora, o núcleo tem ~850 MB)"
Executar compose up -d --build db nucleo-opencl api frontend

Passo "Esperando o banco ficar pronto"
for ($i = 0; $i -lt 30; $i++) {
    & docker compose exec -T db pg_isready -U buscapet *> $null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 2
}

Passo "Criando as tabelas (migrações)"
Executar compose exec -T api alembic upgrade head

Passo "Criando os dados de demonstração (contas, abrigos, animais, perdidos e avistamentos)"
Executar compose exec -T api python -m app.scripts.popular_demo

Passo "Calculando os descritores das fotos no núcleo OpenCL"
for ($i = 0; $i -lt 15; $i++) {
    try { Invoke-RestMethod http://localhost:8001/saude | Out-Null; break } catch { Start-Sleep -Seconds 2 }
}
Executar compose exec -T api python -m app.scripts.indexar_fotos

Write-Host "`nPronto!" -ForegroundColor Green
Write-Host "  Interface:  http://localhost:5173"
Write-Host "  API (docs): http://localhost:8000/docs"
Write-Host "  Contas:     maria@exemplo.com, joao@exemplo.com, patinhas@exemplo.com, amigofiel@exemplo.com, admin@exemplo.com"
Write-Host "  Senha de todas: Senha1234!"
