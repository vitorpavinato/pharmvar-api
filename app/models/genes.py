"""
Database models for pharmacogenomic genes.
"""

from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import List, Optional, Dict, Any
import os

from ..core.database import Base

# Conditional import for PostgreSQL arrays
try:
    from sqlalchemy.dialects.postgresql import ARRAY
    HAS_POSTGRESQL = True
except ImportError:
    HAS_POSTGRESQL = False


def array_field():
    """Return appropriate field type for arrays based on database."""
    # For now, always use JSON for compatibility
    return JSON


class PharmacoGene(Base):
    """Model for pharmacogenomic genes."""
    
    __tablename__ = "pharmaco_genes"
    
    id = Column(Integer, primary_key=True, index=True)
    gene_symbol = Column(String(20), unique=True, index=True, nullable=False)
    ensembl_id = Column(String(50), unique=True, index=True)
    gene_name = Column(String(200))
    description = Column(Text)
    
    # Pharmacogenomic-specific fields
    drug_classes = array_field()  # Use JSON for compatibility
    clinical_importance = Column(String(20))  # "critical", "high", "moderate", "low"
    
    # Genomic location
    chromosome = Column(String(10))
    start_position = Column(Integer)
    end_position = Column(Integer)
    strand = Column(Integer)  # 1 or -1
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_updated_from_api = Column(DateTime(timezone=True))
    
    # Additional data from APIs (flexible JSON field)
    ensembl_data = Column(JSON)
    pharmvar_data = Column(JSON)
    
    # Relationships
    variants = relationship("GeneVariant", back_populates="gene", cascade="all, delete-orphan")
    drug_interactions = relationship("DrugInteraction", back_populates="gene")
    
    def __repr__(self) -> str:
        return f"<PharmacoGene(symbol='{self.gene_symbol}', ensembl_id='{self.ensembl_id}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "gene_symbol": self.gene_symbol,
            "ensembl_id": self.ensembl_id,
            "gene_name": self.gene_name,
            "description": self.description,
            "drug_classes": self.drug_classes,
            "clinical_importance": self.clinical_importance,
            "chromosome": self.chromosome,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "strand": self.strand,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_updated_from_api": self.last_updated_from_api.isoformat() if self.last_updated_from_api else None
        }


