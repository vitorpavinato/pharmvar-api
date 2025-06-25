#!/usr/bin/env python3
"""
Teste Rápido das APIs - PharmVar Project
========================================
"""

import asyncio
import httpx
import json
import time

async def test_ensembl_api():
    """Testa Ensembl REST API com gene farmacogenômico."""
    print("📊 Testando Ensembl REST API...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            start_time = time.time()
            
            # Testar busca do gene CYP2D6
            response = await client.get(
                "https://rest.ensembl.org/lookup/symbol/homo_sapiens/CYP2D6",
                headers={"Content-Type": "application/json"}
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Ensembl OK ({elapsed:.2f}s)")
                print(f"   🧬 Gene: {data.get('display_name')} ({data.get('id')})")
                print(f"   📍 Localização: chr{data.get('seq_region_name')}:{data.get('start')}-{data.get('end')}")
                return True
            else:
                print(f"   ❌ Ensembl ERROR: HTTP {response.status_code}")
                return False
                
    except Exception as e:
        print(f"   ❌ Ensembl ERROR: {e}")
        return False

async def test_ensembl_variants():
    """Testa busca de variantes no Ensembl."""
    print("\n🧬 Testando busca de variantes...")
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. Primeiro buscar o gene
            gene_response = await client.get(
                "https://rest.ensembl.org/lookup/symbol/homo_sapiens/CYP2D6",
                headers={"Content-Type": "application/json"}
            )
            
            if gene_response.status_code != 200:
                print("   ❌ Não conseguiu buscar gene")
                return False
            
            gene_data = gene_response.json()
            ensembl_gene_id = gene_data.get("id")
            
            # 2. Buscar variantes do gene
            await asyncio.sleep(0.5)  # Rate limiting
            
            variants_response = await client.get(
                f"https://rest.ensembl.org/overlap/id/{ensembl_gene_id}",
                headers={"Content-Type": "application/json"},
                params={"feature": "variation"}
            )
            
            if variants_response.status_code == 200:
                variants = variants_response.json()
                rs_variants = [v for v in variants if v.get("id", "").startswith("rs")]
                
                print(f"   ✅ Variantes encontradas: {len(variants)} total, {len(rs_variants)} rs variants")
                
                # Mostrar algumas variantes rs
                for variant in rs_variants[:3]:
                    print(f"      🔍 {variant.get('id')} - chr{variant.get('seq_region_name')}:{variant.get('start')}")
                
                return True
            else:
                print(f"   ❌ Erro ao buscar variantes: HTTP {variants_response.status_code}")
                return False
                
    except Exception as e:
        print(f"   ❌ Erro na busca de variantes: {e}")
        return False

async def test_clinvar_api():
    """Testa ClinVar API via NCBI E-utilities."""
    print("\n💊 Testando ClinVar API...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            start_time = time.time()
            
            # Testar busca da variante rs3892097 (CYP2D6*4)
            response = await client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={
                    "db": "clinvar",
                    "term": "rs3892097[rs]",
                    "retmode": "json",
                    "retmax": "3"
                }
            )
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                count = data.get("esearchresult", {}).get("count", "0")
                id_list = data.get("esearchresult", {}).get("idlist", [])
                
                print(f"   ✅ ClinVar OK ({elapsed:.2f}s)")
                print(f"   🔍 Variante rs3892097: {count} registros encontrados")
                if id_list:
                    print(f"   🆔 ClinVar IDs: {', '.join(id_list)}")
                return True
            else:
                print(f"   ❌ ClinVar ERROR: HTTP {response.status_code}")
                return False
                
    except Exception as e:
        print(f"   ❌ ClinVar ERROR: {e}")
        return False

def test_database():
    """Testa conexão com PostgreSQL."""
    print("\n🗄️  Testando PostgreSQL...")
    
    try:
        from sqlalchemy import create_engine, text
        
        engine = create_engine("postgresql://pharmvar_user:pharmvar_pass@localhost:5432/pharmvar_db")
        
        with engine.connect() as conn:
            # Contar genes
            gene_count = conn.execute(text("SELECT COUNT(*) FROM pharmaco_genes")).scalar()
            
            # Contar variantes atuais
            variant_count = conn.execute(text("SELECT COUNT(*) FROM gene_variants")).scalar()
            
            # Contar interações
            drug_count = conn.execute(text("SELECT COUNT(*) FROM drug_interactions")).scalar()
            
            print(f"   ✅ PostgreSQL OK")
            print(f"   📊 Dados atuais:")
            print(f"      - Genes: {gene_count}")
            print(f"      - Variantes: {variant_count}")
            print(f"      - Interações: {drug_count}")
            
            return True
            
    except Exception as e:
        print(f"   ❌ PostgreSQL ERROR: {e}")
        return False

async def main():
    """Executa todos os testes."""
    print("🧪 PharmVar API Explorer - Teste de Conectividade")
    print("=" * 50)
    
    results = {}
    
    # Teste 1: Ensembl básico
    results['ensembl'] = await test_ensembl_api()
    
    # Teste 2: Variantes Ensembl
    results['variants'] = await test_ensembl_variants()
    
    # Teste 3: ClinVar
    results['clinvar'] = await test_clinvar_api()
    
    # Teste 4: Database
    results['database'] = test_database()
    
    # Resumo
    print("\n" + "=" * 50)
    print("📋 RESUMO DOS TESTES")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"   {test_name.upper()}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("   Pronto para implementar population via APIs reais.")
    else:
        print("⚠️  ALGUNS TESTES FALHARAM!")
        print("   Verifique conectividade de internet e containers Docker.")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(main())
