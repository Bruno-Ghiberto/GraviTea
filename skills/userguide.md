# Guia de Skills para Agentes IA

Guia para el equipo de GRAVITEA-ERP sobre como gestionar, crear e instalar skills que potencian a los agentes de IA (Claude, Gemini, Codex, Copilot) con conocimiento especifico de nuestro proyecto.

## Que es un Skill?

Un skill es una carpeta que contiene un archivo `SKILL.md` con instrucciones especializadas. Cuando un agente de IA detecta que estas trabajando en un area relevante (por ejemplo, editando modelos de Django o componentes React), carga automaticamente el skill correspondiente para darte respuestas precisas basadas en los patrones y convenciones de nuestro proyecto.

Sin skills, el agente responde con conocimiento generico. Con skills, responde siguiendo exactamente nuestras convenciones, modelos, patrones de seguridad y arquitectura.

## Arquitectura: Dos Fuentes de Skills

Nuestro proyecto combina **dos fuentes** de skills que se fusionan automaticamente:

```text
 FUENTE 1: skills/                  FUENTE 2: .agents/skills/
 (Custom - creados por el equipo)   (Marketplace - agentskills.io / Vercel / GitNexus)
          \                            /
           \                          /
            +--- setup.sh ---+
                    |
                    v
        Directorios de salida (generados):
        .claude/skills/   .gemini/skills/   .codex/skills/   .cursor/rules/
```

| Fuente | Ruta | Que contiene | Tracked en git? |
|--------|------|--------------|-----------------|
| Custom | `skills/` | Skills escritos por el equipo para nuestro proyecto | Si |
| Marketplace | `.agents/skills/` | Skills descargados de agentskills.io | Opcional |

El script `setup.sh` se encarga de copiar skills de ambas fuentes a los directorios que cada agente escanea. Esto significa que solo necesitas agregar un skill en UN lugar y `setup.sh` lo distribuye a todos los agentes.

## Inicio Rapido

Desde la raiz del repositorio, usando **Git Bash** (no PowerShell ni CMD):

```bash
# Configurar todos los agentes de una vez
bash skills/setup.sh --all

# Solo Claude
bash skills/setup.sh --claude

# Varios agentes especificos
bash skills/setup.sh --claude --codex

# Menu interactivo
bash skills/setup.sh
```

Despues de ejecutar setup, **reinicia tu agente de IA** para que cargue los skills nuevos.

## Instalar Skills del Marketplace (agentskills.io)

