#!/usr/bin/env python3
"""
Script to test API clients functionality.
Run this to verify that the API integrations are working correctly.
"""

import asyncio
import json
import logging
from pathlib import Path
import sys

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.clients.ensembl_client import EnsemblClient, PharmacoEnsemblClient
from app.clients.clinvar_client import ClinVarClient


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_ensembl_basic():
    """Test basic Ensembl API functionality."""
    logger.info("🧬 Testing Ensembl API...")
    
    client = EnsemblClient()
    
    # Test health check
    logger.info("Testing health check...")
    is_healthy = await client.health_check()
    logger.info(f"API Health: {'✅ OK' if is_healthy else '❌ FAILED'}")
    
    if not is_healthy:
        logger.error("Ensembl API is not accessible. Skipping other tests.")
        return False
    
    # Test gene lookup by symbol
    logger.info("Testing gene lookup by symbol (CYP2D6)...")
    try:
        gene_info = await client.get_gene_by_symbol("CYP2D6")
        logger.info(f"✅ Gene ID: {gene_info.get('id')}")
        logger.info(f"✅ Description: {gene_info.get('description', 'N/A')[:100]}...")
        logger.info(f"✅ Location: {gene_info.get('seq_region_name')}:{gene_info.get('start')}-{gene_info.get('end')}")
    except Exception as e:
        logger.error(f"❌ Gene lookup failed: {e}")
        return False
    
    # Test variant consequences
    logger.info("Testing variant consequences (rs1065852 - CYP2D6*4)...")
    try:
        variant_info = await client.get_variant_consequences("rs1065852")
        logger.info(f"✅ Variant found: {variant_info.get('name')}")
        
        # Check if we have consequence data
        transcript_consequences = variant_info.get('transcript_consequences', [])
        if transcript_consequences:
            first_consequence = transcript_consequences[0]
            consequences = first_consequence.get('consequence_terms', [])
            logger.info(f"✅ Consequences: {', '.join(consequences)}")
        else:
            logger.info("⚠️  No transcript consequences found")
            
    except Exception as e:
        logger.error(f"❌ Variant lookup failed: {e}")
        return False
    
    logger.info("✅ Basic Ensembl tests completed successfully!")
    return True


async def test_pharmaco_ensembl():
    """Test pharmacogenomic-specific Ensembl functionality."""
    logger.info("💊 Testing Pharmacogenomic Ensembl client...")
    
    client = PharmacoEnsemblClient()
    
    # Test pharmaco gene info
    logger.info("Testing CYP2D6 pharmacogenomic info...")
    try:
        cyp2d6_info = await client.get_pharmaco_gene_info("CYP2D6")
        logger.info(f"✅ Gene: {cyp2d6_info.get('display_name')}")
        
        pharmaco_info = cyp2d6_info.get('pharmaco_relevance', {})
        logger.info(f"✅ Function: {pharmaco_info.get('function')}")
        logger.info(f"✅ Drugs: {pharmaco_info.get('drugs')}")
        
    except Exception as e:
        logger.error(f"❌ Pharmaco gene lookup failed: {e}")
        return False
    
    # Test getting variants for CYP2D6
    logger.info("Testing CYP2D6 variants...")
    try:
        gene_id = "ENSG00000100197"  # CYP2D6
        variants = await client.get_gene_variants(
            gene_id, 
            consequence_types=["missense_variant", "stop_gained", "splice_donor_variant"]
        )
        
        logger.info(f"✅ Found {len(variants)} variants with specified consequences")
        
        # Show a few examples
        for i, variant in enumerate(variants[:3]):
            logger.info(f"   Variant {i+1}: {variant.get('id')} - {variant.get('consequence_type')}")
            
    except Exception as e:
        logger.error(f"❌ Variant search failed: {e}")
        return False
    
    logger.info("✅ Pharmacogenomic Ensembl tests completed successfully!")
    return True


async def test_all_pharmaco_genes():
    """Test getting info for all pharmacogenomic genes."""
    logger.info("🧬💊 Testing all pharmacogenomic genes...")
    
    client = PharmacoEnsemblClient()
    
    try:
        all_genes = await client.get_all_pharmaco_genes()
        
        logger.info(f"✅ Retrieved info for {len(all_genes)} pharmacogenomic genes:")
        
        for gene_symbol, gene_info in all_genes.items():
            if "error" in gene_info:
                logger.error(f"   ❌ {gene_symbol}: {gene_info['error']}")
            else:
                gene_name = gene_info.get('display_name', 'Unknown')
                logger.info(f"   ✅ {gene_symbol}: {gene_name}")
                
    except Exception as e:
        logger.error(f"❌ All genes test failed: {e}")
        return False
    
    logger.info("✅ All pharmacogenomic genes test completed!")
    return True


