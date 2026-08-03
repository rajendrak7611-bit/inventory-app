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

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
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

