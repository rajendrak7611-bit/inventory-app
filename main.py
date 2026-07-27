from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from database import engine, get_db, Base
from models import Product, PartMaster, Machine, Operator

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

class MachineBase(BaseModel):
    name: str

class MachineCreate(MachineBase):
    pass

class MachineResponse(MachineBase):
    id: int

    class Config:
        from_attributes = True

class OperatorBase(BaseModel):
    name: str
    department: str

class OperatorCreate(OperatorBase):
    pass

class OperatorResponse(OperatorBase):
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

# --- Machine API Routes ---

@app.get("/api/machines", response_model=List[MachineResponse])
def read_machines(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Machine).offset(skip).limit(limit).all()

@app.post("/api/machines", response_model=MachineResponse)
def create_machine(machine: MachineCreate, db: Session = Depends(get_db)):
    db_machine = Machine(**machine.model_dump())
    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)
    return db_machine

@app.put("/api/machines/{machine_id}", response_model=MachineResponse)
def update_machine(machine_id: int, machine: MachineCreate, db: Session = Depends(get_db)):
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    for key, value in machine.model_dump().items():
        setattr(db_machine, key, value)
    db.commit()
    db.refresh(db_machine)
    return db_machine

@app.delete("/api/machines/{machine_id}")
def delete_machine(machine_id: int, db: Session = Depends(get_db)):
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    db.delete(db_machine)
    db.commit()
    return {"message": "Machine deleted successfully"}

# --- Operator API Routes ---

@app.get("/api/operators", response_model=List[OperatorResponse])
def read_operators(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Operator).offset(skip).limit(limit).all()

@app.post("/api/operators", response_model=OperatorResponse)
def create_operator(operator: OperatorCreate, db: Session = Depends(get_db)):
    db_operator = Operator(**operator.model_dump())
    db.add(db_operator)
    db.commit()
    db.refresh(db_operator)
    return db_operator

@app.put("/api/operators/{operator_id}", response_model=OperatorResponse)
def update_operator(operator_id: int, operator: OperatorCreate, db: Session = Depends(get_db)):
    db_operator = db.query(Operator).filter(Operator.id == operator_id).first()
    if not db_operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    for key, value in operator.model_dump().items():
        setattr(db_operator, key, value)
    db.commit()
    db.refresh(db_operator)
    return db_operator

@app.delete("/api/operators/{operator_id}")
def delete_operator(operator_id: int, db: Session = Depends(get_db)):
    db_operator = db.query(Operator).filter(Operator.id == operator_id).first()
    if not db_operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    db.delete(db_operator)
    db.commit()
    return {"message": "Operator deleted successfully"}

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")
