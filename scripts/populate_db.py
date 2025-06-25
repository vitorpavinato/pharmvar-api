#!/usr/bin/env python3
"""
Script to populate the database with initial pharmacogenomic genes.
Run this after the containers are up and running.
"""

import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection (adjust if needed)
DATABASE_URL = "postgresql://pharmvar_user:pharmvar_pass@localhost:5432/pharmvar_db"

def populate_database():
    """Populate database with initial pharmacogenomic genes."""
    
    print("🔌 Connecting to database...")
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    
    try:
        db = SessionLocal()
        
        # Check if tables exist
        print("🔍 Checking if tables exist...")
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'pharmaco_genes'
            );
        """))
        
        table_exists = result.scalar()
        
        if not table_exists:
            print("❌ Table pharmaco_genes doesn't exist. Make sure the API created the tables first.")
            print("💡 Try: curl http://localhost:8000/health")
            return False
        
        print("✅ Tables exist!")
        
        # Check if we already have data
        count_result = db.execute(text("SELECT COUNT(*) FROM pharmaco_genes"))
        existing_count = count_result.scalar()
        
        if existing_count > 0:
            print(f"ℹ️  Database already has {existing_count} genes. Skipping population.")
            return True
        
        print("📊 Inserting sample pharmacogenomic genes...")
        
        # Insert sample genes
        genes_data = [
            ("CYP2D6", "ENSG00000100197", "Cytochrome P450 2D6", "Cytochrome P450 2D6 - metabolizes ~25% of prescription drugs", "high"),
            ("CYP2C19", "ENSG00000165841", "Cytochrome P450 2C19", "Cytochrome P450 2C19 - metabolizes proton pump inhibitors and clopidogrel", "high"),
            ("CYP2C9", "ENSG00000138109", "Cytochrome P450 2C9", "Cytochrome P450 2C9 - metabolizes warfarin and NSAIDs", "high"),
            ("DPYD", "ENSG00000188641", "Dihydropyrimidine dehydrogenase", "Dihydropyrimidine dehydrogenase - metabolizes 5-fluorouracil", "critical"),
            ("TPMT", "ENSG00000137364", "Thiopurine S-methyltransferase", "Thiopurine S-methyltransferase - metabolizes thiopurine drugs", "critical"),
            ("SLCO1B1", "ENSG00000134538", "Solute carrier organic anion transporter 1B1", "Solute carrier organic anion transporter - transports statins", "moderate"),
            ("UGT1A1", "ENSG00000241635", "UDP glucuronosyltransferase 1A1", "UDP glucuronosyltransferase - metabolizes irinotecan", "high"),
            ("VKORC1", "ENSG00000167397", "Vitamin K epoxide reductase complex subunit 1", "Vitamin K epoxide reductase complex subunit 1 - warfarin target", "high")
        ]
        
        for gene_symbol, ensembl_id, gene_name, description, clinical_importance in genes_data:
            try:
                db.execute(text("""
                    INSERT INTO pharmaco_genes (gene_symbol, ensembl_id, gene_name, description, clinical_importance, created_at) 
                    VALUES (:gene_symbol, :ensembl_id, :gene_name, :description, :clinical_importance, NOW())
                """), {
                    "gene_symbol": gene_symbol,
                    "ensembl_id": ensembl_id,
                    "gene_name": gene_name,
                    "description": description,
                    "clinical_importance": clinical_importance
                })
                
                print(f"   ✅ Added {gene_symbol}")
                
            except Exception as e:
                print(f"   ❌ Error adding {gene_symbol}: {e}")
        
        db.commit()
        print("🎉 Database population completed!")
        
        # Verify
        final_count = db.execute(text("SELECT COUNT(*) FROM pharmaco_genes")).scalar()
        print(f"📊 Total genes in database: {final_count}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 PharmVar Database Population Script")
    print("=" * 50)
    
    success = populate_database()
    
    if success:
        print("\n✅ Success! Test with:")
        print("   curl http://localhost:8000/genes")
        print("   curl http://localhost:8000/genes/CYP2D6")
    else:
        print("\n❌ Failed to populate database")
        
    sys.exit(0 if success else 1)