class GeneVariant(Base):
    """Model for genetic variants in pharmacogenomic genes."""
    
    __tablename__ = "gene_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    gene_id = Column(Integer, ForeignKey("pharmaco_genes.id"), nullable=False)
    
    # Variant identifiers
    variant_id = Column(String(100), index=True)  # e.g., "rs1065852"
    dbsnp_id = Column(String(50), index=True)
    clinvar_id = Column(String(50), index=True)
    
    # Genomic coordinates
    chromosome = Column(String(10))
    position = Column(Integer)
    reference_allele = Column(String(1000))  # Can be long for indels
    alternate_allele = Column(String(1000))
    
    # Variant consequences
    consequence_type = Column(String(100))  # "missense_variant", "stop_gained", etc.
    impact = Column(String(20))  # "high", "moderate", "low", "modifier"
    
    # Clinical data
    clinical_significance = Column(String(100))  # From ClinVar
    review_status = Column(String(100))  # ClinVar review status
    pathogenic_classification = Column(String(50))  # "pathogenic", "benign", etc.
    
    # Population frequencies
    population_frequencies = Column(JSON)  # Store allele frequencies by population
    
    # Pharmacogenomic annotations
    star_allele = Column(String(20))  # e.g., "*4", "*17" for CYP alleles
    functional_status = Column(String(50))  # "normal", "decreased", "poor", "increased"
    drug_response_phenotype = Column(String(100))
    
    # Associated conditions/diseases
    associated_conditions = array_field()  # Use JSON for compatibility
    
    # Raw API data
    ensembl_data = Column(JSON)
    clinvar_data = Column(JSON)
    pharmvar_data = Column(JSON)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_updated_from_api = Column(DateTime(timezone=True))
    
    # Relationships
    gene = relationship("PharmacoGene", back_populates="variants")
    
    def __repr__(self) -> str:
        return f"<GeneVariant(id='{self.variant_id}', gene='{self.gene.gene_symbol if self.gene else 'N/A'}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "gene_id": self.gene_id,
            "variant_id": self.variant_id,
            "dbsnp_id": self.dbsnp_id,
            "clinvar_id": self.clinvar_id,
            "chromosome": self.chromosome,
            "position": self.position,
            "reference_allele": self.reference_allele,
            "alternate_allele": self.alternate_allele,
            "consequence_type": self.consequence_type,
            "impact": self.impact,
            "clinical_significance": self.clinical_significance,
            "review_status": self.review_status,
            "pathogenic_classification": self.pathogenic_classification,
            "star_allele": self.star_allele,
            "functional_status": self.functional_status,
            "drug_response_phenotype": self.drug_response_phenotype,
            "associated_conditions": self.associated_conditions,
            "population_frequencies": self.population_frequencies,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class DrugInteraction(Base):
    """Model for drug-gene interactions."""
    
    __tablename__ = "drug_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    gene_id = Column(Integer, ForeignKey("pharmaco_genes.id"), nullable=False)
    
    # Drug information
    drug_name = Column(String(200), nullable=False, index=True)
    drug_class = Column(String(100))
    atc_code = Column(String(20))  # Anatomical Therapeutic Chemical code
    
    # Interaction details
    interaction_type = Column(String(100))  # "metabolism", "transport", "target"
    mechanism = Column(Text)  # Description of the mechanism
    
    # Clinical recommendations
    dosage_recommendation = Column(Text)
    contraindications = Column(Text)
    monitoring_requirements = Column(Text)
    
    # Evidence and guidelines
    evidence_level = Column(String(20))  # "A", "B", "C", "D" or "strong", "moderate", "weak"
    guideline_source = Column(String(100))  # FDA, EMA, CPIC, DPWG, etc.
    guideline_url = Column(String(500))
    
    # Affected populations/variants
    affected_genotypes = array_field()  # Use JSON for compatibility
    affected_phenotypes = array_field()  # Use JSON for compatibility
    
    # Additional data
    additional_info = Column(JSON)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    gene = relationship("PharmacoGene", back_populates="drug_interactions")
    
    def __repr__(self) -> str:
        return f"<DrugInteraction(drug='{self.drug_name}', gene='{self.gene.gene_symbol if self.gene else 'N/A'}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "gene_id": self.gene_id,
            "drug_name": self.drug_name,
            "drug_class": self.drug_class,
            "atc_code": self.atc_code,
            "interaction_type": self.interaction_type,
            "mechanism": self.mechanism,
            "dosage_recommendation": self.dosage_recommendation,
            "contraindications": self.contraindications,
            "monitoring_requirements": self.monitoring_requirements,
            "evidence_level": self.evidence_level,
            "guideline_source": self.guideline_source,
            "guideline_url": self.guideline_url,
            "affected_genotypes": self.affected_genotypes,
            "affected_phenotypes": self.affected_phenotypes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class AnalysisResult(Base):
    """Model for storing analysis results and reports."""
    
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Analysis metadata
    analysis_type = Column(String(50), nullable=False)  # "gene_analysis", "variant_batch", etc.
    analysis_name = Column(String(200))
    status = Column(String(20), default="running")  # "running", "completed", "failed"
    
    # Input parameters
    input_genes = array_field()  # Use JSON for compatibility
    input_variants = array_field()  # Use JSON for compatibility
    analysis_parameters = Column(JSON)
    
    # Results
    results_summary = Column(JSON)
    detailed_results = Column(JSON)
    
    # Statistics
    total_variants_analyzed = Column(Integer, default=0)
    pathogenic_variants_found = Column(Integer, default=0)
    drug_interactions_identified = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text)
    warnings = array_field()  # Use JSON for compatibility
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    processing_time_seconds = Column(Integer)
    
    def __repr__(self) -> str:
        return f"<AnalysisResult(type='{self.analysis_type}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "analysis_type": self.analysis_type,
            "analysis_name": self.analysis_name,
            "status": self.status,
            "input_genes": self.input_genes,
            "input_variants": self.input_variants,
            "results_summary": self.results_summary,
            "total_variants_analyzed": self.total_variants_analyzed,
            "pathogenic_variants_found": self.pathogenic_variants_found,
            "drug_interactions_identified": self.drug_interactions_identified,
            "error_message": self.error_message,
            "warnings": self.warnings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_time_seconds": self.processing_time_seconds
        }