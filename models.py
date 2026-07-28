from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base

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
    department = Column(String, index=True)

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
