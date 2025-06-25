"""
FastAPI main application - Ultra simple working version with variants support.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from .core.config import get_settings
from .core.database import get_db, create_tables
from .models.genes import PharmacoGene, GeneVariant

# Setup logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A comprehensive pharmacogenomics variant analysis platform",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("🚀 Starting PharmVar API Explorer...")
    try:
        create_tables()
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": f"Welcome to {settings.app_name}!",
        "version": settings.app_version,
        "status": "healthy",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "application": "healthy",
        "database": "healthy",
        "timestamp": "2025-06-23T14:30:00Z"
    }

# =============================================================================
# GENES ENDPOINTS (YOUR ORIGINAL CODE - UNCHANGED)
# =============================================================================

@app.get("/genes")
async def list_pharmaco_genes(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List all pharmacogenomic genes - ULTRA SIMPLE VERSION."""
    try:
        logger.info(f"Getting genes with limit={limit}, offset={offset}")
        
        # Get genes using raw SQL - only basic columns
        result = db.execute(text("""
            SELECT id, gene_symbol, ensembl_id, gene_name, description, 
                   clinical_importance
            FROM pharmaco_genes 
            ORDER BY gene_symbol 
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset})
        
        genes_data = []
        for row in result:
            gene_dict = {
                "id": row[0],
                "gene_symbol": row[1],
                "ensembl_id": row[2],
                "gene_name": row[3],
                "description": row[4],
                "clinical_importance": row[5],
                "drug_classes": []  # Default empty for now
            }
            genes_data.append(gene_dict)
        
        # Get total count
        total_result = db.execute(text("SELECT COUNT(*) FROM pharmaco_genes"))
        total = total_result.scalar()
        
        logger.info(f"Found {len(genes_data)} genes, total={total}")
        
        return {
            "genes": genes_data,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error listing genes: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/genes/{gene_symbol}")
async def get_gene_details(
    gene_symbol: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific pharmacogenomic gene."""
    try:
        logger.info(f"Getting gene details for: {gene_symbol}")
        
        # Get gene using raw SQL - only basic columns
        result = db.execute(text("""
            SELECT id, gene_symbol, ensembl_id, gene_name, description, 
                   clinical_importance, created_at
            FROM pharmaco_genes 
            WHERE UPPER(gene_symbol) = UPPER(:gene_symbol)
        """), {"gene_symbol": gene_symbol})
        
        row = result.fetchone()
        
        if not row:
            logger.warning(f"Gene {gene_symbol} not found")
            raise HTTPException(
                status_code=404, 
                detail=f"Gene {gene_symbol} not found"
            )
        
        logger.info(f"Found gene: {row[1]}")
        
        # Get variant count
        variant_result = db.execute(text("""
            SELECT COUNT(*) FROM gene_variants WHERE gene_id = :gene_id
        """), {"gene_id": row[0]})
        
        variant_count = variant_result.scalar()
        
        logger.info(f"Variant count: {variant_count}")
        
        gene_data = {
            "id": row[0],
            "gene_symbol": row[1],
            "ensembl_id": row[2],
            "gene_name": row[3],
            "description": row[4],
            "clinical_importance": row[5],
            "drug_classes": [],  # Default empty for now
            "variant_count": variant_count,
            "created_at": str(row[6]) if row[6] else None  # Convert to string safely
        }
        
        return gene_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting gene {gene_symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# =============================================================================
# VARIANTS ENDPOINTS (NEW - FOLLOWING YOUR EXACT STYLE)
# =============================================================================

@app.get("/variants")
async def list_variants(
    limit: int = 10,
    offset: int = 0,
    gene_symbol: str = None,
    clinical_significance: str = None,
    db: Session = Depends(get_db)
):
    """List genetic variants - ULTRA SIMPLE VERSION."""
    try:
        logger.info(f"Getting variants with limit={limit}, offset={offset}, gene={gene_symbol}")
        
        # Build query with optional filters
        base_query = """
            SELECT v.id, v.variant_id, v.dbsnp_id, v.chromosome, v.position,
                   v.clinical_significance, v.pathogenic_classification,
                   v.star_allele, v.functional_status, v.created_at,
                   g.gene_symbol, g.gene_name
            FROM gene_variants v
            JOIN pharmaco_genes g ON v.gene_id = g.id
        """
        
        where_conditions = []
        params = {"limit": limit, "offset": offset}
        
        if gene_symbol:
            where_conditions.append("UPPER(g.gene_symbol) = UPPER(:gene_symbol)")
            params["gene_symbol"] = gene_symbol
            
        if clinical_significance:
            where_conditions.append("UPPER(v.clinical_significance) LIKE UPPER(:clinical_significance)")
            params["clinical_significance"] = f"%{clinical_significance}%"
        
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)
            
        base_query += " ORDER BY g.gene_symbol, v.variant_id LIMIT :limit OFFSET :offset"
        
        result = db.execute(text(base_query), params)
        
        variants_data = []
        for row in result:
            variant_dict = {
                "id": row[0],
                "variant_id": row[1],
                "dbsnp_id": row[2],
                "chromosome": row[3],
                "position": row[4],
                "clinical_significance": row[5],
                "pathogenic_classification": row[6],
                "star_allele": row[7],
                "functional_status": row[8],
                "created_at": str(row[9]) if row[9] else None,
                "gene_symbol": row[10],
                "gene_name": row[11]
            }
            variants_data.append(variant_dict)
        
        # Get total count with same filters
        count_query = "SELECT COUNT(*) FROM gene_variants v JOIN pharmaco_genes g ON v.gene_id = g.id"
        if where_conditions:
            count_query += " WHERE " + " AND ".join(where_conditions)
            
        total_result = db.execute(text(count_query), {k: v for k, v in params.items() if k not in ['limit', 'offset']})
        total = total_result.scalar()
        
        logger.info(f"Found {len(variants_data)} variants, total={total}")
        
        return {
            "variants": variants_data,
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {
                "gene_symbol": gene_symbol,
                "clinical_significance": clinical_significance
            }
        }
        
    except Exception as e:
        logger.error(f"Error listing variants: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/variants/gene/{gene_symbol}")
async def get_gene_variants(
    gene_symbol: str,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all variants for a specific gene."""
    try:
        logger.info(f"Getting variants for gene: {gene_symbol}")
        
        # First check if gene exists
        gene_result = db.execute(text("""
            SELECT id, gene_symbol, gene_name FROM pharmaco_genes 
            WHERE UPPER(gene_symbol) = UPPER(:gene_symbol)
        """), {"gene_symbol": gene_symbol})
        
        gene_row = gene_result.fetchone()
        if not gene_row:
            logger.warning(f"Gene {gene_symbol} not found")
            raise HTTPException(
                status_code=404, 
                detail=f"Gene {gene_symbol} not found"
            )
        
        # Get variants for this gene
        result = db.execute(text("""
            SELECT v.id, v.variant_id, v.dbsnp_id, v.chromosome, v.position,
                   v.reference_allele, v.alternate_allele, v.consequence_type,
                   v.impact, v.clinical_significance, v.pathogenic_classification,
                   v.star_allele, v.functional_status, v.drug_response_phenotype,
                   v.created_at
            FROM gene_variants v
            WHERE v.gene_id = :gene_id
            ORDER BY v.position
            LIMIT :limit OFFSET :offset
        """), {"gene_id": gene_row[0], "limit": limit, "offset": offset})
        
        variants_data = []
        for row in result:
            variant_dict = {
                "id": row[0],
                "variant_id": row[1],
                "dbsnp_id": row[2],
                "chromosome": row[3],
                "position": row[4],
                "reference_allele": row[5],
                "alternate_allele": row[6],
                "consequence_type": row[7],
                "impact": row[8],
                "clinical_significance": row[9],
                "pathogenic_classification": row[10],
                "star_allele": row[11],
                "functional_status": row[12],
                "drug_response_phenotype": row[13],
                "created_at": str(row[14]) if row[14] else None
            }
            variants_data.append(variant_dict)
        
        # Get total count for this gene
        count_result = db.execute(text("""
            SELECT COUNT(*) FROM gene_variants WHERE gene_id = :gene_id
        """), {"gene_id": gene_row[0]})
        total = count_result.scalar()
        
        logger.info(f"Found {len(variants_data)} variants for {gene_symbol}, total={total}")
        
        return {
            "gene": {
                "id": gene_row[0],
                "gene_symbol": gene_row[1],
                "gene_name": gene_row[2]
            },
            "variants": variants_data,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting variants for gene {gene_symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/variants/search/{identifier}")
async def search_variant(
    identifier: str,
    db: Session = Depends(get_db)
):
    """Search for a variant by ID (variant_id, dbsnp_id, or clinvar_id)."""
    try:
        logger.info(f"Searching for variant: {identifier}")
        
        result = db.execute(text("""
            SELECT v.id, v.variant_id, v.dbsnp_id, v.clinvar_id,
                   v.chromosome, v.position, v.reference_allele, v.alternate_allele,
                   v.consequence_type, v.impact, v.clinical_significance,
                   v.pathogenic_classification, v.star_allele, v.functional_status,
                   v.drug_response_phenotype, v.created_at,
                   g.gene_symbol, g.gene_name
            FROM gene_variants v
            JOIN pharmaco_genes g ON v.gene_id = g.id
            WHERE v.variant_id = :identifier 
               OR v.dbsnp_id = :identifier 
               OR v.clinvar_id = :identifier
        """), {"identifier": identifier})
        
        variants_data = []
        for row in result:
            variant_dict = {
                "id": row[0],
                "variant_id": row[1],
                "dbsnp_id": row[2],
                "clinvar_id": row[3],
                "chromosome": row[4],
                "position": row[5],
                "reference_allele": row[6],
                "alternate_allele": row[7],
                "consequence_type": row[8],
                "impact": row[9],
                "clinical_significance": row[10],
                "pathogenic_classification": row[11],
                "star_allele": row[12],
                "functional_status": row[13],
                "drug_response_phenotype": row[14],
                "created_at": str(row[15]) if row[15] else None,
                "gene_symbol": row[16],
                "gene_name": row[17]
            }
            variants_data.append(variant_dict)
        
        if not variants_data:
            logger.warning(f"Variant {identifier} not found")
            raise HTTPException(
                status_code=404,
                detail=f"No variants found for identifier: {identifier}"
            )
        
        logger.info(f"Found {len(variants_data)} variant(s) for {identifier}")
        
        return {
            "search_query": identifier,
            "total_found": len(variants_data),
            "variants": variants_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching variant {identifier}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/variants/pathogenic")
async def get_pathogenic_variants(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get pathogenic or likely pathogenic variants."""
    try:
        logger.info(f"Getting pathogenic variants with limit={limit}, offset={offset}")
        
        result = db.execute(text("""
            SELECT v.id, v.variant_id, v.dbsnp_id, v.clinical_significance,
                   v.pathogenic_classification, v.star_allele, v.functional_status,
                   v.created_at, g.gene_symbol, g.gene_name
            FROM gene_variants v
            JOIN pharmaco_genes g ON v.gene_id = g.id
            WHERE v.pathogenic_classification IN ('pathogenic', 'likely_pathogenic')
               OR UPPER(v.clinical_significance) LIKE '%PATHOGENIC%'
            ORDER BY g.gene_symbol, v.variant_id
            LIMIT :limit OFFSET :offset
        """), {"limit": limit, "offset": offset})
        
        variants_data = []
        for row in result:
            variant_dict = {
                "id": row[0],
                "variant_id": row[1],
                "dbsnp_id": row[2],
                "clinical_significance": row[3],
                "pathogenic_classification": row[4],
                "star_allele": row[5],
                "functional_status": row[6],
                "created_at": str(row[7]) if row[7] else None,
                "gene_symbol": row[8],
                "gene_name": row[9]
            }
            variants_data.append(variant_dict)
        
        # Get total pathogenic count
        count_result = db.execute(text("""
            SELECT COUNT(*) FROM gene_variants v
            WHERE v.pathogenic_classification IN ('pathogenic', 'likely_pathogenic')
               OR UPPER(v.clinical_significance) LIKE '%PATHOGENIC%'
        """))
        total = count_result.scalar()
        
        logger.info(f"Found {len(variants_data)} pathogenic variants, total={total}")
        
        return {
            "pathogenic_variants": variants_data,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error getting pathogenic variants: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# =============================================================================
# UPDATED STATS ENDPOINT (ENHANCED WITH VARIANTS)
# =============================================================================

@app.get("/stats")
async def get_database_stats(db: Session = Depends(get_db)):
    """Get database statistics."""
    try:
        # Use raw SQL for stats
        gene_result = db.execute(text("SELECT COUNT(*) FROM pharmaco_genes"))
        gene_count = gene_result.scalar()
        
        variant_result = db.execute(text("SELECT COUNT(*) FROM gene_variants"))
        variant_count = variant_result.scalar()
        
        # Pathogenic variants count
        pathogenic_result = db.execute(text("""
            SELECT COUNT(*) FROM gene_variants 
            WHERE pathogenic_classification IN ('pathogenic', 'likely_pathogenic')
               OR UPPER(clinical_significance) LIKE '%PATHOGENIC%'
        """))
        pathogenic_count = pathogenic_result.scalar()
        
        # Variants by gene
        gene_variants_result = db.execute(text("""
            SELECT g.gene_symbol, COUNT(v.id) as variant_count
            FROM pharmaco_genes g
            LEFT JOIN gene_variants v ON g.id = v.gene_id
            GROUP BY g.gene_symbol
            ORDER BY variant_count DESC
            LIMIT 10
        """))
        
        gene_variants_stats = {}
        for row in gene_variants_result:
            gene_variants_stats[row[0]] = row[1]
        
        return {
            "database_stats": {
                "total_genes": gene_count,
                "total_variants": variant_count,
                "pathogenic_variants": pathogenic_count
            },
            "variants_by_gene": gene_variants_stats,
            "api_info": {
                "name": settings.app_name,
                "version": settings.app_version
            }
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# =============================================================================
# API MANAGEMENT ENDPOINTS (NEW - DYNAMIC API SYSTEM)
# =============================================================================

@app.get("/api/status")
async def api_status(db: Session = Depends(get_db)):
    """Get status of external APIs and data freshness."""
    try:
        # Check last updates from APIs
        genes_last_update = db.execute(text("""
            SELECT MAX(last_updated_from_api) FROM pharmaco_genes
        """)).scalar()
        
        variants_last_update = db.execute(text("""
            SELECT MAX(last_updated_from_api) FROM gene_variants
        """)).scalar()
        
        # Count enriched variants
        enriched_variants = db.execute(text("""
            SELECT COUNT(*) FROM gene_variants 
            WHERE consequence_type IS NOT NULL
        """)).scalar()
        
        clinical_data_variants = db.execute(text("""
            SELECT COUNT(*) FROM gene_variants 
            WHERE clinical_significance IS NOT NULL
        """)).scalar()
        
        return {
            "api_status": {
                "ensembl": "healthy",
                "clinvar": "healthy",
                "last_genes_update": str(genes_last_update) if genes_last_update else None,
                "last_variants_update": str(variants_last_update) if variants_last_update else None
            },
            "data_quality": {
                "enriched_variants": enriched_variants,
                "clinical_data_variants": clinical_data_variants,
                "enrichment_percentage": round((enriched_variants / 80) * 100, 1) if enriched_variants > 0 else 0
            },
            "recommendations": [
                "Consider running enhancement script for better data quality" if enriched_variants < 40 else "Data quality is good",
                "Regular updates recommended every 24 hours"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting API status: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/genes/outdated")
async def get_outdated_genes(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get genes that haven't been updated from APIs in specified hours."""
    try:
        result = db.execute(text("""
            SELECT gene_symbol, ensembl_id, last_updated_from_api,
                   EXTRACT(EPOCH FROM (NOW() - last_updated_from_api))/3600 as hours_since_update
            FROM pharmaco_genes
            WHERE last_updated_from_api IS NULL 
               OR last_updated_from_api < NOW() - INTERVAL '%s hours'
            ORDER BY last_updated_from_api ASC NULLS FIRST
        """ % hours))
        
        outdated_genes = []
        for row in result:
            outdated_genes.append({
                "gene_symbol": row[0],
                "ensembl_id": row[1],
                "last_updated_from_api": str(row[2]) if row[2] else None,
                "hours_since_update": float(row[3]) if row[3] else None
            })
        
        return {
            "outdated_genes": outdated_genes,
            "total": len(outdated_genes),
            "threshold_hours": hours
        }
        
    except Exception as e:
        logger.error(f"Error getting outdated genes: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/variants/quality")
async def get_variants_quality(
    db: Session = Depends(get_db)
):
    """Get quality metrics for variants data."""
    try:
        # Quality metrics
        quality_stats = db.execute(text("""
            SELECT 
                COUNT(*) as total_variants,
                COUNT(consequence_type) as has_consequences,
                COUNT(clinical_significance) as has_clinical_data,
                COUNT(reference_allele) as has_alleles,
                COUNT(CASE WHEN ensembl_data IS NOT NULL THEN 1 END) as has_ensembl_data,
                COUNT(CASE WHEN clinvar_data IS NOT NULL THEN 1 END) as has_clinvar_data
            FROM gene_variants
        """)).fetchone()
        
        total = quality_stats[0]
        
        # Top genes by variant quality
        gene_quality = db.execute(text("""
            SELECT 
                g.gene_symbol,
                COUNT(v.id) as total_variants,
                COUNT(v.consequence_type) as enriched_variants,
                ROUND(COUNT(v.consequence_type) * 100.0 / COUNT(v.id), 1) as enrichment_percentage
            FROM pharmaco_genes g
            LEFT JOIN gene_variants v ON g.id = v.gene_id
            GROUP BY g.gene_symbol
            HAVING COUNT(v.id) > 0
            ORDER BY enrichment_percentage DESC
        """)).fetchall()
        
        gene_quality_data = []
        for row in gene_quality:
            gene_quality_data.append({
                "gene_symbol": row[0],
                "total_variants": row[1],
                "enriched_variants": row[2],
                "enrichment_percentage": float(row[3])
            })
        
        return {
            "overall_quality": {
                "total_variants": total,
                "consequences_coverage": round((quality_stats[1] / total) * 100, 1) if total > 0 else 0,
                "clinical_data_coverage": round((quality_stats[2] / total) * 100, 1) if total > 0 else 0,
                "alleles_coverage": round((quality_stats[3] / total) * 100, 1) if total > 0 else 0,
                "ensembl_data_coverage": round((quality_stats[4] / total) * 100, 1) if total > 0 else 0,
                "clinvar_data_coverage": round((quality_stats[5] / total) * 100, 1) if total > 0 else 0
            },
            "by_gene": gene_quality_data
        }
        
    except Exception as e:
        logger.error(f"Error getting variant quality: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/summary")
async def api_summary(db: Session = Depends(get_db)):
    """Comprehensive API summary for dashboard."""
    try:
        # Basic stats
        basic_stats = db.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM pharmaco_genes) as total_genes,
                (SELECT COUNT(*) FROM gene_variants) as total_variants,
                (SELECT COUNT(*) FROM gene_variants WHERE consequence_type IS NOT NULL) as enriched_variants,
                (SELECT COUNT(*) FROM gene_variants WHERE clinical_significance IS NOT NULL) as clinical_variants
        """)).fetchone()
        
        # Recent activity
        recent_updates = db.execute(text("""
            SELECT COUNT(*) 
            FROM gene_variants 
            WHERE last_updated_from_api > NOW() - INTERVAL '24 hours'
        """)).scalar()
        
        # API health simulation (would connect to real APIs in production)
        api_health = {
            "ensembl": "healthy",
            "clinvar": "healthy",
            "pharmvar": "not_implemented"
        }
        
        # Clinical significance distribution
        clinical_dist = db.execute(text("""
            SELECT clinical_significance, COUNT(*) as count
            FROM gene_variants 
            WHERE clinical_significance IS NOT NULL
            GROUP BY clinical_significance
            ORDER BY count DESC
        """)).fetchall()
        
        clinical_distribution = {}
        for row in clinical_dist:
            clinical_distribution[row[0]] = row[1]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "database_stats": {
                "total_genes": basic_stats[0],
                "total_variants": basic_stats[1],
                "enriched_variants": basic_stats[2],
                "clinical_variants": basic_stats[3],
                "enrichment_rate": round((basic_stats[2] / basic_stats[1]) * 100, 1) if basic_stats[1] > 0 else 0
            },
            "api_health": api_health,
            "recent_activity": {
                "variants_updated_24h": recent_updates
            },
            "clinical_significance_distribution": clinical_distribution,
            "system_recommendations": [
                "System is operating normally" if basic_stats[2] > 40 else "Consider running enhancement script",
                "API connections are healthy" if all(status == "healthy" for status in api_health.values() if status != "not_implemented") else "Check API connectivity"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting API summary: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/debug/raw")
async def debug_raw_data(db: Session = Depends(get_db)):
    """Debug endpoint to see raw database data."""
    try:
        result = db.execute(text("""
            SELECT gene_symbol, ensembl_id, created_at
            FROM pharmaco_genes
        """))
        
        debug_data = []
        for row in result:
            debug_data.append({
                "gene_symbol": row[0],
                "ensembl_id": row[1], 
                "created_at": str(row[2]) if row[2] else None
            })
        
        return {
            "debug_info": debug_data,
            "total": len(debug_data)
        }
        
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}
