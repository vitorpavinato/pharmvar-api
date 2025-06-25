"""
Ensembl REST API client for fetching gene and variant information.
Documentation: https://rest.ensembl.org/
"""

from typing import Dict, List, Optional, Any
from .base_client import BaseAPIClient, APIError


class EnsemblClient(BaseAPIClient):
    """Client for Ensembl REST API."""
    
    def __init__(self, base_url: str = "https://rest.ensembl.org"):
        # Ensembl has a rate limit of 15 requests per second
        super().__init__(base_url=base_url, rate_limit=14.0)  # Slightly under limit
        
    def get_api_info(self) -> Dict[str, str]:
        """Return basic information about this API client."""
        return {
            "name": "Ensembl REST API",
            "base_url": self.base_url,
            "description": "Genomic data including genes, variants, and consequences",
            "rate_limit": "15 requests/second",
            "documentation": "https://rest.ensembl.org/documentation"
        }
    
    async def health_check(self) -> bool:
        """Check if Ensembl API is accessible."""
        try:
            result = await self.get("/info/ping")
            return result.get("ping") == 1
        except Exception as e:
            self.logger.error(f"Ensembl health check failed: {e}")
            return False
    
    async def get_gene_info(self, gene_id: str, species: str = "human") -> Dict[str, Any]:
        """
        Get detailed information about a gene.
        
        Args:
            gene_id: Ensembl gene ID (e.g., 'ENSG00000100197') or gene symbol (e.g., 'CYP2D6')
            species: Species name (default: 'human')
            
        Returns:
            Gene information including location, description, biotype
        """
        endpoint = f"/lookup/id/{gene_id}"
        params = {"species": species, "expand": "1"}
        
        try:
            return await self.get(endpoint, params=params)
        except APIError as e:
            if e.status_code == 404:
                # Try with symbol lookup if ID lookup failed
                return await self.get_gene_by_symbol(gene_id, species)
            raise
    
    async def get_gene_by_symbol(self, gene_symbol: str, species: str = "human") -> Dict[str, Any]:
        """
        Get gene information by gene symbol.
        
        Args:
            gene_symbol: Gene symbol (e.g., 'CYP2D6')
            species: Species name (default: 'human')
            
        Returns:
            Gene information
        """
        endpoint = f"/lookup/symbol/{species}/{gene_symbol}"
        params = {"expand": "1"}
        
        return await self.get(endpoint, params=params)
    
    async def get_gene_variants(
        self, 
        gene_id: str, 
        species: str = "human",
        consequence_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get variants for a specific gene.
        
        Args:
            gene_id: Ensembl gene ID
            species: Species name
            consequence_types: Filter by consequence types (e.g., ['missense_variant'])
            
        Returns:
            List of variants
        """
        endpoint = f"/overlap/id/{gene_id}"
        params = {
            "feature": "variation",
            "species": species
        }
        
        if consequence_types:
            params["consequence_type"] = ",".join(consequence_types)
        
        try:
            variants = await self.get(endpoint, params=params)
            return variants if isinstance(variants, list) else []
        except APIError as e:
            if e.status_code == 404:
                self.logger.warning(f"No variants found for gene {gene_id}")
                return []
            raise
    
    async def get_variant_consequences(
        self, 
        variant_id: str, 
        species: str = "human"
    ) -> Dict[str, Any]:
        """
        Get consequence information for a specific variant.
        
        Args:
            variant_id: Variant ID (e.g., 'rs1065852')
            species: Species name
            
        Returns:
            Variant consequence information
        """
        endpoint = f"/variation/{species}/{variant_id}"
        params = {"consequence": "1"}
        
        return await self.get(endpoint, params=params)
    
    async def get_population_frequencies(
        self, 
        variant_id: str, 
        species: str = "human"
    ) -> Dict[str, Any]:
        """
        Get population frequency data for a variant.
        
        Args:
            variant_id: Variant ID
            species: Species name
            
        Returns:
            Population frequency data
        """
        endpoint = f"/variation/{species}/{variant_id}"
        params = {"pops": "1"}
        
        return await self.get(endpoint, params=params)
    
    async def get_vep_consequences(
        self,
        chromosome: str,
        position: int,
        alleles: str,
        species: str = "human"
    ) -> List[Dict[str, Any]]:
        """
        Get VEP (Variant Effect Predictor) consequences for a genomic variant.
        
        Args:
            chromosome: Chromosome (e.g., '22')
            position: Genomic position
            alleles: Alleles (e.g., 'A/G')
            species: Species name
            
        Returns:
            VEP consequence predictions
        """
        # Format: chr:pos:alleles
        variant_notation = f"{chromosome}:{position}:{alleles}"
        endpoint = f"/vep/{species}/region/{variant_notation}"
        
        try:
            result = await self.get(endpoint)
            return result if isinstance(result, list) else [result]
        except APIError as e:
            self.logger.error(f"VEP lookup failed for {variant_notation}: {e}")
            return []
    
    async def search_genes_by_phenotype(
        self, 
        phenotype: str, 
        species: str = "human"
    ) -> List[Dict[str, Any]]:
        """
        Search for genes associated with a phenotype.
        
        Args:
            phenotype: Phenotype term (e.g., 'drug metabolism')
            species: Species name
            
        Returns:
            List of associated genes
        """
        endpoint = f"/phenotype/term/{species}/{phenotype}"
        
        try:
            result = await self.get(endpoint)
            return result if isinstance(result, list) else []
        except APIError as e:
            if e.status_code == 404:
                self.logger.warning(f"No genes found for phenotype: {phenotype}")
                return []
            raise


# Pharmacogenomic gene mapping
PHARMACO_GENES = {
    "CYP2D6": "ENSG00000100197",
    "CYP2C19": "ENSG00000165841", 
    "CYP2C9": "ENSG00000138109",
    "DPYD": "ENSG00000188641",
    "TPMT": "ENSG00000137364",
    "SLCO1B1": "ENSG00000134538",
    "UGT1A1": "ENSG00000241635",
    "VKORC1": "ENSG00000167397",
    "CFTR": "ENSG00000001626",
    "IFNL3": "ENSG00000163541"
}


class PharmacoEnsemblClient(EnsemblClient):
    """Specialized Ensembl client for pharmacogenomic queries."""
    
    def __init__(self):
        super().__init__()
        self.pharmaco_genes = PHARMACO_GENES
    
    async def get_pharmaco_gene_info(self, gene_symbol: str) -> Dict[str, Any]:
        """Get information for a pharmacogenomic gene."""
        if gene_symbol not in self.pharmaco_genes:
            raise APIError(f"Gene {gene_symbol} not in pharmacogenomic gene list")
        
        ensembl_id = self.pharmaco_genes[gene_symbol]
        gene_info = await self.get_gene_info(ensembl_id)
        
        # Add pharmaco-specific metadata
        gene_info["pharmaco_relevance"] = self._get_pharmaco_relevance(gene_symbol)
        
        return gene_info
    
    def _get_pharmaco_relevance(self, gene_symbol: str) -> Dict[str, str]:
        """Get pharmacogenomic relevance information for a gene."""
        relevance_map = {
            "CYP2D6": {
                "function": "Drug metabolism",
                "drugs": "Codeine, tramadol, antidepressants, antipsychotics",
                "clinical_impact": "Variable drug efficacy and toxicity"
            },
            "CYP2C19": {
                "function": "Drug metabolism", 
                "drugs": "Clopidogrel, proton pump inhibitors, antidepressants",
                "clinical_impact": "Reduced drug efficacy in poor metabolizers"
            },
            "DPYD": {
                "function": "Drug metabolism",
                "drugs": "5-fluorouracil, capecitabine",
                "clinical_impact": "Severe toxicity in deficient patients"
            },
            "TPMT": {
                "function": "Drug metabolism",
                "drugs": "Azathioprine, mercaptopurine, thioguanine", 
                "clinical_impact": "Bone marrow toxicity"
            }
        }
        
        return relevance_map.get(gene_symbol, {
            "function": "Unknown pharmacogenomic function",
            "drugs": "To be determined",
            "clinical_impact": "Under investigation"
        })
    
    async def get_all_pharmaco_genes(self) -> Dict[str, Dict[str, Any]]:
        """Get information for all pharmacogenomic genes."""
        results = {}
        
        for gene_symbol in self.pharmaco_genes:
            try:
                gene_info = await self.get_pharmaco_gene_info(gene_symbol)
                results[gene_symbol] = gene_info
            except Exception as e:
                self.logger.error(f"Failed to get info for {gene_symbol}: {e}")
                results[gene_symbol] = {"error": str(e)}
        
        return results