async def test_clinvar_basic():
    """Test basic ClinVar API functionality."""
    logger.info("🏥 Testing ClinVar API...")
    
    client = ClinVarClient()
    
    # Test health check
    logger.info("Testing ClinVar health check...")
    is_healthy = await client.health_check()
    logger.info(f"API Health: {'✅ OK' if is_healthy else '❌ FAILED'}")
    
    if not is_healthy:
        logger.error("ClinVar API is not accessible. Skipping other tests.")
        return False
    
    # Test variant lookup by RS ID
    logger.info("Testing variant lookup by RS ID (rs1065852)...")
    try:
        variants = await client.search_variant_by_rs("rs1065852")
        
        if variants:
            logger.info(f"✅ Found {len(variants)} ClinVar record(s)")
            
            # Show details of first variant
            first_variant = variants[0]
            logger.info(f"✅ Clinical significance: {first_variant.get('clinical_significance', 'N/A')}")
            logger.info(f"✅ Review status: {first_variant.get('review_status', 'N/A')}")
            
            conditions = first_variant.get('conditions', [])
            if conditions:
                logger.info(f"✅ Associated conditions: {', '.join(conditions[:3])}")
            else:
                logger.info("⚠️  No associated conditions found")
        else:
            logger.info("⚠️  No ClinVar records found for rs1065852")
            
    except Exception as e:
        logger.error(f"❌ ClinVar variant lookup failed: {e}")
        return False
    
    # Test gene-based search
    logger.info("Testing gene-based variant search (CYP2D6)...")
    try:
        gene_variants = await client.search_variant_by_gene("CYP2D6", limit=5)
        
        if gene_variants:
            logger.info(f"✅ Found {len(gene_variants)} CYP2D6 variants in ClinVar")
            
            # Show clinical significance distribution
            clin_sigs = [v.get('clinical_significance', 'Unknown') for v in gene_variants]
            unique_sigs = set(clin_sigs)
            logger.info(f"✅ Clinical significances: {', '.join(unique_sigs)}")
        else:
            logger.info("⚠️  No CYP2D6 variants found in ClinVar")
            
    except Exception as e:
        logger.error(f"❌ Gene variant search failed: {e}")
        return False
    
    logger.info("✅ Basic ClinVar tests completed successfully!")
    return True


async def test_clinvar_pathogenic():
    """Test ClinVar pathogenic variant search."""
    logger.info("🔴 Testing ClinVar pathogenic variants...")
    
    client = ClinVarClient()
    
    try:
        # Test with a gene known to have pathogenic variants
        pathogenic_variants = await client.get_pathogenic_variants("DPYD")
        
        if pathogenic_variants:
            logger.info(f"✅ Found {len(pathogenic_variants)} pathogenic DPYD variants")
            
            # Show some examples
            for i, variant in enumerate(pathogenic_variants[:3]):
                name = variant.get('preferred_name', 'Unknown')
                significance = variant.get('clinical_significance', 'Unknown')
                logger.info(f"   Variant {i+1}: {name} - {significance}")
        else:
            logger.info("⚠️  No pathogenic DPYD variants found")
            
    except Exception as e:
        logger.error(f"❌ Pathogenic variant search failed: {e}")
        return False
    
    logger.info("✅ ClinVar pathogenic test completed!")
    return True
    """Test getting info for all pharmacogenomic genes."""
    logger.info("🧬💊 Testing all pharmacogenomic genes...")
    
    client = PharmacoEnsemblClient()
    
    try:
        all_genes = await client.get_all_pharmaco_genes()
        
        logger.info(f"✅ Retrieved info for {len(all_genes)} pharmacogenomic genes:")
        
        for gene_symbol, gene_info in all_genes.items():
            if "error" in gene_info:
                logger.error(f"   ❌ {gene_symbol}: {gene_info['error']}")
            else:
                gene_name = gene_info.get('display_name', 'Unknown')
                logger.info(f"   ✅ {gene_symbol}: {gene_name}")
                
    except Exception as e:
        logger.error(f"❌ All genes test failed: {e}")
        return False
    
    logger.info("✅ All pharmacogenomic genes test completed!")
    return True


async def performance_test():
    """Test API performance and rate limiting."""
    logger.info("⚡ Testing API performance and rate limiting...")
    
    client = EnsemblClient()
    
    # Test multiple concurrent requests
    gene_symbols = ["CYP2D6", "CYP2C19", "DPYD", "TPMT", "SLCO1B1"]
    
    import time
    start_time = time.time()
    
    try:
        tasks = [client.get_gene_by_symbol(symbol) for symbol in gene_symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        successful = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"✅ Completed {successful}/{len(gene_symbols)} requests in {duration:.2f} seconds")
        logger.info(f"✅ Average time per request: {duration/len(gene_symbols):.2f} seconds")
        
        # Check for rate limiting errors
        rate_limit_errors = sum(1 for r in results if isinstance(r, Exception) and "rate" in str(r).lower())
        if rate_limit_errors > 0:
            logger.warning(f"⚠️  {rate_limit_errors} rate limiting errors encountered")
        else:
            logger.info("✅ No rate limiting issues detected")
            
    except Exception as e:
        logger.error(f"❌ Performance test failed: {e}")
        return False
    
    logger.info("✅ Performance test completed!")
    return True


async def main():
    """Run all API tests."""
    logger.info("🚀 Starting PharmVar API Explorer tests...")
    
    tests = [
        ("Basic Ensembl API", test_ensembl_basic),
        ("Pharmacogenomic Ensembl", test_pharmaco_ensembl),
        ("All Pharmaco Genes", test_all_pharmaco_genes),
        ("Basic ClinVar API", test_clinvar_basic),
        ("ClinVar Pathogenic Variants", test_clinvar_pathogenic),
        ("Performance Test", performance_test),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info('='*50)
        
        try:
            success = await test_func()
            results[test_name] = success
        except Exception as e:
            logger.error(f"❌ Test {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("📊 TEST SUMMARY")
    logger.info('='*50)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 All tests passed! APIs are working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. Check the logs above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)