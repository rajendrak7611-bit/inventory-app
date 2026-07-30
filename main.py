import hashlib
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel

from database import engine, get_db, Base
from models import Product, PartMaster, Machine, Operator, PartOperation, Schedule, ProductionLog, User

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
        conn.execute(text("UPDATE schedules SET status = 'Pending' WHERE status = 'Completed';"))
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

# Seed default admin user
with Session(engine) as db:
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        hashed = hashlib.sha256("admin123".encode()).hexdigest()
        new_admin = User(username="admin", password_hash=hashed, role="admin", accessible_screens='["users","rawmaterial","products","partmaster","machines","operators","schedule","status","prodlog","debur","inspection"]')
        db.add(new_admin)
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

@app.delete("/api/schedule")
def clear_all_schedules(db: Session = Depends(get_db)):
    db.query(Schedule).delete()
    db.commit()
    return {"message": "All schedules cleared"}
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
        part = db.query(PartMaster).filter(PartMaster.partno == schedule.partno).first()
        if part:
            last_op = db.query(PartOperation).filter(PartOperation.part_id == part.id).order_by(PartOperation.id.desc()).first()
            if last_op and log.opn_no == last_op.opn_no:
                # Sum all production for this last operation
                logs = db.query(ProductionLog).filter(
                    ProductionLog.partno == schedule.partno,
                    ProductionLog.opn_no == last_op.opn_no
                ).all()
                total_prod = sum((l.prod_qty or 0) for l in logs)
                if total_prod >= schedule.qty:
                    schedule.status = "Completed"
                    db.commit()
            
    return db_log

@app.get("/api/prodlog")
def get_prodlogs(db: Session = Depends(get_db)):
    return db.query(ProductionLog).order_by(ProductionLog.id.desc()).all()

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
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    hashed = hashlib.sha256(req.password.encode()).hexdigest()
    if hashed != user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    return {
        "message": "Success", 
        "username": user.username, 
        "role": user.role,
        "accessible_screens": user.accessible_screens
    }

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")