[Agent Skills](https://agentskills.io) es un ecosistema abierto impulsado por Vercel donde la comunidad publica skills reutilizables. Puedes encontrar skills para React, Next.js, TypeScript, optimizacion de rendimiento, accesibilidad, y mas.

### Como instalar un skill del marketplace

1. **Visita [agentskills.io](https://agentskills.io)** y busca el skill que necesitas.

2. **Instala el skill** siguiendo las instrucciones de la pagina. El skill se descarga en `.agents/skills/<nombre-del-skill>/`. La estructura tipica de un skill del marketplace es:

```text
.agents/skills/vercel-react-best-practices/
|-- SKILL.md          # Resumen con frontmatter (lo que el agente carga al inicio)
|-- AGENTS.md         # Guia completa compilada con todas las reglas
+-- rules/            # Reglas individuales organizadas por categoria
    |-- rule-01.md
    |-- rule-02.md
    +-- ...
```

3. **Ejecuta setup.sh** para distribuir el skill a todos los agentes:

```bash
bash skills/setup.sh --all
```

4. **Registra el skill en `AGENTS.md`** (en la raiz del repo) bajo la seccion "Marketplace Skills" para que el equipo sepa que esta disponible:

```markdown
### Marketplace Skills (agentskills.io)

| Skill | Descripcion | Trigger |
|-------|-------------|---------|
| `vercel-react-best-practices` | Optimizacion de React/Next.js (45 reglas) | Editando componentes React, paginas Next.js |
```

5. **(Opcional) Haz commit** de `.agents/skills/<nombre>/` para que todo el equipo lo tenga:

```bash
git add .agents/skills/vercel-react-best-practices/
git commit -m "feat: add vercel-react-best-practices marketplace skill"
```

### Donde encontrar skills

- **[agentskills.io](https://agentskills.io)** - Marketplace principal con skills verificados
- **[vercel.com/changelog](https://vercel.com/changelog/introducing-skills-the-open-agent-skills-ecosystem)** - Anuncio original y skills oficiales de Vercel
- **Repositorios de GitHub** - Cualquier repo que siga el formato `SKILL.md` con frontmatter YAML

### Que tipo de skills hay en el marketplace?

El ecosistema incluye skills para muchas tecnologias. Ejemplos:

- **React/Next.js** - Patrones de rendimiento, Server Components, eliminacion de waterfalls
- **TypeScript** - Mejores practicas de tipado, patrones avanzados
- **Accesibilidad** - Cumplimiento WCAG, patrones ARIA
- **Seguridad** - Validacion de inputs, proteccion contra XSS/CSRF
- **Testing** - Estrategias de testing, cobertura, E2E

## Crear un Skill Custom (del equipo)

Cuando necesitas que el agente conozca un patron especifico de nuestro proyecto que no existe en el marketplace.

### Paso a paso

1. **Crea la carpeta** del skill:

```bash
mkdir skills/mi-nuevo-skill
```

2. **Crea el archivo `SKILL.md`** con frontmatter YAML obligatorio:

```markdown
---
name: mi-nuevo-skill
description: >
  Descripcion clara de que ensenya este skill al agente.
  Trigger: Cuando el agente deberia activar este skill.
license: MIT
metadata:
  author: tu-nombre
  version: "1.0"
---

# Mi Nuevo Skill

## Cuando Usar
- Cuando se editen archivos en `apps/mi-modulo/`
- Cuando se creen nuevos endpoints relacionados con X

## Patrones Criticos

### Patron 1: Nombre descriptivo
Explicacion del patron seguida de un ejemplo de codigo real:

\```python
class MiModelo(TenantBoundModel):
    """Siempre heredar de TenantBoundModel para aislamiento de tenant."""
    nombre = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "nombre"],
                name="unique_nombre_per_tenant",
            )
        ]
\```

## Arbol de Decision

\```text
Necesitas crear un modelo nuevo?
|-- Tiene datos de tenant? -> Hereda de TenantBoundModel
|-- Es compartido (global)? -> Hereda de models.Model
+-- Tiene datos sensibles? -> Usa EncryptedField
\```

## Comandos Utiles

\```bash
cd backend && python manage.py makemigrations
cd backend && pytest tests/mi_modulo/ -v
\```
```

3. **Registra en `AGENTS.md`** bajo "Available Skills" y agrega una regla de auto-invocacion si aplica.

4. **Ejecuta setup y haz commit**:

```bash
bash skills/setup.sh --all
git add skills/mi-nuevo-skill/ AGENTS.md
git commit -m "feat: add mi-nuevo-skill AI skill"
```

### Consejos para escribir buenos skills

| Haz esto | No hagas esto |
|----------|---------------|
| Muestra codigo real del proyecto | Dar consejos genericos que el agente ya sabe |
| Incluye arboles de decision | Escribir parrafos largos sin estructura |
| Define triggers claros | Dejar ambiguo cuando se debe usar |
| Un dominio por skill | Mezclar temas no relacionados |
| Usa ejemplos del codebase | Inventar ejemplos que no existen en el proyecto |

## Editar un Skill Existente

Edita **siempre** el archivo en la fuente original:

- Skill custom: `skills/<nombre>/SKILL.md`
- Skill de marketplace: `.agents/skills/<nombre>/SKILL.md`

Luego re-ejecuta setup:

```bash
bash skills/setup.sh --all
```

**Nunca edites** archivos dentro de `.claude/skills/`, `.gemini/skills/` o `.codex/skills/`. Estos son directorios generados que se borran y recrean cada vez que ejecutas `setup.sh`.

## Eliminar un Skill

```bash
# Skill custom
rm -rf skills/<nombre-del-skill>

# Skill de marketplace
rm -rf .agents/skills/<nombre-del-skill>
```

Luego:
1. Elimina la entrada correspondiente en `AGENTS.md`
2. Ejecuta `bash skills/setup.sh --all` (la limpieza de skills obsoletos es automatica)

## Como Descubren los Skills los Agentes

Cada agente busca skills en su propio directorio de salida:

| Agente | Escanea | Archivo de instrucciones |
|--------|---------|--------------------------|
| Claude Code | `.claude/skills/*/SKILL.md` | `CLAUDE.md` (fuente de verdad, editar directamente) |
| Gemini CLI | `.gemini/skills/*/SKILL.md` | `GEMINI.md` (copia de AGENTS.md) |
| Codex (OpenAI) | `.codex/skills/*/SKILL.md` | `AGENTS.md` (lo lee directamente) |
| GitHub Copilot | No escanea skills | `.github/copilot-instructions.md` (copia de CLAUDE.md) |
| Cursor | `.cursor/rules/*.mdc` | Reglas generadas desde SKILL.md de cada skill |

### Carga progresiva

Los agentes NO cargan todos los skills de golpe. El proceso es:

1. **Al iniciar**: Solo leen `name` y `description` del frontmatter (~100 tokens por skill)
2. **Al activarse**: Cuando detectan que estas en un area relevante, cargan el `SKILL.md` completo
3. **Bajo demanda**: Si el skill referencia otros archivos, los cargan cuando los necesitan

Esto mantiene el consumo de contexto bajo mientras tienes muchos skills disponibles.

## Resolucion de Conflictos

Si un skill custom y uno de marketplace tienen **el mismo nombre de carpeta**, el skill custom siempre gana. El script muestra una advertencia:

```
! Conflict: 'nombre-skill' exists in both sources, using custom version
```

Esto permite que sobreescribas un skill del marketplace con tu propia version personalizada sin eliminarlo.

## Estructura de Directorios

```text
GRAVITEA-ERP/
|-- CLAUDE.md                    # Fuente de verdad para Claude (editar directamente)
|-- AGENTS.md                    # Seccion GitNexus (mantenida por la herramienta)
|-- skills/                      # FUENTE 1: Skills custom (git-tracked)
|   |-- setup.sh                 # Script de merge de dos fuentes
|   |-- setup_test.sh            # Tests unitarios del script
|   |-- userguide.md             # Esta guia
|   |-- django-expert/
|   |   +-- SKILL.md
|   |-- gravitea-auth/
|   |   +-- SKILL.md
|   |-- gravitea-tenant/
|   |   +-- SKILL.md
|   +-- ... (10+ skills custom)
|-- .agents/skills/              # FUENTE 2: Skills del marketplace / herramientas externas
|   |-- vercel-react-best-practices/
|   |   |-- SKILL.md
|   |   +-- rules/               # Reglas individuales
|   |-- gitnexus-cli/
|   |   +-- SKILL.md
|   |-- gitnexus-debugging/
|   |   +-- SKILL.md
|   +-- ... (otros skills de marketplace / GitNexus)
|-- .claude/skills/              # SALIDA generada (no editar)
|-- .codex/skills/               # SALIDA generada (no editar)
|-- .gemini/skills/              # SALIDA generada (no editar)
|-- .cursor/rules/               # SALIDA generada: archivos .mdc para Cursor
|-- GEMINI.md                    # Copia generada de AGENTS.md
+-- .github/copilot-instructions.md  # Copia generada de CLAUDE.md
```

## Tests del Script

El script `setup.sh` tiene tests unitarios que verifican:

- Merge de ambas fuentes (custom + marketplace)
- Preservacion de subdirectorios de skills del marketplace
- Resolucion de conflictos (custom gana)
- Idempotencia (ejecutar multiples veces da el mismo resultado)
- Limpieza de skills obsoletos
- Creacion de directorios
- Copia de AGENTS.md

```bash
bash skills/setup_test.sh
```

Ejecuta los tests si haces cambios a `setup.sh`.

## Solucion de Problemas

| Problema | Solucion |
|----------|----------|
| El skill no aparece en el agente | Ejecuta `setup.sh --all` y reinicia el agente |
| Un skill eliminado sigue apareciendo | Re-ejecuta `setup.sh --all` (limpia directorios de salida) |
| `setup.sh` falla en Windows | Usa Git Bash, no PowerShell ni CMD |
| No hay carpeta `.agents/skills/` | Normal si no has instalado skills del marketplace |
| El agente no sigue el skill | Verifica que el `description` en el frontmatter incluya triggers claros |
| Quiero sobreescribir un skill del marketplace | Crea un skill custom con el mismo nombre de carpeta |

## Referencia Rapida

```bash
# Configurar todos los agentes
bash skills/setup.sh --all

# Solo un agente
bash skills/setup.sh --claude

# Ejecutar tests del script
bash skills/setup_test.sh

# Ver los skills disponibles en la fuente custom
ls skills/*/SKILL.md

# Ver los skills del marketplace instalados
ls .agents/skills/*/SKILL.md 2>/dev/null

# Ver los skills que tiene Claude actualmente
ls .claude/skills/
```
