# 🧬 PharmVar API Explorer

**Prova Prática - Desenvolvedor Full Stack (Bioinformática) - GnTech**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docker.com)

---

## 📋 **Avaliação Técnica GnTech**

**Candidato**: Vitor Antonio Corrêa Pavinato  
**Data**: Junho 2025  
**Posição**: Desenvolvedor Full Stack (Bioinformática)

### ✅ **Requisitos Atendidos**

- ✅ **Extração de dados via API**: Ensembl REST API + ClinVar E-utilities
- ✅ **Banco de dados relacional**: PostgreSQL com 4 tabelas
- ✅ **API REST**: FastAPI com 12+ endpoints + Swagger UI
- ✅ **Conteinerização**: Docker Compose multi-container
- ✅ **Controle de versão**: Repositório GitHub

---

### 🚀 **Setup, Execução e Testes**

#### **Pré-requisitos**
- Docker + Docker Compose
- Git

#### **Step 1: Setup**
```bash
# 1. Clone
git clone https://github.com/vitorpavinato/pharmvar-api.git
cd pharmvar-api

# 2. Instalar Poetry (se não tiver installado)
curl -sSL https://install.python-poetry.org | python3 -

# 3. Instalar dependências locais
poetry install
```

#### **Step 2: Execução**
```bash
# 1. Containers (API + PostgreSQL + Redis)
docker-compose up -d

# 2. Popular com dados via APIs reais
# 2.1. Genes pré-definidos manualmente
poetry run python scripts/populate_db.py

# 2.2. Variantes dinamicamente através das APIs
poetry run python scripts/real_api_population.py

# 2.3. Enriquecer com dados completos (opcional)
poetry run python scripts/enhanced_api_population.py
```

#### **Step 3: Testes**
```bash
# 1. Testar alguns endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs (navegador)
curl "http://localhost:8000/api/status"

# 2. Testar Dashboard
# Após execução, iniciar dashboard
poetry run python serve_dashboard.py

# Acesse: http://localhost:8080/dashboard.html
```

---

### 🔗 Endpoints Principais

- **API**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8080/dashboard.html

---

### 📊 Scripts de Produção

- `scripts/populate_db.py` - População inicial de genes
- `scripts/real_api_population.py` - Busca dinâmica via APIs
- `scripts/enhanced_api_population.py` - Enriquecimento completo
- `serve_dashboard.py` - Servidor do dashboard

---

### 🧪 Scripts de Desenvolvimento

- `scripts/dev/test_apis.py` - Testes das APIs externas
- `scripts/dev/test_apis_quick.py` - Testes rápidos

---

### 🏗️ **Arquitetura**

#### **Stack**
- **Backend**: Python 3.12 + FastAPI
- **Banco**: PostgreSQL 15 
- **ORM**: SQLAlchemy
- **Cache**: Redis
- **Container**: Docker + Docker Compose

#### **Estrutura**
```
pharmvar-api/
├── app/                     # Código da API
│   ├── main.py             # FastAPI app
│   ├── clients/            # Clientes APIs externas
│   ├── core/               # Config + Database
│   └── models/             # SQLAlchemy models
├── scripts/                # Scripts de produção
│   ├──dev
|   |   ├── test_apis_quick.py
|   |   └── test_apis.py
│   ├── populate_db.py      # População inicial
│   ├── real_api_population.py    # Extração APIs
│   └── enhanced_api_population.py # Enriquecimento
├── dashboard.html          # Interface visual
├── docker-compose.yml      # Orquestração
├── Dockerfile
├── nginx.conf
├── poetry.lock
├── pyproject.toml
├── README.md
├── requirements.txt
└── server_dashboard.py
```

---

### 💎 **Demonstração dos Requisitos**

#### 1. **Extração de Dados via API** 🌐

**APIs Utilizadas**:
- **Ensembl REST API**: `https://rest.ensembl.org`
- **ClinVar E-utilities**: `https://eutils.ncbi.nlm.nih.gov`

**Parâmetros Dinâmicos**:
- Gene symbols: `CYP2D6`, `CYP2C19`, `DPYD`
- Exemplos de variant IDs: `rs3892097`, `rs1065852`

**Evidência**:
```bash
# Ver extração dinâmica de variantes SNPS em ação
# Se esse script já foi executado, a mensagem: 
# "Variante rs1203567065 já existe" aparece para todas as variantes
poetry run python scripts/real_api_population.py

# Verificar dados obtidos
curl http://localhost:8000/api/status
```

#### 2. **Banco de Dados Relacional** 🗄️

**PostgreSQL 15** com estrutura completa:

```sql
-- Verificar tabelas criadas
docker exec -it pharmvar_db psql -U pharmvar_user -d pharmvar_db -c "\dt"
```

Resultado esperado:
```bash
List of relations
 Schema |       Name        | Type  |     Owner
--------+-------------------+-------+---------------
 public | analysis_results  | table | pharmvar_user
 public | drug_interactions | table | pharmvar_user
 public | gene_variants     | table | pharmvar_user
 public | pharmaco_genes    | table | pharmvar_user
(4 rows)
```

```sql
-- Ver dados inseridos
docker exec -it pharmvar_db psql -U pharmvar_user -d pharmvar_db -c "SELECT COUNT(*) FROM gene_variants;"
```
Resultado esperado:
```bash
count
-------
    80
(1 row)
```

**Estrutura**:
- `pharmaco_genes`: 8 genes farmacogenômicos
- `gene_variants`: 80 variantes genéticas
- `drug_interactions`: Interações medicamentosas
- `analysis_results`: Resultados de análises

#### 3. **API REST** 🔗

