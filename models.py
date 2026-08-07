from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Float, DateTime
from datetime import datetime
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="admin")
    accessible_screens = Column(String, default="")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    family = Column(String, index=True)
    spec = Column(String)
    make = Column(String, index=True)
    stock = Column(Integer, default=0)
    price = Column(Numeric(10, 2))

class PartMaster(Base):
    __tablename__ = "part_masters"

    id = Column(Integer, primary_key=True, index=True)
    family = Column(String, index=True)
    forge_pn = Column(String, index=True)
    partno = Column(String, index=True)
    customer = Column(String, index=True)
    department = Column(String, index=True)
    va = Column(String)

    operations = relationship("PartOperation", back_populates="part", cascade="all, delete-orphan")

class PartOperation(Base):
    __tablename__ = "part_operations"

    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("part_masters.id", ondelete="CASCADE"), index=True)
    opn_no = Column(String)
    description = Column(String)
    machine = Column(String)
    cycle_time = Column(Float)

    part = relationship("PartMaster", back_populates="operations")

class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    department = Column(String, index=True)

class Operator(Base):
    __tablename__ = "operators"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    department = Column(String, index=True)
    designation = Column(String, default="Operator", nullable=True)

class Setter(Base):
    __tablename__ = "setters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    department = Column(String, index=True)

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    hours = Column(Float, default=8.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    details = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    department = Column(String, index=True)
    partno = Column(String, index=True)
    target_date = Column(String, index=True)
    qty = Column(Integer)
    completed_qty = Column(Integer, default=0)
    status = Column(String, default="Pending")

from datetime import datetime
from sqlalchemy import DateTime

class ProductionLog(Base):
    __tablename__ = "production_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    dept = Column(String, index=True)
    date = Column(String)
    shift = Column(String)
    setter = Column(String)
    machine = Column(String)
    operator = Column(String)
    partno = Column(String, index=True)
    opn_no = Column(String)
    description = Column(String)
    runtime = Column(Float)
    cycle_time = Column(Float)
    target_qty = Column(Float)
    prod_qty = Column(Float)
    efficiency = Column(Float)
    idle_hours = Column(Float)
    idle_reason = Column(String)
    idle_hours_2 = Column(Float)
    idle_reason_2 = Column(String)
    idle_hours_3 = Column(Float)
    idle_reason_3 = Column(String)
    multiple_mc = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

class RawMaterial(Base):
    __tablename__ = "raw_materials"
    id = Column(Integer, primary_key=True, index=True)
    forge_pn = Column(String, index=True)
    receipt = Column(Integer, default=0)
    despatch = Column(Integer, default=0)
    stock = Column(Integer, default=0)

class RawMaterialLog(Base):
    __tablename__ = "raw_material_logs"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String) # 'receipt' or 'despatch'
    date = Column(String)
    forge_pn = Column(String)
    dc_no = Column(String, nullable=True)
    finish_part_no = Column(String, nullable=True)
    qty = Column(Integer, default=0)

class HTLog(Base):
    __tablename__ = "ht_logs"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String)
    dc_no = Column(String, nullable=True)
    vendor = Column(String, index=True)
    partno = Column(String, index=True)
    qty = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class HTReceiptLog(Base):
    __tablename__ = "ht_receipt_logs"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String)
    vendor = Column(String, index=True)
    partno = Column(String, index=True)
    qty = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_name = Column(String, index=True)
    dept = Column(String, index=True)
    designation = Column(String, nullable=True)
    month_year = Column(String, index=True)
    day = Column(Integer)
    hours = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class InsertMaster(Base):
    __tablename__ = "insert_masters"

    id = Column(Integer, primary_key=True, index=True)
    insert_spec = Column(String, index=True, nullable=True)
    no_of_edges = Column(Integer, default=1)
    name = Column(String, index=True, nullable=True)
    specification = Column(String, nullable=True)
    grade = Column(String, nullable=True)
    make = Column(String, nullable=True)
    stock = Column(Integer, default=0)
    price = Column(Numeric(10, 2), default=0.00)

class DrillMaster(Base):
    __tablename__ = "drill_masters"

    id = Column(Integer, primary_key=True, index=True)
    drill_size = Column(String, index=True, nullable=True)
    sl_no = Column(String, index=True, nullable=True)
    resharp_count = Column(Integer, default=0)
    name = Column(String, nullable=True)
    size_dia = Column(String, nullable=True)
    specification = Column(String, nullable=True)
    make = Column(String, nullable=True)
    stock = Column(Integer, default=0)
    price = Column(Numeric(10, 2), default=0.00)

class InsertReceipt(Base):
    __tablename__ = "insert_receipts"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)
    supplier = Column(String, index=True, nullable=True)
    insert_spec = Column(String, index=True)
    batch_no = Column(String, nullable=True)
    qty = Column(Integer, default=0)
    rate = Column(Numeric(10, 2), default=0.00)
    created_at = Column(DateTime, default=datetime.utcnow)

class InsertIssue(Base):
    __tablename__ = "insert_issues"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)
    department = Column(String, index=True, nullable=True)
    insert_spec = Column(String, index=True)
    batch_no = Column(String, nullable=True)
    qty_issued = Column(Integer, default=0)
    machine = Column(String, nullable=True)
    operator = Column(String, nullable=True)
    partno = Column(String, nullable=True)
    opn_no = Column(String, nullable=True)
    receipt_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


