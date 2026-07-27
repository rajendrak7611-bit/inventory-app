from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from database import engine, get_db, Base
from models import Product, PartMaster

# Ensure tables are created (just in case they aren't)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Inventory Management API")

# Pydantic schemas for data validation
class ProductBase(BaseModel):
    family: str
    spec: str
    make: str
    stock: int
    price: float

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int

    class Config:
        from_attributes = True

class PartMasterBase(BaseModel):
    family: str
    forge_pn: str
    partno: str

class PartMasterCreate(PartMasterBase):
    pass

class PartMasterResponse(PartMasterBase):
    id: int

    class Config:
        from_attributes = True

# API Routes
@app.get("/api/products", response_model=List[ProductResponse])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    products = db.query(Product).offset(skip).limit(limit).all()
    return products

@app.post("/api/products", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.put("/api/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product: ProductCreate, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for key, value in product.model_dump().items():
        setattr(db_product, key, value)
        
    db.commit()
    db.refresh(db_product)
    return db_product

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"}

# --- Part Master API Routes ---

@app.get("/api/partmaster", response_model=List[PartMasterResponse])
def read_partmasters(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    parts = db.query(PartMaster).offset(skip).limit(limit).all()
    return parts

@app.post("/api/partmaster", response_model=PartMasterResponse)
def create_partmaster(part: PartMasterCreate, db: Session = Depends(get_db)):
    db_part = PartMaster(**part.model_dump())
    db.add(db_part)
    db.commit()
    db.refresh(db_part)
    return db_part

@app.put("/api/partmaster/{part_id}", response_model=PartMasterResponse)
def update_partmaster(part_id: int, part: PartMasterCreate, db: Session = Depends(get_db)):
    db_part = db.query(PartMaster).filter(PartMaster.id == part_id).first()
    if not db_part:
        raise HTTPException(status_code=404, detail="Part not found")
    
    for key, value in part.model_dump().items():
        setattr(db_part, key, value)
        
    db.commit()
    db.refresh(db_part)
    return db_part

@app.delete("/api/partmaster/{part_id}")
def delete_partmaster(part_id: int, db: Session = Depends(get_db)):
    db_part = db.query(PartMaster).filter(PartMaster.id == part_id).first()
    if not db_part:
        raise HTTPException(status_code=404, detail="Part not found")
    db.delete(db_part)
    db.commit()
    return {"message": "Part deleted successfully"}

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")
