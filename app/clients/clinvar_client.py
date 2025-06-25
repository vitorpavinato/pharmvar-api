"""
ClinVar API client using NCBI E-utilities for clinical variant data.
Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25499/
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from urllib.parse import quote
from .base_client import BaseAPIClient, APIError


class ClinVarClient(BaseAPIClient):
    """Client for ClinVar data via NCBI E-utilities."""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
            rate_limit=9.0 if api_key else 2.0  # 10/sec with key, 3/sec without
        )
        self.api_key = api_key
        
    def get_api_info(self) -> Dict[str, str]:
        """Return basic information about this API client."""
        return {
            "name": "ClinVar via NCBI E-utilities",
            "base_url": self.base_url,
            "description": "Clinical significance and disease associations for variants",
            "rate_limit": "10/sec with API key, 3/sec without",
            "documentation": "https://www.ncbi.nlm.nih.gov/books/NBK25499/"
        }
    
    async def health_check(self) -> bool:
        """Check if NCBI E-utilities API is accessible."""
        try:
            # Test with a simple info query
            params = {"db": "clinvar"}
            if self.api_key:
                params["api_key"] = self.api_key
                
            result = await self.get("/einfo.fcgi", params=params)
            # E-utilities returns XML, if we get data back, it's working
            return bool(result)
        except Exception as e:
            self.logger.error(f"ClinVar health check failed: {e}")
            return False
    
    def _parse_clinvar_xml(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse ClinVar XML response into structured data."""
        try:
            root = ET.fromstring(xml_content)
            variants = []
            
            # Look for ClinVarSet elements
            for clinvar_set in root.findall('.//ClinVarSet'):
                variant_data = {}
                
                # Get variant ID
                variant_id = clinvar_set.get('ID')
                if variant_id:
                    variant_data['clinvar_id'] = variant_id
                
                # Get ReferenceClinVarAssertion
                ref_assertion = clinvar_set.find('.//ReferenceClinVarAssertion')
                if ref_assertion is not None:
                    
                    # Clinical significance
                    clin_sig = ref_assertion.find('.//ClinicalSignificance/Description')
                    if clin_sig is not None:
                        variant_data['clinical_significance'] = clin_sig.text
                    
                    # Review status
                    review_status = ref_assertion.find('.//ClinicalSignificance/ReviewStatus')
                    if review_status is not None:
                        variant_data['review_status'] = review_status.text
                    
                    # Variant names/identifiers
                    measure_set = ref_assertion.find('.//MeasureSet')
                    if measure_set is not None:
                        measure = measure_set.find('.//Measure')
                        if measure is not None:
                            # Get variant name
                            name_elem = measure.find('.//Name/ElementValue[@Type="Preferred"]')
                            if name_elem is not None:
                                variant_data['preferred_name'] = name_elem.text
                            
                            # Get dbSNP ID
                            for xref in measure.findall('.//XRef'):
                                if xref.get('DB') == 'dbSNP':
                                    variant_data['dbsnp_id'] = f"rs{xref.get('ID')}"
                    
                    # Conditions/Traits
                    trait_set = ref_assertion.find('.//TraitSet')
                    if trait_set is not None:
                        conditions = []
                        for trait in trait_set.findall('.//Trait'):
                            trait_name = trait.find('.//Name/ElementValue[@Type="Preferred"]')
                            if trait_name is not None:
                                conditions.append(trait_name.text)
                        variant_data['conditions'] = conditions
                
                if variant_data:  # Only add if we found some data
                    variants.append(variant_data)
            
            return variants
            
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error parsing ClinVar data: {e}")
            return []
    
    async def search_variant_by_rs(self, rs_id: str) -> List[Dict[str, Any]]:
        """
        Search for variant information by dbSNP RS ID.
        
        Args:
            rs_id: dbSNP ID (e.g., 'rs1065852' or just '1065852')
            
        Returns:
            List of variant records with clinical data
        """
        # Clean up RS ID
        rs_number = rs_id.replace('rs', '') if rs_id.startswith('rs') else rs_id
        
        # Step 1: Search for the variant
        search_params = {
            "db": "clinvar",
            "term": f"{rs_number}[RS]",
            "retmode": "json"
        }
        if self.api_key:
            search_params["api_key"] = self.api_key
        
        try:
            search_result = await self.get("/esearch.fcgi", params=search_params)
            
            # Extract IDs from search result
            if isinstance(search_result, dict):
                id_list = search_result.get("esearchresult", {}).get("idlist", [])
            else:
                self.logger.warning("Unexpected search result format")
                return []
            
            if not id_list:
                self.logger.info(f"No ClinVar records found for RS ID: {rs_id}")
                return []
            
            # Step 2: Fetch detailed records
            fetch_params = {
                "db": "clinvar", 
                "id": ",".join(id_list[:10]),  # Limit to first 10 results
                "rettype": "vcv",  # ClinVar XML format
                "retmode": "xml"
            }
            if self.api_key:
                fetch_params["api_key"] = self.api_key
            
            # Note: E-utilities returns XML as text, not JSON
            xml_response = await self._make_request("GET", "/efetch.fcgi", params=fetch_params)
            
            # Parse XML response
            if isinstance(xml_response, str):
                return self._parse_clinvar_xml(xml_response)
            else:
                self.logger.warning("Expected XML string but got different format")
                return []
                
        except APIError as e:
            if e.status_code == 404:
                self.logger.info(f"No ClinVar data found for RS ID: {rs_id}")
                return []
            raise
    
    async def search_variant_by_gene(self, gene_symbol: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for variants in a specific gene.
        
        Args:
            gene_symbol: Gene symbol (e.g., 'CYP2D6')
            limit: Maximum number of results to return
            
        Returns:
            List of variant records
        """
        search_params = {
            "db": "clinvar",
            "term": f"{gene_symbol}[gene]",
            "retmax": str(limit),
            "retmode": "json"
        }
        if self.api_key:
            search_params["api_key"] = self.api_key
        
        try:
            search_result = await self.get("/esearch.fcgi", params=search_params)
            
            if isinstance(search_result, dict):
                id_list = search_result.get("esearchresult", {}).get("idlist", [])
            else:
                return []
            
            if not id_list:
                self.logger.info(f"No ClinVar variants found for gene: {gene_symbol}")
                return []
            
            # Fetch detailed records
            fetch_params = {
                "db": "clinvar",
                "id": ",".join(id_list),
                "rettype": "vcv",
                "retmode": "xml"
            }
            if self.api_key:
                fetch_params["api_key"] = self.api_key
            
            xml_response = await self._make_request("GET", "/efetch.fcgi", params=fetch_params)
            
            if isinstance(xml_response, str):
                return self._parse_clinvar_xml(xml_response)
            else:
                return []
                
        except APIError as e:
            if e.status_code == 404:
                self.logger.info(f"No ClinVar data found for gene: {gene_symbol}")
                return []
            raise
    
    async def get_pathogenic_variants(self, gene_symbol: str) -> List[Dict[str, Any]]:
        """
        Get pathogenic/likely pathogenic variants for a gene.
        
        Args:
            gene_symbol: Gene symbol
            
        Returns:
            List of pathogenic variants
        """
        search_term = f"{gene_symbol}[gene] AND (pathogenic[clin] OR likely pathogenic[clin])"
        
        search_params = {
            "db": "clinvar",
            "term": search_term,
            "retmax": "50",
            "retmode": "json"
        }
        if self.api_key:
            search_params["api_key"] = self.api_key
        
        try:
            search_result = await self.get("/esearch.fcgi", params=search_params)
            
            if isinstance(search_result, dict):
                id_list = search_result.get("esearchresult", {}).get("idlist", [])
            else:
                return []
            
            if not id_list:
                return []
            
            # Fetch detailed records
            fetch_params = {
                "db": "clinvar",
                "id": ",".join(id_list),
                "rettype": "vcv",
                "retmode": "xml"
            }
            if self.api_key:
                fetch_params["api_key"] = self.api_key
            
            xml_response = await self._make_request("GET", "/efetch.fcgi", params=fetch_params)
            
            if isinstance(xml_response, str):
                variants = self._parse_clinvar_xml(xml_response)
                # Filter to only pathogenic/likely pathogenic
                pathogenic_variants = [
                    v for v in variants 
                    if v.get('clinical_significance') and 
                    ('pathogenic' in v['clinical_significance'].lower())
                ]
                return pathogenic_variants
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching pathogenic variants for {gene_symbol}: {e}")
            return []
    
    # Override the _make_request method to handle XML responses
    async def _make_request(self, method: str, endpoint: str, params=None, **kwargs):
        """Override to handle both JSON and XML responses from NCBI."""
        url = self._build_url(endpoint)
        
        # Use the parent's rate limiting and retry logic
        await self.rate_limiter.acquire()
        
        import aiohttp
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.request(method, url, params=params, **kwargs) as response:
                if response.status == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'xml' in content_type or endpoint.endswith('efetch.fcgi'):
                        # Return XML as text
                        return await response.text()
                    else:
                        # Return JSON
                        return await response.json()
                else:
                    error_text = await response.text()
                    raise APIError(
                        f"NCBI API error: {response.status} - {error_text}",
                        status_code=response.status
                    )