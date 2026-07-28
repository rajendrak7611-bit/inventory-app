from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from database import engine, get_db, Base
from models import Product, PartMaster, Machine, Operator, PartOperation, Schedule

# Ensure tables are created (just in case they aren't)
Base.metadata.create_all(bind=engine)

# Lightweight migrations for adding columns safely
from sqlalchemy import text
with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
    try:
        conn.execute(text("ALTER TABLE part_masters ADD COLUMN department VARCHAR;"))
        conn.execute(text("CREATE INDEX ix_part_masters_department ON part_masters (department);"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE part_masters ADD COLUMN va VARCHAR;"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE machines ADD COLUMN department VARCHAR;"))
        conn.execute(text("CREATE INDEX ix_machines_department ON machines (department);"))
    except Exception:
        pass

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
    family: Optional[str] = ""
    forge_pn: Optional[str] = ""
    partno: Optional[str] = ""
    department: Optional[str] = ""
    va: Optional[str] = ""

class PartMasterCreate(PartMasterBase):
    pass

class PartMasterResponse(PartMasterBase):
    id: int

    class Config:
        from_attributes = True

class PartOperationBase(BaseModel):
    opn_no: Optional[str] = ""
    description: Optional[str] = ""
    machine: Optional[str] = ""
    cycle_time: Optional[float] = 0.0

class PartOperationCreate(PartOperationBase):
    pass

class PartOperationResponse(PartOperationBase):
    id: int
    part_id: int

    class Config:
        from_attributes = True

class BulkImportPart(BaseModel):
    family: Optional[str] = ""
    forge_pn: Optional[str] = ""
    partno: Optional[str] = ""
    department: Optional[str] = ""
    va: Optional[str] = ""
    operations: List[PartOperationBase]

class BulkImportPayload(BaseModel):
    parts: List[BulkImportPart]



class MachineBase(BaseModel):
    name: str
    department: Optional[str] = ""

class MachineCreate(MachineBase):
    pass

class MachineResponse(MachineBase):
    id: int

    class Config:
        from_attributes = True

class OperatorBase(BaseModel):
    name: str
    department: Optional[str] = ""

class BulkImportMachinePayload(BaseModel):
    machines: List[MachineBase]

class BulkImportOperatorPayload(BaseModel):
    operators: List[OperatorBase]

class OperatorCreate(OperatorBase):
    pass

class OperatorResponse(OperatorBase):
    id: int

    class Config:
        from_attributes = True

class ScheduleBase(BaseModel):
    department: Optional[str] = ""
    partno: str
    target_date: str
    qty: int
    status: Optional[str] = "Pending"

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleResponse(ScheduleBase):
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

# --- Part Operations Routes ---
@app.get("/api/partmaster/{part_id}/operations", response_model=List[PartOperationResponse])
def get_part_operations(part_id: int, db: Session = Depends(get_db)):
    operations = db.query(PartOperation).filter(PartOperation.part_id == part_id).order_by(PartOperation.id).all()
    return operations

@app.put("/api/partmaster/{part_id}/operations")
def update_part_operations(part_id: int, operations: List[PartOperationCreate], db: Session = Depends(get_db)):
    db_part = db.query(PartMaster).filter(PartMaster.id == part_id).first()
    if not db_part:
        raise HTTPException(status_code=404, detail="Part not found")
    
    # Delete existing operations for this part
    db.query(PartOperation).filter(PartOperation.part_id == part_id).delete()
    
    # Add new operations
    for op in operations:
        db_op = PartOperation(**op.model_dump(), part_id=part_id)
        db.add(db_op)
    
    db.commit()
    return {"message": "Operations updated successfully"}

@app.post("/api/partmaster/bulk_import")
def bulk_import_partmaster(payload: BulkImportPayload, db: Session = Depends(get_db)):
    for part_data in payload.parts:
        # Overwrite existing part if partno matches
        existing_part = db.query(PartMaster).filter(PartMaster.partno == part_data.partno).first()
        if existing_part:
            existing_part.family = part_data.family
            existing_part.forge_pn = part_data.forge_pn
            existing_part.department = part_data.department
            existing_part.va = part_data.va
            db.query(PartOperation).filter(PartOperation.part_id == existing_part.id).delete()
            db.commit()
            part_id = existing_part.id
        else:
            new_part = PartMaster(family=part_data.family, forge_pn=part_data.forge_pn, partno=part_data.partno, department=part_data.department, va=part_data.va)
            db.add(new_part)
            db.commit()
            db.refresh(new_part)
            part_id = new_part.id
            
        for op_data in part_data.operations:
            new_op = PartOperation(**op_data.model_dump(), part_id=part_id)
            db.add(new_op)
            
    db.commit()
    return {"message": "Import successful"}

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

@app.post("/api/machines/bulk_import")
def bulk_import_machines(payload: BulkImportMachinePayload, db: Session = Depends(get_db)):
    for machine_data in payload.machines:
        existing = db.query(Machine).filter(Machine.name == machine_data.name).first()
        if existing:
            existing.department = machine_data.department
        else:
            db.add(Machine(**machine_data.model_dump()))
    db.commit()
    return {"message": "Import successful"}

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

@app.post("/api/operators/bulk_import")
def bulk_import_operators(payload: BulkImportOperatorPayload, db: Session = Depends(get_db)):
    for op_data in payload.operators:
        existing = db.query(Operator).filter(Operator.name == op_data.name).first()
        if existing:
            existing.department = op_data.department
        else:
            db.add(Operator(**op_data.model_dump()))
    db.commit()
    return {"message": "Import successful"}

# --- Schedule API Routes ---

@app.get("/api/schedule", response_model=List[ScheduleResponse])
def read_schedules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Schedule).offset(skip).limit(limit).all()

@app.post("/api/schedule", response_model=ScheduleResponse)
def create_schedule(schedule: ScheduleCreate, db: Session = Depends(get_db)):
    db_schedule = Schedule(**schedule.model_dump())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")
