#!/usr/bin/env python3
"""
PharmVar API Explorer - Enhanced API Population System
=====================================================

Sistema avançado que:
1. Busca dados COMPLETOS do ClinVar
2. Adiciona consequências de variantes via Ensembl VEP
3. Enriquece dados com alelos de referência/alternativos
4. Implementa cache Redis para melhor performance
5. Adiciona validação e tratamento de erros robusto

Autor: Vitor Pavinato
Data: Junho 2025
"""

import asyncio
import httpx
import json
import logging
import redis
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedAPIPopulator:
    """
    Sistema avançado de população com dados completos das APIs.
    
    Melhorias principais:
    - Dados completos do ClinVar via E-utilities
    - Consequências de variantes via Ensembl VEP
    - Cache Redis para performance
    - Validação robusta de dados
    """
    
    def __init__(self):
        self.db_url = "postgresql://pharmvar_user:pharmvar_pass@localhost:5432/pharmvar_db"
        self.engine = create_engine(self.db_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Redis cache
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            self.redis_client.ping()
            self.cache_enabled = True
            logger.info("✅ Redis cache conectado")
        except:
            self.cache_enabled = False
            logger.warning("⚠️  Redis cache não disponível - funcionando sem cache")
        
        # Rate limiting
        self.ensembl_delay = 0.2  # 200ms entre requests
        self.clinvar_delay = 0.5  # 500ms entre requests (mais conservador)
        
        # Stats
        self.stats = {
            "genes_processed": 0,
            "variants_processed": 0,
            "variants_enriched": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": []
        }

    async def enhance_existing_variants(self) -> Dict[str, Any]:
        """
        Enriquece variantes já existentes no banco com dados completos.
        
        Returns:
            Dict com estatísticas do processo
        """
        logger.info("🚀 Iniciando enriquecimento de variantes existentes...")
        
        # Buscar variantes existentes que precisam de enriquecimento
        variants = self.get_variants_needing_enrichment()
        logger.info(f"📊 Encontradas {len(variants)} variantes para enriquecer")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for variant_id, rs_id, gene_symbol in variants:
                await self.enrich_variant(client, variant_id, rs_id, gene_symbol)
                self.stats["variants_processed"] += 1
        
        self.show_enhancement_stats()
        return self.stats

    def get_variants_needing_enrichment(self) -> List[tuple]:
        """
        Busca variantes que precisam de enriquecimento.
        
        Returns:
            Lista de tuplas (variant_id, rs_id, gene_symbol)
        """
        query = text("""
            SELECT v.id, v.variant_id, g.gene_symbol
            FROM gene_variants v
            JOIN pharmaco_genes g ON v.gene_id = g.id
            WHERE v.clinical_significance IS NULL 
               OR v.consequence_type IS NULL
               OR v.reference_allele IS NULL
            ORDER BY g.gene_symbol, v.variant_id
            LIMIT 50
        """)
        
        result = self.session.execute(query).fetchall()
        return [(row[0], row[1], row[2]) for row in result]

    async def enrich_variant(self, client: httpx.AsyncClient, variant_id: int, rs_id: str, gene_symbol: str):
        """
        Enriquece uma variante com dados completos.
        
        Args:
            client: HTTP client
            variant_id: ID da variante no banco
            rs_id: ID rs da variante
            gene_symbol: Símbolo do gene
        """
        logger.info(f"🔬 Enriquecendo {rs_id} ({gene_symbol})...")
        
        try:
            # 1. Buscar dados completos do ClinVar
            clinvar_data = await self.fetch_complete_clinvar_data(client, rs_id)
            
            # 2. Buscar consequências do VEP
            vep_data = await self.fetch_vep_consequences(client, rs_id)
            
            # 3. Atualizar no banco
            if clinvar_data or vep_data:
                await self.update_variant_enrichment(variant_id, clinvar_data, vep_data)
                self.stats["variants_enriched"] += 1
                logger.info(f"   ✅ {rs_id} enriquecido")
            else:
                logger.info(f"   ⚠️  {rs_id} - nenhum dado adicional encontrado")
            
        except Exception as e:
            error_msg = f"Erro ao enriquecer {rs_id}: {e}"
            logger.error(f"   ❌ {error_msg}")
            self.stats["errors"].append(error_msg)

    async def fetch_complete_clinvar_data(self, client: httpx.AsyncClient, rs_id: str) -> Optional[Dict]:
        """
        Busca dados COMPLETOS do ClinVar (não apenas placeholders).
        
        Args:
            client: HTTP client
            rs_id: ID rs da variante
            
        Returns:
            Dados completos do ClinVar ou None
        """
        cache_key = f"clinvar:{rs_id}"
        
        # Tentar cache primeiro
        if self.cache_enabled:
            cached = self.redis_client.get(cache_key)
            if cached:
                self.stats["cache_hits"] += 1
                return json.loads(cached)
        
        self.stats["cache_misses"] += 1
        
        try:
            # 1. Buscar IDs no ClinVar
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            search_params = {
                "db": "clinvar",
                "term": f"{rs_id}[rs]",
                "retmode": "json",
                "retmax": "5"
            }
            
            search_response = await client.get(search_url, params=search_params)
            await asyncio.sleep(self.clinvar_delay)
            
            if search_response.status_code != 200:
                return None
            
            search_data = search_response.json()
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                return None
            
            # 2. Buscar detalhes completos
            fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            fetch_params = {
                "db": "clinvar",
                "id": ",".join(id_list[:3]),  # Limitar a 3 IDs
                "retmode": "xml"
            }
            
            fetch_response = await client.get(fetch_url, params=fetch_params)
            await asyncio.sleep(self.clinvar_delay)
            
            if fetch_response.status_code != 200:
                return None
            
            # 3. Parsear XML do ClinVar
            clinvar_data = self.parse_clinvar_xml(fetch_response.text, rs_id)
            
            # Cache por 1 hora
            if self.cache_enabled and clinvar_data:
                self.redis_client.setex(cache_key, 3600, json.dumps(clinvar_data))
            
            return clinvar_data
            
        except Exception as e:
            logger.error(f"   ❌ Erro ao buscar ClinVar para {rs_id}: {e}")
            return None

    def parse_clinvar_xml(self, xml_content: str, rs_id: str) -> Optional[Dict]:
        """
        Parseia XML do ClinVar para extrair dados estruturados.
        
        Args:
            xml_content: Conteúdo XML do ClinVar
            rs_id: ID rs da variante
            
        Returns:
            Dados estruturados do ClinVar
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Buscar primeira VariationArchive
            variation = root.find(".//VariationArchive")
            if variation is None:
                return None
            
            # Extrair dados básicos
            clinvar_data = {
                "clinvar_accession": variation.get("Accession"),
                "variation_id": variation.get("VariationID"),
                "variation_name": variation.get("VariationName"),
                "rs_id": rs_id
            }
            
            # Significância clínica
            interp = variation.find(".//Interpretation")
            if interp is not None:
                clinvar_data["clinical_significance"] = interp.get("Description", "").lower()
                
                # Review status
                review_status = interp.find("ReviewStatus")
                if review_status is not None:
                    clinvar_data["review_status"] = review_status.text
            
            # Condições associadas
            traits = variation.findall(".//Trait")
            conditions = []
            for trait in traits:
                name_elem = trait.find(".//Name/ElementValue[@Type='Preferred']")
                if name_elem is not None:
                    conditions.append(name_elem.text)
            
            if conditions:
                clinvar_data["associated_conditions"] = conditions[:5]  # Limitar a 5
            
            # Dados moleculares
            molecular = variation.find(".//MolecularConsequence")
            if molecular is not None:
                so_elem = molecular.find("SO")
                if so_elem is not None:
                    clinvar_data["molecular_consequence"] = so_elem.text
            
            return clinvar_data
            
        except ET.ParseError as e:
            logger.error(f"   ❌ Erro ao parsear XML do ClinVar: {e}")
            return None

    async def fetch_vep_consequences(self, client: httpx.AsyncClient, rs_id: str) -> Optional[Dict]:
        """
        Busca consequências de variantes via Ensembl VEP.
        
        Args:
            client: HTTP client
            rs_id: ID rs da variante
            
        Returns:
            Dados de consequências do VEP
        """
        cache_key = f"vep:{rs_id}"
        
        # Tentar cache primeiro
        if self.cache_enabled:
            cached = self.redis_client.get(cache_key)
            if cached:
                self.stats["cache_hits"] += 1
                return json.loads(cached)
        
        self.stats["cache_misses"] += 1
        
        try:
            # Buscar dados do VEP
            vep_url = f"https://rest.ensembl.org/vep/human/id/{rs_id}"
            headers = {"Content-Type": "application/json"}
            
            vep_response = await client.get(vep_url, headers=headers)
            await asyncio.sleep(self.ensembl_delay)
            
            if vep_response.status_code != 200:
                return None
            
            vep_data = vep_response.json()
            
            if not vep_data:
                return None
            
            # Processar primeiro resultado
            first_result = vep_data[0] if isinstance(vep_data, list) else vep_data
            
            processed_data = {
                "variant_id": first_result.get("id"),
                "allele_string": first_result.get("allele_string"),
                "most_severe_consequence": first_result.get("most_severe_consequence"),
                "regulatory_feature_consequences": first_result.get("regulatory_feature_consequences", []),
                "transcript_consequences": first_result.get("transcript_consequences", [])[:3]  # Limitar a 3
            }
            
            # Extrair alelos de referência e alternativo
            allele_string = first_result.get("allele_string", "")
            if "/" in allele_string:
                alleles = allele_string.split("/")
                if len(alleles) == 2:
                    processed_data["reference_allele"] = alleles[0]
                    processed_data["alternate_allele"] = alleles[1]
            
            # Cache por 1 hora
            if self.cache_enabled:
                self.redis_client.setex(cache_key, 3600, json.dumps(processed_data))
            
            return processed_data
            
        except Exception as e:
            logger.error(f"   ❌ Erro ao buscar VEP para {rs_id}: {e}")
            return None

    async def update_variant_enrichment(self, variant_id: int, clinvar_data: Optional[Dict], vep_data: Optional[Dict]):
        """
        Atualiza variante no banco com dados enriquecidos.
        
        Args:
            variant_id: ID da variante no banco
            clinvar_data: Dados do ClinVar (pode ser None)
            vep_data: Dados do VEP (pode ser None)
        """
        try:
            update_parts = []
            params = {"variant_id": variant_id, "updated_at": datetime.now()}
            
            # Dados do ClinVar
            if clinvar_data:
                update_parts.extend([
                    "clinical_significance = :clinical_significance",
                    "review_status = :review_status",
                    "associated_conditions = :associated_conditions",
                    "clinvar_data = :clinvar_data"
                ])
                
                params.update({
                    "clinical_significance": clinvar_data.get("clinical_significance"),
                    "review_status": clinvar_data.get("review_status"),
                    "associated_conditions": json.dumps(clinvar_data.get("associated_conditions", [])),
                    "clinvar_data": json.dumps(clinvar_data)
                })
            
            # Dados do VEP
            if vep_data:
                update_parts.extend([
                    "reference_allele = :reference_allele",
                    "alternate_allele = :alternate_allele", 
                    "consequence_type = :consequence_type",
                    "ensembl_data = :ensembl_data"
                ])
                
                params.update({
                    "reference_allele": vep_data.get("reference_allele"),
                    "alternate_allele": vep_data.get("alternate_allele"),
                    "consequence_type": vep_data.get("most_severe_consequence"),
                    "ensembl_data": json.dumps(vep_data)
                })
            
            if update_parts:
                update_parts.append("last_updated_from_api = :updated_at")
                
                update_query = text(f"""
                    UPDATE gene_variants 
                    SET {', '.join(update_parts)}
                    WHERE id = :variant_id
                """)
                
                self.session.execute(update_query, params)
                self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            raise e

    def show_enhancement_stats(self):
        """Exibe estatísticas do enriquecimento."""
        logger.info("\n" + "="*60)
        logger.info("📊 ESTATÍSTICAS DO ENRIQUECIMENTO")
        logger.info("="*60)
        logger.info(f"   🔬 Variantes processadas: {self.stats['variants_processed']}")
        logger.info(f"   ✅ Variantes enriquecidas: {self.stats['variants_enriched']}")
        
        if self.cache_enabled:
            total_requests = self.stats['cache_hits'] + self.stats['cache_misses']
            if total_requests > 0:
                hit_rate = (self.stats['cache_hits'] / total_requests) * 100
                logger.info(f"   🗄️  Cache hit rate: {hit_rate:.1f}% ({self.stats['cache_hits']}/{total_requests})")
        
        if self.stats['errors']:
            logger.warning(f"   ⚠️  Erros: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:3]:
                logger.warning(f"      - {error}")

    def close(self):
        """Fecha conexões."""
        if self.session:
            self.session.close()
        if self.cache_enabled:
            self.redis_client.close()


async def main():
    """Função principal."""
    print("🔬 PharmVar API Explorer - Enhanced API Population")
    print("=" * 55)
    print("Este script enriquece variantes existentes com:")
    print("- Dados completos do ClinVar")
    print("- Consequências do Ensembl VEP")
    print("- Cache Redis para performance")
    print()
    
    populator = EnhancedAPIPopulator()
    
    try:
        stats = await populator.enhance_existing_variants()
        
        print("\n🎉 Enriquecimento concluído!")
        print(f"   🔬 {stats['variants_processed']} variantes processadas")
        print(f"   ✅ {stats['variants_enriched']} variantes enriquecidas")
        
        if stats['errors']:
            print(f"   ⚠️  {len(stats['errors'])} erros (verifique logs)")
        
        print("\n🔍 Teste os resultados:")
        print("   curl http://localhost:8000/variants?limit=3")
        print("   curl http://localhost:8000/variants/search/rs1065852")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        populator.close()


if __name__ == "__main__":
    asyncio.run(main())
