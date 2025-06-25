"""
Database connection and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
import logging

from .config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Database engine configuration
if settings.database_url.startswith("sqlite"):
    # SQLite configuration (for testing)
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.debug
    )
else:
    # PostgreSQL configuration (for production)
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.debug
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI.
    Creates a new database session for each request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all database tables."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully!")


def drop_tables() -> None:
    """Drop all database tables (use with caution!)."""
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("All tables dropped!")


def init_db() -> None:
    """Initialize database with tables and initial data."""
    create_tables()
    
    # Add initial pharmacogenomic genes
    from ..models.genes import PharmacoGene
    from sqlalchemy.orm import Session
    
    db = SessionLocal()
    try:
        # Check if we already have data
        existing_genes = db.query(PharmacoGene).count()
        if existing_genes > 0:
            logger.info(f"Database already initialized with {existing_genes} genes")
            return
        
        # Insert initial pharmacogenomic genes
        initial_genes = [
            {
                "gene_symbol": "CYP2D6",
                "ensembl_id": "ENSG00000100197",
                "description": "Cytochrome P450 2D6 - metabolizes ~25% of prescription drugs",
                "drug_classes": ["antidepressants", "antipsychotics", "opioids", "beta-blockers"],
                "clinical_importance": "high"
            },
            {
                "gene_symbol": "CYP2C19", 
                "ensembl_id": "ENSG00000165841",
                "description": "Cytochrome P450 2C19 - metabolizes proton pump inhibitors and clopidogrel",
                "drug_classes": ["proton pump inhibitors", "antiplatelet agents", "antidepressants"],
                "clinical_importance": "high"
            },
            {
                "gene_symbol": "CYP2C9",
                "ensembl_id": "ENSG00000138109", 
                "description": "Cytochrome P450 2C9 - metabolizes warfarin and NSAIDs",
                "drug_classes": ["anticoagulants", "NSAIDs", "antidiabetics"],
                "clinical_importance": "high"
            },
            {
                "gene_symbol": "DPYD",
                "ensembl_id": "ENSG00000188641",
                "description": "Dihydropyrimidine dehydrogenase - metabolizes 5-fluorouracil",
                "drug_classes": ["antineoplastics", "pyrimidine analogs"],
                "clinical_importance": "critical"
            },
            {
                "gene_symbol": "TPMT",
                "ensembl_id": "ENSG00000137364",
                "description": "Thiopurine S-methyltransferase - metabolizes thiopurine drugs",
                "drug_classes": ["immunosuppressants", "antineoplastics"],
                "clinical_importance": "critical"
            },
            {
                "gene_symbol": "SLCO1B1",
                "ensembl_id": "ENSG00000134538",
                "description": "Solute carrier organic anion transporter - transports statins",
                "drug_classes": ["statins", "HMG-CoA reductase inhibitors"],
                "clinical_importance": "moderate"
            },
            {
                "gene_symbol": "UGT1A1",
                "ensembl_id": "ENSG00000241635",
                "description": "UDP glucuronosyltransferase - metabolizes irinotecan",
                "drug_classes": ["antineoplastics", "topoisomerase inhibitors"],
                "clinical_importance": "high"
            },
            {
                "gene_symbol": "VKORC1",
                "ensembl_id": "ENSG00000167397",
                "description": "Vitamin K epoxide reductase complex subunit 1 - warfarin target",
                "drug_classes": ["anticoagulants", "vitamin K antagonists"],
                "clinical_importance": "high"
            }
        ]
        
        for gene_data in initial_genes:
            gene = PharmacoGene(**gene_data)
            db.add(gene)
        
        db.commit()
        logger.info(f"Initialized database with {len(initial_genes)} pharmacogenomic genes")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()