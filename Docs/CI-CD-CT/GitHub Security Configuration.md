# 🔒 Configuración de Seguridad y Permisos - GitHub

## 📋 Tabla de Contenidos
1. [Configuración de Branch Protection](#configuración-de-branch-protection)
2. [Gestión de Permisos y Colaboradores](#gestión-de-permisos-y-colaboradores)
3. [CODEOWNERS Configuration](#codeowners-configuration)
4. [Configuración mediante GitHub UI](#configuración-mediante-github-ui)
5. [Configuración mediante GitHub CLI](#configuración-mediante-github-cli)
6. [Configuración mediante API](#configuración-mediante-api)
7. [Matriz de Permisos](#matriz-de-permisos)
8. [Scripts de Automatización](#scripts-de-automatización)

---

## 🛡️ Configuración de Branch Protection

### Protección para `main` (Producción)

#### Reglas Estrictas - Solo Admin (Bruno)

```yaml
Branch: main
Protection Rules:
  ✅ Require a pull request before merging
    - Required approvals: 1 (mínimo)
    - Dismiss stale PR approvals when new commits are pushed: ✅
    - Require review from CODEOWNERS: ✅
    - Restrict who can dismiss PR reviews: Only Admin

  ✅ Require status checks to pass before merging
    - Status checks required:
      - continuous-integration/github-actions
      - build
      - test
      - lint
    - Require branches to be up to date: ✅

  ✅ Require conversation resolution before merging

  ✅ Require signed commits: ✅

  ✅ Include administrators: ❌ (permite bypass al admin)

  ✅ Restrict who can push to matching branches
    - Users: Bruno-Ghiberto (solo tú)
    - Teams: None
    - Apps: github-actions[bot] (para CI/CD)

  ✅ Allow force pushes: ❌
  ✅ Allow deletions: ❌
  ✅ Lock branch: ❌
  ✅ Require linear history: ✅
```

### Protección para `develop` (Integración)

#### Reglas Moderadas - Control del Admin

```yaml
Branch: develop
Protection Rules:
  ✅ Require a pull request before merging
    - Required approvals: 1
    - Dismiss stale PR approvals: ✅
    - Require review from CODEOWNERS: ✅
    - Restrict who can dismiss: Admin only

  ✅ Require status checks to pass
    - Required checks:
      - test
      - lint
    - Require up to date: ✅

  ✅ Require conversation resolution: ✅

  ✅ Include administrators: ❌

  ✅ Restrict who can push
    - Users: Bruno-Ghiberto
    - Teams: None
    - Apps: github-actions[bot]

  ✅ Allow force pushes: ❌
  ✅ Allow deletions: ❌
  ✅ Require linear history: ❌
```

### Protección para `feature/*` branches

#### Reglas Flexibles - Por Desarrollador

```yaml
Pattern: feature/*
Protection Rules:
  ✅ Allow specific users to push
    - feature/inventory-backend: Bruno-Ghiberto
    - feature/inventory-frontend: [frontend-dev-username]
    - feature/inventory-database: [database-dev-username]

  ✅ Require status checks: ❌ (opcional)
  ✅ Allow force pushes: ✅ (solo el owner)
  ✅ Allow deletions: ✅ (solo el owner)
```

---

## 👥 Gestión de Permisos y Colaboradores

### Niveles de Acceso en GitHub

| Nivel | Permisos | Asignado a |
|-------|----------|------------|
| **Admin** | Todo (incluye settings, delete repo) | Bruno (Owner) |
| **Maintain** | Gestión sin settings críticos | - |
| **Write** | Push a ramas no protegidas, crear PRs | Desarrolladores |
| **Triage** | Gestionar issues y PRs sin código | QA/Testers |
| **Read** | Solo lectura | Stakeholders |

### Asignación de Colaboradores

#### Via GitHub UI
```
1. Settings → Manage access → Invite a collaborator
2. Buscar por username o email
3. Seleccionar rol:
   - Write: Para desarrolladores
   - Read: Para observadores
4. Send invitation
```

#### Via GitHub CLI
```bash
# Instalar GitHub CLI
brew install gh  # macOS
choco install gh # Windows

# Autenticar
gh auth login

# Agregar colaborador con permisos Write
gh api repos/Bruno-Ghiberto/GRAVITEA-ERP/collaborators/USERNAME \
  --method PUT \
  --field permission='push'

# Permisos disponibles: pull (read), push (write), admin, maintain, triage
```

---

## 📝 CODEOWNERS Configuration

Crear archivo `.github/CODEOWNERS`:

```bash
# CODEOWNERS - Define quién debe revisar qué código
# Formato: pattern owner

# Global owners (todo el código)
* @Bruno-Ghiberto

# Backend - Solo Bruno puede aprobar
/backend/ @Bruno-Ghiberto
/backend/**/*.js @Bruno-Ghiberto
/backend/**/*.py @Bruno-Ghiberto

# Frontend - Frontend dev debe revisar
/frontend/ @frontend-developer-username
/frontend/**/*.jsx @frontend-developer-username
/frontend/**/*.css @frontend-developer-username

# Database - Database dev debe revisar
/database/ @database-developer-username
/database/**/*.sql @database-developer-username
/database/migrations/ @database-developer-username

# Documentación - Bruno revisa
/Docs/ @Bruno-Ghiberto
*.md @Bruno-Ghiberto

# Configuración crítica - Solo admin
/.github/ @Bruno-Ghiberto
/package.json @Bruno-Ghiberto
/package-lock.json @Bruno-Ghiberto
/.env.example @Bruno-Ghiberto

# DevOps - Admin only
/docker-compose.yml @Bruno-Ghiberto
/Dockerfile @Bruno-Ghiberto
/.github/workflows/ @Bruno-Ghiberto
```

---

## 🖱️ Configuración mediante GitHub UI

### Paso a Paso con Screenshots

#### 1. Acceder a Settings
```
Repositorio → Settings → Branches
```

#### 2. Agregar Branch Protection Rule
```
1. Click "Add rule"
2. Branch name pattern: main
3. Configurar las opciones según la sección anterior
4. Click "Create"
```

#### 3. Configuración Detallada para `main`

**Require a pull request before merging:**
- ✅ Activar
- Required approving reviews: 1
- ✅ Dismiss stale pull request approvals
- ✅ Require review from CODEOWNERS
- ✅ Restrict who can dismiss pull request reviews
  - Search: Bruno-Ghiberto

**Require status checks:**
- ✅ Activar
- Search checks:
  - build
  - test
  - lint
- ✅ Require branches to be up to date

**Require conversation resolution:**
- ✅ Activar

**Require signed commits:**
- ✅ Activar (recomendado)

**Include administrators:**
- ❌ Desactivar (permite que puedas hacer bypass como admin)

**Restrict who can push:**
- ✅ Activar
- Add people: Bruno-Ghiberto
- Add apps: github-actions[bot]

**Rules at bottom:**
- ❌ Allow force pushes
- ❌ Allow deletions
- ✅ Require linear history

#### 4. Repetir para `develop`
Similar pero con reglas menos estrictas

---

## 💻 Configuración mediante GitHub CLI

### Script Completo de Configuración

```bash
#!/bin/bash
# setup-branch-protection.sh

REPO="Bruno-Ghiberto/GRAVITEA-ERP"
ADMIN="Bruno-Ghiberto"

# Configurar protección para main
echo "🔒 Configurando protección para main..."
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/$REPO/branches/main/protection \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["build", "test", "lint"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismissal_restrictions": {
      "users": ["$ADMIN"],
      "teams": []
    },
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1,
    "bypass_pull_request_allowances": {
      "users": ["$ADMIN"],
      "teams": []
    }
  },
  "restrictions": {
    "users": ["$ADMIN"],
    "teams": [],
    "apps": ["github-actions"]
  },
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": false
}
EOF

echo "✅ main configurado"

# Configurar protección para develop
echo "🔒 Configurando protección para develop..."
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/$REPO/branches/develop/protection \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["test", "lint"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismissal_restrictions": {
      "users": ["$ADMIN"],
      "teams": []
    },
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": {
    "users": ["$ADMIN"],
    "teams": [],
    "apps": ["github-actions"]
  },
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
EOF

echo "✅ develop configurado"
```

### Agregar Colaboradores via CLI

```bash
#!/bin/bash
# add-collaborators.sh

REPO="Bruno-Ghiberto/GRAVITEA-ERP"

# Función para agregar colaborador
add_collaborator() {
  local username=$1
  local permission=$2

  echo "➕ Agregando $username con permisos $permission..."

  gh api \
    --method PUT \
    -H "Accept: application/vnd.github+json" \
    /repos/$REPO/collaborators/$username \
    -f permission="$permission"

  echo "✅ $username agregado"
}

# Agregar desarrolladores
add_collaborator "frontend-dev-username" "push"  # Write access
add_collaborator "database-dev-username" "push"  # Write access
add_collaborator "qa-tester-username" "triage"   # Triage access
add_collaborator "stakeholder-username" "pull"   # Read access
```

---

## 🔑 Configuración mediante API

### Usando cURL directamente

```bash
# Obtener token en: Settings → Developer settings → Personal access tokens

TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
REPO="Bruno-Ghiberto/GRAVITEA-ERP"

# Proteger main
curl \
  -X PUT \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $TOKEN" \
  https://api.github.com/repos/$REPO/branches/main/protection \
  -d @protection-main.json

# protection-main.json
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["continuous-integration/github-actions"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismissal_restrictions": {
      "users": ["Bruno-Ghiberto"]
    },
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": {
    "users": ["Bruno-Ghiberto"],
    "teams": []
  },
  "allow_force_pushes": false,
  "allow_deletions": false
}
```

### Script Python para Configuración

```python
#!/usr/bin/env python3
# github_security_setup.py

import requests
import json

# Configuración
TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxx"  # Tu token
OWNER = "Bruno-Ghiberto"
REPO = "GRAVITEA-ERP"
BASE_URL = f"https://api.github.com/repos/{OWNER}/{REPO}"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json"
}

def protect_branch(branch_name, protection_rules):
    """Proteger una rama con reglas específicas"""
    url = f"{BASE_URL}/branches/{branch_name}/protection"

    response = requests.put(url, headers=headers, json=protection_rules)

    if response.status_code == 200:
        print(f"✅ {branch_name} protegida exitosamente")
    else:
        print(f"❌ Error protegiendo {branch_name}: {response.text}")

    return response

def add_collaborator(username, permission="push"):
    """Agregar colaborador con permisos específicos"""
    url = f"{BASE_URL}/collaborators/{username}"

    response = requests.put(
        url,
        headers=headers,
        json={"permission": permission}
    )

    if response.status_code in [201, 204]:
        print(f"✅ {username} agregado con permisos {permission}")
    else:
        print(f"❌ Error agregando {username}: {response.text}")

    return response

# Reglas para main
main_protection = {
    "required_status_checks": {
        "strict": True,
        "contexts": ["build", "test", "lint"]
    },
    "enforce_admins": False,
    "required_pull_request_reviews": {
        "dismissal_restrictions": {
            "users": ["Bruno-Ghiberto"],
            "teams": []
        },
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": True,
        "required_approving_review_count": 1
    },
    "restrictions": {
        "users": ["Bruno-Ghiberto"],
        "teams": [],
        "apps": []
    },
    "required_linear_history": True,
    "allow_force_pushes": False,
    "allow_deletions": False,
    "required_conversation_resolution": True
}

# Reglas para develop
develop_protection = {
    "required_status_checks": {
        "strict": True,
        "contexts": ["test", "lint"]
    },
    "enforce_admins": False,
    "required_pull_request_reviews": {
        "dismissal_restrictions": {
            "users": ["Bruno-Ghiberto"]
        },
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": True,
        "required_approving_review_count": 1
    },
    "restrictions": {
        "users": ["Bruno-Ghiberto"],
        "teams": []
    },
    "allow_force_pushes": False,
    "allow_deletions": False,
    "required_conversation_resolution": True
}

if __name__ == "__main__":
    print("🔒 Configurando seguridad del repositorio...")

    # Proteger ramas
    protect_branch("main", main_protection)
    protect_branch("develop", develop_protection)

    # Agregar colaboradores (reemplazar con usernames reales)
    # add_collaborator("frontend-dev", "push")
    # add_collaborator("database-dev", "push")
    # add_collaborator("qa-tester", "triage")

    print("✅ Configuración completada")
```

---

## 📊 Matriz de Permisos

### Permisos por Rama y Usuario

| Rama/Acción | Bruno (Admin) | Frontend Dev | Database Dev | QA/Testers | Otros |
|-------------|---------------|--------------|--------------|------------|-------|
| **main** |
| View | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create PR | ✅ | ✅ | ✅ | ❌ | ❌ |
| Push Direct | ✅ | ❌ | ❌ | ❌ | ❌ |
| Merge PR | ✅ | ❌ | ❌ | ❌ | ❌ |
| Delete | ❌ | ❌ | ❌ | ❌ | ❌ |
| **develop** |
| View | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create PR | ✅ | ✅ | ✅ | ❌ | ❌ |
| Push Direct | ✅ | ❌ | ❌ | ❌ | ❌ |
| Merge PR | ✅ | ❌ | ❌ | ❌ | ❌ |
| Delete | ❌ | ❌ | ❌ | ❌ | ❌ |
| **feature/inventory-backend** |
| View | ✅ | ✅ | ✅ | ✅ | ✅ |
| Push | ✅ | ❌ | ❌ | ❌ | ❌ |
| Force Push | ✅ | ❌ | ❌ | ❌ | ❌ |
| Delete | ✅ | ❌ | ❌ | ❌ | ❌ |
| **feature/inventory-frontend** |
| View | ✅ | ✅ | ✅ | ✅ | ✅ |
| Push | ✅ | ✅ | ❌ | ❌ | ❌ |
| Force Push | ✅ | ✅ | ❌ | ❌ | ❌ |
| Delete | ✅ | ✅ | ❌ | ❌ | ❌ |
| **feature/inventory-database** |
| View | ✅ | ✅ | ✅ | ✅ | ✅ |
| Push | ✅ | ❌ | ✅ | ❌ | ❌ |
| Force Push | ✅ | ❌ | ✅ | ❌ | ❌ |
| Delete | ✅ | ❌ | ✅ | ❌ | ❌ |

### Permisos de PR y Review

| Acción | Bruno | Developers | QA | Otros |
|--------|-------|------------|-----|-------|
| Crear PR | ✅ | ✅ | ❌ | ❌ |
| Comentar PR | ✅ | ✅ | ✅ | ✅ |
| Aprobar PR | ✅ | ✅ | ❌ | ❌ |
| Merge PR to main | ✅ | ❌ | ❌ | ❌ |
| Merge PR to develop | ✅ | ❌ | ❌ | ❌ |
| Dismiss Review | ✅ | ❌ | ❌ | ❌ |
| Re-request Review | ✅ | ✅ | ❌ | ❌ |

---

## 🔧 Scripts de Automatización

### Script Completo de Setup Inicial

```bash
#!/bin/bash
# complete-security-setup.sh

set -e  # Exit on error

echo "🚀 Iniciando configuración de seguridad completa..."

# Variables
REPO="Bruno-Ghiberto/GRAVITEA-ERP"
ADMIN="Bruno-Ghiberto"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir con color
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Verificar gh CLI instalado
if ! command -v gh &> /dev/null; then
    print_error "GitHub CLI no está instalado"
    echo "Instalar con: brew install gh (macOS) o choco install gh (Windows)"
    exit 1
fi

# Verificar autenticación
if ! gh auth status &> /dev/null; then
    print_error "No estás autenticado en GitHub CLI"
    echo "Ejecuta: gh auth login"
    exit 1
fi

# 1. Crear CODEOWNERS
print_status "Creando archivo CODEOWNERS..."
mkdir -p .github
cat > .github/CODEOWNERS << 'EOF'
# CODEOWNERS
* @Bruno-Ghiberto
/backend/ @Bruno-Ghiberto
/frontend/ @frontend-developer
/database/ @database-developer
/Docs/ @Bruno-Ghiberto
/.github/ @Bruno-Ghiberto
EOF
print_status "CODEOWNERS creado"

# 2. Configurar Branch Protection para main
print_status "Configurando protección para rama main..."
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/$REPO/branches/main/protection \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["build", "test", "lint"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismissal_restrictions": {
      "users": ["$ADMIN"]
    },
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": {
    "users": ["$ADMIN"],
    "teams": []
  },
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
EOF
print_status "Rama main protegida"

# 3. Configurar Branch Protection para develop
print_status "Configurando protección para rama develop..."
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/$REPO/branches/develop/protection \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["test", "lint"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismissal_restrictions": {
      "users": ["$ADMIN"]
    },
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": {
    "users": ["$ADMIN"],
    "teams": []
  },
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
EOF
print_status "Rama develop protegida"

# 4. Crear GitHub Actions para validación
print_status "Creando workflows de GitHub Actions..."
mkdir -p .github/workflows

cat > .github/workflows/protection.yml << 'EOF'
name: Branch Protection Check

on:
  pull_request:
    branches: [main, develop]

jobs:
  check-protection:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check PR Author
        run: |
          echo "PR Author: ${{ github.event.pull_request.user.login }}"
          echo "Target Branch: ${{ github.base_ref }}"

      - name: Validate Permissions
        if: github.base_ref == 'main' || github.base_ref == 'develop'
        run: |
          if [[ "${{ github.event.pull_request.user.login }}" != "Bruno-Ghiberto" ]]; then
            if [[ "${{ github.base_ref }}" == "main" ]]; then
              echo "⚠️ Solo el administrador puede hacer merge a main"
            fi
          fi
EOF
print_status "Workflows creados"

# 5. Resumen
echo ""
echo "========================================="
print_status "CONFIGURACIÓN COMPLETADA"
echo "========================================="
echo ""
echo "📋 Resumen de cambios:"
echo "  • main: Protegida - Solo $ADMIN puede hacer merge"
echo "  • develop: Protegida - Solo $ADMIN puede hacer merge"
echo "  • CODEOWNERS: Configurado para revisiones obligatorias"
echo "  • GitHub Actions: Workflow de validación creado"
echo ""
echo "📝 Próximos pasos:"
echo "  1. Commit y push estos cambios"
echo "  2. Ir a Settings → Branches en GitHub"
echo "  3. Verificar las reglas aplicadas"
echo "  4. Agregar colaboradores en Settings → Manage access"
echo ""
print_warning "Recuerda agregar los usernames reales de tu equipo en CODEOWNERS"
```

### Script para Verificar Configuración

```bash
#!/bin/bash
# verify-security.sh

REPO="Bruno-Ghiberto/GRAVITEA-ERP"

echo "🔍 Verificando configuración de seguridad..."

# Verificar protección de main
echo ""
echo "📌 Estado de rama main:"
gh api \
  -H "Accept: application/vnd.github+json" \
  /repos/$REPO/branches/main/protection \
  | jq '{
    required_approvals: .required_pull_request_reviews.required_approving_review_count,
    require_code_owner: .required_pull_request_reviews.require_code_owner_reviews,
    dismiss_stale: .required_pull_request_reviews.dismiss_stale_reviews,
    restricted_push_users: .restrictions.users,
    allow_force_push: .allow_force_pushes,
    allow_deletions: .allow_deletions
  }'

# Verificar protección de develop
echo ""
echo "📌 Estado de rama develop:"
gh api \
  -H "Accept: application/vnd.github+json" \
  /repos/$REPO/branches/develop/protection \
  | jq '{
    required_approvals: .required_pull_request_reviews.required_approving_review_count,
    require_code_owner: .required_pull_request_reviews.require_code_owner_reviews,
    restricted_push_users: .restrictions.users
  }'

# Listar colaboradores
echo ""
echo "👥 Colaboradores actuales:"
gh api \
  -H "Accept: application/vnd.github+json" \
  /repos/$REPO/collaborators \
  | jq '.[] | {username: .login, permissions: .permissions}'
```

---

## 🚨 Comandos de Emergencia

### Desactivar Protección Temporalmente

```bash
# Solo en emergencias - Desactivar protección de main
gh api \
  --method DELETE \
  -H "Accept: application/vnd.github+json" \
  /repos/$REPO/branches/main/protection

# Reactivar después con el script de setup
```

### Bypass de Admin

Si necesitas hacer push directo como admin:

```bash
# Opción 1: Desactivar temporalmente "Include administrators"
# En GitHub UI: Settings → Branches → main → Edit → Uncheck "Include administrators"

# Opción 2: Force push (PELIGROSO)
git push --force-with-lease origin main

# Opción 3: Crear PR y auto-aprobar
gh pr create --title "Emergency fix" --body "Critical fix"
gh pr review --approve
gh pr merge --admin
```

---

## 📚 Documentación Adicional

- [GitHub Docs - Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- [GitHub API - Branch Protection](https://docs.github.com/en/rest/branches/branch-protection)
- [CODEOWNERS Syntax](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub CLI Documentation](https://cli.github.com/manual/)

---

## ✅ Checklist de Implementación

- [ ] Configurar Branch Protection para `main`
- [ ] Configurar Branch Protection para `develop`
- [ ] Crear archivo CODEOWNERS
- [ ] Agregar colaboradores con permisos apropiados
- [ ] Configurar GitHub Actions para CI/CD
- [ ] Probar creando PR desde cuenta de desarrollador
- [ ] Verificar que solo admin puede hacer merge
- [ ] Documentar usernames y permisos del equipo
- [ ] Comunicar cambios al equipo
- [ ] Crear guía de emergencia para el equipo

---

**Última actualización**: Noviembre 2024
**Configurado por**: Bruno (Admin)
**Repositorio**: GRAVITEA-ERP