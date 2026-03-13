# Recreate Qdrant collections for qwen3-embedding:4b (2560 dims)
# Run this before re-ingesting with the new model

$ErrorActionPreference = "Stop"

$QDRANT_URL = "http://localhost:6333"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Qdrant Collection Recreation" -ForegroundColor Cyan
Write-Host "Model: qwen3-embedding:4b (2560 dims)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Function to delete collection if exists
function Delete-Collection {
    param([string]$collection)

    Write-Host "Checking collection: $collection"

    try {
        $response = Invoke-RestMethod -Uri "$QDRANT_URL/collections/$collection" -Method Get -ErrorAction SilentlyContinue
        if ($response.status -eq "ok") {
            Write-Host "  → Deleting existing collection..." -ForegroundColor Yellow
            Invoke-RestMethod -Uri "$QDRANT_URL/collections/$collection" -Method Delete | Out-Null
            Write-Host "  ✓ Deleted" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "  → Collection doesn't exist (OK)" -ForegroundColor Gray
    }
}

# Function to create collection
function Create-Collection {
    param(
        [string]$collection,
        [string]$description,
        [int]$vectorSize = 2560
    )

    Write-Host "Creating collection: $collection"
    Write-Host "  Description: $description"

    $body = @{
        vectors = @{
            size = $vectorSize
            distance = "Cosine"
        }
        optimizers_config = @{
            indexing_threshold = 10000
        }
        on_disk_payload = $true
    } | ConvertTo-Json -Depth 10

    $response = Invoke-RestMethod -Uri "$QDRANT_URL/collections/$collection" `
        -Method Put `
        -Body $body `
        -ContentType "application/json"

    if ($response.status -eq "ok") {
        Write-Host "  ✓ Created ($vectorSize dims, Cosine distance)" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ Failed: $($response | ConvertTo-Json)" -ForegroundColor Red
        throw "Collection creation failed"
    }
    Write-Host ""
}

# Function to create payload index
function Create-PayloadIndex {
    param(
        [string]$collection,
        [string]$field,
        [string]$schema
    )

    $body = @{
        field_name = $field
        field_schema = $schema
    } | ConvertTo-Json

    Invoke-RestMethod -Uri "$QDRANT_URL/collections/$collection/index" `
        -Method Put `
        -Body $body `
        -ContentType "application/json" | Out-Null
}

# Delete existing collections
Write-Host "Step 1: Deleting old collections" -ForegroundColor Yellow
Write-Host "-----------------------------------------"
Delete-Collection "arca_api_specs"
Delete-Collection "arca_dev_guides"
Delete-Collection "arca_setup_certs"
Delete-Collection "wikis"
Write-Host ""

Write-Host "Step 2: Creating collections" -ForegroundColor Yellow
Write-Host "-----------------------------------------"
Create-Collection "arca_api_specs" "ARCA API specifications, error codes, WSDL, validation rules" 2560
Create-Collection "arca_dev_guides" "Developer manuals, code examples, integration workflows" 2560
Create-Collection "arca_setup_certs" "Certificate setup procedures, environment configuration" 2560
Create-Collection "wikis" "General reference docs (Django, JWT, etc.)" 768

# Create payload indexes
Write-Host "Step 3: Creating payload indexes" -ForegroundColor Yellow
Write-Host "---------------------------------"

Write-Host "Creating indexes for arca_api_specs..."
Create-PayloadIndex "arca_api_specs" "ws_name" "keyword"
Create-PayloadIndex "arca_api_specs" "section" "text"
Create-PayloadIndex "arca_api_specs" "source_file" "keyword"
Write-Host "  ✓ arca_api_specs indexes created" -ForegroundColor Green

Write-Host "Creating indexes for arca_dev_guides..."
Create-PayloadIndex "arca_dev_guides" "ws_name" "keyword"
Create-PayloadIndex "arca_dev_guides" "section" "text"
Create-PayloadIndex "arca_dev_guides" "source_file" "keyword"
Write-Host "  ✓ arca_dev_guides indexes created" -ForegroundColor Green

Write-Host "Creating indexes for arca_setup_certs..."
Create-PayloadIndex "arca_setup_certs" "environment" "keyword"
Create-PayloadIndex "arca_setup_certs" "procedure_type" "keyword"
Create-PayloadIndex "arca_setup_certs" "source_file" "keyword"
Write-Host "  ✓ arca_setup_certs indexes created" -ForegroundColor Green

Write-Host "Creating indexes for wikis..."
Create-PayloadIndex "wikis" "topic" "keyword"
Create-PayloadIndex "wikis" "doc_type" "keyword"
Create-PayloadIndex "wikis" "source_file" "keyword"
Write-Host "  ✓ wikis indexes created" -ForegroundColor Green
Write-Host ""

# Verify collections
Write-Host "Step 4: Verifying collections" -ForegroundColor Yellow
Write-Host "------------------------------"
$response = Invoke-RestMethod -Uri "$QDRANT_URL/collections" -Method Get
foreach ($coll in $response.result.collections) {
    if ($coll.name -like "arca_*" -or $coll.name -eq "wikis") {
        $count = $coll.vectors_count ?? 0
        Write-Host "  ✓ $($coll.name): $count vectors" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "✓ Collections recreated successfully!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Verify Ollama has required models:"
Write-Host "   ollama list | findstr qwen3-embedding"
Write-Host "   ollama list | findstr nomic-embed-text"
Write-Host ""
Write-Host "2. Run ARCA re-ingestion (qwen3-embedding:4b, 2560 dims):"
Write-Host "   cd backend"
Write-Host "   python ..\scripts\qdrant\ingest_arca_qdrant.py --collection all"
Write-Host ""
Write-Host "3. Run wikis ingestion (nomic-embed-text, 768 dims):"
Write-Host "   python ..\scripts\qdrant\ingest_wikis_qdrant.py"
Write-Host ""
Write-Host "4. Benchmark ARCA model against baseline queries:"
Write-Host "   python ..\scripts\qdrant\benchmark_qdrant_search.py"
Write-Host ""