**FastAPI** com documentação automática:

**Endpoints para test**:
```bash
# Listar genes
curl http://localhost:8000/genes | jq

# Buscar variantes
curl http://localhost:8000/variants/search/rs367543001

# Estatísticas
curl http://localhost:8000/stats
```

**Documentação Interativa**:
- **Swagger UI**: http://localhost:8000/docs

#### 4. **Conteinerização** 🐳

**Docker Compose** com 4 containers:

```bash
# Verificar containers
docker-compose ps
```
Resultado esperado:
```bash
NAME             IMAGE                       COMMAND                  SERVICE   CREATED          STATUS                      PORTS
pharmvar_api     pharmvar-api-explorer-api   "uvicorn app.main:ap…"   api       20 minutes ago   Up 20 minutes (unhealthy)   0.0.0.0:8000->8000/tcp
pharmvar_db      postgres:15-alpine          "docker-entrypoint.s…"   db        20 minutes ago   Up 20 minutes (healthy)     0.0.0.0:5432->5432/tcp
pharmvar_nginx   nginx:alpine                "/docker-entrypoint.…"   nginx     20 minutes ago   Up 20 minutes               0.0.0.0:80->80/tcp
pharmvar_redis   redis:7-alpine              "docker-entrypoint.s…"   redis     20 minutes ago   Up 20 minutes (healthy)     0.0.0.0:6379->6379/tcp
```

```bash
# Logs da aplicação
docker-compose logs api | head
```
Resultado esperado:
```bash
pharmvar_api  | INFO:     Started server process [1]
pharmvar_api  | INFO:     Waiting for application startup.
pharmvar_api  | 2025-06-25 12:00:16,840 - app.main - INFO - 🚀 Starting PharmVar API Explorer...
pharmvar_api  | 2025-06-25 12:00:16,840 - app.core.database - INFO - Creating database tables...
pharmvar_api  | 2025-06-25 12:00:16,868 - app.core.database - INFO - Database tables created successfully!
pharmvar_api  | 2025-06-25 12:00:16,868 - app.main - INFO - ✅ Database tables created/verified
pharmvar_api  | INFO:     Application startup complete.
pharmvar_api  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
pharmvar_api  | INFO:     192.168.65.1:21368 - "GET /api/summary HTTP/1.1" 200 OK
pharmvar_api  | INFO:     192.168.65.1:21368 - "GET /api/variants/quality HTTP/1.1" 200 OK
```

**Containers**:
- `api`: FastAPI application
- `db`: PostgreSQL database  
- `redis`: Cache layer

#### 5. **Controle de Versão** 📁

**GitHub** com organização profissional:
- **Repositório**: https://github.com/vitorpavinato/pharmvar-api

---

### 📈 **Próximas Evoluções Propostas**

#### **1. Classificação Funcional de Variantes** 🧬

**Inspirado no projeto**: [dosage-sensitive-gene-variants](https://github.com/vitorpavinato/dosage-sensitive-gene-variants)

**Categorização por impacto funcional**:
```python
# Classificação por tipo de consequência
variant_categories = {
    'synonymous': ['synonymous_variant'],
    'missense': ['missense_variant', 'protein_altering_variant'], 
    'intronic': ['intron_variant', 'splice_region_variant'],
    'regulatory': ['5_prime_UTR_variant', '3_prime_UTR_variant']
}

# Cruzamento com significância clínica
clinical_impact = {
    'pathogenic': ['pathogenic', 'likely_pathogenic'],
    'uncertain': ['uncertain_significance', 'conflicting_interpretations'],
    'benign': ['benign', 'likely_benign']
}
```

**Métricas propostas**:
- **Synonymous**: Total vs Clinicamente relevantes
- **Missense**: Total vs Patogênicas vs Benignas  
- **Intronic**: Total vs Com impacto no splicing
- **Regulatory**: Total vs Alterando expressão

**Visualizações**:
```python
# Dashboard com gráficos estratificados
plot_categories = [
    'synonymous_total', 'synonymous_clinical',
    'missense_total', 'missense_pathogenic', 'missense_benign',
    'intronic_total', 'intronic_splice_impact',
    'regulatory_total', 'regulatory_expression_impact'
]
```

#### **2. Análises Farmacogenômicas Avançadas** 💊

**Star Alleles Detection**:
- Identificação automática de haplótipos conhecidos
- Predição de fenótipos metabólicos
- Recomendações de dosagem

**Population Stratification**:
- Frequências por grupos étnicos
- Comparação com dados 1000 Genomes
- Impacto na medicina personalizada

#### **3. Integração com Mais Bases** 🔗

**APIs Adicionais**:
- **PharmGKB**: Diretrizes clínicas
- **CPIC**: Recomendações de dosagem
- **FDA Table**: Biomarcadores aprovados
- **gnomAD**: Frequências populacionais

**Workflow Proposto**:
```bash
# Pipeline completo de análise
poetry run python scripts/functional_classification.py
poetry run python scripts/clinical_annotation.py  
poetry run python scripts/population_analysis.py
poetry run python scripts/generate_reports.py
```

---

### 📞 **Contato e Próximos Passos**

**Vitor Antonio Corrêa Pavinato**
- **email**: vi***ato@proton.me
- **LinkedIn**: [vitor-antonio-correa-pavinato](https://www.linkedin.com/in/vitor-antonio-correa-pavinato-4b5522368/)
- **GitHub**: [vitorpavinato](https://github.com/vitorpavinato)

---

*Desenvolvido especificamente para demonstrar competências técnicas e de domínio para a posição de Desenvolvedor Full Stack (Bioinformática) na GnTech.*
