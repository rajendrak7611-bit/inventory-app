import hashlib
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, func, or_
from typing import List, Optional
from pydantic import BaseModel

from database import engine, get_db, Base
from models import Product, PartMaster, Machine, Operator, Setter, PartOperation, Schedule, ProductionLog, User, RawMaterial, RawMaterialLog, Department, Shift, Vendor, HTLog, HTReceiptLog, Attendance, InsertMaster, DrillMaster

# Ensure tables are created (just in case they aren't)
Base.metadata.create_all(bind=engine)

# Lightweight migrations for adding columns safely
with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
    try:
        conn.execute(text("ALTER TABLE part_masters ADD COLUMN department VARCHAR;"))
        conn.execute(text("CREATE INDEX ix_part_masters_department ON part_masters (department);"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE part_masters ADD COLUMN customer VARCHAR;"))
        conn.execute(text("CREATE INDEX ix_part_masters_customer ON part_masters (customer);"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE part_masters ADD COLUMN va VARCHAR;"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN accessible_screens VARCHAR DEFAULT '';"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE machines ADD COLUMN department VARCHAR;"))
        conn.execute(text("CREATE INDEX ix_machines_department ON machines (department);"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE schedules ADD COLUMN completed_qty INTEGER DEFAULT 0;"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE schedules ADD COLUMN status VARCHAR DEFAULT 'Pending';"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE production_logs ADD COLUMN cycle_time FLOAT DEFAULT 0.0;"))
    except:
        pass
    try:
        conn.execute(text("ALTER TABLE raw_material_logs ADD COLUMN dc_no VARCHAR;"))
    except:
        pass
    try:
        conn.execute(text("ALTER TABLE raw_material_logs ADD COLUMN finish_part_no VARCHAR;"))
    except:
        pass
    try:
        conn.execute(text("UPDATE schedules SET status = 'Pending';"))
        conn.execute(text("UPDATE schedules SET status = 'Completed' WHERE qty <= (SELECT COALESCE(SUM(prod_qty), 0) FROM production_logs WHERE production_logs.partno = schedules.partno AND opn_no = 'rfd');"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE production_logs ADD COLUMN idle_hours_2 FLOAT;"))
        conn.execute(text("ALTER TABLE production_logs ADD COLUMN idle_reason_2 VARCHAR;"))
        conn.execute(text("ALTER TABLE production_logs ADD COLUMN idle_hours_3 FLOAT;"))
        conn.execute(text("ALTER TABLE production_logs ADD COLUMN idle_reason_3 VARCHAR;"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE production_logs ADD COLUMN multiple_mc INTEGER DEFAULT 1;"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE insert_masters ADD COLUMN insert_spec VARCHAR;"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE insert_masters ADD COLUMN no_of_edges INTEGER DEFAULT 1;"))
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE operators ADD COLUMN designation VARCHAR DEFAULT 'Operator';"))
    except Exception:
        pass

# Seed default admin user
with Session(engine) as db:
    admin_user = db.query(User).filter(func.lower(User.username) == "admin").first()
    hashed = hashlib.sha256("admin123".encode()).hexdigest()
    if not admin_user:
        new_admin = User(username="admin", password_hash=hashed, role="admin", accessible_screens='["users","rawmaterial","products","partmaster","machines","operators","schedule","status","prodlog","debur","inspection"]')
        db.add(new_admin)
        db.commit()
    else:
        admin_user.password_hash = hashed
        db.commit()

app = FastAPI(title="Inventory Management API")

# Pydantic schemas for data validation
class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    accessible_screens: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    accessible_screens: str
    class Config:
        from_attributes = True

class RawMaterialBase(BaseModel):
    forge_pn: str
    receipt: Optional[int] = 0
    despatch: Optional[int] = 0
    stock: Optional[int] = 0

class RawMaterialCreate(RawMaterialBase):
    pass

class RawMaterialResponse(RawMaterialBase):
    id: int
    
    class Config:
        from_attributes = True

class RawMaterialLogBase(BaseModel):
    type: str
    date: str
    forge_pn: str
    dc_no: Optional[str] = None
    finish_part_no: Optional[str] = None
    qty: int

class RawMaterialLogCreate(RawMaterialLogBase):
    pass

class RawMaterialLogResponse(RawMaterialLogBase):
    id: int
    
    class Config:
        from_attributes = True

class BulkImportRmLogPayload(BaseModel):
    logs: List[RawMaterialLogBase]

class BulkImportRmPayload(BaseModel):
    rawmaterials: List[RawMaterialBase]

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
    customer: Optional[str] = ""
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
    designation: Optional[str] = "Operator"

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

class SetterBase(BaseModel):
    name: str
    department: Optional[str] = ""

class BulkImportSetterPayload(BaseModel):
    setters: List[SetterBase]

class SetterCreate(SetterBase):
    pass

class SetterResponse(SetterBase):
    id: int

    class Config:
        from_attributes = True

class AttendanceEntry(BaseModel):
    employee_name: str
    dept: Optional[str] = ""
    designation: Optional[str] = ""
    day: int
    hours: str

class AttendanceBulkPayload(BaseModel):
    month_year: str
    entries: List[AttendanceEntry]

class AttendanceResponse(BaseModel):
    id: int
    employee_name: str
    dept: Optional[str] = ""
    designation: Optional[str] = ""
    month_year: str
    day: int
    hours: str

    class Config:
        from_attributes = True

class DepartmentBase(BaseModel):
    name: str

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentResponse(DepartmentBase):
    id: int

    class Config:
        from_attributes = True

class ShiftBase(BaseModel):
    name: str
    hours: float

class ShiftCreate(ShiftBase):
    pass

class ShiftResponse(ShiftBase):
    id: int
    
    class Config:
        from_attributes = True

class VendorBase(BaseModel):
    name: str
    details: Optional[str] = None

class VendorCreate(VendorBase):
    pass

class VendorResponse(VendorBase):
    id: int
    
    class Config:
        from_attributes = True

class HTLogBase(BaseModel):
    date: str
    dc_no: Optional[str] = ""
    vendor: str
    partno: str
    qty: int

class HTLogCreate(HTLogBase):
    pass

class HTLogResponse(HTLogBase):
    id: int

    class Config:
        from_attributes = True

class HTReceiptLogBase(BaseModel):
    date: str
    vendor: str
    partno: str
    qty: int

class HTReceiptLogCreate(HTReceiptLogBase):
    pass

class HTReceiptLogResponse(HTReceiptLogBase):
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
def read_products(skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)):
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
def read_partmasters(skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)):
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
def read_machines(skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)):
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
def read_operators(skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)):
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
        existing = db.query(Operator).filter(func.lower(Operator.name) == op_data.name.lower().strip()).first()
        if existing:
            existing.department = op_data.department
            existing.designation = op_data.designation or "Operator"
        else:
            db.add(Operator(**op_data.model_dump()))
    db.commit()
    return {"message": "Import successful"}

# --- Setter API Routes ---
@app.get("/api/setters", response_model=List[SetterResponse])
def read_setters(skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)):
    return db.query(Setter).offset(skip).limit(limit).all()

@app.post("/api/setters", response_model=SetterResponse)
def create_setter(setter: SetterCreate, db: Session = Depends(get_db)):
    db_setter = Setter(**setter.model_dump())
    db.add(db_setter)
    db.commit()
    db.refresh(db_setter)
    return db_setter

@app.put("/api/setters/{setter_id}", response_model=SetterResponse)
def update_setter(setter_id: int, setter: SetterCreate, db: Session = Depends(get_db)):
    db_setter = db.query(Setter).filter(Setter.id == setter_id).first()
    if not db_setter:
        raise HTTPException(status_code=404, detail="Setter not found")
    for key, value in setter.model_dump().items():
        setattr(db_setter, key, value)
    db.commit()
    db.refresh(db_setter)
    return db_setter

@app.delete("/api/setters/{setter_id}")
def delete_setter(setter_id: int, db: Session = Depends(get_db)):
    db_setter = db.query(Setter).filter(Setter.id == setter_id).first()
    if not db_setter:
        raise HTTPException(status_code=404, detail="Setter not found")
    db.delete(db_setter)
    db.commit()
    return {"message": "Setter deleted successfully"}

# --- Department Endpoints ---
@app.get("/api/departments", response_model=List[DepartmentResponse])
def read_departments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Department).offset(skip).limit(limit).all()

@app.post("/api/departments", response_model=DepartmentResponse)
def create_department(department: DepartmentCreate, db: Session = Depends(get_db)):
    db_dept = Department(**department.model_dump())
    db.add(db_dept)
    db.commit()
    db.refresh(db_dept)
    return db_dept

@app.put("/api/departments/{dept_id}", response_model=DepartmentResponse)
def update_department(dept_id: int, department: DepartmentCreate, db: Session = Depends(get_db)):
    db_dept = db.query(Department).filter(Department.id == dept_id).first()
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    for key, value in department.model_dump().items():
        setattr(db_dept, key, value)
    db.commit()
    db.refresh(db_dept)
    return db_dept

@app.delete("/api/departments/{dept_id}")
def delete_department(dept_id: int, db: Session = Depends(get_db)):
    db_dept = db.query(Department).filter(Department.id == dept_id).first()
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    db.delete(db_dept)
    db.commit()
    return {"message": "Department deleted successfully"}

# --- Shift Endpoints ---
@app.get("/api/shifts", response_model=List[ShiftResponse])
def read_shifts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Shift).offset(skip).limit(limit).all()

@app.post("/api/shifts", response_model=ShiftResponse)
def create_shift(shift: ShiftCreate, db: Session = Depends(get_db)):
    db_shift = Shift(**shift.model_dump())
    db.add(db_shift)
    db.commit()
    db.refresh(db_shift)
    return db_shift

@app.put("/api/shifts/{shift_id}", response_model=ShiftResponse)
def update_shift(shift_id: int, shift: ShiftCreate, db: Session = Depends(get_db)):
    db_shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not db_shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    for key, value in shift.model_dump().items():
        setattr(db_shift, key, value)
    db.commit()
    db.refresh(db_shift)
    return db_shift

@app.delete("/api/shifts/{shift_id}")
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    db_shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not db_shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    db.delete(db_shift)
    db.commit()
    return {"message": "Shift deleted"}

# --- VENDOR ENDPOINTS ---
@app.get("/api/vendors", response_model=List[VendorResponse])
def get_vendors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Vendor).offset(skip).limit(limit).all()

@app.post("/api/vendors", response_model=VendorResponse)
def create_vendor(vendor: VendorCreate, db: Session = Depends(get_db)):
    db_vendor = Vendor(**vendor.model_dump())
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    return db_vendor

@app.put("/api/vendors/{vendor_id}", response_model=VendorResponse)
def update_vendor(vendor_id: int, vendor: VendorCreate, db: Session = Depends(get_db)):
    db_vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    for key, value in vendor.model_dump().items():
        setattr(db_vendor, key, value)
    db.commit()
    db.refresh(db_vendor)
    return db_vendor

@app.delete("/api/vendors/{vendor_id}")
def delete_vendor(vendor_id: int, db: Session = Depends(get_db)):
    db_vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    db.delete(db_vendor)
    db.commit()
    return {"message": "Vendor deleted successfully"}

# --- HT LOG ENDPOINTS ---
@app.get("/api/ht_logs", response_model=List[HTLogResponse])
def get_ht_logs(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    return db.query(HTLog).order_by(HTLog.id.desc()).offset(skip).limit(limit).all()

@app.post("/api/ht_logs", response_model=HTLogResponse)
def create_ht_log(log: HTLogCreate, db: Session = Depends(get_db)):
    db_log = HTLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@app.delete("/api/ht_logs/{log_id}")
def delete_ht_log(log_id: int, db: Session = Depends(get_db)):
    db_log = db.query(HTLog).filter(HTLog.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail="HT Log not found")
    db.delete(db_log)
    db.commit()
    return {"message": "HT log deleted"}

@app.get("/api/ht/spider_parts")
def get_spider_parts(db: Session = Depends(get_db)):
    pm_parts = db.query(PartMaster.partno).filter(func.lower(PartMaster.department) == "spider").distinct().all()
    pl_parts = db.query(ProductionLog.partno).filter(func.lower(ProductionLog.dept) == "spider").distinct().all()
    
    all_partnos = set([p[0] for p in pm_parts if p[0]] + [p[0] for p in pl_parts if p[0]])
    
    result = []
    for partno in sorted(all_partnos):
        prod_logs = db.query(ProductionLog).filter(
            ProductionLog.partno == partno,
            or_(
                func.lower(func.trim(ProductionLog.opn_no)) == '40',
                func.lower(func.trim(ProductionLog.opn_no)) == 'opn 40',
                func.lower(func.trim(ProductionLog.opn_no)) == 'opn40',
                func.lower(func.trim(ProductionLog.opn_no)) == '50',
                func.lower(func.trim(ProductionLog.opn_no)) == 'opn 50',
                func.lower(func.trim(ProductionLog.opn_no)) == 'opn50'
            )
        ).all()
        produced_qty = int(sum((l.prod_qty or 0) for l in prod_logs))
        
        ht_logs = db.query(HTLog).filter(HTLog.partno == partno).all()
        ht_sent_qty = int(sum((h.qty or 0) for h in ht_logs))
        
        available_qty = max(0, produced_qty - ht_sent_qty)
        
        result.append({
            "partno": partno,
            "department": "SPIDER",
            "produced_qty": produced_qty,
            "ht_sent_qty": ht_sent_qty,
            "available_qty": available_qty
        })
    return result

# --- HT RECEIPT ENDPOINTS ---
@app.get("/api/ht_receipt_logs", response_model=List[HTReceiptLogResponse])
def get_ht_receipt_logs(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    return db.query(HTReceiptLog).order_by(HTReceiptLog.id.desc()).offset(skip).limit(limit).all()

@app.post("/api/ht_receipt_logs", response_model=HTReceiptLogResponse)
def create_ht_receipt_log(log: HTReceiptLogCreate, db: Session = Depends(get_db)):
    db_log = HTReceiptLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@app.delete("/api/ht_receipt_logs/{log_id}")
def delete_ht_receipt_log(log_id: int, db: Session = Depends(get_db)):
    db_log = db.query(HTReceiptLog).filter(HTReceiptLog.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail="HT Receipt log not found")
    db.delete(db_log)
    db.commit()
    return {"message": "HT receipt log deleted"}

@app.get("/api/ht/vendor_pending_parts")
def get_vendor_pending_parts(db: Session = Depends(get_db)):
    dispatches = db.query(HTLog.vendor, HTLog.partno).distinct().all()
    result = []
    for vendor, partno in dispatches:
        if not vendor or not partno:
            continue
        
        sent_logs = db.query(HTLog).filter(HTLog.vendor == vendor, HTLog.partno == partno).all()
        sent_qty = int(sum((l.qty or 0) for l in sent_logs))
        
        rec_logs = db.query(HTReceiptLog).filter(HTReceiptLog.vendor == vendor, HTReceiptLog.partno == partno).all()
        rec_qty = int(sum((l.qty or 0) for l in rec_logs))
        
        pending_qty = max(0, sent_qty - rec_qty)
        
        result.append({
            "vendor": vendor,
            "partno": partno,
            "sent_qty": sent_qty,
            "received_qty": rec_qty,
            "pending_qty": pending_qty
        })
    return result

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
def read_schedules(skip: int = 0, limit: int = 10000, db: Session = Depends(get_db)):
    return db.query(Schedule).offset(skip).limit(limit).all()

@app.post("/api/schedule", response_model=ScheduleResponse)
def create_schedule(schedule: ScheduleCreate, db: Session = Depends(get_db)):
    db_schedule = Schedule(**schedule.model_dump())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@app.delete("/api/schedule")
def clear_all_schedules(db: Session = Depends(get_db)):
    db.query(Schedule).delete()
    db.commit()
    return {"ok": True}

@app.put("/api/schedule/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: int, schedule: ScheduleCreate, db: Session = Depends(get_db)):
    db_schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    for key, value in schedule.model_dump().items():
        setattr(db_schedule, key, value)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

@app.delete("/api/schedule/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    db_schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db.delete(db_schedule)
    db.commit()
    return {"ok": True}

@app.get("/api/schedule/run")
def get_run_schedule(db: Session = Depends(get_db)):
    from datetime import date, timedelta
    
    # 1. Fetch all pending schedules
    schedules = db.query(Schedule).filter(Schedule.status == "Pending").all()
    # Sort by target_date (assuming YYYY-MM-DD format from input date)
    schedules = sorted(schedules, key=lambda s: s.target_date)
    
    # 2. Track availability in working minutes from today
    machine_available_time = {}
    
    today = date.today()
    
    def get_calendar_date(working_minutes):
        # 1 working day = 21 hours = 1260 minutes
        working_days = int(working_minutes // 1260)
        current = today
        days_added = 0
        
        # We must add 'working_days' skipping Sundays
        while days_added < working_days:
            current += timedelta(days=1)
            if current.weekday() != 6: # 6 is Sunday
                days_added += 1
        return current.strftime("%d/%m")
        
    run_list = []
    
    for sched in schedules:
        # Fetch part operations for this schedule's partno
        part = db.query(PartMaster).filter(PartMaster.partno == sched.partno).first()
        if not part:
            continue
            
        operations = db.query(PartOperation).filter(PartOperation.part_id == part.id).order_by(PartOperation.id).all()
        
        prev_start_time = 0
        prev_end_time = 0
        prev_cycle_time = 0
        
        for op in operations:
            if not op.machine:
                continue
                
            # Calculate remaining qty for this specific operation
            logs = db.query(ProductionLog).filter(
                ProductionLog.partno == sched.partno,
                ProductionLog.opn_no == op.opn_no
            ).all()
            op_completed = sum((l.prod_qty or 0) for l in logs)
            remaining_qty = sched.qty - op_completed
            
            # If this specific operation is completed, skip it from the schedule run
            if remaining_qty <= 0:
                continue
                
            machine = op.machine
            mach_avail = machine_available_time.get(machine, 0)
            runtime_minutes = op.cycle_time * remaining_qty
            
            if prev_end_time == 0:
                # First operation for the part OR previous operations completed
                start_time = mach_avail
                end_time = start_time + runtime_minutes
            else:
                # Subsequent operations: Overlapping (transfer batch of 1 piece)
                earliest_start = prev_start_time + prev_cycle_time
                start_time = max(mach_avail, earliest_start)
                
                earliest_end = prev_end_time + op.cycle_time
                projected_end = start_time + runtime_minutes
                
                if projected_end < earliest_end:
                    # This operation is faster than the previous one.
                    # It would be starved if it started early. 
                    # Shift it to the end so it finishes at exactly the same time.
                    end_time = earliest_end
                    start_time = end_time - runtime_minutes
                    if start_time < mach_avail:
                        start_time = mach_avail
                        end_time = start_time + runtime_minutes
                else:
                    # Operation is slower or started late, runs continuously
                    end_time = projected_end
            
            # Update availability trackers
            machine_available_time[machine] = end_time
            
            prev_start_time = start_time
            prev_end_time = end_time
            prev_cycle_time = op.cycle_time
            
            run_list.append({
                "partno": sched.partno,
                "opn_no": op.opn_no,
                "description": op.description,
                "machine": machine,
                "qty": remaining_qty,
                "cycle_time": op.cycle_time,
                "runtime": round(runtime_minutes / 60, 2), # Runtime in hours
                "start_date": get_calendar_date(start_time),
                "end_date": get_calendar_date(end_time)
            })
            
    return run_list

class ProdLogCreate(BaseModel):
    dept: str
    date: str
    shift: str
    setter: str
    machine: str
    operator: str
    partno: str
    opn_no: str
    description: str
    runtime: float
    cycle_time: Optional[float] = 0.0
    target_qty: float
    prod_qty: float
    efficiency: float
    idle_hours: float
    idle_reason: str
    idle_hours_2: Optional[float] = 0.0
    idle_reason_2: Optional[str] = ""
    idle_hours_3: Optional[float] = 0.0
    idle_reason_3: Optional[str] = ""
    multiple_mc: Optional[int] = 1

@app.post("/api/prodlog")
def create_prodlog(log: ProdLogCreate, db: Session = Depends(get_db)):
    db_log = ProductionLog(**log.dict())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    
    # Check if we should mark the schedule as Completed
    schedule = db.query(Schedule).filter(Schedule.partno == log.partno, Schedule.status == "Pending").first()
    if schedule:
        if log.opn_no == 'rfd':
            logs = db.query(ProductionLog).filter(
                ProductionLog.partno == schedule.partno,
                ProductionLog.opn_no == 'rfd'
            ).all()
            total_prod = sum((l.prod_qty or 0) for l in logs)
            if total_prod >= schedule.qty:
                schedule.status = "Completed"
                db.commit()
            
    return db_log

@app.get("/api/prodlog")
def get_prodlogs(db: Session = Depends(get_db)):
    return db.query(ProductionLog).order_by(ProductionLog.id.desc()).all()

@app.delete("/api/prodlog/spider")
def delete_spider_prodlogs(db: Session = Depends(get_db)):
    spider_parts = [p.partno for p in db.query(PartMaster).filter(func.lower(PartMaster.department) == "spider").all()]
    deleted_count = db.query(ProductionLog).filter(
        or_(
            func.lower(ProductionLog.dept) == "spider",
            ProductionLog.partno.in_(spider_parts)
        )
    ).delete(synchronize_session=False)
    db.commit()
    return {"message": f"Successfully deleted {deleted_count} SPIDER production logs"}

class ProdLogDateUpdatePayload(BaseModel):
    date: str

@app.put("/api/prodlog/{log_id}")
def update_prodlog_date(log_id: int, payload: ProdLogDateUpdatePayload, db: Session = Depends(get_db)):
    db_log = db.query(ProductionLog).filter(ProductionLog.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail="Log not found")
    db_log.date = payload.date
    db.commit()
    db.refresh(db_log)
    return {"message": "Date updated successfully", "date": db_log.date}

@app.delete("/api/prodlog/{log_id}")
def delete_prodlog(log_id: int, db: Session = Depends(get_db)):
    db_log = db.query(ProductionLog).filter(ProductionLog.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail="Log not found")
    db.delete(db_log)
    db.commit()
    return {"message": "Log deleted"}

# --- RAW MATERIALS ENDPOINTS ---
@app.get("/api/rawmaterials", response_model=List[RawMaterialResponse])
def get_raw_materials(db: Session = Depends(get_db)):
    return db.query(RawMaterial).all()

@app.post("/api/rawmaterials", response_model=RawMaterialResponse)
def create_raw_material(rm: RawMaterialCreate, db: Session = Depends(get_db)):
    db_rm = RawMaterial(**rm.dict())
    db.add(db_rm)
    db.commit()
    db.refresh(db_rm)
    return db_rm

@app.put("/api/rawmaterials/{rm_id}", response_model=RawMaterialResponse)
def update_raw_material(rm_id: int, rm: RawMaterialCreate, db: Session = Depends(get_db)):
    db_rm = db.query(RawMaterial).filter(RawMaterial.id == rm_id).first()
    if not db_rm:
        raise HTTPException(status_code=404, detail="Raw Material not found")
    
    for key, value in rm.dict().items():
        setattr(db_rm, key, value)
        
    db.commit()
    db.refresh(db_rm)
    return db_rm

@app.delete("/api/rawmaterials/{rm_id}")
def delete_raw_material(rm_id: int, db: Session = Depends(get_db)):
    db_rm = db.query(RawMaterial).filter(RawMaterial.id == rm_id).first()
    if not db_rm:
        raise HTTPException(status_code=404, detail="Raw Material not found")
    db.delete(db_rm)
    db.commit()
    return {"message": "Raw Material deleted"}

@app.post("/api/rawmaterials/bulk")
def bulk_import_raw_materials(payload: BulkImportRmPayload, db: Session = Depends(get_db)):
    for rm in payload.rawmaterials:
        db_rm = db.query(RawMaterial).filter(RawMaterial.forge_pn == rm.forge_pn).first()
        if db_rm:
            db_rm.receipt = rm.receipt
            db_rm.despatch = rm.despatch
            db_rm.stock = rm.stock
        else:
            new_rm = RawMaterial(
                forge_pn=rm.forge_pn,
                receipt=rm.receipt,
                despatch=rm.despatch,
                stock=rm.stock
            )
            db.add(new_rm)
    db.commit()
    return {"message": f"Successfully processed {len(payload.rawmaterials)} raw materials"}

@app.get("/api/rawmateriallogs", response_model=List[RawMaterialLogResponse])
def get_raw_material_logs(db: Session = Depends(get_db)):
    return db.query(RawMaterialLog).all()

@app.post("/api/rawmateriallogs", response_model=RawMaterialLogResponse)
def create_raw_material_log(log: RawMaterialLogCreate, db: Session = Depends(get_db)):
    db_log = RawMaterialLog(**log.dict())
    db.add(db_log)
    
    # Update master RawMaterial
    master = db.query(RawMaterial).filter(RawMaterial.forge_pn == log.forge_pn).first()
    if not master:
        master = RawMaterial(forge_pn=log.forge_pn, receipt=0, despatch=0, stock=0)
        db.add(master)
        
    if log.type == 'receipt':
        master.receipt += log.qty
    elif log.type == 'despatch':
        master.despatch += log.qty
    master.stock = master.receipt - master.despatch
    
    db.commit()
    db.refresh(db_log)
    return db_log

@app.delete("/api/rawmateriallogs/{log_id}")
def delete_raw_material_log(log_id: int, db: Session = Depends(get_db)):
    db_log = db.query(RawMaterialLog).filter(RawMaterialLog.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail="Log record not found")
    
    master = db.query(RawMaterial).filter(RawMaterial.forge_pn == db_log.forge_pn).first()
    if master:
        if db_log.type == 'receipt':
            master.receipt = max(0, master.receipt - db_log.qty)
        elif db_log.type == 'despatch':
            master.despatch = max(0, master.despatch - db_log.qty)
        master.stock = master.receipt - master.despatch
        
    db.delete(db_log)
    db.commit()
    return {"message": "Log record deleted"}

@app.post("/api/rawmateriallogs/bulk")
def bulk_import_raw_material_logs(payload: BulkImportRmLogPayload, db: Session = Depends(get_db)):
    for log in payload.logs:
        db_log = RawMaterialLog(**log.dict())
        db.add(db_log)
        
        master = db.query(RawMaterial).filter(RawMaterial.forge_pn == log.forge_pn).first()
        if not master:
            master = RawMaterial(forge_pn=log.forge_pn, receipt=0, despatch=0, stock=0)
            db.add(master)
            
        if log.type == 'receipt':
            master.receipt += log.qty
        elif log.type == 'despatch':
            master.despatch += log.qty
        master.stock = master.receipt - master.despatch
        
    db.commit()
    return {"message": f"{len(payload.logs)} logs imported successfully"}

class UserPasswordChange(BaseModel):
    new_password: str

@app.get("/api/users", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@app.post("/api/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = hashlib.sha256(user.password.encode()).hexdigest()
    db_user = User(
        username=user.username,
        password_hash=hashed,
        role="operator",
        accessible_screens=user.accessible_screens
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

class UserUpdatePayload(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    accessible_screens: Optional[str] = None

@app.put("/api/users/{user_id}")
def update_user(user_id: int, payload: UserUpdatePayload, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if payload.username and payload.username.strip():
        db_user.username = payload.username.strip()
    if payload.password and payload.password.strip():
        db_user.password_hash = hashlib.sha256(payload.password.strip().encode()).hexdigest()
    if payload.accessible_screens is not None:
        db_user.accessible_screens = payload.accessible_screens
        
    db.commit()
    return {"message": f"User {db_user.username} updated successfully"}

@app.put("/api/users/{user_id}/password")
def change_user_password(user_id: int, payload: UserPasswordChange, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if not payload.new_password or not payload.new_password.strip():
        raise HTTPException(status_code=400, detail="Password cannot be empty")
    hashed = hashlib.sha256(payload.new_password.strip().encode()).hexdigest()
    db_user.password_hash = hashed
    db.commit()
    return {"message": f"Password updated for {db_user.username}"}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if db_user.username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete master admin")
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted"}

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    clean_username = (req.username or "").strip()
    clean_password = (req.password or "").strip()
    
    user = db.query(User).filter(func.lower(User.username) == clean_username.lower()).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    hashed = hashlib.sha256(clean_password.encode()).hexdigest()
    if hashed != user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    return {
        "message": "Success", 
        "username": user.username, 
        "role": user.role,
        "accessible_screens": user.accessible_screens
    }

# --- Attendance API Routes ---
@app.get("/api/attendance", response_model=List[AttendanceResponse])
def get_attendance(month_year: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Attendance)
    if month_year:
        query = query.filter(Attendance.month_year == month_year)
    return query.all()

@app.post("/api/attendance")
def save_attendance(payload: AttendanceBulkPayload, db: Session = Depends(get_db)):
    m_year = payload.month_year
    db.query(Attendance).filter(Attendance.month_year == m_year).delete()
    db.commit()

    new_records = []
    for entry in payload.entries:
        new_records.append(Attendance(
            employee_name=entry.employee_name,
            dept=entry.dept or "",
            designation=entry.designation or "",
            month_year=m_year,
            day=entry.day,
            hours=str(entry.hours)
        ))
    db.add_all(new_records)
    db.commit()
    return {"message": f"Attendance saved successfully for {m_year}"}

# --- Insert Master Schemas & Endpoints ---
class InsertMasterBase(BaseModel):
    insert_spec: str
    no_of_edges: Optional[int] = 1
    name: Optional[str] = ""
    specification: Optional[str] = ""
    grade: Optional[str] = ""
    make: Optional[str] = ""
    stock: Optional[int] = 0
    price: Optional[float] = 0.00

class InsertMasterCreate(InsertMasterBase):
    pass

class InsertMasterResponse(InsertMasterBase):
    id: int
    class Config:
        from_attributes = True

@app.get("/api/insert_masters", response_model=List[InsertMasterResponse])
def get_insert_masters(db: Session = Depends(get_db)):
    return db.query(InsertMaster).order_by(InsertMaster.id.desc()).all()

@app.post("/api/insert_masters", response_model=InsertMasterResponse)
def create_insert_master(item: InsertMasterCreate, db: Session = Depends(get_db)):
    db_item = InsertMaster(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.put("/api/insert_masters/{item_id}", response_model=InsertMasterResponse)
def update_insert_master(item_id: int, item: InsertMasterCreate, db: Session = Depends(get_db)):
    db_item = db.query(InsertMaster).filter(InsertMaster.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Insert Master item not found")
    for key, value in item.model_dump().items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

class BulkImportInsertMasterPayload(BaseModel):
    inserts: List[InsertMasterCreate]

@app.post("/api/insert_masters/bulk")
def bulk_import_insert_masters(payload: BulkImportInsertMasterPayload, db: Session = Depends(get_db)):
    new_items = []
    for item in payload.inserts:
        new_items.append(InsertMaster(**item.model_dump()))
    db.add_all(new_items)
    db.commit()
    return {"message": f"Successfully imported {len(new_items)} insert master records"}

@app.delete("/api/insert_masters/{item_id}")
def delete_insert_master(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(InsertMaster).filter(InsertMaster.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Insert Master item not found")
    db.delete(db_item)
    db.commit()
    return {"message": "Insert Master item deleted"}

# --- Drill Master Schemas & Endpoints ---
class DrillMasterBase(BaseModel):
    name: str
    size_dia: Optional[str] = ""
    specification: Optional[str] = ""
    make: Optional[str] = ""
    stock: Optional[int] = 0
    price: Optional[float] = 0.00

class DrillMasterCreate(DrillMasterBase):
    pass

class DrillMasterResponse(DrillMasterBase):
    id: int
    class Config:
        from_attributes = True

@app.get("/api/drill_masters", response_model=List[DrillMasterResponse])
def get_drill_masters(db: Session = Depends(get_db)):
    return db.query(DrillMaster).order_by(DrillMaster.id.desc()).all()

@app.post("/api/drill_masters", response_model=DrillMasterResponse)
def create_drill_master(item: DrillMasterCreate, db: Session = Depends(get_db)):
    db_item = DrillMaster(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.put("/api/drill_masters/{item_id}", response_model=DrillMasterResponse)
def update_drill_master(item_id: int, item: DrillMasterCreate, db: Session = Depends(get_db)):
    db_item = db.query(DrillMaster).filter(DrillMaster.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Drill Master item not found")
    for key, value in item.model_dump().items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/drill_masters/{item_id}")
def delete_drill_master(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(DrillMaster).filter(DrillMaster.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Drill Master item not found")
    db.delete(db_item)
    db.commit()
    return {"message": "Drill Master item deleted"}

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")
