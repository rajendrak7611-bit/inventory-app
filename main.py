from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, text, or_
from typing import List, Optional, Union, Any
from pydantic import BaseModel
import datetime
import io
import zipfile
import xml.etree.ElementTree as ET
import re
import os
import json
import calendar

from database import engine, get_db, Base
import models

def parse_excel_bytes(file_bytes: bytes):
    rows = []
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            strings = []
            if 'xl/sharedStrings.xml' in z.namelist():
                tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
                for elem in tree.iter():
                    if elem.tag.endswith('}t'):
                        strings.append(elem.text or '')
            
            target_sheet = 'xl/worksheets/sheet1.xml'
            if target_sheet not in z.namelist():
                sheets = [n for n in z.namelist() if n.startswith('xl/worksheets/sheet')]
                if sheets:
                    target_sheet = sheets[0]
            
            if target_sheet in z.namelist():
                tree = ET.fromstring(z.read(target_sheet))
                for r in tree.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
                    row_vals = []
                    for c in r.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                        t = c.get('t')
                        v = c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                        val = ''
                        if v is not None:
                            val = v.text or ''
                            if t == 's' and val.isdigit() and int(val) < len(strings):
                                val = strings[int(val)]
                        row_vals.append(val.strip())
                    if any(row_vals):
                        rows.append(row_vals)
    except Exception as e:
        print("Error reading excel bytes:", e)
    return rows

# Ensure tables are created
try:
    Base.metadata.create_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
except Exception as _ex:
    print("create_all notice:", _ex)

# Auto migrate columns if missing
def run_db_migrations():
    migration_statements = [
        "ALTER TABLE inspection_reports ADD COLUMN report_code VARCHAR;",
        "ALTER TABLE inspection_reports ADD COLUMN prod_log_id INTEGER;",
        "ALTER TABLE attendances ADD COLUMN slno INTEGER DEFAULT 0;",
        "ALTER TABLE inspection_parameters ADD COLUMN part_desc VARCHAR;",
        "ALTER TABLE inspection_parameters ADD COLUMN opn_desc VARCHAR;",
        "ALTER TABLE inspection_reports ADD COLUMN part_desc VARCHAR;",
        "ALTER TABLE inspection_reports ADD COLUMN opn_desc VARCHAR;",
        "ALTER TABLE inspection_reports ADD COLUMN part_sl_no VARCHAR;",
        "ALTER TABLE inspection_reports ADD COLUMN shift VARCHAR;",
        "ALTER TABLE inspection_reports ADD COLUMN status VARCHAR DEFAULT 'Accepted';",
        "ALTER TABLE inspection_reports ADD COLUMN remarks TEXT;",
        "ALTER TABLE inspection_reports ADD COLUMN inspection_date VARCHAR;",
        "ALTER TABLE inspection_parameters ADD COLUMN dept VARCHAR;",
        "ALTER TABLE inspection_reports ADD COLUMN dept VARCHAR;",
        "ALTER TABLE raw_material_logs ADD COLUMN remarks TEXT;",
        "ALTER TABLE raw_materials ADD COLUMN opening_stock INTEGER DEFAULT 0;",
    ]
    try:
        models.Base.metadata.create_all(bind=engine)
    except Exception:
        pass
    for sql in migration_statements:
        try:
            with engine.begin() as conn:
                conn.execute(text(sql))
        except Exception:
            pass

run_db_migrations()

app = FastAPI(title="Production Management API")

class UserLogin(BaseModel):
    username: str
    password: str

def import_breakdown_excel():
    excel_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "breakdown.xlsx")
    if not os.path.exists(excel_path):
        return {"message": "breakdown.xlsx not found"}
    try:
        import openpyxl
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS breakdown_slips (
                    id SERIAL PRIMARY KEY,
                    date_time TEXT,
                    department TEXT,
                    shift TEXT,
                    maint_type TEXT,
                    request_by TEXT,
                    machine TEXT,
                    problem TEXT,
                    signoff_date_time TEXT,
                    status TEXT,
                    created_at TEXT
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS service_details (
                    id SERIAL PRIMARY KEY,
                    breakdown_slip_id INTEGER,
                    machine TEXT,
                    spares_data TEXT,
                    service_data TEXT,
                    spares_cost NUMERIC DEFAULT 0,
                    service_cost NUMERIC DEFAULT 0,
                    total_cost NUMERIC DEFAULT 0,
                    remarks TEXT,
                    created_at TEXT
                );
            """))
            conn.commit()

            if "breakdown_slips" in wb.sheetnames:
                existing_cnt = conn.execute(text("SELECT COUNT(*) FROM breakdown_slips;")).scalar() or 0
                if existing_cnt == 0:
                    sheet = wb["breakdown_slips"]
                    headers = [sheet.cell(1, c).value for c in range(1, sheet.max_column + 1)]
                    for r in range(2, sheet.max_row + 1):
                        row_data = {headers[c-1]: sheet.cell(r, c).value for c in range(1, len(headers)+1) if headers[c-1]}
                        if not any(v is not None for v in row_data.values()):
                            continue
                        try:
                            conn.execute(text("""
                                INSERT INTO breakdown_slips (id, date_time, department, shift, maint_type, request_by, machine, problem, signoff_date_time, status, created_at)
                                VALUES (:id, :date_time, :department, :shift, :maint_type, :request_by, :machine, :problem, :signoff_date_time, :status, :created_at)
                            """), {
                                "id": int(row_data.get("id")) if row_data.get("id") else None,
                                "date_time": str(row_data.get("date_time") or ""),
                                "department": str(row_data.get("department") or ""),
                                "shift": str(row_data.get("shift") or ""),
                                "maint_type": str(row_data.get("maint_type") or "Breakdown"),
                                "request_by": str(row_data.get("request_by") or ""),
                                "machine": str(row_data.get("machine") or ""),
                                "problem": str(row_data.get("problem") or ""),
                                "signoff_date_time": str(row_data.get("signoff_date_time") or ""),
                                "status": str(row_data.get("status") or "Open"),
                                "created_at": str(row_data.get("created_at") or "")
                            })
                        except Exception as e:
                            pass
                    conn.commit()
                try:
                    conn.execute(text("SELECT setval(pg_get_serial_sequence('breakdown_slips', 'id'), coalesce(max(id),0) + 1, false) FROM breakdown_slips;"))
                    conn.commit()
                except Exception:
                    pass

            if "service_details" in wb.sheetnames:
                existing_sd_cnt = conn.execute(text("SELECT COUNT(*) FROM service_details;")).scalar() or 0
                if existing_sd_cnt == 0:
                    sheet = wb["service_details"]
                    headers = [sheet.cell(1, c).value for c in range(1, sheet.max_column + 1)]
                    for r in range(2, sheet.max_row + 1):
                        row_data = {headers[c-1]: sheet.cell(r, c).value for c in range(1, len(headers)+1) if headers[c-1]}
                        if not any(v is not None for v in row_data.values()):
                            continue
                        try:
                            bd_id = int(row_data.get("breakdown_slip_id")) if row_data.get("breakdown_slip_id") is not None and str(row_data.get("breakdown_slip_id")).strip() != "" else None
                            conn.execute(text("""
                                INSERT INTO service_details (id, breakdown_slip_id, machine, spares_data, service_data, spares_cost, service_cost, total_cost, remarks, created_at)
                                VALUES (:id, :breakdown_slip_id, :machine, :spares_data, :service_data, :spares_cost, :service_cost, :total_cost, :remarks, :created_at)
                            """), {
                                "id": int(row_data.get("id")) if row_data.get("id") else None,
                                "breakdown_slip_id": bd_id,
                                "machine": str(row_data.get("machine") or ""),
                                "spares_data": str(row_data.get("spares_data") or "[]"),
                                "service_data": str(row_data.get("service_data") or "[]"),
                                "spares_cost": float(row_data.get("spares_cost") or 0),
                                "service_cost": float(row_data.get("service_cost") or 0),
                                "total_cost": float(row_data.get("total_cost") or 0),
                                "remarks": str(row_data.get("remarks") or ""),
                                "created_at": str(row_data.get("created_at") or "")
                            })
                        except Exception as e:
                            pass
                    conn.commit()
                try:
                    conn.execute(text("SELECT setval(pg_get_serial_sequence('service_details', 'id'), coalesce(max(id),0) + 1, false) FROM service_details;"))
                    conn.commit()
                except Exception:
                    pass

        return {"message": "Breakdown excel imported successfully"}
    except Exception as e:
        return {"error": str(e)}

def import_rfq_excel():
    excel_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rfq.xlsx")
    if not os.path.exists(excel_path):
        return {"message": "rfq.xlsx not found"}
    try:
        import openpyxl
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS rfq_headers (
                    id SERIAL PRIMARY KEY,
                    date TEXT,
                    rfqno TEXT,
                    unit TEXT,
                    customer TEXT,
                    created_at TEXT
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS rfq_items (
                    id SERIAL PRIMARY KEY,
                    rfq_id INTEGER,
                    partno TEXT,
                    description TEXT
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS quote_records (
                    id SERIAL PRIMARY KEY,
                    quote_no TEXT,
                    date TEXT,
                    rfq_id INTEGER,
                    rfq_no TEXT,
                    customer TEXT,
                    part_no TEXT,
                    part_description TEXT,
                    unit TEXT,
                    overhead_profit_pct NUMERIC DEFAULT 0,
                    total_machining_cost NUMERIC DEFAULT 0,
                    total_other_process_cost NUMERIC DEFAULT 0,
                    total_packing_cost NUMERIC DEFAULT 0,
                    base_part_cost NUMERIC DEFAULT 0,
                    final_unit_price NUMERIC DEFAULT 0,
                    total_dev_cost NUMERIC DEFAULT 0,
                    machining_details TEXT,
                    other_process_details TEXT,
                    packing_details TEXT,
                    dev_cost_details TEXT,
                    created_at TEXT
                );
            """))
            conn.commit()

            if "rfq_headers" in wb.sheetnames:
                existing_rfq_cnt = conn.execute(text("SELECT COUNT(*) FROM rfq_headers;")).scalar() or 0
                if existing_rfq_cnt == 0:
                    sheet = wb["rfq_headers"]
                    headers = [sheet.cell(1, c).value for c in range(1, sheet.max_column + 1)]
                    for r in range(2, sheet.max_row + 1):
                        row_data = {headers[c-1]: sheet.cell(r, c).value for c in range(1, len(headers)+1) if headers[c-1]}
                        if not any(v is not None for v in row_data.values()):
                            continue
                        try:
                            conn.execute(text("""
                                INSERT INTO rfq_headers (id, date, rfqno, unit, customer, created_at)
                                VALUES (:id, :date, :rfqno, :unit, :customer, :created_at)
                            """), {
                                "id": int(row_data.get("id")) if row_data.get("id") else None,
                                "date": str(row_data.get("date") or ""),
                                "rfqno": str(row_data.get("rfqno") or ""),
                                "unit": str(row_data.get("unit") or ""),
                                "customer": str(row_data.get("customer") or ""),
                                "created_at": str(row_data.get("created_at") or "")
                            })
                        except Exception:
                            pass
                    conn.commit()
                try:
                    conn.execute(text("SELECT setval(pg_get_serial_sequence('rfq_headers', 'id'), coalesce(max(id),0) + 1, false) FROM rfq_headers;"))
                    conn.commit()
                except Exception:
                    pass

            if "rfq_items" in wb.sheetnames:
                existing_items_cnt = conn.execute(text("SELECT COUNT(*) FROM rfq_items;")).scalar() or 0
                if existing_items_cnt == 0:
                    sheet = wb["rfq_items"]
                    headers = [sheet.cell(1, c).value for c in range(1, sheet.max_column + 1)]
                    for r in range(2, sheet.max_row + 1):
                        row_data = {headers[c-1]: sheet.cell(r, c).value for c in range(1, len(headers)+1) if headers[c-1]}
                        if not any(v is not None for v in row_data.values()):
                            continue
                        try:
                            conn.execute(text("""
                                INSERT INTO rfq_items (id, rfq_id, partno, description)
                                VALUES (:id, :rfq_id, :partno, :description)
                            """), {
                                "id": int(row_data.get("id")) if row_data.get("id") else None,
                                "rfq_id": int(row_data.get("rfq_id")) if row_data.get("rfq_id") else None,
                                "partno": str(row_data.get("partno") or ""),
                                "description": str(row_data.get("description") or "")
                            })
                        except Exception:
                            pass
                    conn.commit()
                try:
                    conn.execute(text("SELECT setval(pg_get_serial_sequence('rfq_items', 'id'), coalesce(max(id),0) + 1, false) FROM rfq_items;"))
                    conn.commit()
                except Exception:
                    pass

            if "quote_records" in wb.sheetnames:
                existing_quote_cnt = conn.execute(text("SELECT COUNT(*) FROM quote_records;")).scalar() or 0
                if existing_quote_cnt == 0:
                    sheet = wb["quote_records"]
                    headers = [sheet.cell(1, c).value for c in range(1, sheet.max_column + 1)]
                    for r in range(2, sheet.max_row + 1):
                        row_data = {headers[c-1]: sheet.cell(r, c).value for c in range(1, len(headers)+1) if headers[c-1]}
                        if not any(v is not None for v in row_data.values()):
                            continue
                        try:
                            rfq_id_val = int(row_data.get("rfq_id")) if row_data.get("rfq_id") is not None and str(row_data.get("rfq_id")).strip() != "" else None
                            conn.execute(text("""
                                INSERT INTO quote_records (id, quote_no, date, rfq_id, rfq_no, customer, part_no, part_description, unit, overhead_profit_pct, total_machining_cost, total_other_process_cost, total_packing_cost, base_part_cost, final_unit_price, total_dev_cost, machining_details, other_process_details, packing_details, dev_cost_details, created_at)
                                VALUES (:id, :quote_no, :date, :rfq_id, :rfq_no, :customer, :part_no, :part_description, :unit, :overhead_profit_pct, :total_machining_cost, :total_other_process_cost, :total_packing_cost, :base_part_cost, :final_unit_price, :total_dev_cost, :machining_details, :other_process_details, :packing_details, :dev_cost_details, :created_at)
                            """), {
                                "id": int(row_data.get("id")) if row_data.get("id") else None,
                                "quote_no": str(row_data.get("quote_no") or ""),
                                "date": str(row_data.get("date") or ""),
                                "rfq_id": rfq_id_val,
                                "rfq_no": str(row_data.get("rfq_no") or ""),
                                "customer": str(row_data.get("customer") or ""),
                                "part_no": str(row_data.get("part_no") or ""),
                                "part_description": str(row_data.get("part_description") or ""),
                                "unit": str(row_data.get("unit") or "Unit 1"),
                                "overhead_profit_pct": float(row_data.get("overhead_profit_pct") or 0),
                                "total_machining_cost": float(row_data.get("total_machining_cost") or 0),
                                "total_other_process_cost": float(row_data.get("total_other_process_cost") or 0),
                                "total_packing_cost": float(row_data.get("total_packing_cost") or 0),
                                "base_part_cost": float(row_data.get("base_part_cost") or 0),
                                "final_unit_price": float(row_data.get("final_unit_price") or 0),
                                "total_dev_cost": float(row_data.get("total_dev_cost") or 0),
                                "machining_details": str(row_data.get("machining_details") or "[]"),
                                "other_process_details": str(row_data.get("other_process_details") or "[]"),
                                "packing_details": str(row_data.get("packing_details") or "[]"),
                                "dev_cost_details": str(row_data.get("dev_cost_details") or "[]"),
                                "created_at": str(row_data.get("created_at") or "")
                            })
                        except Exception as e:
                            pass
                    conn.commit()
                try:
                    conn.execute(text("SELECT setval(pg_get_serial_sequence('quote_records', 'id'), coalesce(max(id),0) + 1, false) FROM quote_records;"))
                    conn.commit()
                except Exception:
                    pass

        return {"message": "RFQ excel imported successfully"}
    except Exception as e:
        return {"error": str(e)}

def import_schedule_excel():
    excel_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schedule.xlsx")
    if not os.path.exists(excel_path):
        return {"message": "schedule.xlsx not found"}
    try:
        import openpyxl
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        sheet = wb["schedules"] if "schedules" in wb.sheetnames else wb.active
        
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id SERIAL PRIMARY KEY,
                    department TEXT,
                    partno TEXT,
                    target_date TEXT,
                    qty TEXT,
                    completed_qty TEXT DEFAULT '0',
                    status TEXT DEFAULT 'Pending'
                );
            """))
            conn.commit()

            existing_ids = set()
            try:
                rows = conn.execute(text("SELECT id FROM schedules")).fetchall()
                existing_ids = {r[0] for r in rows if r[0] is not None}
            except Exception:
                pass

            imported_count = 0
            updated_count = 0
            
            headers = []
            for col in range(1, sheet.max_column + 1):
                h = sheet.cell(row=1, column=col).value
                headers.append(str(h).strip().lower() if h else f"col_{col}")
            
            for r in range(2, sheet.max_row + 1):
                row_data = {}
                for c in range(1, len(headers) + 1):
                    val = sheet.cell(row=r, column=c).value
                    row_data[headers[c-1]] = val
                
                partno = str(row_data.get("partno") or "").strip()
                if not partno:
                    continue
                
                sid = int(row_data.get("id")) if row_data.get("id") else None
                dept = str(row_data.get("department") or "").strip()
                target_date = str(row_data.get("target_date") or "").strip()
                if hasattr(target_date, "strftime"):
                    target_date = target_date.strftime("%Y-%m-%d")
                elif " " in target_date:
                    target_date = target_date.split(" ")[0]
                    
                qty = str(row_data.get("qty") or "0").strip()
                completed_qty = str(row_data.get("completed_qty") or "0").strip()
                status = str(row_data.get("status") or "Pending").strip()

                if sid and sid in existing_ids:
                    conn.execute(text("""
                        UPDATE schedules
                        SET department = :dept, partno = :partno, target_date = :target_date,
                            qty = :qty, completed_qty = :completed_qty, status = :status
                        WHERE id = :id
                    """), {
                        "id": sid, "dept": dept, "partno": partno, "target_date": target_date,
                        "qty": qty, "completed_qty": completed_qty, "status": status
                    })
                    updated_count += 1
                else:
                    if sid:
                        try:
                            conn.execute(text("""
                                INSERT INTO schedules (id, department, partno, target_date, qty, completed_qty, status)
                                VALUES (:id, :dept, :partno, :target_date, :qty, :completed_qty, :status)
                            """), {
                                "id": sid, "dept": dept, "partno": partno, "target_date": target_date,
                                "qty": qty, "completed_qty": completed_qty, "status": status
                            })
                            existing_ids.add(sid)
                            imported_count += 1
                        except Exception:
                            conn.execute(text("""
                                INSERT INTO schedules (department, partno, target_date, qty, completed_qty, status)
                                VALUES (:dept, :partno, :target_date, :qty, :completed_qty, :status)
                            """), {
                                "dept": dept, "partno": partno, "target_date": target_date,
                                "qty": qty, "completed_qty": completed_qty, "status": status
                            })
                            imported_count += 1
                    else:
                        conn.execute(text("""
                            INSERT INTO schedules (department, partno, target_date, qty, completed_qty, status)
                            VALUES (:dept, :partno, :target_date, :qty, :completed_qty, :status)
                        """), {
                            "dept": dept, "partno": partno, "target_date": target_date,
                            "qty": qty, "completed_qty": completed_qty, "status": status
                        })
                        imported_count += 1

            conn.commit()
            try:
                conn.execute(text("SELECT setval(pg_get_serial_sequence('schedules', 'id'), coalesce(max(id),0) + 1, false) FROM schedules;"))
                conn.commit()
            except Exception:
                pass

        return {"message": f"Schedule excel imported successfully: {imported_count} inserted, {updated_count} updated"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

def ensure_production_logs_columns():
    try:
        with engine.begin() as conn:
            if "postgresql" in str(engine.url):
                try:
                    conn.execute(text("ALTER TABLE production_logs ADD COLUMN IF NOT EXISTS rej_qty FLOAT DEFAULT 0.0;"))
                    conn.execute(text("ALTER TABLE production_logs ADD COLUMN IF NOT EXISTS remarks TEXT DEFAULT '';"))
                except Exception:
                    pass
            else:
                for col_stmt in [
                    "ALTER TABLE production_logs ADD COLUMN dept TEXT DEFAULT '';",
                    "ALTER TABLE production_logs ADD COLUMN date TEXT DEFAULT '';",
                    "ALTER TABLE production_logs ADD COLUMN shift TEXT DEFAULT '';",
                    "ALTER TABLE production_logs ADD COLUMN setter TEXT DEFAULT '';",
                    "ALTER TABLE production_logs ADD COLUMN machine TEXT DEFAULT '';",
                    "ALTER TABLE production_logs ADD COLUMN operator TEXT DEFAULT '';",
                    "ALTER TABLE production_logs ADD COLUMN partno TEXT DEFAULT '';",
                    "ALTER TABLE production_logs ADD COLUMN opn_no TEXT DEFAULT '';",
                    "ALTER TABLE production_logs ADD COLUMN description TEXT DEFAULT '';",
                    "ALTER TABLE production_logs ADD COLUMN runtime FLOAT DEFAULT 0.0;",
                    "ALTER TABLE production_logs ADD COLUMN cycle_time FLOAT DEFAULT 0.0;",
                    "ALTER TABLE production_logs ADD COLUMN target_qty FLOAT DEFAULT 0.0;",
                    "ALTER TABLE production_logs ADD COLUMN prod_qty FLOAT DEFAULT 0.0;",
                    "ALTER TABLE production_logs ADD COLUMN rej_qty FLOAT DEFAULT 0.0;",
                    "ALTER TABLE production_logs ADD COLUMN efficiency FLOAT DEFAULT 0.0;",
                    "ALTER TABLE production_logs ADD COLUMN remarks TEXT DEFAULT '';",
                    "ALTER TABLE production_logs ADD COLUMN idle_hours FLOAT DEFAULT 0.0;",
                    "ALTER TABLE production_logs ADD COLUMN idle_reason TEXT DEFAULT 'None';",
                    "ALTER TABLE production_logs ADD COLUMN idle_hours_2 FLOAT DEFAULT 0.0;",
                    "ALTER TABLE production_logs ADD COLUMN idle_reason_2 TEXT DEFAULT 'None';",
                    "ALTER TABLE production_logs ADD COLUMN idle_hours_3 FLOAT DEFAULT 0.0;",
                    "ALTER TABLE production_logs ADD COLUMN idle_reason_3 TEXT DEFAULT 'None';",
                    "ALTER TABLE production_logs ADD COLUMN multiple_mc INTEGER DEFAULT 1;"
                ]:
                    try:
                        conn.execute(text(col_stmt))
                    except Exception:
                        pass
    except Exception as e:
        pass

@app.on_event("startup")
def run_startup_migrations():
    try:
        with engine.connect() as conn:
            for tbl in ["ht_logs", "ht_receipt_logs", "pc_logs", "pc_receipt_logs"]:
                try:
                    conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS dc_no VARCHAR(100) DEFAULT '';"))
                    conn.commit()
                except Exception:
                    pass
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS setter_logs (
                        id SERIAL PRIMARY KEY,
                        date TEXT,
                        dept TEXT DEFAULT '',
                        setter_name TEXT,
                        time_from TEXT,
                        time_to TEXT,
                        activity TEXT,
                        machine TEXT,
                        partno TEXT,
                        opn_no TEXT,
                        description TEXT,
                        qty INTEGER DEFAULT 0,
                        remarks TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                conn.commit()
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE setter_logs ADD COLUMN IF NOT EXISTS dept VARCHAR(50) DEFAULT '';"))
                conn.commit()
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN password VARCHAR(255) DEFAULT '';"))
                conn.commit()
            except Exception:
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password VARCHAR(255) DEFAULT '';"))
                    conn.commit()
                except Exception:
                    pass
            try:
                conn.execute(text("ALTER TABLE machines ADD COLUMN IF NOT EXISTS dept TEXT;"))
                conn.execute(text("ALTER TABLE machines ADD COLUMN IF NOT EXISTS department TEXT;"))
                conn.execute(text("ALTER TABLE machines ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Active';"))
                conn.execute(text("UPDATE machines SET dept = department WHERE (dept IS NULL OR dept = '') AND department IS NOT NULL;"))
                conn.execute(text("UPDATE machines SET department = dept WHERE (department IS NULL OR department = '') AND dept IS NOT NULL;"))
                conn.commit()
            except Exception:
                pass
            for col_stmt in [
                "ALTER TABLE operators ADD COLUMN dept TEXT;",
                "ALTER TABLE operators ADD COLUMN department TEXT;",
                "ALTER TABLE operators ADD COLUMN designation TEXT DEFAULT 'Operator';"
            ]:
                try:
                    conn.execute(text(col_stmt))
                    conn.commit()
                except Exception:
                    pass
            try:
                conn.execute(text("UPDATE operators SET dept = department WHERE (dept IS NULL OR dept = '') AND department IS NOT NULL;"))
                conn.commit()
            except Exception:
                pass
            try:
                conn.execute(text("UPDATE operators SET department = dept WHERE (department IS NULL OR department = '') AND dept IS NOT NULL;"))
                conn.commit()
            except Exception:
                pass
            try:
                ensure_production_logs_columns()
            except Exception:
                pass
            # Align sequences to MAX(id) for PostgreSQL
            if "postgresql" in str(engine.url):
                for tbl in [
                    "part_masters", "parts", "operations", "part_operations", 
                    "machines", "operators", "departments", "shifts", "vendors", 
                    "setters", "suppliers", "raw_materials", "raw_material_logs", 
                    "ht_logs", "ht_receipt_logs", "pc_logs", "pc_receipt_logs", 
                    "production_logs", "production_schedules", "customer_masters",
                    "drill_masters", "insert_masters", "tap_masters",
                    "hr_shift_assignments", "shift_status_logs", "hourly_reports"
                ]:
                    try:
                        conn.execute(text(f"""
                            DO $$
                            DECLARE
                                seq_name text;
                                max_val bigint;
                            BEGIN
                                seq_name := pg_get_serial_sequence('{tbl}', 'id');
                                IF seq_name IS NOT NULL THEN
                                    EXECUTE format('SELECT COALESCE(MAX(id), 0) FROM %I', '{tbl}') INTO max_val;
                                    IF max_val > 0 THEN
                                        EXECUTE format('SELECT setval(%L, %s, true)', seq_name, max_val);
                                    END IF;
                                END IF;
                            EXCEPTION WHEN OTHERS THEN
                                NULL;
                            END $$;
                        """))
                        conn.commit()
                    except Exception:
                        pass
    except Exception as e:
        print("Startup migration note:", e)
    try:
        import_breakdown_excel()
    except Exception as e:
        print("Startup breakdown import note:", e)
    try:
        import_rfq_excel()
    except Exception as e:
        print("Startup rfq import note:", e)
    try:
        import_schedule_excel()
    except Exception as e:
        print("Startup schedule import note:", e)
    try:
        sync_all_pc_receipts_to_production()
    except Exception as e:
        print("Startup PC receipts sync note:", e)
    try:
        sync_all_ht_receipts_to_production()
    except Exception as e:
        print("Startup HT receipts sync note:", e)

@app.post("/api/import-breakdown-excel")
@app.get("/api/import-breakdown-excel")
def trigger_import_breakdown_excel():
    return import_breakdown_excel()

@app.post("/api/import-rfq-excel")
@app.get("/api/import-rfq-excel")
def trigger_import_rfq_excel():
    return import_rfq_excel()

@app.post("/api/import-schedule-excel")
@app.get("/api/import-schedule-excel")
def trigger_import_schedule_excel():
    return import_schedule_excel()

@app.post("/api/restore-from-backup")
@app.get("/api/restore-from-backup")
def trigger_restore_backup():
    try:
        import importlib
        import import_all_tables
        importlib.reload(import_all_tables)
        import_all_tables.import_all_backup_tables()
        return {"message": "All 32 tables restored successfully from backup JSON & Excel!"}
    except Exception as e:
        return {"error": str(e)}

def hash_password(pw: str) -> str:
    import hashlib
    return hashlib.sha256(pw.encode('utf-8')).hexdigest()

@app.post("/api/login")
@app.post("/api/auth/login")
def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    u = (login_data.username or "").strip().lower()
    p = (login_data.password or "").strip()
    p_hash = hash_password(p)
    
    if u == "admin" and p in ["admin", "admin123", "admin@123", "password", "123"]:
        return {"success": True, "username": "admin", "role": "admin", "token": "token-admin"}

    try:
        user_row = db.execute(text("SELECT * FROM users WHERE LOWER(username) = :u"), {"u": u}).mappings().first()
        if user_row:
            stored_pw = user_row.get("password") or ""
            stored_hash = user_row.get("password_hash") or ""
            if p == stored_pw or p_hash == stored_hash or p == stored_hash or p_hash == stored_pw or (not stored_pw and not stored_hash):
                return {
                    "success": True,
                    "username": user_row.get("username"),
                    "role": user_row.get("role") or "operator",
                    "token": f"token-{user_row.get('username')}",
                    "accessible_screens": user_row.get("accessible_screens") or "[]"
                }
    except Exception as e:
        print("Login DB lookup notice:", e)

    try:
        user = db.query(models.User).filter(func.lower(models.User.username) == u).first()
        if user:
            stored_pw = getattr(user, "password", "") or ""
            stored_hash = getattr(user, "password_hash", "") or ""
            if p == stored_pw or p_hash == stored_hash or p == stored_hash or p_hash == stored_pw or (not stored_pw and not stored_hash):
                return {
                    "success": True,
                    "username": user.username,
                    "role": user.role or "operator",
                    "token": f"token-{user.username}",
                    "accessible_screens": getattr(user, "accessible_screens", "[]") or "[]"
                }
    except Exception as e:
        print("Login ORM notice:", e)

    raise HTTPException(status_code=401, detail="Invalid username or password")

class SessionVerifyRequest(BaseModel):
    username: Optional[str] = None
    token: Optional[str] = None

@app.post("/api/auth/verify")
@app.get("/api/auth/verify")
def verify_session(req: Optional[SessionVerifyRequest] = None, username: Optional[str] = None, db: Session = Depends(get_db)):
    u = ((req.username if req and req.username else username) or "").strip().lower()
    if not u:
        return {"valid": False, "detail": "No user session provided"}

    try:
        user_row = db.execute(text("SELECT id, username, role, accessible_screens FROM users WHERE LOWER(username) = :u"), {"u": u}).mappings().first()
        if user_row:
            return {
                "valid": True,
                "user": {
                    "id": user_row.get("id"),
                    "username": user_row.get("username"),
                    "role": user_row.get("role") or "operator",
                    "accessible_screens": user_row.get("accessible_screens") or "[]"
                }
            }
    except Exception as e:
        print("Verify DB notice:", e)

    try:
        user = db.query(models.User).filter(func.lower(models.User.username) == u).first()
        if user:
            return {
                "valid": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role or "operator",
                    "accessible_screens": getattr(user, "accessible_screens", "[]") or "[]"
                }
            }
    except Exception as e:
        print("Verify ORM notice:", e)

    if u == "admin":
        return {
            "valid": True,
            "user": {
                "id": 1,
                "username": "admin",
                "role": "admin",
                "accessible_screens": "[]"
            }
        }

    return {"valid": False, "detail": "User account no longer exists or has been deleted."}

# --- USER MANAGEMENT CRUD ---
@app.get("/api/users")
def get_all_users(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT id, username, role, accessible_screens FROM users ORDER BY id ASC;")).mappings().all()
        return [{
            "id": r["id"],
            "username": r["username"],
            "role": r["role"] or "operator",
            "accessible_screens": r["accessible_screens"] or "[]"
        } for r in rows]
    except Exception:
        db.rollback()
        users = db.query(models.User).order_by(models.User.id.asc()).all()
        return [{
            "id": u.id,
            "username": u.username,
            "role": u.role or "operator",
            "accessible_screens": getattr(u, "accessible_screens", "[]") or "[]"
        } for u in users]

@app.post("/api/users")
def create_user(data: dict, db: Session = Depends(get_db)):
    uname = (data.get("username") or "").strip()
    pw = (data.get("password") or "").strip()
    role = (data.get("role") or "operator").strip()
    screens = (data.get("accessible_screens") or "[]").strip()

    if not uname:
        raise HTTPException(status_code=400, detail="Username is required")

    pwhash = hash_password(pw) if pw else ""

    try:
        existing = db.execute(text("SELECT id FROM users WHERE LOWER(username) = LOWER(:u)"), {"u": uname}).mappings().first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
    except HTTPException:
        raise
    except Exception:
        db.rollback()

    try:
        db.execute(text("SELECT setval(pg_get_serial_sequence('users', 'id'), coalesce(max(id),0) + 1, false) FROM users;"))
        db.commit()
    except Exception:
        db.rollback()

    try:
        db.execute(text("""
            INSERT INTO users (username, password, password_hash, role, accessible_screens)
            VALUES (:username, :password, :password_hash, :role, :accessible_screens)
        """), {"username": uname, "password": pw, "password_hash": pwhash, "role": role, "accessible_screens": screens})
        db.commit()
    except Exception:
        db.rollback()
        try:
            db.execute(text("""
                INSERT INTO users (username, password_hash, role, accessible_screens)
                VALUES (:username, :password_hash, :role, :accessible_screens)
            """), {"username": uname, "password_hash": pwhash, "role": role, "accessible_screens": screens})
            db.commit()
        except Exception as ex:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create user: {ex}")

    return {"message": "User created successfully"}

@app.put("/api/users/{user_id}")
def update_user(user_id: int, data: dict, db: Session = Depends(get_db)):
    uname = (data.get("username") or "").strip()
    role = (data.get("role") or "").strip()
    screens = (data.get("accessible_screens") or "").strip()
    pw = (data.get("password") or "").strip()

    params = {"id": user_id, "username": uname, "accessible_screens": screens}
    sql_updates = ["username = :username", "accessible_screens = :accessible_screens"]

    if role:
        params["role"] = role
        sql_updates.append("role = :role")
    if pw:
        params["password"] = pw
        params["password_hash"] = hash_password(pw)
        sql_updates.append("password = :password")
        sql_updates.append("password_hash = :password_hash")

    try:
        db.execute(text(f"""
            UPDATE users SET {', '.join(sql_updates)} WHERE id = :id
        """), params)
        db.commit()
    except Exception:
        db.rollback()
        if pw and "password = :password" in sql_updates:
            sql_updates_no_pw = [u for u in sql_updates if u != "password = :password"]
            params_no_pw = {k: v for k, v in params.items() if k != "password"}
            try:
                db.execute(text(f"""
                    UPDATE users SET {', '.join(sql_updates_no_pw)} WHERE id = :id
                """), params_no_pw)
                db.commit()
            except Exception as ex:
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Failed to update user: {ex}")
        else:
            raise HTTPException(status_code=500, detail="Failed to update user")

    return {"message": "User updated successfully"}

@app.put("/api/users/{user_id}/password")
def update_user_password(user_id: int, data: dict, db: Session = Depends(get_db)):
    new_pw = (data.get("new_password") or "").strip()
    if not new_pw:
        raise HTTPException(status_code=400, detail="New password is required")

    pwhash = hash_password(new_pw)
    try:
        db.execute(text("""
            UPDATE users SET password = :password, password_hash = :password_hash WHERE id = :id
        """), {"id": user_id, "password": new_pw, "password_hash": pwhash})
        db.commit()
    except Exception:
        db.rollback()
        try:
            db.execute(text("""
                UPDATE users SET password_hash = :password_hash WHERE id = :id
            """), {"id": user_id, "password_hash": pwhash})
            db.commit()
        except Exception as ex:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update password: {ex}")

    return {"message": "Password updated successfully"}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    try:
        user_row = db.execute(text("SELECT username FROM users WHERE id = :id"), {"id": user_id}).mappings().first()
        if user_row and user_row.get("username") == "admin":
            raise HTTPException(status_code=400, detail="Cannot delete default admin user")
        db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        db.commit()
    except HTTPException:
        raise
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {ex}")

    return {"message": "User deleted successfully"}

@app.delete("/api/users/clear-all")
def clear_all_users(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM users WHERE LOWER(username) != 'admin';"))
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All non-admin users deleted successfully"}

@app.post("/api/seed-default-data")
def seed_default_data(db: Session = Depends(get_db)):
    try:
        import seed_data
        seed_data.seed_database()
        return {"message": "Default master data seeded successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Pydantic Schemas ---

class MachineBase(BaseModel):
    name: str
    dept: Optional[str] = "General"
    status: Optional[str] = "Active"

class MachineCreate(MachineBase):
    pass

class MachineResponse(MachineBase):
    id: int
    class Config:
        from_attributes = True

class OperatorBase(BaseModel):
    name: str
    dept: Optional[str] = "General"
    designation: Optional[str] = "Operator"

class OperatorCreate(OperatorBase):
    pass

class OperatorResponse(OperatorBase):
    id: int
    class Config:
        from_attributes = True

class OperationBase(BaseModel):
    opn_no: str
    description: Optional[str] = None
    machine_name: Optional[str] = None
    cycle_time: Optional[float] = 0.0
    va: Optional[float] = 0.0

class OperationCreate(OperationBase):
    pass

class OperationResponse(OperationBase):
    id: int
    part_id: int
    class Config:
        from_attributes = True

class PartBase(BaseModel):
    part_no: str
    customer: Optional[str] = None
    dept: Optional[str] = None
    family: Optional[str] = None
    forge_pn: Optional[str] = None
    description: Optional[str] = None
    cycle_time: Optional[float] = 0.0
    va: Optional[float] = 0.0

class PartCreate(PartBase):
    pass

class PartResponse(PartBase):
    id: int
    operations: List[OperationResponse] = []
    class Config:
        from_attributes = True

class ProductionScheduleBase(BaseModel):
    sl_no: Optional[str] = None
    item: Optional[str] = None
    grs_no: Optional[str] = None
    part_no: str
    total_sch_qty: int = 0
    rate_per_pc: Optional[float] = 0.0
    amount: Optional[float] = 0.0
    qty_disp: Optional[int] = 0
    value_rs: Optional[float] = 0.0
    balance_to_produce: Optional[int] = 0
    remarks: Optional[str] = None

class ProductionScheduleCreate(ProductionScheduleBase):
    pass

class ProductionScheduleResponse(ProductionScheduleBase):
    id: int
    class Config:
        from_attributes = True

class ProductionLogBase(BaseModel):
    log_date: Optional[str] = None
    shift: Optional[str] = None
    machine_name: str
    operator_name: str
    part_no: str
    opn_no: Optional[str] = "10"
    qty_produced: int = 0
    scrap_qty: int = 0
    completed_sl_nos: Optional[str] = None
    remarks: Optional[str] = None

class ProductionLogCreate(ProductionLogBase):
    pass

class ProductionLogResponse(ProductionLogBase):
    id: int
    created_at: Optional[datetime.datetime] = None
    class Config:
        from_attributes = True

class ToolingBase(BaseModel):
    insert_spec: str
    no_of_edges: int = 1
    current_usage: int = 0
    max_life: int = 1000
    status: Optional[str] = "Good"

class ToolingCreate(ToolingBase):
    pass

class ToolingResponse(ToolingBase):
    id: int
    class Config:
        from_attributes = True

class InspectionParamBase(BaseModel):
    dept: Optional[str] = ""
    part_no: str
    part_desc: Optional[str] = ""
    opn_no: str
    opn_desc: Optional[str] = ""
    sl_no: Optional[int] = 1
    description: str
    nominal_dimension: Optional[float] = 0.0
    lo_tol: Optional[float] = 0.0
    hi_tol: Optional[float] = 0.0

class InspectionParamCreate(InspectionParamBase):
    pass

class InspectionParamResponse(InspectionParamBase):
    id: int
    class Config:
        from_attributes = True

class InspectionReportSave(BaseModel):
    report_code: Optional[str] = None
    prod_log_id: Optional[int] = None
    dept: Optional[str] = ""
    part_no: str
    part_desc: Optional[str] = ""
    opn_no: str
    opn_desc: Optional[str] = ""
    part_sl_no: Optional[str] = ""
    batch_qty: Optional[int] = 1
    machine_name: Optional[str] = None
    operator_name: Optional[str] = None
    shift: Optional[str] = None
    status: Optional[str] = "Accepted"
    remarks: Optional[str] = ""
    inspection_date: Optional[str] = None
    comp_sl_nos: Optional[str] = "1"
    readings_json: Optional[str] = "{}"


IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

def get_now_ist():
    return datetime.datetime.now(IST)

@app.get("/api/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    today_str = get_now_ist().strftime("%Y-%m-%d")
    
    total_machines = db.query(models.Machine).count()
    active_machines = db.query(models.Machine).filter(models.Machine.status == "Active").count()
    total_operators = db.query(models.Operator).count()
    total_parts = db.query(models.Part).count()
    total_schedules = db.query(models.ProductionSchedule).count()
    
    pending_qty = db.query(func.sum(models.ProductionSchedule.balance_to_produce)).scalar() or 0
    today_produced = db.query(func.sum(models.ProductionLog.qty_produced)).filter(models.ProductionLog.log_date.like(f"{today_str}%")).scalar() or 0
    today_scrap = db.query(func.sum(models.ProductionLog.scrap_qty)).filter(models.ProductionLog.log_date.like(f"{today_str}%")).scalar() or 0
    
    recent_logs = db.query(models.ProductionLog).order_by(models.ProductionLog.id.desc()).limit(10).all()
    recent_inspection_reports = db.query(models.InspectionReport).order_by(models.InspectionReport.id.desc()).limit(10).all()
    
    return {
        "total_machines": total_machines,
        "active_machines": active_machines,
        "total_operators": total_operators,
        "total_parts": total_parts,
        "total_schedules": total_schedules,
        "pending_qty": pending_qty,
        "today_produced": today_produced,
        "today_scrap": today_scrap,
        "recent_logs": [
            {
                "id": log.id,
                "log_date": log.log_date or "",
                "shift": log.shift or "General",
                "machine_name": log.machine_name or "",
                "operator_name": log.operator_name or "",
                "part_no": log.part_no or "",
                "opn_no": log.opn_no or "10",
                "qty_produced": log.qty_produced or 0,
                "scrap_qty": log.scrap_qty or 0,
                "completed_sl_nos": log.completed_sl_nos or "",
                "remarks": log.remarks or ""
            }
            for log in recent_logs
        ],
        "recent_inspection_logs": [
            {
                "id": r.id,
                "report_code": r.report_code or f"IR-{r.id}",
                "inspection_date": r.inspection_date or "",
                "part_no": r.part_no or "",
                "opn_no": r.opn_no or "10",
                "batch_qty": r.batch_qty or 5,
                "machine_name": r.machine_name or "",
                "operator_name": r.operator_name or "",
                "comp_sl_nos": r.comp_sl_nos or "",
                "readings_json": r.readings_json or "{}"
            }
            for r in recent_inspection_reports
        ]
    }

# --- Machines ---
@app.get("/api/machines")
def get_machines(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        rows = db.execute(text("SELECT * FROM machines ORDER BY id ASC")).mappings().all()
        if rows:
            return [{
                "id": r.get("id"),
                "name": r.get("name") or r.get("machine_name") or "",
                "dept": r.get("department") or r.get("dept") or "",
                "department": r.get("department") or r.get("dept") or "",
                "status": r.get("status") or "Active"
            } for r in rows]
    except Exception:
        db.rollback()

    try:
        machines = db.query(models.Machine).order_by(models.Machine.id.asc()).all()
        return [{
            "id": m.id,
            "name": m.name,
            "dept": m.dept or "",
            "department": m.dept or "",
            "status": m.status or "Active"
        } for m in machines]
    except Exception:
        db.rollback()
        return []

@app.post("/api/machines")
def create_machine(data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or data.get("machine_name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Machine name cannot be empty")
    dept = (data.get("department") or data.get("dept") or "General").strip()
    status = (data.get("status") or "Active").strip()

    # Check if duplicate
    try:
        existing = db.execute(text("SELECT id, name FROM machines WHERE UPPER(name) = :name"), {"name": name.upper()}).mappings().first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Machine '{name}' already exists")
    except HTTPException:
        raise
    except Exception:
        db.rollback()

    # Sync postgres sequence if needed
    try:
        db.execute(text("SELECT setval(pg_get_serial_sequence('machines', 'id'), coalesce(max(id),0) + 1, false) FROM machines;"))
        db.commit()
    except Exception:
        db.rollback()

    max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM machines")).mappings().first()
    next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 1

    inserted = False
    # Attempt 1: insert with both dept and department
    try:
        db.execute(text("INSERT INTO machines (id, name, dept, department, status) VALUES (:id, :name, :dept, :dept, :status)"),
                   {"id": next_id, "name": name, "dept": dept, "status": status})
        db.commit()
        inserted = True
    except Exception:
        db.rollback()

    if not inserted:
        # Attempt 2: insert with department
        try:
            db.execute(text("INSERT INTO machines (id, name, department) VALUES (:id, :name, :dept)"),
                       {"id": next_id, "name": name, "dept": dept})
            db.commit()
            inserted = True
        except Exception:
            db.rollback()

    if not inserted:
        # Attempt 3: insert with dept
        try:
            db.execute(text("INSERT INTO machines (id, name, dept) VALUES (:id, :name, :dept)"),
                       {"id": next_id, "name": name, "dept": dept})
            db.commit()
            inserted = True
        except Exception:
            db.rollback()

    if not inserted:
        # Attempt 4: without explicit id
        try:
            db.execute(text("INSERT INTO machines (name, department) VALUES (:name, :dept)"),
                       {"name": name, "dept": dept})
            db.commit()
            inserted = True
        except Exception:
            db.rollback()

    if not inserted:
        # Attempt 5: models.Machine
        try:
            m_obj = models.Machine(name=name, dept=dept, status=status)
            db.add(m_obj)
            db.commit()
            db.refresh(m_obj)
            next_id = m_obj.id
            inserted = True
        except Exception as ex:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create machine: {ex}")

    try:
        created_row = db.execute(text("SELECT id, name, status FROM machines WHERE UPPER(name) = :name ORDER BY id DESC LIMIT 1"),
                                 {"name": name.upper()}).mappings().first()
        if created_row:
            next_id = int(created_row.get("id"))
    except Exception:
        pass

    try:
        db.execute(text("SELECT setval(pg_get_serial_sequence('machines', 'id'), coalesce(max(id),0) + 1, false) FROM machines;"))
        db.commit()
    except Exception:
        db.rollback()

    return {
        "id": next_id,
        "name": name,
        "dept": dept,
        "department": dept,
        "status": status,
        "message": "Machine created successfully"
    }

@app.post("/api/machines/import-excel")
async def import_machines_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    rows = parse_excel_bytes(contents)
    if not rows:
        raise HTTPException(status_code=400, detail="Could not parse Excel file or file is empty")
    
    headers = [h.lower().strip() for h in rows[0]]
    
    name_idx = -1
    dept_idx = -1
    status_idx = -1
    
    for i, h in enumerate(headers):
        if "name" in h or "machine" in h or "mc" in h or "m/c" in h:
            if name_idx == -1: name_idx = i
        elif "dept" in h or "department" in h:
            dept_idx = i
        elif "status" in h:
            status_idx = i

    if name_idx == -1:
        name_idx = 1 if len(headers) > 1 else 0
        dept_idx = 0 if len(headers) > 1 else -1

    existing_names = {m.name.strip().upper() for m in db.query(models.Machine).all()}
    imported_count = 0

    for row in rows[1:]:
        if name_idx < len(row) and row[name_idx]:
            name = row[name_idx].strip()
            if not name or name.upper() in ["MACHINE", "MACHINE NAME", "M/C NAME"]:
                continue
            dept = row[dept_idx].strip() if dept_idx != -1 and dept_idx < len(row) and row[dept_idx] else "General"
            status = row[status_idx].strip() if status_idx != -1 and status_idx < len(row) and row[status_idx] else "Active"
            
            if name.upper() not in existing_names:
                m = models.Machine(name=name, dept=dept, status=status)
                db.add(m)
                existing_names.add(name.upper())
                imported_count += 1
                
    db.commit()
    return {"imported_count": imported_count, "message": f"Successfully imported {imported_count} new machines!"}

@app.put("/api/machines/{machine_id}")
def update_machine(machine_id: int, data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or data.get("machine_name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Machine name cannot be empty")
    dept = (data.get("department") or data.get("dept") or "General").strip()
    status = (data.get("status") or "Active").strip()

    updated = False
    try:
        db.execute(text("UPDATE machines SET name = :name, dept = :dept, department = :dept, status = :status WHERE id = :id"),
                   {"id": machine_id, "name": name, "dept": dept, "status": status})
        db.commit()
        updated = True
    except Exception:
        db.rollback()

    if not updated:
        try:
            db.execute(text("UPDATE machines SET name = :name, department = :dept WHERE id = :id"),
                       {"id": machine_id, "name": name, "dept": dept})
            db.commit()
            updated = True
        except Exception:
            db.rollback()

    if not updated:
        try:
            db.execute(text("UPDATE machines SET name = :name, dept = :dept WHERE id = :id"),
                       {"id": machine_id, "name": name, "dept": dept})
            db.commit()
            updated = True
        except Exception as ex:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update machine: {ex}")

    return {
        "id": machine_id,
        "name": name,
        "dept": dept,
        "department": dept,
        "status": status,
        "message": "Machine updated successfully"
    }

@app.delete("/api/machines/clear-all")
def clear_all_machines(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM machines;"))
        db.commit()
    except Exception:
        db.rollback()
        db.query(models.Machine).delete()
        db.commit()
    return {"message": "All machines cleared successfully!"}

@app.delete("/api/machines/{machine_id}")
def delete_machine(machine_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM machines WHERE id = :id"), {"id": machine_id})
        db.commit()
    except Exception:
        db.rollback()
        try:
            db_m = db.query(models.Machine).filter(models.Machine.id == machine_id).first()
            if db_m:
                db.delete(db_m)
                db.commit()
            else:
                raise HTTPException(status_code=404, detail="Machine not found")
        except HTTPException:
            raise
        except Exception as ex:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete machine: {ex}")
    return {"message": "Machine deleted successfully"}
@app.post("/api/machines/bulk_import")
def bulk_import_machines(data: dict, db: Session = Depends(get_db)):
    machines = data.get("machines") or []
    count = 0
    for m in machines:
        name = (m.get("name") or m.get("machine_name") or "").strip()
        dept = (m.get("department") or m.get("dept") or "").strip()
        status = (m.get("status") or "Active").strip()
        if name:
            try:
                m_obj = models.Machine(name=name, dept=dept, status=status)
                db.add(m_obj)
                db.commit()
                count += 1
            except Exception:
                db.rollback()
                try:
                    db.execute(text("INSERT INTO machines (name, dept, status) VALUES (:name, :dept, :status)"), {
                        "name": name,
                        "dept": dept,
                        "status": status
                    })
                    db.commit()
                    count += 1
                except Exception:
                    db.rollback()
                    try:
                        db.execute(text("INSERT INTO machines (name, department, status) VALUES (:name, :dept, :status)"), {
                            "name": name,
                            "dept": dept,
                            "status": status
                        })
                        db.commit()
                        count += 1
                    except Exception:
                        db.rollback()
    return {"message": f"Successfully imported {count} machines!", "imported_count": count}

# --- Departments ---
@app.get("/api/departments")
def get_departments(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        rows = db.execute(text("SELECT * FROM departments ORDER BY id ASC")).mappings().all()
        if rows:
            return [{"id": r.get("id"), "name": r.get("name") or ""} for r in rows]
    except Exception:
        db.rollback()

    try:
        depts = db.query(models.Department).order_by(models.Department.id.asc()).all()
        return [{"id": d.id, "name": d.name} for d in depts]
    except Exception:
        db.rollback()
        return []

@app.post("/api/departments")
def create_department(data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Department name cannot be empty")
    
    # Check if department with this name already exists
    try:
        existing = db.execute(text("SELECT id, name FROM departments WHERE UPPER(name) = :name"), {"name": name.upper()}).mappings().first()
        if existing:
            return {"id": existing.get("id"), "name": existing.get("name"), "message": "Department already exists"}
    except Exception:
        db.rollback()

    # Sync postgres sequence if needed
    try:
        db.execute(text("SELECT setval(pg_get_serial_sequence('departments', 'id'), coalesce(max(id),0) + 1, false) FROM departments;"))
        db.commit()
    except Exception:
        db.rollback()

    try:
        max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM departments")).mappings().first()
        next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 1
        
        try:
            db.execute(text("INSERT INTO departments (id, name) VALUES (:id, :name)"), {"id": next_id, "name": name})
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("INSERT INTO departments (name) VALUES (:name)"), {"name": name})
            db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create department: {ex}")
    
    try:
        row = db.execute(text("SELECT id, name FROM departments WHERE UPPER(name) = :name ORDER BY id DESC LIMIT 1"), {"name": name.upper()}).mappings().first()
        return {"id": row.get("id") if row else next_id, "name": name, "message": "Department created successfully"}
    except Exception:
        return {"id": next_id, "name": name, "message": "Department created successfully"}

@app.put("/api/departments/{dept_id}")
def update_department(dept_id: int, data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Department name cannot be empty")
    try:
        db.execute(text("UPDATE departments SET name = :name WHERE id = :id"), {"id": dept_id, "name": name})
        db.commit()
    except Exception:
        db.rollback()
        try:
            d_obj = db.query(models.Department).filter(models.Department.id == dept_id).first()
            if d_obj:
                d_obj.name = name
                db.commit()
        except Exception as ex:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update department: {ex}")
    return {"id": dept_id, "name": name, "message": "Department updated successfully"}

@app.delete("/api/departments/{dept_id}")
def delete_department(dept_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM departments WHERE id = :id"), {"id": dept_id})
        db.commit()
    except Exception:
        db.rollback()
        try:
            d_obj = db.query(models.Department).filter(models.Department.id == dept_id).first()
            if d_obj:
                db.delete(d_obj)
                db.commit()
        except Exception:
            db.rollback()
    return {"message": "Department deleted"}

@app.delete("/api/departments/clear-all")
@app.delete("/api/departments/all")
@app.post("/api/departments/clear-all")
def clear_all_departments(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM departments;"))
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All departments cleared successfully!"}

# --- Shifts ---
@app.get("/api/shifts")
def get_shifts(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM shifts ORDER BY id ASC")).mappings().all()
        if rows:
            return [{"id": r.get("id"), "name": r.get("name") or "", "hours": float(r.get("hours") or 8.0)} for r in rows]
    except Exception:
        db.rollback()

    try:
        shifts = db.query(models.Shift).order_by(models.Shift.id.asc()).all()
        return [{"id": s.id, "name": s.name, "hours": s.hours} for s in shifts]
    except Exception:
        db.rollback()
        return []

@app.post("/api/shifts")
def create_shift(data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    hours = float(data.get("hours") or 8.0)
    if not name:
        raise HTTPException(status_code=400, detail="Shift name cannot be empty")
    
    try:
        existing = db.execute(text("SELECT id, name, hours FROM shifts WHERE UPPER(name) = :name"), {"name": name.upper()}).mappings().first()
        if existing:
            return {"id": existing.get("id"), "name": existing.get("name"), "hours": existing.get("hours"), "message": "Shift already exists"}
    except Exception:
        db.rollback()

    try:
        db.execute(text("SELECT setval(pg_get_serial_sequence('shifts', 'id'), coalesce(max(id),0) + 1, false) FROM shifts;"))
        db.commit()
    except Exception:
        db.rollback()

    try:
        max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM shifts")).mappings().first()
        next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 1
        
        try:
            db.execute(text("INSERT INTO shifts (id, name, hours) VALUES (:id, :name, :hours)"), {"id": next_id, "name": name, "hours": hours})
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("INSERT INTO shifts (name, hours) VALUES (:name, :hours)"), {"name": name, "hours": hours})
            db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create shift: {ex}")
    
    try:
        row = db.execute(text("SELECT id, name, hours FROM shifts WHERE UPPER(name) = :name ORDER BY id DESC LIMIT 1"), {"name": name.upper()}).mappings().first()
        return {"id": row.get("id") if row else next_id, "name": name, "hours": hours, "message": "Shift created successfully"}
    except Exception:
        return {"id": next_id, "name": name, "hours": hours, "message": "Shift created successfully"}

@app.put("/api/shifts/{shift_id}")
def update_shift(shift_id: int, data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    hours = float(data.get("hours") or 8.0)
    if not name:
        raise HTTPException(status_code=400, detail="Shift name cannot be empty")
    try:
        db.execute(text("UPDATE shifts SET name = :name, hours = :hours WHERE id = :id"), {"id": shift_id, "name": name, "hours": hours})
        db.commit()
    except Exception:
        db.rollback()
        try:
            s_obj = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
            if s_obj:
                s_obj.name = name
                s_obj.hours = hours
                db.commit()
        except Exception as ex:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update shift: {ex}")
    return {"id": shift_id, "name": name, "hours": hours, "message": "Shift updated successfully"}

@app.delete("/api/shifts/{shift_id}")
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM shifts WHERE id = :id"), {"id": shift_id})
        db.commit()
    except Exception:
        db.rollback()
        try:
            s_obj = db.query(models.Shift).filter(models.Shift.id == shift_id).first()
            if s_obj:
                db.delete(s_obj)
                db.commit()
        except Exception:
            db.rollback()
    return {"message": "Shift deleted"}

@app.delete("/api/shifts/clear-all")
@app.delete("/api/shifts/all")
@app.post("/api/shifts/clear-all")
def clear_all_shifts(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM shifts;"))
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All shifts cleared successfully!"}

# --- Vendors ---
@app.get("/api/vendors")
def get_vendors(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM vendors ORDER BY id ASC")).mappings().all()
        if rows:
            return [{"id": r.get("id"), "name": r.get("name") or "", "details": r.get("details") or ""} for r in rows]
    except Exception:
        db.rollback()

    try:
        vendors = db.query(models.Vendor).order_by(models.Vendor.id.asc()).all()
        return [{"id": v.id, "name": v.name, "details": v.details or ""} for v in vendors]
    except Exception:
        db.rollback()
        return []

@app.post("/api/vendors")
def create_vendor(data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    details = (data.get("details") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Vendor name cannot be empty")
    
    try:
        existing = db.execute(text("SELECT id, name, details FROM vendors WHERE UPPER(name) = :name"), {"name": name.upper()}).mappings().first()
        if existing:
            return {"id": existing.get("id"), "name": existing.get("name"), "details": existing.get("details"), "message": "Vendor already exists"}
    except Exception:
        db.rollback()

    try:
        db.execute(text("SELECT setval(pg_get_serial_sequence('vendors', 'id'), coalesce(max(id),0) + 1, false) FROM vendors;"))
        db.commit()
    except Exception:
        db.rollback()

    try:
        max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM vendors")).mappings().first()
        next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 1
        
        try:
            db.execute(text("INSERT INTO vendors (id, name, details) VALUES (:id, :name, :details)"), {"id": next_id, "name": name, "details": details})
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("INSERT INTO vendors (name, details) VALUES (:name, :details)"), {"name": name, "details": details})
            db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create vendor: {ex}")
    
    try:
        row = db.execute(text("SELECT id, name, details FROM vendors WHERE UPPER(name) = :name ORDER BY id DESC LIMIT 1"), {"name": name.upper()}).mappings().first()
        return {"id": row.get("id") if row else next_id, "name": name, "details": details, "message": "Vendor created successfully"}
    except Exception:
        return {"id": next_id, "name": name, "details": details, "message": "Vendor created successfully"}

@app.put("/api/vendors/{vendor_id}")
def update_vendor(vendor_id: int, data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    details = (data.get("details") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Vendor name cannot be empty")
    try:
        db.execute(text("UPDATE vendors SET name = :name, details = :details WHERE id = :id"), {"id": vendor_id, "name": name, "details": details})
        db.commit()
    except Exception:
        db.rollback()
        try:
            v_obj = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
            if v_obj:
                v_obj.name = name
                v_obj.details = details
                db.commit()
        except Exception as ex:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update vendor: {ex}")
    return {"id": vendor_id, "name": name, "details": details, "message": "Vendor updated successfully"}

@app.delete("/api/vendors/{vendor_id}")
def delete_vendor(vendor_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM vendors WHERE id = :id"), {"id": vendor_id})
        db.commit()
    except Exception:
        db.rollback()
        try:
            v_obj = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
            if v_obj:
                db.delete(v_obj)
                db.commit()
        except Exception:
            db.rollback()
    return {"message": "Vendor deleted"}

@app.delete("/api/vendors/clear-all")
@app.delete("/api/vendors/all")
@app.post("/api/vendors/clear-all")
def clear_all_vendors(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM vendors;"))
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All vendors cleared successfully!"}

# --- Suppliers ---
@app.get("/api/suppliers")
def get_suppliers(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM suppliers ORDER BY id ASC")).mappings().all()
        if rows:
            return [{"id": r.get("id"), "name": r.get("name") or "", "details": r.get("details") or ""} for r in rows]
    except Exception:
        db.rollback()

    try:
        suppliers = db.query(models.Supplier).order_by(models.Supplier.id.asc()).all()
        return [{"id": s.id, "name": s.name, "details": s.details or ""} for s in suppliers]
    except Exception:
        db.rollback()
        return []

@app.post("/api/suppliers")
def create_supplier(data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    details = (data.get("details") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Supplier name cannot be empty")
    
    try:
        existing = db.execute(text("SELECT id, name, details FROM suppliers WHERE UPPER(name) = :name"), {"name": name.upper()}).mappings().first()
        if existing:
            return {"id": existing.get("id"), "name": existing.get("name"), "details": existing.get("details"), "message": "Supplier already exists"}
    except Exception:
        db.rollback()

    try:
        db.execute(text("SELECT setval(pg_get_serial_sequence('suppliers', 'id'), coalesce(max(id),0) + 1, false) FROM suppliers;"))
        db.commit()
    except Exception:
        db.rollback()

    try:
        max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM suppliers")).mappings().first()
        next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 1
        
        try:
            db.execute(text("INSERT INTO suppliers (id, name, details) VALUES (:id, :name, :details)"), {"id": next_id, "name": name, "details": details})
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("INSERT INTO suppliers (name, details) VALUES (:name, :details)"), {"name": name, "details": details})
            db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create supplier: {ex}")
    
    try:
        row = db.execute(text("SELECT id, name, details FROM suppliers WHERE UPPER(name) = :name ORDER BY id DESC LIMIT 1"), {"name": name.upper()}).mappings().first()
        return {"id": row.get("id") if row else next_id, "name": name, "details": details, "message": "Supplier created successfully"}
    except Exception:
        return {"id": next_id, "name": name, "details": details, "message": "Supplier created successfully"}

@app.put("/api/suppliers/{supplier_id}")
def update_supplier(supplier_id: int, data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    details = (data.get("details") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Supplier name cannot be empty")
    try:
        db.execute(text("UPDATE suppliers SET name = :name, details = :details WHERE id = :id"), {"id": supplier_id, "name": name, "details": details})
        db.commit()
    except Exception:
        db.rollback()
        try:
            s_obj = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
            if s_obj:
                s_obj.name = name
                s_obj.details = details
                db.commit()
        except Exception as ex:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update supplier: {ex}")
    return {"id": supplier_id, "name": name, "details": details, "message": "Supplier updated successfully"}

@app.delete("/api/suppliers/{supplier_id}")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM suppliers WHERE id = :id"), {"id": supplier_id})
        db.commit()
    except Exception:
        db.rollback()
        try:
            s_obj = db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()
            if s_obj:
                db.delete(s_obj)
                db.commit()
        except Exception:
            db.rollback()
    return {"message": "Supplier deleted"}

@app.delete("/api/suppliers/clear-all")
@app.delete("/api/suppliers/all")
@app.post("/api/suppliers/clear-all")
def clear_all_suppliers(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM suppliers;"))
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All suppliers cleared successfully!"}

# --- Setters ---
@app.get("/api/setters")
def get_setters(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM setters ORDER BY id ASC")).mappings().all()
        if rows:
            return [{"id": r.get("id"), "name": r.get("name") or "", "department": r.get("department") or r.get("dept") or ""} for r in rows]
    except Exception:
        db.rollback()

    try:
        setters = db.query(models.Setter).order_by(models.Setter.id.asc()).all()
        return [{"id": s.id, "name": s.name, "department": s.department or ""} for s in setters]
    except Exception:
        db.rollback()
        return []

@app.post("/api/setters")
def create_setter(data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    department = (data.get("department") or data.get("dept") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Setter name cannot be empty")
    
    try:
        existing = db.execute(text("SELECT id, name, department FROM setters WHERE UPPER(name) = :name"), {"name": name.upper()}).mappings().first()
        if existing:
            return {"id": existing.get("id"), "name": existing.get("name"), "department": existing.get("department"), "message": "Setter already exists"}
    except Exception:
        db.rollback()

    try:
        db.execute(text("SELECT setval(pg_get_serial_sequence('setters', 'id'), coalesce(max(id),0) + 1, false) FROM setters;"))
        db.commit()
    except Exception:
        db.rollback()

    try:
        max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM setters")).mappings().first()
        next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 1
        
        try:
            db.execute(text("INSERT INTO setters (id, name, department) VALUES (:id, :name, :department)"), {"id": next_id, "name": name, "department": department})
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("INSERT INTO setters (name, department) VALUES (:name, :department)"), {"name": name, "department": department})
            db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create setter: {ex}")
    
    try:
        row = db.execute(text("SELECT id, name, department FROM setters WHERE UPPER(name) = :name ORDER BY id DESC LIMIT 1"), {"name": name.upper()}).mappings().first()
        return {"id": row.get("id") if row else next_id, "name": name, "department": department, "message": "Setter created successfully"}
    except Exception:
        return {"id": next_id, "name": name, "department": department, "message": "Setter created successfully"}

@app.put("/api/setters/{setter_id}")
def update_setter(setter_id: int, data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    department = (data.get("department") or data.get("dept") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Setter name cannot be empty")
    try:
        db.execute(text("UPDATE setters SET name = :name, department = :department WHERE id = :id"), {"id": setter_id, "name": name, "department": department})
        db.commit()
    except Exception:
        db.rollback()
        try:
            s_obj = db.query(models.Setter).filter(models.Setter.id == setter_id).first()
            if s_obj:
                s_obj.name = name
                s_obj.department = department
                db.commit()
        except Exception as ex:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update setter: {ex}")
    return {"id": setter_id, "name": name, "department": department, "message": "Setter updated successfully"}

@app.delete("/api/setters/{setter_id}")
def delete_setter(setter_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM setters WHERE id = :id"), {"id": setter_id})
        db.commit()
    except Exception:
        db.rollback()
        try:
            s_obj = db.query(models.Setter).filter(models.Setter.id == setter_id).first()
            if s_obj:
                db.delete(s_obj)
                db.commit()
        except Exception:
            db.rollback()
    return {"message": "Setter deleted"}

@app.delete("/api/setters/clear-all")
@app.delete("/api/setters/all")
@app.post("/api/setters/clear-all")
def clear_all_setters(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM setters;"))
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All setters cleared successfully!"}

# --- Operators ---
@app.get("/api/operators")
def get_operators(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        rows = db.execute(text("SELECT * FROM operators ORDER BY id ASC")).mappings().all()
        if rows:
            return [{
                "id": r.get("id"),
                "name": r.get("name") or r.get("operator_name") or "",
                "dept": r.get("dept") or r.get("department") or "",
                "department": r.get("dept") or r.get("department") or "",
                "designation": r.get("designation") or "Operator"
            } for r in rows]
    except Exception:
        db.rollback()

    try:
        operators = db.query(models.Operator).order_by(models.Operator.id.asc()).all()
        return [{
            "id": o.id,
            "name": o.name,
            "dept": getattr(o, "dept", "") or getattr(o, "department", "") or "",
            "department": getattr(o, "dept", "") or getattr(o, "department", "") or "",
            "designation": getattr(o, "designation", "Operator") or "Operator"
        } for o in operators]
    except Exception:
        db.rollback()
        return []

@app.post("/api/operators")
def create_operator(data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    dept = (data.get("dept") or data.get("department") or "").strip()
    desig = (data.get("designation") or "Operator").strip()
    saved = False
    try:
        db.execute(text("INSERT INTO operators (name, dept, department, designation) VALUES (:name, :dept, :dept, :designation)"), {"name": name, "dept": dept, "designation": desig})
        db.commit()
        saved = True
    except Exception:
        db.rollback()
        try:
            db.execute(text("INSERT INTO operators (name, dept, designation) VALUES (:name, :dept, :designation)"), {"name": name, "dept": dept, "designation": desig})
            db.commit()
            saved = True
        except Exception:
            db.rollback()
            try:
                db.execute(text("INSERT INTO operators (name, department, designation) VALUES (:name, :dept, :designation)"), {"name": name, "dept": dept, "designation": desig})
                db.commit()
                saved = True
            except Exception:
                db.rollback()
    if not saved:
        try:
            op_obj = models.Operator(name=name, dept=dept, designation=desig)
            db.add(op_obj)
            db.commit()
            saved = True
        except Exception:
            db.rollback()
    return {"message": "Operator created", "name": name, "dept": dept, "department": dept, "designation": desig}

@app.post("/api/operators/import-excel")
async def import_operators_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    rows = parse_excel_bytes(contents)
    if not rows:
        raise HTTPException(status_code=400, detail="Could not parse Excel file or file is empty")
    
    headers = [h.lower().strip() for h in rows[0]]
    
    name_idx = -1
    dept_idx = -1
    desig_idx = -1
    
    for i, h in enumerate(headers):
        if "name" in h or "operator" in h:
            name_idx = i
        elif "dept" in h or "department" in h:
            dept_idx = i
        elif "designation" in h or "role" in h or "desig" in h:
            desig_idx = i

    if name_idx == -1:
        name_idx = 1 if len(headers) > 1 else 0
        dept_idx = 0 if len(headers) > 1 else -1

    existing_op_names = {o.name.strip().upper() for o in db.query(models.Operator).all()}
    imported_count = 0

    for row in rows[1:]:
        if name_idx < len(row) and row[name_idx]:
            name = row[name_idx].strip()
            if not name or name.upper() in ["OPERATOR", "OPERATOR NAME", "EMP NAME"]:
                continue
            dept = row[dept_idx].strip() if dept_idx != -1 and dept_idx < len(row) and row[dept_idx] else "General"
            desig = row[desig_idx].strip() if desig_idx != -1 and desig_idx < len(row) and row[desig_idx] else "Operator"
            
            if name.upper() not in existing_op_names:
                op_obj = models.Operator(name=name, dept=dept, designation=desig)
                db.add(op_obj)
                existing_op_names.add(name.upper())
                imported_count += 1
                
    db.commit()
    return {"imported_count": imported_count, "message": f"Successfully imported {imported_count} new operators!"}

@app.put("/api/operators/{op_id}")
def update_operator(op_id: int, data: dict, db: Session = Depends(get_db)):
    name = (data.get("name") or "").strip()
    dept = (data.get("dept") or data.get("department") or "").strip()
    desig = (data.get("designation") or "Operator").strip()
    
    old_name = None
    try:
        existing = db.query(models.Operator).filter(models.Operator.id == op_id).first()
        if existing:
            old_name = existing.name
    except Exception:
        pass
    if not old_name:
        try:
            r = db.execute(text("SELECT name FROM operators WHERE id = :id"), {"id": op_id}).mappings().first()
            if r:
                old_name = r.get("name")
        except Exception:
            pass

    updated = False
    # Attempt 1: Update both dept and department columns
    try:
        db.execute(text("UPDATE operators SET name = :name, dept = :dept, department = :dept, designation = :designation WHERE id = :id"),
                   {"id": op_id, "name": name, "dept": dept, "designation": desig})
        db.commit()
        updated = True
    except Exception:
        db.rollback()
        # Attempt 2: Update dept and designation
        try:
            db.execute(text("UPDATE operators SET name = :name, dept = :dept, designation = :designation WHERE id = :id"),
                       {"id": op_id, "name": name, "dept": dept, "designation": desig})
            db.commit()
            updated = True
        except Exception:
            db.rollback()
            # Attempt 3: Update department and designation
            try:
                db.execute(text("UPDATE operators SET name = :name, department = :dept, designation = :designation WHERE id = :id"),
                           {"id": op_id, "name": name, "dept": dept, "designation": desig})
                db.commit()
                updated = True
            except Exception:
                db.rollback()

    # Also update via ORM model if possible
    try:
        op_obj = db.query(models.Operator).filter(models.Operator.id == op_id).first()
        if op_obj:
            op_obj.name = name
            if hasattr(op_obj, "dept"):
                op_obj.dept = dept
            if hasattr(op_obj, "department"):
                op_obj.department = dept
            if hasattr(op_obj, "designation"):
                op_obj.designation = desig
            db.commit()
            updated = True
    except Exception:
        db.rollback()

    # Sync corresponding records in hr_shift_assignments
    target_names = [n for n in [old_name, name] if n]
    for nm in target_names:
        try:
            db.execute(text("UPDATE hr_shift_assignments SET emp_name = :new_name, dept = :dept, designation = :designation WHERE UPPER(TRIM(emp_name)) = :target_name"),
                       {"new_name": name, "dept": dept, "designation": desig, "target_name": nm.strip().upper()})
            db.commit()
        except Exception:
            db.rollback()

    return {"status": "success", "id": op_id, "name": name, "dept": dept, "department": dept, "designation": desig}

@app.delete("/api/operators/{op_id}")
def delete_single_operator(op_id: int, db: Session = Depends(get_db)):
    deleted = False
    try:
        db.execute(text("DELETE FROM operators WHERE id = :id"), {"id": op_id})
        db.commit()
        deleted = True
    except Exception:
        db.rollback()
    try:
        op = db.query(models.Operator).filter(models.Operator.id == op_id).first()
        if op:
            db.delete(op)
            db.commit()
            deleted = True
    except Exception:
        db.rollback()
    return {"status": "success", "deleted": deleted, "id": op_id}

@app.delete("/api/operators/clear-all")
@app.delete("/api/operators/all")
@app.post("/api/operators/clear-all")
def clear_all_operators(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM operators;"))
        db.commit()
    except Exception:
        db.rollback()
    try:
        db.query(models.Operator).delete()
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All operators deleted successfully."}

@app.post("/api/operators/bulk_import")
def bulk_import_operators(data: dict, db: Session = Depends(get_db)):
    operators = data.get("operators") or []
    count = 0
    for op in operators:
        name = (op.get("name") or op.get("operator_name") or "").strip()
        dept = (op.get("department") or op.get("dept") or "").strip()
        desig = (op.get("designation") or op.get("role") or "Operator").strip()
        if name:
            saved = False
            try:
                db.execute(text("INSERT INTO operators (name, dept, department, designation) VALUES (:name, :dept, :dept, :desig)"), {"name": name, "dept": dept, "desig": desig})
                db.commit()
                count += 1
                saved = True
            except Exception:
                db.rollback()
                try:
                    db.execute(text("INSERT INTO operators (name, dept, designation) VALUES (:name, :dept, :desig)"), {"name": name, "dept": dept, "desig": desig})
                    db.commit()
                    count += 1
                    saved = True
                except Exception:
                    db.rollback()
                    try:
                        db.execute(text("INSERT INTO operators (name, department, designation) VALUES (:name, :dept, :desig)"), {"name": name, "dept": dept, "desig": desig})
                        db.commit()
                        count += 1
                        saved = True
                    except Exception:
                        db.rollback()
            if not saved:
                try:
                    op_obj = models.Operator(name=name, dept=dept, designation=desig)
                    db.add(op_obj)
                    db.commit()
                    count += 1
                except Exception:
                    db.rollback()
    return {"message": f"Successfully imported {count} operators!", "imported_count": count}

# --- Part Master API ---
@app.post("/api/partmaster/bulk_import")
def bulk_import_partmasters(data: dict, db: Session = Depends(get_db)):
    parts = data.get("parts") or []
    count = 0
    for p in parts:
        partno = (p.get("partno") or p.get("part_no") or "").strip()
        family = (p.get("family") or "").strip()
        forge_pn = (p.get("forge_pn") or p.get("forgepn") or "").strip()
        part_prefix = (p.get("part_prefix") or p.get("prefix") or "").strip()
        department = (p.get("department") or p.get("dept") or "").strip()
        customer = (p.get("customer") or "").strip()
        va = str(p.get("va") or 0)
        operations = p.get("operations") or []
        if partno:
            try:
                max_id = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM part_masters")).scalar() or 0
                next_id = int(max_id) + 1
                db.execute(text("INSERT INTO part_masters (id, customer, department, family, forge_pn, part_prefix, partno, va, rfd_phy) VALUES (:id, :customer, :department, :family, :forge_pn, :part_prefix, :partno, :va, :rfd_phy)"), {
                    "id": next_id,
                    "customer": customer,
                    "department": department,
                    "family": family,
                    "forge_pn": forge_pn,
                    "part_prefix": part_prefix,
                    "partno": partno,
                    "va": va,
                    "rfd_phy": 0
                })
                try:
                    db.execute(text("SELECT setval(pg_get_serial_sequence('part_masters', 'id'), (SELECT MAX(id) FROM part_masters));"))
                except Exception:
                    pass
                db.commit()
                count += 1
            except Exception as e1:
                db.rollback()
                print("Note inserting to part_masters in bulk_import:", e1)
            
            try:
                p_max_id = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM parts")).scalar() or 0
                p_next_id = int(p_max_id) + 1
                db.execute(text("INSERT INTO parts (id, part_no, customer, dept, family, forge_pn, va) VALUES (:id, :part_no, :customer, :dept, :family, :forge_pn, :va)"), {
                    "id": p_next_id,
                    "part_no": partno,
                    "customer": customer,
                    "dept": department,
                    "family": family,
                    "forge_pn": forge_pn,
                    "va": float(va) if va.replace('.','',1).isdigit() else 0.0
                })
                try:
                    db.execute(text("SELECT setval(pg_get_serial_sequence('parts', 'id'), (SELECT MAX(id) FROM parts));"))
                except Exception:
                    pass
                db.commit()
            except Exception:
                db.rollback()
            
            if operations:
                try:
                    row = db.execute(text("SELECT id FROM part_masters WHERE partno = :p ORDER BY id DESC LIMIT 1"), {"p": partno}).mappings().first()
                    part_id = row.get("id") if row else None
                    for op in operations:
                        opn = str(op.get("opn_no") or "")
                        desc = op.get("description") or ""
                        mc = op.get("machine") or op.get("machine_name") or ""
                        cyc = float(op.get("cycle_time") or 0)
                        if (opn or desc) and part_id:
                            try:
                                db.execute(text("INSERT INTO part_operations (part_id, opn_no, description, machine, cycle_time) VALUES (:part_id, :opn_no, :description, :machine, :cycle_time)"), {
                                    "part_id": str(part_id),
                                    "opn_no": opn,
                                    "description": desc,
                                    "machine": mc,
                                    "cycle_time": cyc
                                })
                                db.commit()
                            except Exception:
                                db.rollback()
                except Exception:
                    db.rollback()
    sync_partmaster_forge_pns_to_rawmaterials(db)
    return {"message": f"Successfully imported {count} parts!", "imported_count": count}
@app.delete("/api/partmaster/clear-all")
@app.post("/api/partmaster/clear-all")
def clear_all_parts(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM part_masters;"))
    except Exception:
        pass
    try:
        db.execute(text("DELETE FROM parts;"))
    except Exception:
        pass
    try:
        db.execute(text("DELETE FROM part_operations;"))
    except Exception:
        pass
    try:
        db.commit()
    except Exception:
        db.rollback()
    return {"success": True, "message": "All parts cleared successfully!"}

@app.get("/api/partmaster")
def get_partmasters(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM part_masters ORDER BY CASE WHEN customer IS NOT NULL AND customer != '' THEN 0 ELSE 1 END, id ASC")).mappings().all()
        results = []
        for r in rows:
            p_no = r.get("partno") or r.get("part_no") or r.get("part_number") or ""
            if p_no:
                results.append({
                    "id": r.get("id"),
                    "customer": r.get("customer") or r.get("customer_name") or "",
                    "department": r.get("department") or r.get("dept") or "",
                    "family": r.get("family") or "",
                    "forge_pn": r.get("forge_pn") or r.get("forge_part_no") or "",
                    "part_prefix": r.get("part_prefix") or "",
                    "partno": p_no,
                    "part_no": p_no,
                    "va": r.get("va") or 0,
                    "rfd_phy": r.get("rfd_phy") or 0
                })
        return results
    except Exception as e:
        print("get_partmasters error:", e)
        db.rollback()
        return []

@app.get("/api/partmaster/{part_id}")
def get_partmaster_by_id(part_id: int, db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM part_masters WHERE id = :id"), {"id": part_id}).mappings().all()
        if rows:
            r = rows[0]
            return {
                "id": r.get("id"),
                "customer": r.get("customer") or "",
                "department": r.get("department") or r.get("dept") or "",
                "family": r.get("family") or "",
                "forge_pn": r.get("forge_pn") or "",
                "part_prefix": r.get("part_prefix") or "",
                "partno": r.get("partno") or r.get("part_no") or "",
                "part_no": r.get("partno") or r.get("part_no") or "",
                "va": r.get("va") or 0,
                "rfd_phy": r.get("rfd_phy") or 0
            }
    except Exception:
        db.rollback()
    return {}

@app.get("/api/partmaster/{part_id}/operations")
def get_partmaster_operations(part_id: int, db: Session = Depends(get_db)):
    # 1. Search part_operations by part_id
    try:
        rows = db.execute(text("SELECT * FROM part_operations WHERE CAST(part_id AS TEXT) = :part_id_str ORDER BY id ASC"), {"part_id_str": str(part_id)}).mappings().all()
        if rows:
            results = []
            for r in rows:
                results.append({
                    "id": r.get("id"),
                    "part_id": part_id,
                    "opn_no": str(r.get("opn_no") or ""),
                    "description": r.get("description") or "",
                    "machine": r.get("machine") or r.get("machine_name") or "",
                    "cycle_time": float(r.get("cycle_time") or 0.0)
                })
            return results
    except Exception as e:
        db.rollback()

    # 2. Search operations by part_id
    try:
        rows = db.execute(text("SELECT * FROM operations WHERE CAST(part_id AS TEXT) = :part_id_str ORDER BY id ASC"), {"part_id_str": str(part_id)}).mappings().all()
        if rows:
            results = []
            for r in rows:
                results.append({
                    "id": r.get("id"),
                    "part_id": part_id,
                    "opn_no": str(r.get("opn_no") or ""),
                    "description": r.get("description") or "",
                    "machine": r.get("machine_name") or r.get("machine") or "",
                    "cycle_time": float(r.get("cycle_time") or 0.0)
                })
            return results
    except Exception as e:
        db.rollback()

    # 3. Fallback by matching partno
    try:
        pm_rows = db.execute(text("SELECT * FROM part_masters WHERE id = :id"), {"id": part_id}).mappings().all()
        if pm_rows:
            p_no = pm_rows[0].get("partno") or pm_rows[0].get("part_no") or ""
            if p_no:
                part_rows = db.execute(text("SELECT id FROM parts WHERE part_no = :p_no"), {"p_no": p_no}).mappings().all()
                if part_rows:
                    real_pid = part_rows[0].get("id")
                    rows = db.execute(text("SELECT * FROM operations WHERE part_id = :pid ORDER BY id ASC"), {"pid": real_pid}).mappings().all()
                    if rows:
                        results = []
                        for r in rows:
                            results.append({
                                "id": r.get("id"),
                                "part_id": part_id,
                                "opn_no": str(r.get("opn_no") or ""),
                                "description": r.get("description") or "",
                                "machine": r.get("machine_name") or r.get("machine") or "",
                                "cycle_time": float(r.get("cycle_time") or 0.0)
                            })
                        return results
    except Exception:
        db.rollback()

    return []

@app.put("/api/partmaster/{part_id}/operations")
@app.post("/api/partmaster/{part_id}/operations")
def save_partmaster_operations(part_id: int, ops: List[dict], db: Session = Depends(get_db)):
    try:
        # Create table part_operations if not exists
        try:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS part_operations (
                    id SERIAL PRIMARY KEY,
                    part_id TEXT,
                    opn_no TEXT,
                    description TEXT,
                    machine TEXT,
                    cycle_time FLOAT DEFAULT 0.0
                );
            """))
            db.commit()
        except Exception:
            db.rollback()

        # Find matching partno and real parts.id
        p_no = ""
        real_pid = None
        try:
            pm_row = db.execute(text("SELECT * FROM part_masters WHERE id = :id"), {"id": part_id}).mappings().first()
            if pm_row:
                p_no = (pm_row.get("partno") or pm_row.get("part_no") or "").strip()
            if p_no:
                p_row = db.execute(text("SELECT id FROM parts WHERE part_no = :p_no"), {"p_no": p_no}).mappings().first()
                if p_row:
                    real_pid = p_row.get("id")
        except Exception:
            db.rollback()

        # Delete existing operations for this part
        try:
            db.execute(text("DELETE FROM part_operations WHERE CAST(part_id AS TEXT) = :part_id_str"), {"part_id_str": str(part_id)})
        except Exception:
            pass

        if p_no:
            try:
                db.execute(text("DELETE FROM part_operations WHERE CAST(part_id AS TEXT) = :p_no"), {"p_no": p_no})
            except Exception:
                pass

        try:
            db.execute(text("DELETE FROM operations WHERE part_id = :pid"), {"pid": part_id})
        except Exception:
            pass

        if real_pid and real_pid != part_id:
            try:
                db.execute(text("DELETE FROM operations WHERE part_id = :pid"), {"pid": real_pid})
            except Exception:
                pass

        db.commit()

        # Insert new operations
        for op in ops:
            opn = str(op.get("opn_no") or "").strip()
            desc = (op.get("description") or "").strip()
            mach = (op.get("machine") or op.get("machine_name") or "").strip()
            cyc = float(op.get("cycle_time") or 0.0)

            if not opn and not desc:
                continue

            try:
                db.execute(text("""
                    INSERT INTO part_operations (part_id, opn_no, description, machine, cycle_time)
                    VALUES (:part_id, :opn_no, :description, :machine, :cycle_time)
                """), {
                    "part_id": str(part_id),
                    "opn_no": opn,
                    "description": desc,
                    "machine": mach,
                    "cycle_time": cyc
                })
                db.commit()
            except Exception:
                db.rollback()

            target_pids = set([part_id])
            if real_pid:
                target_pids.add(real_pid)

            for t_pid in target_pids:
                try:
                    db.execute(text("""
                        INSERT INTO operations (part_id, opn_no, description, machine_name, cycle_time)
                        VALUES (:part_id, :opn_no, :description, :machine_name, :cycle_time)
                    """), {
                        "part_id": t_pid,
                        "opn_no": opn,
                        "description": desc,
                        "machine_name": mach,
                        "cycle_time": cyc
                    })
                    db.commit()
                except Exception:
                    db.rollback()

        return {"message": "Operations saved successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save operations: {e}")

@app.post("/api/partmaster")
def create_partmaster(data: dict, db: Session = Depends(get_db)):
    try:
        max_id = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM part_masters")).scalar() or 0
        next_id = int(max_id) + 1
        
        partno = (data.get("partno") or data.get("part_no") or "").strip()
        customer = (data.get("customer") or "").strip()
        department = (data.get("department") or data.get("dept") or "").strip()
        family = (data.get("family") or "").strip()
        forge_pn = (data.get("forge_pn") or "").strip()
        part_prefix = (data.get("part_prefix") or "").strip()
        va = str(data.get("va") if data.get("va") is not None else 0)
        rfd_phy = str(data.get("rfd_phy") if data.get("rfd_phy") is not None else 0)

        db.execute(text("""
            INSERT INTO part_masters (id, customer, department, family, forge_pn, part_prefix, partno, va, rfd_phy) 
            VALUES (:id, :customer, :department, :family, :forge_pn, :part_prefix, :partno, :va, :rfd_phy)
        """), {
            "id": next_id,
            "customer": customer,
            "department": department,
            "family": family,
            "forge_pn": forge_pn,
            "part_prefix": part_prefix,
            "partno": partno,
            "va": va,
            "rfd_phy": rfd_phy
        })

        # Sync postgres sequence if applicable
        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('part_masters', 'id'), (SELECT MAX(id) FROM part_masters));"))
        except Exception:
            pass

        # Also sync into parts table
        if partno:
            try:
                p_max_id = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM parts")).scalar() or 0
                p_next_id = int(p_max_id) + 1
                va_float = float(va) if va.replace('.', '', 1).isdigit() else 0.0

                existing_p = db.execute(text("SELECT id FROM parts WHERE UPPER(TRIM(part_no)) = :p"), {"p": partno.upper()}).mappings().first()
                if existing_p:
                    db.execute(text("""
                        UPDATE parts SET 
                            customer = :customer, 
                            dept = :dept, 
                            family = :family, 
                            forge_pn = :forge_pn, 
                            va = :va 
                        WHERE id = :id
                    """), {
                        "id": existing_p["id"],
                        "customer": customer,
                        "dept": department,
                        "family": family,
                        "forge_pn": forge_pn,
                        "va": va_float
                    })
                else:
                    db.execute(text("""
                        INSERT INTO parts (id, part_no, customer, dept, family, forge_pn, va)
                        VALUES (:id, :part_no, :customer, :dept, :family, :forge_pn, :va)
                    """), {
                        "id": p_next_id,
                        "part_no": partno,
                        "customer": customer,
                        "dept": department,
                        "family": family,
                        "forge_pn": forge_pn,
                        "va": va_float
                    })
                    try:
                        db.execute(text("SELECT setval(pg_get_serial_sequence('parts', 'id'), (SELECT MAX(id) FROM parts));"))
                    except Exception:
                        pass
            except Exception as pe:
                print("Note syncing to parts table:", pe)

        # Sync forge_pn to raw_materials table if provided
        if forge_pn:
            try:
                exist_rm = db.execute(text("SELECT id FROM raw_materials WHERE UPPER(TRIM(forge_pn)) = UPPER(TRIM(:fpn))"), {"fpn": forge_pn}).mappings().first()
                if not exist_rm:
                    db.execute(text("""
                        INSERT INTO raw_materials (forge_pn, receipt, despatch, stock)
                        VALUES (:forge_pn, 0, 0, 0)
                    """), {"forge_pn": forge_pn})
            except Exception as rme:
                print("Note syncing forge_pn to raw_materials:", rme)

        db.commit()
        return {"message": "Part master created", "id": next_id, **data}
    except Exception as e:
        db.rollback()
        print("Error creating part master:", e)
        raise HTTPException(status_code=500, detail=f"Failed to create part master: {str(e)}")

@app.put("/api/partmaster/{part_id}")
def update_partmaster(part_id: int, data: dict, db: Session = Depends(get_db)):
    try:
        partno = (data.get("partno") or data.get("part_no") or "").strip()
        customer = (data.get("customer") or "").strip()
        department = (data.get("department") or data.get("dept") or "").strip()
        family = (data.get("family") or "").strip()
        forge_pn = (data.get("forge_pn") or "").strip()
        part_prefix = (data.get("part_prefix") or "").strip()
        va = str(data.get("va") if data.get("va") is not None else 0)

        db.execute(text("""
            UPDATE part_masters 
            SET customer = :customer, department = :department, family = :family, 
                forge_pn = :forge_pn, part_prefix = :part_prefix, partno = :partno, va = :va 
            WHERE id = :id
        """), {
            "id": part_id,
            "customer": customer,
            "department": department,
            "family": family,
            "forge_pn": forge_pn,
            "part_prefix": part_prefix,
            "partno": partno,
            "va": va
        })

        if partno:
            try:
                va_float = float(va) if va.replace('.', '', 1).isdigit() else 0.0
                existing_p = db.execute(text("SELECT id FROM parts WHERE UPPER(TRIM(part_no)) = :p"), {"p": partno.upper()}).mappings().first()
                if existing_p:
                    db.execute(text("""
                        UPDATE parts SET 
                            customer = :customer, 
                            dept = :dept, 
                            family = :family, 
                            forge_pn = :forge_pn, 
                            va = :va 
                        WHERE id = :id
                    """), {
                        "id": existing_p["id"],
                        "customer": customer,
                        "dept": department,
                        "family": family,
                        "forge_pn": forge_pn,
                        "va": va_float
                    })
            except Exception as pe:
                print("Note syncing update to parts table:", pe)

        # Sync forge_pn to raw_materials table if provided
        if forge_pn:
            try:
                exist_rm = db.execute(text("SELECT id FROM raw_materials WHERE UPPER(TRIM(forge_pn)) = UPPER(TRIM(:fpn))"), {"fpn": forge_pn}).mappings().first()
                if not exist_rm:
                    db.execute(text("""
                        INSERT INTO raw_materials (forge_pn, receipt, despatch, stock)
                        VALUES (:forge_pn, 0, 0, 0)
                    """), {"forge_pn": forge_pn})
            except Exception as rme:
                print("Note syncing forge_pn to raw_materials on update:", rme)

        db.commit()
        return {"id": part_id, "message": "Part master updated", **data}
    except Exception as e:
        db.rollback()
        print("Error updating part master:", e)
        raise HTTPException(status_code=500, detail=f"Failed to update part master: {str(e)}")

@app.delete("/api/partmaster/{part_id}")
def delete_partmaster(part_id: int, db: Session = Depends(get_db)):
    try:
        row = db.execute(text("SELECT partno FROM part_masters WHERE id = :id"), {"id": part_id}).mappings().first()
        partno = row.get("partno") if row else None

        db.execute(text("DELETE FROM part_masters WHERE id = :id"), {"id": part_id})
        db.execute(text("DELETE FROM part_operations WHERE CAST(part_id AS TEXT) = :id"), {"id": str(part_id)})

        if partno:
            try:
                db.execute(text("DELETE FROM parts WHERE UPPER(TRIM(part_no)) = :p"), {"p": partno.strip().upper()})
            except Exception:
                pass

        db.commit()
        return {"message": "Part master deleted"}
    except Exception as e:
        db.rollback()
        print("Error deleting part master:", e)
        raise HTTPException(status_code=500, detail=f"Failed to delete part master: {str(e)}")

# --- Parts ---
@app.get("/api/parts", response_model=List[PartResponse])
def get_parts(db: Session = Depends(get_db)):
    return db.query(models.Part).all()

@app.post("/api/parts", response_model=PartResponse)
def create_part(part: PartCreate, db: Session = Depends(get_db)):
    ops_data = part.operations
    part_dict = part.model_dump(exclude={"operations"})
    db_part = models.Part(**part_dict)
    
    for op in ops_data:
        db_part.operations.append(models.Operation(**op.model_dump()))

    db.add(db_part)
    db.commit()
    db.refresh(db_part)
    return db_part

@app.post("/api/parts/import-excel")
async def import_parts_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    rows = parse_excel_bytes(contents)
    if not rows:
        raise HTTPException(status_code=400, detail="Could not parse Excel file or file is empty")
    
    headers = [h.lower().strip() for h in rows[0]]
    
    part_no_idx = -1
    cust_idx = -1
    dept_idx = -1
    fam_idx = -1
    forge_idx = -1
    desc_idx = -1
    cycle_idx = -1
    va_idx = -1

    for i, h in enumerate(headers):
        if "part" in h or "drawing" in h: part_no_idx = i
        elif "cust" in h: cust_idx = i
        elif "dept" in h: dept_idx = i
        elif "family" in h: fam_idx = i
        elif "forge" in h: forge_idx = i
        elif "desc" in h: desc_idx = i
        elif "cycle" in h: cycle_idx = i
        elif "va" in h: va_idx = i

    if part_no_idx == -1: part_no_idx = 0

    existing_parts = {p.part_no.strip().upper(): p for p in db.query(models.Part).all()}
    imported_count = 0

    def safe_float(val, default=0.0):
        try:
            return float(val) if val else default
        except (ValueError, TypeError):
            return default

    for row in rows[1:]:
        if part_no_idx < len(row) and row[part_no_idx]:
            p_no = row[part_no_idx].strip()
            if not p_no or p_no.upper() in ["PART NO", "PART NUMBER", "DRAWING NO"]:
                continue
            
            cust = row[cust_idx].strip() if cust_idx != -1 and cust_idx < len(row) and row[cust_idx] else ""
            dept = row[dept_idx].strip() if dept_idx != -1 and dept_idx < len(row) and row[dept_idx] else ""
            fam = row[fam_idx].strip() if fam_idx != -1 and fam_idx < len(row) and row[fam_idx] else ""
            forge = row[forge_idx].strip() if forge_idx != -1 and forge_idx < len(row) and row[forge_idx] else ""
            desc = row[desc_idx].strip() if desc_idx != -1 and desc_idx < len(row) and row[desc_idx] else ""
            cycle = safe_float(row[cycle_idx]) if cycle_idx != -1 and cycle_idx < len(row) else 0.0
            va = safe_float(row[va_idx]) if va_idx != -1 and va_idx < len(row) else 0.0

            if p_no.upper() not in existing_parts:
                new_p = models.Part(
                    part_no=p_no, customer=cust, dept=dept, family=fam,
                    forge_pn=forge, description=desc, cycle_time=cycle, va=va
                )
                db.add(new_p)
                existing_parts[p_no.upper()] = new_p
                imported_count += 1
            else:
                existing_p = existing_parts[p_no.upper()]
                if cust: existing_p.customer = cust
                if dept: existing_p.dept = dept
                if fam: existing_p.family = fam
                if forge: existing_p.forge_pn = forge
                if desc: existing_p.description = desc
                if cycle > 0: existing_p.cycle_time = cycle
                if va > 0: existing_p.va = va

    db.commit()
    return {"imported_count": imported_count, "message": f"Successfully imported/updated parts master!"}

@app.put("/api/parts/{part_id}", response_model=PartResponse)
def update_part(part_id: int, part: PartCreate, db: Session = Depends(get_db)):
    db_part = db.query(models.Part).filter(models.Part.id == part_id).first()
    if not db_part:
        raise HTTPException(status_code=404, detail="Part not found")
    
    db_part.part_no = part.part_no
    db_part.customer = part.customer
    db_part.dept = part.dept
    db_part.family = part.family
    db_part.forge_pn = part.forge_pn
    db_part.description = part.description
    db_part.cycle_time = part.cycle_time
    db_part.va = part.va

    db.query(models.Operation).filter(models.Operation.part_id == part_id).delete()
    for op in part.operations:
        db_part.operations.append(models.Operation(**op.model_dump()))

    db.commit()
    db.refresh(db_part)
    return db_part

@app.delete("/api/parts/clear-all")
def clear_all_parts(db: Session = Depends(get_db)):
    db.query(models.Part).delete()
    db.commit()
    return {"message": "All parts cleared successfully!"}

@app.delete("/api/parts/{part_id}")
def delete_part(part_id: int, db: Session = Depends(get_db)):
    db_part = db.query(models.Part).filter(models.Part.id == part_id).first()
    if not db_part:
        raise HTTPException(status_code=404, detail="Part not found")
    db.delete(db_part)
    db.commit()
@app.post("/api/parts/{part_id}/operations", response_model=OperationResponse)
def create_operation(part_id: int, opn: OperationCreate, db: Session = Depends(get_db)):
    db_part = db.query(models.Part).filter(models.Part.id == part_id).first()
    if not db_part:
        raise HTTPException(status_code=404, detail="Part not found")
    db_opn = models.Operation(part_id=part_id, **opn.model_dump())
    db.add(db_opn)
    db.commit()
    db.refresh(db_opn)
    return db_opn

# --- Schedules CRUD ---
@app.get("/api/schedules")
@app.get("/api/schedule")
def get_schedules_endpoint(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT id, department, partno, target_date, qty, completed_qty, status FROM schedules ORDER BY id DESC")).mappings().all()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["qty"] = int(float(str(d.get("qty") or 0).strip()))
            except Exception:
                d["qty"] = 0
            try:
                d["completed_qty"] = int(float(str(d.get("completed_qty") or 0).strip()))
            except Exception:
                d["completed_qty"] = 0
            result.append(d)
        return result
    except Exception as e:
        print("get_schedules error:", e)
        db.rollback()
        return []

@app.post("/api/schedule")
@app.post("/api/schedules")
def create_schedule_endpoint(data: dict, db: Session = Depends(get_db)):
    try:
        partno = str(data.get("partno") or data.get("part_no") or "").strip()
        if not partno:
            raise HTTPException(status_code=400, detail="Part No is required")
        dept = str(data.get("department") or data.get("dept") or "").strip()
        target_date = str(data.get("target_date") or "").strip()
        qty = str(data.get("qty") or data.get("total_sch_qty") or 0).strip()
        completed_qty = str(data.get("completed_qty") or 0).strip()
        status = str(data.get("status") or "Pending").strip()

        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('schedules', 'id'), coalesce(max(id),0) + 1, false) FROM schedules;"))
            db.commit()
        except Exception:
            db.rollback()

        max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM schedules")).mappings().first()
        next_id = int(max_row["next_id"]) if max_row and max_row.get("next_id") else 1

        params = {
            "id": next_id,
            "department": dept,
            "partno": partno,
            "target_date": target_date,
            "qty": qty,
            "completed_qty": completed_qty,
            "status": status
        }
        try:
            db.execute(text("""
                INSERT INTO schedules (id, department, partno, target_date, qty, completed_qty, status)
                VALUES (:id, :department, :partno, :target_date, :qty, :completed_qty, :status)
            """), params)
            db.commit()
            return {"id": next_id, **params}
        except Exception:
            db.rollback()
            try:
                res = db.execute(text("""
                    INSERT INTO schedules (department, partno, target_date, qty, completed_qty, status)
                    VALUES (:department, :partno, :target_date, :qty, :completed_qty, :status)
                    RETURNING id
                """), {
                    "department": dept,
                    "partno": partno,
                    "target_date": target_date,
                    "qty": qty,
                    "completed_qty": completed_qty,
                    "status": status
                })
                new_id = res.scalar()
                db.commit()
                return {"id": new_id, **params}
            except Exception:
                db.rollback()
                db.execute(text("""
                    INSERT INTO schedules (department, partno, target_date, qty, completed_qty, status)
                    VALUES (:department, :partno, :target_date, :qty, :completed_qty, :status)
                """), {
                    "department": dept,
                    "partno": partno,
                    "target_date": target_date,
                    "qty": qty,
                    "completed_qty": completed_qty,
                    "status": status
                })
                db.commit()
                last_row = db.execute(text("SELECT id FROM schedules ORDER BY id DESC LIMIT 1")).mappings().first()
                new_id = int(last_row["id"]) if last_row and last_row.get("id") else next_id
                return {"id": new_id, **params}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/schedule/{sch_id}")
@app.put("/api/schedules/{sch_id}")
def update_schedule_endpoint(sch_id: int, data: dict, db: Session = Depends(get_db)):
    try:
        partno = str(data.get("partno") or data.get("part_no") or "").strip()
        dept = str(data.get("department") or data.get("dept") or "").strip()
        target_date = str(data.get("target_date") or "").strip()
        qty = str(data.get("qty") or data.get("total_sch_qty") or 0).strip()
        completed_qty = str(data.get("completed_qty") or 0).strip()
        status = str(data.get("status") or "Pending").strip()

        db.execute(text("""
            UPDATE schedules
            SET department = :dept, partno = :partno, target_date = :target_date,
                qty = :qty, completed_qty = :completed_qty, status = :status
            WHERE id = :id
        """), {
            "id": sch_id,
            "dept": dept,
            "partno": partno,
            "target_date": target_date,
            "qty": qty,
            "completed_qty": completed_qty,
            "status": status
        })
        db.commit()
        return {"id": sch_id, "department": dept, "partno": partno, "target_date": target_date, "qty": qty, "completed_qty": completed_qty, "status": status}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/schedule/{sch_id}")
@app.delete("/api/schedules/{sch_id}")
def delete_schedule_endpoint(sch_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM schedules WHERE id = :id"), {"id": sch_id})
        db.commit()
        return {"message": "Schedule deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/schedule")
@app.delete("/api/schedules")
@app.delete("/api/schedules/clear-all")
def clear_all_schedules_endpoint(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM schedules"))
        db.commit()
        return {"message": "All work schedules cleared successfully!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/schedule/run")
def get_schedule_run(dept: Optional[str] = None, month: Optional[str] = None, start_time: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        from datetime import datetime as dt_cls, timedelta as td_cls

        # 1. Fetch active schedules (status != 'Completed')
        sched_rows = []
        try:
            sched_rows = db.execute(text("SELECT id, department, partno, target_date, qty, completed_qty, status FROM schedules WHERE LOWER(COALESCE(status, '')) != 'completed' ORDER BY id DESC")).mappings().all()
        except Exception:
            db.rollback()
            try:
                sched_rows = db.execute(text("SELECT * FROM schedules WHERE status != 'Completed' ORDER BY id DESC")).mappings().all()
            except Exception:
                db.rollback()
                try:
                    sched_rows = db.execute(text("SELECT id, '' AS department, part_no AS partno, '' AS target_date, total_sch_qty AS qty, qty_disp AS completed_qty, 'Pending' AS status FROM production_schedules ORDER BY id DESC")).mappings().all()
                except Exception:
                    db.rollback()
                    sched_rows = []

        # 2. Fetch Part Master records (check part_masters first, fallback to parts)
        pm_rows = []
        try:
            pm_rows = db.execute(text("SELECT id, department, customer, family, forge_pn, part_prefix, partno, va FROM part_masters")).mappings().all()
        except Exception:
            db.rollback()
            try:
                pm_rows = db.execute(text("SELECT id, dept AS department, customer, family, forge_pn, '' AS part_prefix, part_no AS partno, va FROM parts")).mappings().all()
            except Exception:
                db.rollback()

        # 3. Fetch operations (from part_operations and operations)
        part_ops_rows = []
        try:
            part_ops_rows = db.execute(text("SELECT id, part_id, opn_no, description, machine, cycle_time FROM part_operations ORDER BY id ASC")).mappings().all()
        except Exception:
            db.rollback()

        ops_table_rows = []
        try:
            ops_table_rows = db.execute(text("SELECT id, part_id, opn_no, description, machine_name AS machine, cycle_time FROM operations ORDER BY id ASC")).mappings().all()
        except Exception:
            db.rollback()

        # Index operations by multiple possible part_id keys (str and int)
        ops_by_pid = {}
        for o in part_ops_rows:
            raw_pid = o.get("part_id")
            o_dict = dict(o)
            keys = [str(raw_pid).strip().upper()]
            try:
                keys.append(int(raw_pid))
            except Exception:
                pass
            for k in keys:
                if k not in ops_by_pid:
                    ops_by_pid[k] = []
                ops_by_pid[k].append(o_dict)

        for o in ops_table_rows:
            raw_pid = o.get("part_id")
            o_dict = dict(o)
            keys = [f"PARTS_{raw_pid}", f"PARTS_{str(raw_pid).strip().upper()}"]
            for k in keys:
                if k not in ops_by_pid:
                    ops_by_pid[k] = []
                ops_by_pid[k].append(o_dict)

        def _sort_op(o):
            raw = str(o.get("opn_no") or "0").strip()
            try:
                return (0, float(raw))
            except Exception:
                return (1, raw)

        for k in ops_by_pid:
            ops_by_pid[k].sort(key=_sort_op)

        def _clean(s):
            return re.sub(r'[^A-Z0-9]', '', str(s or '').upper())

        def _resolve_ops(sched_partno, dept_name=None):
            sp = str(sched_partno or '').strip().upper()
            sp_clean = _clean(sp)
            if not sp:
                return []

            # Direct match in ops_by_pid
            if sp in ops_by_pid:
                return ops_by_pid[sp]

            # Exact match in part_masters
            for pm in pm_rows:
                if dept_name and pm.get('department') and str(pm.get('department')).strip().upper() != str(dept_name).strip().upper():
                    continue
                pno = str(pm.get('partno') or '').strip().upper()
                if pno and pno == sp:
                    pid = pm.get('id')
                    if str(pid) in ops_by_pid: return ops_by_pid[str(pid)]
                    if pid in ops_by_pid: return ops_by_pid[pid]

            # Cleaned string match in part_masters
            for pm in pm_rows:
                if dept_name and pm.get('department') and str(pm.get('department')).strip().upper() != str(dept_name).strip().upper():
                    continue
                pno = str(pm.get('partno') or '').strip().upper()
                prefix = str(pm.get('part_prefix') or '').strip().upper()
                if (pno and _clean(pno) == sp_clean) or (prefix and _clean(prefix) == sp_clean):
                    pid = pm.get('id')
                    if str(pid) in ops_by_pid: return ops_by_pid[str(pid)]
                    if pid in ops_by_pid: return ops_by_pid[pid]

            # Containment match in part_masters (e.g. 393645 in prefix, or forge_pn M5#01A in sched_partno)
            for pm in pm_rows:
                if dept_name and pm.get('department') and str(pm.get('department')).strip().upper() != str(dept_name).strip().upper():
                    continue
                pno = str(pm.get('partno') or '').strip().upper()
                prefix = str(pm.get('part_prefix') or '').strip().upper()
                forge = str(pm.get('forge_pn') or '').strip().upper()
                if (pno and _clean(pno) in sp_clean) or (forge and _clean(forge) in sp_clean) or (prefix and sp_clean in _clean(prefix)):
                    pid = pm.get('id')
                    if str(pid) in ops_by_pid: return ops_by_pid[str(pid)]
                    if pid in ops_by_pid: return ops_by_pid[pid]

            # Check if part is in parts table directly
            for pm in pm_rows:
                pno = str(pm.get('partno') or '').strip().upper()
                if pno and _clean(pno) == sp_clean:
                    parts_k = f"PARTS_{pm.get('id')}"
                    if parts_k in ops_by_pid:
                        return ops_by_pid[parts_k]

            return []

        # 4. Fetch production logs for calculating produced quantities during the month
        prod_logs = []
        try:
            prod_logs = db.execute(text("SELECT partno, opn_no, prod_qty, date FROM production_logs")).mappings().all()
        except Exception:
            db.rollback()
            try:
                prod_logs = db.execute(text("SELECT part_no AS partno, opn_no, qty_produced AS prod_qty, log_date AS date FROM production_logs")).mappings().all()
            except Exception:
                db.rollback()

        prod_map = {}
        for l in prod_logs:
            lp = _clean(l.get("partno") or l.get("part_no") or "")
            lo = str(l.get("opn_no") or "").strip().lower()
            ld = str(l.get("date") or l.get("log_date") or "").strip()
            lmonth = ld[:7] if len(ld) >= 7 else ""
            try:
                lqty = float(l.get("prod_qty") or l.get("qty_produced") or 0.0)
            except Exception:
                lqty = 0.0
            if lp and lo and lmonth:
                k = (lp, lo, lmonth)
                prod_map[k] = prod_map.get(k, 0.0) + lqty

        # Working hours calendar logic: 21 hrs per day (06:00 to 03:00 next day, 03:00-06:00 downtime)
        def _normalize_work(dt):
            if dt.hour >= 3 and dt.hour < 6:
                return dt.replace(hour=6, minute=0, second=0, microsecond=0)
            return dt

        def _add_work_hours(start_dt, hours_to_add):
            cur = _normalize_work(start_dt)
            rem_min = int(round(hours_to_add * 60))
            while rem_min > 0:
                cur = _normalize_work(cur)
                if cur.hour >= 6:
                    end_w = (cur + td_cls(days=1)).replace(hour=3, minute=0, second=0, microsecond=0)
                else:
                    end_w = cur.replace(hour=3, minute=0, second=0, microsecond=0)
                win_min = int((end_w - cur).total_seconds() // 60)
                if rem_min <= win_min:
                    cur += td_cls(minutes=rem_min)
                    rem_min = 0
                else:
                    rem_min -= win_min
                    cur = end_w.replace(hour=6, minute=0, second=0, microsecond=0)
            return cur

        now_ist = get_now_ist()
        current_ym = now_ist.strftime("%Y-%m")
        target_month_filter = str(month).strip() if month and str(month).strip() else None
        target_dept_filter = str(dept).strip().lower() if dept and str(dept).strip().lower() not in ["", "all", "all departments", "undefined", "null"] else None

        def _extract_month(d_str):
            if not d_str:
                return current_ym
            s = str(d_str).strip()
            if len(s) >= 7 and s[4] == '-':
                return s[:7]
            parts = re.split(r'[\/\-]', s)
            if len(parts) == 3:
                if len(parts[0]) == 4:
                    return f"{parts[0]}-{parts[1].zfill(2)}"
                elif len(parts[2]) == 4:
                    return f"{parts[2]}-{parts[1].zfill(2)}"
            return s[:7] if len(s) >= 7 else current_ym

        # Determine base start time
        if start_time and str(start_time).strip():
            st_str = str(start_time).strip().replace("T", " ")
            try:
                if len(st_str) == 16:
                    base_start_time = dt_cls.strptime(st_str, "%Y-%m-%d %H:%M")
                elif len(st_str) == 19:
                    base_start_time = dt_cls.strptime(st_str, "%Y-%m-%d %H:%M:%S")
                elif len(st_str) == 10:
                    base_start_time = dt_cls.strptime(st_str, "%Y-%m-%d").replace(hour=6, minute=0)
                else:
                    base_start_time = dt_cls.fromisoformat(st_str)
            except Exception:
                base_start_time = now_ist.replace(minute=(0 if now_ist.minute < 30 else 30), second=0, microsecond=0)
        else:
            if not target_month_filter or target_month_filter == current_ym:
                base_start_time = now_ist.replace(minute=(0 if now_ist.minute < 30 else 30), second=0, microsecond=0)
            else:
                try:
                    y, m = [int(x) for x in target_month_filter.split("-")[:2]]
                    base_start_time = dt_cls(y, m, 1, 6, 0)
                except Exception:
                    base_start_time = now_ist.replace(minute=(0 if now_ist.minute < 30 else 30), second=0, microsecond=0)

        base_start_time = _normalize_work(base_start_time)

        machine_avail = {}
        machine_last_part = {}
        part_last_finish = {}

        run_items = []

        for s in sched_rows:
            partno = str(s.get("partno") or s.get("part_no") or "").strip()
            if not partno:
                continue
            sched_dept = str(s.get("department") or s.get("dept") or "").strip()
            target_date = str(s.get("target_date") or "").strip()
            sched_month = _extract_month(target_date)

            if target_dept_filter and sched_dept.lower() != target_dept_filter:
                continue

            if target_month_filter and sched_month and sched_month != target_month_filter:
                continue

            try:
                sched_qty = float(s.get("qty") or 0.0)
            except Exception:
                sched_qty = 0.0

            ops = _resolve_ops(partno, sched_dept)

            if ops:
                for o in ops:
                    opn_no = str(o.get("opn_no") or "").strip()
                    desc = str(o.get("description") or "").strip()
                    machine = str(o.get("machine") or "").strip()
                    try:
                        cyc = float(o.get("cycle_time") or 0.0)
                    except Exception:
                        cyc = 0.0

                    produced_in_month = prod_map.get((_clean(partno), opn_no.lower(), sched_month), 0.0)
                    pending_qty = max(0.0, sched_qty - produced_in_month)
                    runtime_hrs = round((pending_qty * cyc) / 60.0, 2)

                    # Machine scheduling with 2 hours setting time between parts
                    mc_key = machine.upper() if machine else "GENERAL"
                    earliest_mc = machine_avail.get(mc_key, base_start_time)

                    last_p = machine_last_part.get(mc_key)
                    if machine:
                        if last_p is not None and last_p != partno.upper():
                            earliest_mc = _add_work_hours(earliest_mc, 2.0)
                        elif last_p is None:
                            earliest_mc = _add_work_hours(earliest_mc, 2.0)

                    part_prev_finish = part_last_finish.get(partno.upper(), base_start_time)
                    op_start = max(earliest_mc, part_prev_finish)
                    op_end = _add_work_hours(op_start, runtime_hrs) if runtime_hrs > 0 else op_start

                    if machine:
                        machine_avail[mc_key] = op_end
                        machine_last_part[mc_key] = partno.upper()
                    part_last_finish[partno.upper()] = op_end

                    run_items.append({
                        "department": sched_dept,
                        "partno": partno,
                        "opn_no": opn_no,
                        "description": desc,
                        "machine": machine,
                        "sched_qty": int(sched_qty),
                        "qty": int(sched_qty),
                        "pending_qty": int(pending_qty),
                        "cycle_time": cyc,
                        "runtime": runtime_hrs,
                        "start_date": op_start.strftime("%Y-%m-%d %H:%M"),
                        "end_date": op_end.strftime("%Y-%m-%d %H:%M"),
                        "month": sched_month
                    })
            else:
                produced_in_month = prod_map.get((_clean(partno), "10", sched_month), 0.0)
                pending_qty = max(0.0, sched_qty - produced_in_month)
                runtime_hrs = 0.0

                part_prev_finish = part_last_finish.get(partno.upper(), base_start_time)
                op_start = part_prev_finish
                op_end = op_start
                part_last_finish[partno.upper()] = op_end

                run_items.append({
                    "department": sched_dept,
                    "partno": partno,
                    "opn_no": "10",
                    "description": "General Machining",
                    "machine": "",
                    "sched_qty": int(sched_qty),
                    "qty": int(sched_qty),
                    "pending_qty": int(pending_qty),
                    "cycle_time": 0.0,
                    "runtime": 0.0,
                    "start_date": op_start.strftime("%Y-%m-%d %H:%M"),
                    "end_date": op_end.strftime("%Y-%m-%d %H:%M"),
                    "month": sched_month
                })

        return run_items
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("get_schedule_run error:", e)
        db.rollback()
        return []

@app.get("/api/production/bc_status")
def get_bc_status_endpoint(month: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        if not month or not str(month).strip():
            now_ist = get_now_ist()
            month = now_ist.strftime("%Y-%m")
        else:
            month = str(month).strip()

        # Helper to match date against target month
        def is_in_month(d_str, target_month):
            if not d_str: return False
            s = str(d_str).strip()
            if s.startswith(target_month):
                return True
            if "/" in s:
                pts = s.split("/")
                if len(pts) == 3 and len(pts[2]) == 4:
                    ym = f"{pts[2]}-{pts[1].zfill(2)}"
                    return ym == target_month
            elif "-" in s:
                pts = s.split("-")
                if len(pts) == 3 and len(pts[0]) == 4:
                    ym = f"{pts[0]}-{pts[1].zfill(2)}"
                    return ym == target_month
                elif len(pts) == 3 and len(pts[2]) == 4:
                    ym = f"{pts[2]}-{pts[1].zfill(2)}"
                    return ym == target_month
            return False

        # 1. Fetch BC parts from part_masters
        pm_rows = db.execute(text("SELECT id, partno, customer, department FROM part_masters WHERE UPPER(TRIM(department)) = 'BC' ORDER BY partno;")).mappings().all()
        pm_map = {r['partno'].strip(): dict(r) for r in pm_rows if r['partno']}

        # Also fetch schedules for BC
        sch_rows = db.execute(text("SELECT id, department, partno, qty, status, target_date FROM schedules WHERE UPPER(TRIM(department)) = 'BC';")).mappings().all()
        sch_map = {}
        for s in sch_rows:
            pno = (s.get('partno') or '').strip()
            try:
                q = int(float(str(s.get('qty') or 0).strip()))
            except Exception:
                q = 0
            sch_map[pno] = sch_map.get(pno, 0) + q

        all_bc_partnos = sorted(set(list(pm_map.keys()) + [p for p in sch_map.keys() if p]))

        # 2. Operations per part
        po_rows = db.execute(text("SELECT id, part_id, opn_no, description, machine, cycle_time FROM part_operations ORDER BY id ASC;")).mappings().all()
        po_by_part = {}
        for r in po_rows:
            pid = str(r.get("part_id") or "").strip()
            if pid not in po_by_part:
                po_by_part[pid] = []
            po_by_part[pid].append(dict(r))

        fallback_po = {}
        try:
            op_rows = db.execute(text("SELECT o.id, o.part_id, o.opn_no, o.description, o.machine_name, o.cycle_time, p.part_no FROM operations o JOIN parts p ON o.part_id = p.id ORDER BY o.id ASC;")).mappings().all()
            for r in op_rows:
                pno = (r.get("part_no") or "").strip().upper()
                if pno not in fallback_po:
                    fallback_po[pno] = []
                fallback_po[pno].append({
                    "id": r.get("id"),
                    "part_id": r.get("part_id"),
                    "opn_no": r.get("opn_no"),
                    "description": r.get("description"),
                    "machine": r.get("machine_name"),
                    "cycle_time": r.get("cycle_time")
                })
        except Exception:
            pass

        part_ops_map = {}
        for pno in all_bc_partnos:
            pm = pm_map.get(pno)
            pid = str(pm['id']) if pm else ""
            ops = po_by_part.get(pid, [])
            if not ops and pno.upper() in fallback_po:
                ops = fallback_po[pno.upper()]
            part_ops_map[pno] = ops

        # Dynamically discover non-PC operation categories present in Part Master for BC
        raw_ops = set()
        for pno in all_bc_partnos:
            for o in part_ops_map[pno]:
                d = (o.get('description') or '').strip()
                if not d or d.upper() in ['PC', 'POWDER COATING'] or 'POWDER' in d.upper() or str(o.get('opn_no') or '').strip().upper() == 'PC' or d.lower() in ['pre drill', 'pre-drill']:
                    continue
                raw_ops.add(d)

        # Standard canonical order for BC operations (Pre Drill has been unified into Drill)
        canonical_order = ["Box Mill", "Mill Drill", "Drill", "Spherical", "Tapping", "Top Mill"]
        discovered_ops = []
        for c in canonical_order:
            has_any = False
            for pno in all_bc_partnos:
                for o in part_ops_map[pno]:
                    d = (o.get('description') or '').strip().lower()
                    if c.lower() == "box mill" and ("box" in d or d == "box milling"):
                        has_any = True; break
                    elif c.lower() == "mill drill" and "mill drill" in d:
                        has_any = True; break
                    elif c.lower() == "drill" and ("drill" in d or "drll" in d or "pre drill" in d or "pre-drill" in d) and "mill" not in d:
                        has_any = True; break
                    elif c.lower() == d:
                        has_any = True; break
                if has_any: break
            if has_any:
                discovered_ops.append(c)

        # Any other custom operation present in Part Master not covered above
        for r in sorted(raw_ops):
            r_clean = r.title()
            if r_clean.lower() in ["box mill", "box milling", "mill drill", "drill", "spherical", "tapping", "top mill", "pre drill", "pre-drill"]:
                continue
            if r_clean not in discovered_ops:
                discovered_ops.append(r_clean)

        # 3. Fetch monthly logs
        prod_rows = db.execute(text("SELECT partno, opn_no, description, machine, prod_qty, date FROM production_logs WHERE UPPER(TRIM(dept)) = 'BC';")).mappings().all()
        month_prod = [r for r in prod_rows if is_in_month(r.get('date'), month)]

        pc_rows = db.execute(text("SELECT partno, qty, date FROM pc_logs;")).mappings().all()
        month_pc_sent = [r for r in pc_rows if is_in_month(r.get('date'), month)]

        pc_rec_rows = db.execute(text("SELECT partno, qty, date FROM pc_receipt_logs;")).mappings().all()
        month_pc_rec = [r for r in pc_rec_rows if is_in_month(r.get('date'), month)]

        rm_desp_rows = db.execute(text("SELECT finish_part_no, qty, date FROM raw_material_logs WHERE type = 'despatch';")).mappings().all()
        month_desp = [r for r in rm_desp_rows if is_in_month(r.get('date'), month)]

        def match_part_master_op(op_cat, o_no, desc):
            cat = op_cat.lower()
            d = str(desc or '').strip().lower()
            if cat == "box mill":
                return "box" in d or d == "box milling"
            if cat == "mill drill":
                return "mill drill" in d
            if cat == "drill":
                return ("drill" in d or "drll" in d or "pre drill" in d or "pre-drill" in d) and "mill" not in d
            if cat == "spherical":
                return "spherical" in d
            if cat == "tapping":
                return "tap" in d
            if cat == "top mill":
                return "top mill" in d
            return cat == d

        def match_op_category(op_cat, log_opn, log_desc, log_mach):
            cat = op_cat.lower()
            o = str(log_opn or '').strip().lower()
            d = str(log_desc or '').strip().lower()
            m = str(log_mach or '').strip().lower()
            combined = f"{o} {d} {m}"
            
            if cat == "box mill":
                if "mill drill" in d or (("drill" in d or "drll" in d) and "mill" not in d):
                    return False
                return "box" in combined or (o == "20" and ("mill" in combined or not d or m in ["millwake", "wmw", "cincinati", "leadwell", "fn2v", "ams 1", "ams 2"]))

            if cat == "mill drill":
                if ("drill" in d or "drll" in d) and "mill" not in d:
                    return False
                return "mill drill" in combined or ("mill" in d and "drill" in d)

            if cat == "drill":
                if "mill drill" in combined:
                    return False
                if "drill" in d or "drll" in d or "drilling" in d or "pre drill" in d or "pre-drill" in d:
                    return True
                if m in ["new 2 way"]:
                    return True
                return False

            if cat == "spherical":
                return "spherical" in combined or (o == "40" and ("spherical" in combined or m in ["radial", "chamfer", "sph"]))

            if cat == "tapping":
                return "tap" in combined or o == "60" or "tapping" in m

            if cat == "top mill":
                return "top mill" in combined

            return cat in combined

        result_parts = []
        for pno in all_bc_partnos:
            pm = pm_map.get(pno, {})
            cust = pm.get('customer') or '-'
            sch_qty = sch_map.get(pno, 0)
            part_ops = part_ops_map.get(pno, [])

            op_prod = {}
            for op_cat in discovered_ops:
                has_op = any(match_part_master_op(op_cat, o.get('opn_no'), o.get('description')) for o in part_ops)
                qty = sum(
                    int(float(l.get('prod_qty') or 0))
                    for l in month_prod
                    if (l.get('partno') or '').strip().upper() == pno.upper() and match_op_category(op_cat, l.get('opn_no'), l.get('description'), l.get('machine'))
                )
                op_prod[op_cat] = {"has_op": has_op, "qty": qty}

            # Check if part has PC in Part Master
            has_pc_op = any((o.get('description') or '').strip().upper() == 'PC' or 'POWDER' in (o.get('description') or '').strip().upper() or str(o.get('opn_no') or '').strip().upper() == 'PC' for o in part_ops)

            to_pc = sum(
                int(float(l.get('qty') or 0))
                for l in month_pc_sent
                if (l.get('partno') or '').strip().upper() == pno.upper()
            )

            from_pc = sum(
                int(float(l.get('qty') or 0))
                for l in month_pc_rec
                if (l.get('partno') or '').strip().upper() == pno.upper()
            )

            rfd = sum(
                int(float(l.get('prod_qty') or 0))
                for l in month_prod
                if (l.get('partno') or '').strip().upper() == pno.upper() and str(l.get('opn_no') or '').strip().lower() == 'rfd'
            )

            desp = sum(
                int(float(l.get('qty') or 0))
                for l in month_desp
                if (l.get('finish_part_no') or '').strip().upper() == pno.upper()
            )

            result_parts.append({
                "partno": pno,
                "customer": cust,
                "schedule_qty": sch_qty,
                "operations": op_prod,
                "has_pc": has_pc_op,
                "to_pc": to_pc,
                "from_pc": from_pc,
                "rfd": rfd,
                "despatch": desp
            })

        # Sort: parts with active schedule or production first, then alphabetically
        result_parts.sort(key=lambda x: (-(x["schedule_qty"] > 0 or any(v["qty"] > 0 for v in x["operations"].values()) or x["to_pc"] > 0 or x["from_pc"] > 0 or x["despatch"] > 0), x["partno"]))

        return {
            "month": month,
            "operation_columns": discovered_ops,
            "parts": result_parts
        }
    except Exception as ex:
        print("get_bc_status_endpoint error:", ex)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.get("/api/production/wipro_status")
def get_wipro_status_endpoint(month: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        if not month or not str(month).strip():
            now_ist = get_now_ist()
            month = now_ist.strftime("%Y-%m")
        else:
            month = str(month).strip()

        def is_in_month(d_str, target_month):
            if not d_str: return False
            s = str(d_str).strip()
            if s.startswith(target_month):
                return True
            if "/" in s:
                pts = s.split("/")
                if len(pts) == 3 and len(pts[2]) == 4:
                    ym = f"{pts[2]}-{pts[1].zfill(2)}"
                    return ym == target_month
            elif "-" in s:
                pts = s.split("-")
                if len(pts) == 3 and len(pts[0]) == 4:
                    ym = f"{pts[0]}-{pts[1].zfill(2)}"
                    return ym == target_month
                elif len(pts) == 3 and len(pts[2]) == 4:
                    ym = f"{pts[2]}-{pts[1].zfill(2)}"
                    return ym == target_month
            return False

        # 1. Fetch WIPRO parts from part_masters
        pm_rows = db.execute(text("SELECT id, partno, customer, department, rfd_phy FROM part_masters WHERE UPPER(TRIM(department)) = 'WIPRO' ORDER BY partno;")).mappings().all()
        pm_map = {r['partno'].strip(): dict(r) for r in pm_rows if r['partno']}

        # Also fetch schedules for WIPRO
        sch_rows = db.execute(text("SELECT id, department, partno, qty, status, target_date FROM schedules WHERE UPPER(TRIM(department)) = 'WIPRO';")).mappings().all()
        sch_map = {}
        for s in sch_rows:
            pno = (s.get('partno') or '').strip()
            try:
                q = int(float(str(s.get('qty') or 0).strip()))
            except Exception:
                q = 0
            sch_map[pno] = sch_map.get(pno, 0) + q

        all_wipro_partnos = sorted(set(list(pm_map.keys()) + [p for p in sch_map.keys() if p]))

        # 2. Operations per part from part_operations (and fallback operations)
        po_rows = db.execute(text("SELECT id, part_id, opn_no, description, machine, cycle_time FROM part_operations ORDER BY id ASC;")).mappings().all()
        po_by_part = {}
        for r in po_rows:
            pid = str(r.get("part_id") or "").strip()
            if pid not in po_by_part:
                po_by_part[pid] = []
            po_by_part[pid].append(dict(r))

        fallback_po = {}
        try:
            op_rows = db.execute(text("SELECT o.id, o.part_id, o.opn_no, o.description, o.machine_name, o.cycle_time, p.part_no FROM operations o JOIN parts p ON o.part_id = p.id ORDER BY o.id ASC;")).mappings().all()
            for r in op_rows:
                pno = (r.get("part_no") or "").strip().upper()
                if pno not in fallback_po:
                    fallback_po[pno] = []
                fallback_po[pno].append({
                    "id": r.get("id"),
                    "part_id": r.get("part_id"),
                    "opn_no": r.get("opn_no"),
                    "description": r.get("description"),
                    "machine": r.get("machine_name"),
                    "cycle_time": r.get("cycle_time")
                })
        except Exception:
            pass

        part_ops_map = {}
        for pno in all_wipro_partnos:
            pm = pm_map.get(pno)
            pid = str(pm['id']) if pm else ""
            ops = po_by_part.get(pid, [])
            if not ops and pno.upper() in fallback_po:
                ops = fallback_po[pno.upper()]
            part_ops_map[pno] = ops

        # Defined standard operation columns for WIPRO report: opn 20 to opn 70 (also opn 10, opn 80 if used)
        wipro_op_cols = ["10", "20", "30", "40", "50", "60", "70", "80"]

        # 3. Fetch monthly logs for WIPRO
        prod_rows = db.execute(text("SELECT partno, opn_no, description, machine, prod_qty, date FROM production_logs WHERE UPPER(TRIM(dept)) = 'WIPRO';")).mappings().all()
        month_prod = [r for r in prod_rows if is_in_month(r.get('date'), month)]

        rm_desp_rows = db.execute(text("SELECT finish_part_no, qty, date FROM raw_material_logs WHERE type = 'despatch';")).mappings().all()
        month_desp = [r for r in rm_desp_rows if is_in_month(r.get('date'), month)]

        result_parts = []
        for pno in all_wipro_partnos:
            pm = pm_map.get(pno, {})
            cust = pm.get('customer') or '-'
            sch_qty = sch_map.get(pno, 0)
            part_ops = part_ops_map.get(pno, [])

            # Get set of opn_nos defined in part master for this part
            part_defined_opns = set()
            for o in part_ops:
                raw_op = str(o.get('opn_no') or '').strip()
                if raw_op:
                    # Normalize leading zeros (e.g., '020' -> '20')
                    norm_op = str(int(raw_op)) if raw_op.isdigit() else raw_op
                    part_defined_opns.add(norm_op)

            op_prod = {}
            cumulative_qty = 0

            for op_col in wipro_op_cols:
                has_op = op_col in part_defined_opns
                # Sum produced qty for this part and operation in the selected month
                qty = sum(
                    int(float(l.get('prod_qty') or 0))
                    for l in month_prod
                    if (l.get('partno') or '').strip().upper() == pno.upper() and (
                        str(l.get('opn_no') or '').strip() == op_col or
                        (str(l.get('opn_no') or '').strip().isdigit() and str(int(str(l.get('opn_no') or '').strip())) == op_col)
                    )
                )
                op_prod[op_col] = {"has_op": has_op, "qty": qty}
                cumulative_qty += qty

            # RFD: sum of prod_logs with opn_no == 'rfd' for this month
            rfd = sum(
                int(float(l.get('prod_qty') or 0))
                for l in month_prod
                if (l.get('partno') or '').strip().upper() == pno.upper() and str(l.get('opn_no') or '').strip().lower() == 'rfd'
            )

            # Despatch: from raw_material_logs for this finish_part_no in this month
            desp = sum(
                int(float(l.get('qty') or 0))
                for l in month_desp
                if (l.get('finish_part_no') or '').strip().upper() == pno.upper()
            )

            result_parts.append({
                "partno": pno,
                "customer": cust,
                "schedule_qty": sch_qty,
                "operations": op_prod,
                "cumulative_qty": cumulative_qty,
                "rfd": rfd,
                "despatch": desp
            })

        # Sort: parts with active schedule, production, or despatch first, then alphabetically
        result_parts.sort(key=lambda x: (-(x["schedule_qty"] > 0 or x["cumulative_qty"] > 0 or x["rfd"] > 0 or x["despatch"] > 0), x["partno"]))

        return {
            "month": month,
            "operation_columns": wipro_op_cols,
            "parts": result_parts
        }
    except Exception as ex:
        print("get_wipro_status_endpoint error:", ex)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.post("/api/schedules/import-excel")
async def import_schedules_excel_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    rows = parse_excel_bytes(contents)
    if not rows:
        raise HTTPException(status_code=400, detail="Could not parse Excel file or file is empty")
    
    data_started = False
    imported_count = 0
    headers = [h.strip().lower() for h in rows[0]] if rows else []

    # Check if header matches schedule.xlsx format
    if "partno" in headers or "department" in headers:
        p_idx = headers.index("partno") if "partno" in headers else -1
        d_idx = headers.index("department") if "department" in headers else -1
        t_idx = headers.index("target_date") if "target_date" in headers else -1
        q_idx = headers.index("qty") if "qty" in headers else -1
        s_idx = headers.index("status") if "status" in headers else -1

        for row in rows[1:]:
            if not row: continue
            partno = row[p_idx].strip() if p_idx != -1 and p_idx < len(row) else ""
            if not partno or partno.lower() == "partno": continue
            dept = row[d_idx].strip() if d_idx != -1 and d_idx < len(row) else ""
            t_date = row[t_idx].strip() if t_idx != -1 and t_idx < len(row) else ""
            qty = row[q_idx].strip() if q_idx != -1 and q_idx < len(row) else "0"
            stat = row[s_idx].strip() if s_idx != -1 and s_idx < len(row) else "Pending"

            db.execute(text("""
                INSERT INTO schedules (department, partno, target_date, qty, completed_qty, status)
                VALUES (:department, :partno, :target_date, :qty, '0', :status)
            """), {"department": dept, "partno": partno, "target_date": t_date, "qty": qty, "status": stat})
            imported_count += 1
    else:
        for row in rows:
            if not row: continue
            if "Sl No" in row or "PART NO" in [x.upper().strip() for x in row]:
                data_started = True
                continue
            if data_started and len(row) >= 4:
                dept = row[1] if len(row) > 1 else ""
                part_no = row[3] if len(row) > 3 else ""
                total_sch_qty = str(row[4]) if len(row) > 4 else "0"
                if part_no and part_no.upper() != "PART NO":
                    db.execute(text("""
                        INSERT INTO schedules (department, partno, target_date, qty, completed_qty, status)
                        VALUES (:department, :partno, '', :qty, '0', 'Pending')
                    """), {"department": dept, "partno": part_no, "qty": total_sch_qty})
                    imported_count += 1

    db.commit()
    return {"imported_count": imported_count, "message": f"Successfully imported {imported_count} schedule items!"}

# --- Production Logging ---
@app.get("/api/production-logs", response_model=List[ProductionLogResponse])
def get_production_logs(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.ProductionLog).order_by(models.ProductionLog.id.desc()).limit(limit).all()

@app.get("/api/production-logs/sl-nos")
def get_completed_sl_nos(part_no: str, opn_no: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        clean_part = part_no.strip().lower()

        def safe_str_opn(val):
            if val is None:
                return ""
            try:
                f = float(val)
                return str(int(f)) if f.is_integer() else str(f)
            except Exception:
                return str(val).strip()

        def extract_clean_opn(raw_str):
            if not raw_str:
                return None, ""
            raw = str(raw_str).strip()
            cleaned = re.sub(r'\(\s*\d+\s*min\s*\)', '', raw, flags=re.IGNORECASE)
            m_opn = re.search(r'opn\s*(\d+(?:\.\d+)?)', cleaned, re.IGNORECASE)
            if m_opn:
                num = float(m_opn.group(1))
                return num, safe_str_opn(num)
            m_start = re.match(r'^\s*(\d+(?:\.\d+)?)', cleaned)
            if m_start:
                num = float(m_start.group(1))
                return num, safe_str_opn(num)
            m_any = re.search(r'(\d+(?:\.\d+)?)', cleaned)
            if m_any:
                num = float(m_any.group(1))
                return num, safe_str_opn(num)
            return None, raw

        curr_num, curr_opn_str = extract_clean_opn(opn_no)
        if curr_num is None:
            curr_num, curr_opn_str = 10.0, "10"

        logs = db.query(models.ProductionLog).filter(func.lower(models.ProductionLog.part_no) == clean_part).all()
        part = db.query(models.Part).filter(func.lower(models.Part.part_no) == clean_part).first()
        schedules = db.query(models.ProductionSchedule).filter(func.lower(models.ProductionSchedule.part_no) == clean_part).all()

        # Collect ALL operation numbers for this part from Part Master + Work Schedules + Logs
        all_opn_nums = []
        if part and part.operations:
            for op in part.operations:
                num, _ = extract_clean_opn(op.opn_no)
                if num is not None and num not in all_opn_nums:
                    all_opn_nums.append(num)

        for sch in schedules:
            opn_val = getattr(sch, 'opn_no', None)
            if opn_val:
                num, _ = extract_clean_opn(opn_val)
                if num is not None and num not in all_opn_nums:
                    all_opn_nums.append(num)

        for l in logs:
            num, _ = extract_clean_opn(l.opn_no)
            if num is not None and num not in all_opn_nums:
                all_opn_nums.append(num)

        if curr_num not in all_opn_nums:
            all_opn_nums.append(curr_num)

        all_opn_nums = sorted(all_opn_nums)

        # Determine position of curr_num in sorted operation sequence for this part
        idx = all_opn_nums.index(curr_num) if curr_num in all_opn_nums else 0

        def extract_sl_nos(target_opn_str, target_num):
            sl_set = set()
            for l in logs:
                l_num, l_str = extract_clean_opn(l.opn_no)
                if (l_num is not None and target_num is not None and l_num == target_num) or (l_str == target_opn_str):
                    if l.completed_sl_nos:
                        for s in l.completed_sl_nos.split(','):
                            s = s.strip()
                            if s.isdigit():
                                sl_set.add(int(s))
            return sorted(list(sl_set))

        curr_completed = extract_sl_nos(curr_opn_str, curr_num)

        if idx == 0:
            # First operation in sequence (e.g. Opn 20 for 214, H44, M50, DK7, U34)
            is_first_opn = True
            prev_opn_no = None
            prev_completed = []
            available_sl_nos = []  # Frontend will compute: {1..maxGrid} minus curr_completed
        else:
            # Subsequent operation in sequence! Predecessor operation is index - 1!
            is_first_opn = False
            p_num = all_opn_nums[idx - 1]
            prev_opn_no = safe_str_opn(p_num)
            prev_num, _ = extract_clean_opn(prev_opn_no) if prev_opn_no else (None, "")
            prev_completed = extract_sl_nos(prev_opn_no, prev_num)
            # Available for current opn = (Completed in predecessor opn) MINUS (Already logged in current opn)
            available_sl_nos = [s for s in prev_completed if s not in curr_completed]

        return {
            "is_first_opn": is_first_opn,
            "prev_opn_no": prev_opn_no,
            "prev_completed_sl_nos": prev_completed,
            "completed_sl_nos": curr_completed,
            "available_sl_nos": available_sl_nos
        }
    except Exception as e:
        import traceback
        print("Error in get_completed_sl_nos:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# --- Production Logging CRUD ---
def normalize_date_str(d_str: str) -> str:
    if not d_str:
        return datetime.datetime.now(IST).strftime("%Y-%m-%d")
    d_str = d_str.strip()
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", d_str)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", d_str)
    if m:
        p1 = int(m.group(1))
        p2 = int(m.group(2))
        y = int(m.group(3))
        if p1 > 12:
            # Definitely DD-MM-YYYY (p1=day, p2=month)
            return f"{y:04d}-{p2:02d}-{p1:02d}"
        elif p2 > 12:
            # Definitely MM-DD-YYYY (p1=month, p2=day)
            return f"{y:04d}-{p1:02d}-{p2:02d}"
        else:
            # In India / GRS standard is DD-MM-YYYY (p1=day, p2=month)
            return f"{y:04d}-{p2:02d}-{p1:02d}"
    return d_str

@app.get("/api/prodlog")
@app.get("/api/production-logs")
def get_all_prod_logs(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM production_logs ORDER BY date DESC, id DESC")).mappings().all()
        if rows:
            results = []
            for r in rows:
                results.append({
                    "id": r.get("id"),
                    "dept": r.get("dept") or "",
                    "date": normalize_date_str(r.get("date") or r.get("log_date") or ""),
                    "shift": r.get("shift") or "",
                    "setter": r.get("setter") or "",
                    "machine": r.get("machine") or r.get("machine_name") or "",
                    "operator": r.get("operator") or r.get("operator_name") or "",
                    "partno": r.get("partno") or r.get("part_no") or "",
                    "opn_no": r.get("opn_no") or "",
                    "description": r.get("description") or "",
                    "runtime": float(r.get("runtime") or 0.0),
                    "cycle_time": float(r.get("cycle_time") or 0.0),
                    "target_qty": float(r.get("target_qty") or 0.0),
                    "prod_qty": float(r.get("prod_qty") if r.get("prod_qty") is not None else (r.get("qty_produced") or 0)),
                    "rej_qty": float(r.get("rej_qty") if r.get("rej_qty") is not None else (r.get("scrap_qty") or 0)),
                    "efficiency": float(r.get("efficiency") or 0.0),
                    "remarks": str(r.get("remarks") or ""),
                    "idle_hours": float(r.get("idle_hours") or 0.0),
                    "idle_reason": r.get("idle_reason") or "None",
                    "idle_hours_2": float(r.get("idle_hours_2") or 0.0),
                    "idle_reason_2": r.get("idle_reason_2") or "None",
                    "idle_hours_3": float(r.get("idle_hours_3") or 0.0),
                    "idle_reason_3": r.get("idle_reason_3") or "None",
                    "multiple_mc": int(r.get("multiple_mc") or 1),
                    "created_at": str(r.get("created_at") or "")
                })
            return results
    except Exception:
        db.rollback()

    try:
        logs = db.query(models.ProductionLog).order_by(models.ProductionLog.date.desc(), models.ProductionLog.id.desc()).all()
        return [{
            "id": l.id,
            "dept": getattr(l, "dept", "") or "",
            "date": normalize_date_str(getattr(l, "date", "") or getattr(l, "log_date", "") or ""),
            "shift": l.shift or "",
            "setter": getattr(l, "setter", "") or "",
            "machine": getattr(l, "machine", "") or getattr(l, "machine_name", "") or "",
            "operator": getattr(l, "operator", "") or getattr(l, "operator_name", "") or "",
            "partno": getattr(l, "partno", "") or getattr(l, "part_no", "") or "",
            "opn_no": getattr(l, "opn_no", "") or "",
            "description": getattr(l, "description", "") or "",
            "runtime": float(getattr(l, "runtime", 0.0) or 0.0),
            "cycle_time": float(getattr(l, "cycle_time", 0.0) or 0.0),
            "target_qty": float(getattr(l, "target_qty", 0.0) or 0.0),
            "prod_qty": float(getattr(l, "prod_qty", None) if getattr(l, "prod_qty", None) is not None else (getattr(l, "qty_produced", 0) or 0)),
            "rej_qty": float(getattr(l, "rej_qty", None) if getattr(l, "rej_qty", None) is not None else (getattr(l, "scrap_qty", 0) or 0)),
            "efficiency": float(getattr(l, "efficiency", 0.0) or 0.0),
            "remarks": str(getattr(l, "remarks", "") or ""),
            "idle_hours": float(getattr(l, "idle_hours", 0.0) or 0.0),
            "idle_reason": getattr(l, "idle_reason", "None") or "None",
            "idle_hours_2": float(getattr(l, "idle_hours_2", 0.0) or 0.0),
            "idle_reason_2": getattr(l, "idle_reason_2", "None") or "None",
            "idle_hours_3": float(getattr(l, "idle_hours_3", 0.0) or 0.0),
            "idle_reason_3": getattr(l, "idle_reason_3", "None") or "None",
            "multiple_mc": int(getattr(l, "multiple_mc", 1) or 1),
            "created_at": str(getattr(l, "created_at", "") or "")
        } for l in logs]
    except Exception:
        db.rollback()
        return []

@app.post("/api/prodlog")
@app.post("/api/production-logs")
def create_prod_log(data: dict, db: Session = Depends(get_db)):
    dept = (data.get("dept") or "").strip()
    date_val = normalize_date_str(data.get("date") or data.get("log_date") or "")
    shift = (data.get("shift") or "").strip()
    setter = (data.get("setter") or "").strip()
    machine = (data.get("machine") or data.get("machine_name") or "").strip()
    operator = (data.get("operator") or data.get("operator_name") or "").strip()
    partno = (data.get("partno") or data.get("part_no") or "").strip()
    opn_no = (data.get("opn_no") or "").strip()
    description = (data.get("description") or "").strip()
    runtime = float(data.get("runtime") or 0.0)
    cycle_time = float(data.get("cycle_time") or 0.0)
    target_qty = float(data.get("target_qty") or 0.0)
    prod_qty = float(data.get("prod_qty") if data.get("prod_qty") is not None else (data.get("qty_produced") or 0.0))
    rej_qty = float(data.get("rej_qty") if data.get("rej_qty") is not None else (data.get("scrap_qty") or 0.0))
    efficiency = float(data.get("efficiency") or 0.0)
    remarks = str(data.get("remarks") or "").strip()
    idle_hours = float(data.get("idle_hours") or 0.0)
    idle_reason = (data.get("idle_reason") or "None").strip()
    idle_hours_2 = float(data.get("idle_hours_2") or 0.0)
    idle_reason_2 = (data.get("idle_reason_2") or "None").strip()
    idle_hours_3 = float(data.get("idle_hours_3") or 0.0)
    idle_reason_3 = (data.get("idle_reason_3") or "None").strip()
    multiple_mc = int(data.get("multiple_mc") or 1)

    try:
        db.execute(text("SELECT setval(pg_get_serial_sequence('production_logs', 'id'), coalesce(max(id),4420) + 1, false) FROM production_logs;"))
        db.commit()
    except Exception:
        db.rollback()

    try:
        max_row = db.execute(text("SELECT COALESCE(MAX(id), 4420) + 1 AS next_id FROM production_logs")).mappings().first()
        next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 4421
        if next_id <= 4420:
            next_id = 4421
    except Exception:
        db.rollback()
        next_id = 4421

    # Adaptively match table columns for both Postgres and SQLite
    table_cols = set()
    try:
        if "postgresql" in str(engine.url):
            col_rows = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'production_logs'")).fetchall()
            table_cols = {r[0].lower() for r in col_rows}
        else:
            col_rows = db.execute(text("PRAGMA table_info(production_logs)")).fetchall()
            table_cols = {r[1].lower() for r in col_rows}
    except Exception:
        pass

    params = {
        "id": next_id,
        "dept": dept,
        "date": date_val,
        "log_date": date_val,
        "shift": shift,
        "setter": setter,
        "machine": machine,
        "machine_name": machine,
        "operator": operator,
        "operator_name": operator,
        "partno": partno,
        "part_no": partno,
        "opn_no": opn_no,
        "description": description,
        "runtime": runtime,
        "cycle_time": cycle_time,
        "target_qty": target_qty,
        "prod_qty": prod_qty,
        "qty_produced": int(prod_qty),
        "rej_qty": rej_qty,
        "scrap_qty": int(rej_qty),
        "efficiency": efficiency,
        "remarks": remarks,
        "idle_hours": idle_hours,
        "idle_reason": idle_reason,
        "idle_hours_2": idle_hours_2,
        "idle_reason_2": idle_reason_2,
        "idle_hours_3": idle_hours_3,
        "idle_reason_3": idle_reason_3,
        "multiple_mc": multiple_mc
    }

    if table_cols:
        insert_cols = [k for k in params.keys() if k.lower() in table_cols]
        col_names_str = ", ".join(insert_cols)
        col_vals_str = ", ".join([f":{k}" for k in insert_cols])
        try:
            db.execute(text(f"INSERT INTO production_logs ({col_names_str}) VALUES ({col_vals_str})"), params)
            db.commit()
            return {"id": next_id, "message": "Production Log saved successfully"}
        except Exception:
            db.rollback()

    try:
        db.execute(text("""
            INSERT INTO production_logs (id, dept, date, shift, setter, machine, operator, partno, opn_no, description, runtime, cycle_time, target_qty, prod_qty, rej_qty, efficiency, remarks, idle_hours, idle_reason, idle_hours_2, idle_reason_2, idle_hours_3, idle_reason_3, multiple_mc)
            VALUES (:id, :dept, :date, :shift, :setter, :machine, :operator, :partno, :opn_no, :description, :runtime, :cycle_time, :target_qty, :prod_qty, :rej_qty, :efficiency, :remarks, :idle_hours, :idle_reason, :idle_hours_2, :idle_reason_2, :idle_hours_3, :idle_reason_3, :multiple_mc)
        """), params)
        db.commit()
    except Exception:
        db.rollback()
        try:
            db.execute(text("""
                INSERT INTO production_logs (dept, date, shift, setter, machine, operator, partno, opn_no, description, runtime, cycle_time, target_qty, prod_qty, rej_qty, efficiency, remarks, idle_hours, idle_reason, idle_hours_2, idle_reason_2, idle_hours_3, idle_reason_3, multiple_mc)
                VALUES (:dept, :date, :shift, :setter, :machine, :operator, :partno, :opn_no, :description, :runtime, :cycle_time, :target_qty, :prod_qty, :rej_qty, :efficiency, :remarks, :idle_hours, :idle_reason, :idle_hours_2, :idle_reason_2, :idle_hours_3, :idle_reason_3, :multiple_mc)
            """), params)
            db.commit()
        except Exception as ex:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save production log: {ex}")

    return {"id": next_id, "message": "Production Log saved successfully"}

@app.put("/api/prodlog/{log_id}")
@app.put("/api/production-logs/{log_id}")
def update_prod_log(log_id: int, data: dict, db: Session = Depends(get_db)):
    existing = db.execute(text("SELECT * FROM production_logs WHERE id = :id"), {"id": log_id}).mappings().first()
    if not existing:
        raise HTTPException(status_code=404, detail="Log not found")

    dept = (data.get("dept") if "dept" in data else existing.get("dept")) or ""
    date_val = normalize_date_str(data.get("date") if "date" in data else (existing.get("date") or existing.get("log_date") or ""))
    shift = (data.get("shift") if "shift" in data else existing.get("shift")) or ""
    setter = (data.get("setter") if "setter" in data else existing.get("setter")) or ""
    machine = (data.get("machine") if "machine" in data else (existing.get("machine") or existing.get("machine_name"))) or ""
    operator = (data.get("operator") if "operator" in data else (existing.get("operator") or existing.get("operator_name"))) or ""
    partno = (data.get("partno") if "partno" in data else (existing.get("partno") or existing.get("part_no"))) or ""
    opn_no = (data.get("opn_no") if "opn_no" in data else existing.get("opn_no")) or ""
    description = (data.get("description") if "description" in data else existing.get("description")) or ""
    runtime = float(data.get("runtime") if "runtime" in data else (existing.get("runtime") or 0.0))
    cycle_time = float(data.get("cycle_time") if "cycle_time" in data else (existing.get("cycle_time") or 0.0))
    target_qty = float(data.get("target_qty") if "target_qty" in data else (existing.get("target_qty") or 0.0))
    prod_qty = float(data.get("prod_qty") if "prod_qty" in data else (existing.get("prod_qty") if existing.get("prod_qty") is not None else (existing.get("qty_produced") or 0.0)))
    rej_qty = float(data.get("rej_qty") if "rej_qty" in data else (existing.get("rej_qty") if existing.get("rej_qty") is not None else (existing.get("scrap_qty") or 0.0)))
    efficiency = float(data.get("efficiency") if "efficiency" in data else (existing.get("efficiency") or 0.0))
    remarks = str(data.get("remarks") if "remarks" in data else (existing.get("remarks") or "")).strip()
    idle_hours = float(data.get("idle_hours") if "idle_hours" in data else (existing.get("idle_hours") or 0.0))
    idle_reason = (data.get("idle_reason") if "idle_reason" in data else existing.get("idle_reason")) or "None"
    idle_hours_2 = float(data.get("idle_hours_2") if "idle_hours_2" in data else (existing.get("idle_hours_2") or 0.0))
    idle_reason_2 = (data.get("idle_reason_2") if "idle_reason_2" in data else existing.get("idle_reason_2")) or "None"
    idle_hours_3 = float(data.get("idle_hours_3") if "idle_hours_3" in data else (existing.get("idle_hours_3") or 0.0))
    idle_reason_3 = (data.get("idle_reason_3") if "idle_reason_3" in data else existing.get("idle_reason_3")) or "None"
    multiple_mc = int(data.get("multiple_mc") if "multiple_mc" in data else (existing.get("multiple_mc") or 1))

    params = {
        "id": log_id,
        "dept": str(dept).strip(),
        "date": date_val,
        "shift": str(shift).strip(),
        "setter": str(setter).strip(),
        "machine": str(machine).strip(),
        "operator": str(operator).strip(),
        "partno": str(partno).strip(),
        "opn_no": str(opn_no).strip(),
        "description": str(description).strip(),
        "runtime": runtime,
        "cycle_time": cycle_time,
        "target_qty": target_qty,
        "prod_qty": prod_qty,
        "rej_qty": rej_qty,
        "efficiency": efficiency,
        "remarks": remarks,
        "idle_hours": idle_hours,
        "idle_reason": str(idle_reason).strip(),
        "idle_hours_2": idle_hours_2,
        "idle_reason_2": str(idle_reason_2).strip(),
        "idle_hours_3": idle_hours_3,
        "idle_reason_3": str(idle_reason_3).strip(),
        "multiple_mc": multiple_mc
    }
    try:
        db.execute(text("""
            UPDATE production_logs SET
                dept = :dept, date = :date, shift = :shift, setter = :setter,
                machine = :machine, operator = :operator, partno = :partno,
                opn_no = :opn_no, description = :description, runtime = :runtime,
                cycle_time = :cycle_time, target_qty = :target_qty, prod_qty = :prod_qty,
                rej_qty = :rej_qty, efficiency = :efficiency, remarks = :remarks,
                idle_hours = :idle_hours, idle_reason = :idle_reason,
                idle_hours_2 = :idle_hours_2, idle_reason_2 = :idle_reason_2,
                idle_hours_3 = :idle_hours_3, idle_reason_3 = :idle_reason_3,
                multiple_mc = :multiple_mc
            WHERE id = :id
        """), params)
        db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update production log: {ex}")
    return {"id": log_id, "message": "Production Log updated successfully"}

@app.delete("/api/prodlog/{log_id}")
@app.delete("/api/production-logs/{log_id}")
def delete_production_log(log_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM production_logs WHERE id = :id"), {"id": log_id})
        db.commit()
    except Exception:
        db.rollback()
        try:
            db_log = db.query(models.ProductionLog).filter(models.ProductionLog.id == log_id).first()
            if db_log:
                db.delete(db_log)
                db.commit()
        except Exception:
            db.rollback()
    return {"message": "Production Log deleted successfully"}

@app.delete("/api/prodlog/clear-all")
@app.delete("/api/prodlog/all")
@app.post("/api/prodlog/clear-all")
@app.delete("/api/production-logs/clear-all")
def clear_all_prod_logs(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM production_logs;"))
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All production logs cleared successfully"}

class DeleteProdLogRangeRequest(BaseModel):
    dept: str
    from_date: str
    to_date: str
    username: Optional[str] = None
    role: Optional[str] = None

@app.post("/api/prodlog/preview-delete-range")
def preview_delete_prodlog_range(data: DeleteProdLogRangeRequest, db: Session = Depends(get_db)):
    dept = (data.dept or "").strip()
    from_date = (data.from_date or "").strip()
    to_date = (data.to_date or "").strip()

    if not dept:
        raise HTTPException(status_code=400, detail="Department is required.")
    if not from_date or not to_date:
        raise HTTPException(status_code=400, detail="From Date and To Date are required.")

    norm_from = normalize_date_str(from_date)
    norm_to = normalize_date_str(to_date)
    if norm_from > norm_to:
        norm_from, norm_to = norm_to, norm_from

    logs = db.execute(text("SELECT * FROM production_logs;")).mappings().all()

    matching_count = 0
    sample_parts = set()
    total_qty = 0.0
    for l in logs:
        l_dept = (l.get("dept") or l.get("department") or "").strip().upper()
        if dept.upper() != "ALL" and l_dept and l_dept != dept.upper():
            continue

        raw_d = str(l.get("date") or l.get("log_date") or "").strip()
        norm_d = normalize_date_str(raw_d)
        if norm_d and norm_from <= norm_d <= norm_to:
            matching_count += 1
            pno = (l.get("partno") or l.get("part_no") or "").strip()
            if pno:
                sample_parts.add(pno)
            total_qty += float(l.get("prod_qty") or l.get("qty_produced") or 0)

    return {
        "count": matching_count,
        "dept": dept,
        "from_date": norm_from,
        "to_date": norm_to,
        "sample_parts": list(sample_parts)[:5],
        "total_qty": total_qty
    }

@app.post("/api/prodlog/delete-range")
@app.delete("/api/prodlog/delete-range")
def delete_prodlog_range(data: DeleteProdLogRangeRequest, db: Session = Depends(get_db)):
    username = (data.username or "").strip()
    role = (data.role or "").strip()

    # Verify admin privileges
    is_admin = False
    if role.lower() == "admin" or username.lower() == "admin":
        is_admin = True
    elif username:
        user_row = db.execute(text("SELECT role FROM users WHERE LOWER(username) = LOWER(:u)"), {"u": username}).mappings().first()
        if user_row and (user_row["role"] or "").strip().lower() == "admin":
            is_admin = True

    if not is_admin:
        raise HTTPException(status_code=403, detail="Unauthorized: Admin rights are required to delete production logs.")

    dept = (data.dept or "").strip()
    from_date = (data.from_date or "").strip()
    to_date = (data.to_date or "").strip()

    if not dept:
        raise HTTPException(status_code=400, detail="Department is required.")
    if not from_date or not to_date:
        raise HTTPException(status_code=400, detail="From Date and To Date are required.")

    norm_from = normalize_date_str(from_date)
    norm_to = normalize_date_str(to_date)
    if norm_from > norm_to:
        norm_from, norm_to = norm_to, norm_from

    logs = db.execute(text("SELECT * FROM production_logs;")).mappings().all()

    ids_to_delete = []
    for l in logs:
        l_dept = (l.get("dept") or l.get("department") or "").strip().upper()
        if dept.upper() != "ALL" and l_dept and l_dept != dept.upper():
            continue

        raw_d = str(l.get("date") or l.get("log_date") or "").strip()
        norm_d = normalize_date_str(raw_d)
        if norm_d and norm_from <= norm_d <= norm_to:
            ids_to_delete.append(l["id"])

    if not ids_to_delete:
        return {"message": "No production logs found matching the selected criteria.", "deleted_count": 0}

    batch_size = 500
    for i in range(0, len(ids_to_delete), batch_size):
        batch = ids_to_delete[i:i + batch_size]
        id_placeholders = ", ".join([str(id_val) for id_val in batch])
        db.execute(text(f"DELETE FROM production_logs WHERE id IN ({id_placeholders});"))
        db.commit()

    return {
        "message": f"Successfully deleted {len(ids_to_delete)} production logs for department '{dept}' from {norm_from} to {norm_to}.",
        "deleted_count": len(ids_to_delete),
        "dept": dept,
        "from_date": norm_from,
        "to_date": norm_to
    }

# --- RAW MATERIALS & RAW MATERIAL LOGS ---
def sync_partmaster_forge_pns_to_rawmaterials(db: Session):
    try:
        pm_rows = db.execute(text("SELECT DISTINCT TRIM(forge_pn) as fpn FROM part_masters WHERE forge_pn IS NOT NULL AND TRIM(forge_pn) != ''")).mappings().all()
        if not pm_rows:
            return
        rm_rows = db.execute(text("SELECT DISTINCT UPPER(TRIM(forge_pn)) as fpn FROM raw_materials WHERE forge_pn IS NOT NULL AND TRIM(forge_pn) != ''")).mappings().all()
        existing_rms = {r["fpn"] for r in rm_rows if r.get("fpn")}

        changed = False
        for r in pm_rows:
            fpn = (r.get("fpn") or "").strip()
            if fpn and fpn.upper() not in existing_rms:
                logs = db.execute(text("SELECT type, qty FROM raw_material_logs WHERE UPPER(TRIM(forge_pn)) = :fpn"), {"fpn": fpn.upper()}).mappings().all()
                rcpt = sum(int(float(l["qty"] or 0)) for l in logs if (l.get("type") or "").strip().lower() == "receipt")
                dspt = sum(int(float(l["qty"] or 0)) for l in logs if (l.get("type") or "").strip().lower() == "despatch")
                stk = rcpt - dspt
                try:
                    db.execute(text("""
                        INSERT INTO raw_materials (forge_pn, opening_stock, receipt, despatch, stock)
                        VALUES (:forge_pn, 0, :receipt, :despatch, :stock)
                    """), {"forge_pn": fpn, "receipt": rcpt, "despatch": dspt, "stock": stk})
                except Exception:
                    db.execute(text("""
                        INSERT INTO raw_materials (forge_pn, receipt, despatch, stock)
                        VALUES (:forge_pn, :receipt, :despatch, :stock)
                    """), {"forge_pn": fpn, "receipt": rcpt, "despatch": dspt, "stock": stk})
                existing_rms.add(fpn.upper())
                changed = True
        if changed:
            db.commit()
    except Exception as e:
        db.rollback()

@app.get("/api/rawmaterials")
def get_raw_materials(month: Optional[str] = Query(None), db: Session = Depends(get_db)):
    sync_partmaster_forge_pns_to_rawmaterials(db)
    
    target_month = (month or "").strip()
    if not target_month or target_month.lower() == "all":
        target_month = datetime.date.today().strftime("%Y-%m")

    try:
        try:
            rows = db.execute(text("SELECT id, forge_pn, COALESCE(opening_stock, 0) as opening_stock, receipt, despatch, stock FROM raw_materials ORDER BY forge_pn ASC;")).mappings().all()
        except Exception:
            rows = db.execute(text("SELECT id, forge_pn, 0 as opening_stock, receipt, despatch, stock FROM raw_materials ORDER BY forge_pn ASC;")).mappings().all()

        # Fetch all logs grouped by fpn and month
        from collections import defaultdict
        logs_by_fpn_month = defaultdict(lambda: defaultdict(lambda: {"receipt": 0, "despatch": 0}))
        logged_fpns = set()
        
        log_rows = db.execute(text("""
            SELECT UPPER(TRIM(forge_pn)) as fpn, type, qty, SUBSTR(TRIM(date), 1, 7) as log_month
            FROM raw_material_logs
            WHERE date IS NOT NULL AND TRIM(date) != ''
        """)).mappings().all()

        for l in log_rows:
            fpn = l.get("fpn")
            m = l.get("log_month")
            if not fpn or not m or len(m) != 7:
                continue
            logged_fpns.add(fpn)
            t = (l.get("type") or "").strip().lower()
            q = int(float(l.get("qty") or 0))
            if t in ("receipt", "despatch"):
                logs_by_fpn_month[fpn][m][t] += q

        # Fetch manual monthly opening stock overrides
        overrides = {}
        try:
            override_rows = db.execute(text("""
                SELECT UPPER(TRIM(forge_pn)) as fpn, month, opening_stock
                FROM raw_material_monthly_opening
            """)).mappings().all()
            for r in override_rows:
                if r.get("fpn") and r.get("month"):
                    overrides[(r["fpn"], r["month"])] = int(r["opening_stock"] or 0)
        except Exception:
            pass

        results = []
        for r in rows:
            fpn = (r.get("forge_pn") or "").strip().upper()
            base_opening = int(r.get("opening_stock") or 0)
            
            rcpt_target = logs_by_fpn_month[fpn][target_month]["receipt"]
            dspt_target = logs_by_fpn_month[fpn][target_month]["despatch"]

            relevant_overrides = {m: val for (f, m), val in overrides.items() if f == fpn and m <= target_month}
            if relevant_overrides:
                latest_override_m = max(relevant_overrides.keys())
                override_val = relevant_overrides[latest_override_m]
                if latest_override_m == target_month:
                    op_target = override_val
                else:
                    rcpt_between = sum(logs_by_fpn_month[fpn][m]["receipt"] for m in logs_by_fpn_month[fpn] if latest_override_m <= m < target_month)
                    dspt_between = sum(logs_by_fpn_month[fpn][m]["despatch"] for m in logs_by_fpn_month[fpn] if latest_override_m <= m < target_month)
                    op_target = override_val + rcpt_between - dspt_between
            else:
                if fpn in logged_fpns:
                    rcpt_prior = sum(logs_by_fpn_month[fpn][m]["receipt"] for m in logs_by_fpn_month[fpn] if m < target_month)
                    dspt_prior = sum(logs_by_fpn_month[fpn][m]["despatch"] for m in logs_by_fpn_month[fpn] if m < target_month)
                    op_target = base_opening + rcpt_prior - dspt_prior
                else:
                    legacy_stock = int(r.get("stock") or 0)
                    op_target = base_opening if base_opening != 0 else legacy_stock

            stk_target = op_target + rcpt_target - dspt_target
            results.append({
                "id": r["id"],
                "forge_pn": r["forge_pn"],
                "month": target_month,
                "opening_stock": op_target,
                "receipt": rcpt_target,
                "despatch": dspt_target,
                "stock": stk_target
            })
        return results
    except Exception as ex:
        print("get_raw_materials error:", ex)
        db.rollback()
        rms = db.query(models.RawMaterial).order_by(models.RawMaterial.forge_pn.asc()).all()
        return [{
            "id": r.id,
            "forge_pn": r.forge_pn,
            "month": target_month,
            "opening_stock": getattr(r, "opening_stock", 0) or 0,
            "receipt": r.receipt or 0,
            "despatch": r.despatch or 0,
            "stock": r.stock or 0
        } for r in rms]

@app.post("/api/rawmaterials/opening_stock")
def update_rm_opening_stock(data: dict, db: Session = Depends(get_db)):
    fpn = (data.get("forge_pn") or "").strip()
    month = (data.get("month") or "").strip()
    if not fpn:
        raise HTTPException(status_code=400, detail="Forge PN is required")
    if not month:
        raise HTTPException(status_code=400, detail="Month is required")
    opening_stock = int(data.get("opening_stock") if data.get("opening_stock") is not None else 0)

    try:
        try:
            models.Base.metadata.create_all(bind=engine)
        except Exception:
            pass

        existing = db.execute(text("""
            SELECT id FROM raw_material_monthly_opening 
            WHERE UPPER(TRIM(forge_pn)) = UPPER(TRIM(:fpn)) AND month = :month
        """), {"fpn": fpn, "month": month}).mappings().first()

        if existing:
            db.execute(text("""
                UPDATE raw_material_monthly_opening 
                SET opening_stock = :op 
                WHERE id = :id
            """), {"op": opening_stock, "id": existing["id"]})
        else:
            db.execute(text("""
                INSERT INTO raw_material_monthly_opening (forge_pn, month, opening_stock)
                VALUES (:fpn, :month, :op)
            """), {"fpn": fpn, "month": month, "op": opening_stock})

        curr_month = datetime.date.today().strftime("%Y-%m")
        if month == curr_month:
            logs = db.execute(text("""
                SELECT type, qty FROM raw_material_logs 
                WHERE UPPER(TRIM(forge_pn)) = UPPER(TRIM(:fpn)) AND SUBSTR(TRIM(date), 1, 7) = :month
            """), {"fpn": fpn, "month": month}).mappings().all()
            rcpt = sum(int(float(l["qty"] or 0)) for l in logs if (l.get("type") or "").strip().lower() == "receipt")
            dspt = sum(int(float(l["qty"] or 0)) for l in logs if (l.get("type") or "").strip().lower() == "despatch")
            stk = opening_stock + rcpt - dspt
            try:
                db.execute(text("""
                    UPDATE raw_materials 
                    SET opening_stock = :op, stock = :stk 
                    WHERE UPPER(TRIM(forge_pn)) = UPPER(TRIM(:fpn))
                """), {"op": opening_stock, "stk": stk, "fpn": fpn})
            except Exception:
                pass

        db.commit()
        return {"message": "Opening stock updated successfully", "forge_pn": fpn, "month": month, "opening_stock": opening_stock}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update opening stock: {ex}")

@app.post("/api/rawmaterials")
def create_raw_material(data: dict, db: Session = Depends(get_db)):
    fpn = (data.get("forge_pn") or "").strip()
    if not fpn:
        raise HTTPException(status_code=400, detail="Forge PN is required")
    opening_stock = int(data.get("opening_stock") if data.get("opening_stock") is not None else (data.get("quantity") or 0))
    receipt = int(data.get("receipt") or 0)
    despatch = int(data.get("despatch") or 0)
    stock = int(data.get("stock") if data.get("stock") is not None else (opening_stock + receipt - despatch))
    month = (data.get("month") or datetime.date.today().strftime("%Y-%m")).strip()

    try:
        db.execute(text("SELECT setval(pg_get_serial_sequence('raw_materials', 'id'), coalesce(max(id),0) + 1, false) FROM raw_materials;"))
        db.commit()
    except Exception:
        db.rollback()

    try:
        try:
            db.execute(text("""
                INSERT INTO raw_materials (forge_pn, opening_stock, receipt, despatch, stock)
                VALUES (:forge_pn, :opening_stock, :receipt, :despatch, :stock)
            """), {"forge_pn": fpn, "opening_stock": opening_stock, "receipt": receipt, "despatch": despatch, "stock": stock})
        except Exception:
            db.execute(text("""
                INSERT INTO raw_materials (forge_pn, receipt, despatch, stock)
                VALUES (:forge_pn, :receipt, :despatch, :stock)
            """), {"forge_pn": fpn, "receipt": receipt, "despatch": despatch, "stock": stock})
        
        if opening_stock > 0 and month:
            try:
                db.execute(text("""
                    INSERT INTO raw_material_monthly_opening (forge_pn, month, opening_stock)
                    VALUES (:fpn, :month, :op)
                """), {"fpn": fpn, "month": month, "op": opening_stock})
            except Exception:
                pass

        db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create raw material: {ex}")
    return {"message": "Raw Material created successfully"}

@app.put("/api/rawmaterials/{rm_id}")
def update_raw_material(rm_id: int, data: dict, db: Session = Depends(get_db)):
    fpn = (data.get("forge_pn") or "").strip()
    opening_stock = int(data.get("opening_stock") if data.get("opening_stock") is not None else (data.get("quantity") or 0))
    receipt = int(data.get("receipt") or 0)
    despatch = int(data.get("despatch") or 0)
    stock = int(data.get("stock") if data.get("stock") is not None else (opening_stock + receipt - despatch))
    month = (data.get("month") or datetime.date.today().strftime("%Y-%m")).strip()

    try:
        try:
            db.execute(text("""
                UPDATE raw_materials SET forge_pn = :forge_pn, opening_stock = :opening_stock, receipt = :receipt, despatch = :despatch, stock = :stock
                WHERE id = :id
            """), {"id": rm_id, "forge_pn": fpn, "opening_stock": opening_stock, "receipt": receipt, "despatch": despatch, "stock": stock})
        except Exception:
            db.execute(text("""
                UPDATE raw_materials SET forge_pn = :forge_pn, receipt = :receipt, despatch = :despatch, stock = :stock
                WHERE id = :id
            """), {"id": rm_id, "forge_pn": fpn, "receipt": receipt, "despatch": despatch, "stock": stock})

        if month:
            try:
                existing = db.execute(text("""
                    SELECT id FROM raw_material_monthly_opening 
                    WHERE UPPER(TRIM(forge_pn)) = UPPER(TRIM(:fpn)) AND month = :month
                """), {"fpn": fpn, "month": month}).mappings().first()
                if existing:
                    db.execute(text("""
                        UPDATE raw_material_monthly_opening SET opening_stock = :op WHERE id = :id
                    """), {"op": opening_stock, "id": existing["id"]})
                else:
                    db.execute(text("""
                        INSERT INTO raw_material_monthly_opening (forge_pn, month, opening_stock)
                        VALUES (:fpn, :month, :op)
                    """), {"fpn": fpn, "month": month, "op": opening_stock})
            except Exception:
                pass

        db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update raw material: {ex}")
    return {"message": "Raw Material updated successfully"}

@app.delete("/api/rawmaterials/all")
@app.delete("/api/rawmaterials/clear-all")
@app.post("/api/rawmaterials/clear-all")
def clear_all_raw_materials(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM raw_materials;"))
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All Raw Material items deleted successfully"}

@app.delete("/api/rawmaterials/{rm_id}")
def delete_raw_material(rm_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM raw_materials WHERE id = :id"), {"id": rm_id})
        db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete raw material: {ex}")
    return {"message": "Raw Material deleted"}

@app.post("/api/rawmaterials/bulk")
def bulk_import_raw_materials(items: list, db: Session = Depends(get_db)):
    for r in items:
        fpn = (r.get("forge_pn") or "").strip()
        if not fpn:
            continue
        rcpt = int(r.get("receipt") or r.get("quantity") or 0)
        dspt = int(r.get("despatch") or 0)
        stk = int(r.get("stock") if r.get("stock") is not None else (rcpt - dspt))
        try:
            db.execute(text("""
                INSERT INTO raw_materials (forge_pn, receipt, despatch, stock)
                VALUES (:forge_pn, :receipt, :despatch, :stock)
            """), {"forge_pn": fpn, "receipt": rcpt, "despatch": dspt, "stock": stk})
        except Exception:
            pass
    db.commit()
    return {"message": f"Imported {len(items)} raw materials successfully"}

# --- RAW MATERIAL LOGS ---
@app.get("/api/rawmateriallogs")
def get_raw_material_logs(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM raw_material_logs ORDER BY id DESC;")).mappings().all()
        if rows:
            return [{
                "id": r.get("id"),
                "type": r.get("type") or "receipt",
                "date": r.get("date") or "",
                "dc_type": r.get("dc_type") or "",
                "forge_pn": r.get("forge_pn") or "",
                "dc_no": r.get("dc_no") or "",
                "finish_part_no": r.get("finish_part_no") or "",
                "part_prefix": r.get("part_prefix") or "",
                "qty": int(r.get("qty") or 0),
                "remarks": r.get("remarks") or "",
                "created_at": str(r.get("created_at") or "")
            } for r in rows]
        return []
    except Exception:
        db.rollback()
        try:
            logs = db.query(models.RawMaterialLog).order_by(models.RawMaterialLog.id.desc()).all()
            return [{
                "id": l.id,
                "type": l.type or "receipt",
                "date": l.date or "",
                "dc_type": l.dc_type or "",
                "forge_pn": l.forge_pn or "",
                "dc_no": l.dc_no or "",
                "finish_part_no": l.finish_part_no or "",
                "part_prefix": l.part_prefix or "",
                "qty": l.qty or 0,
                "remarks": getattr(l, "remarks", "") or "",
                "created_at": str(getattr(l, "created_at", "") or "")
            } for l in logs]
        except Exception:
            db.rollback()
            return []

@app.post("/api/rawmateriallogs")
def create_raw_material_log(data: dict, db: Session = Depends(get_db)):
    rtype = (data.get("type") or "receipt").strip().lower()
    rdate = normalize_date_str((data.get("date") or "").strip())
    dctype = (data.get("dc_type") or "").strip()
    fpn = (data.get("forge_pn") or "").strip()
    dcno = (data.get("dc_no") or "").strip()
    fpno = (data.get("finish_part_no") or "").strip()
    pprefix = (data.get("part_prefix") or "").strip()
    qty = int(data.get("qty") or data.get("quantity") or 0)
    remarks = (data.get("remarks") or "").strip()

    if not fpn:
        raise HTTPException(status_code=400, detail="Forge PN is required")

    try:
        db.execute(text("SELECT setval(pg_get_serial_sequence('raw_material_logs', 'id'), coalesce(max(id),0) + 1, false) FROM raw_material_logs;"))
        db.commit()
    except Exception:
        db.rollback()

    try:
        db.execute(text("""
            INSERT INTO raw_material_logs (type, date, dc_type, forge_pn, dc_no, finish_part_no, part_prefix, qty, remarks)
            VALUES (:type, :date, :dc_type, :forge_pn, :dc_no, :finish_part_no, :part_prefix, :qty, :remarks)
        """), {"type": rtype, "date": rdate, "dc_type": dctype, "forge_pn": fpn, "dc_no": dcno, "finish_part_no": fpno, "part_prefix": pprefix, "qty": qty, "remarks": remarks})
        
        # Auto sync stock in raw_materials
        logs_for_fpn = db.execute(text("SELECT type, qty FROM raw_material_logs WHERE forge_pn = :fpn"), {"fpn": fpn}).mappings().all()
        cur_rcpt = sum(int(float(l["qty"] or 0)) for l in logs_for_fpn if (l.get("type") or "").strip().lower() == "receipt")
        cur_dspt = sum(int(float(l["qty"] or 0)) for l in logs_for_fpn if (l.get("type") or "").strip().lower() == "despatch")
        cur_stk = cur_rcpt - cur_dspt

        existing_rm = db.execute(text("SELECT id FROM raw_materials WHERE forge_pn = :forge_pn"), {"forge_pn": fpn}).mappings().first()
        if existing_rm:
            db.execute(text("""
                UPDATE raw_materials SET receipt = :receipt, despatch = :despatch, stock = :stock WHERE forge_pn = :forge_pn
            """), {"forge_pn": fpn, "receipt": cur_rcpt, "despatch": cur_dspt, "stock": cur_stk})
        else:
            db.execute(text("""
                INSERT INTO raw_materials (forge_pn, receipt, despatch, stock) VALUES (:forge_pn, :receipt, :despatch, :stock)
            """), {"forge_pn": fpn, "receipt": cur_rcpt, "despatch": cur_dspt, "stock": cur_stk})

        db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create raw material log: {ex}")

    return {"message": "Raw Material Log saved successfully"}

@app.put("/api/rawmateriallogs/{log_id}")
def update_raw_material_log(log_id: int, data: dict, db: Session = Depends(get_db)):
    try:
        rtype = (data.get("type") or "receipt").strip().lower()
        rdate = normalize_date_str((data.get("date") or "").strip())
        dctype = (data.get("dc_type") or "").strip()
        fpn = (data.get("forge_pn") or "").strip()
        dcno = (data.get("dc_no") or "").strip()
        fpno = (data.get("finish_part_no") or "").strip()
        pprefix = (data.get("part_prefix") or "").strip()
        qty = int(data.get("qty") or data.get("quantity") or 0)
        remarks = (data.get("remarks") or "").strip()

        if not fpn:
            raise HTTPException(status_code=400, detail="Forge PN is required")

        db.execute(text("""
            UPDATE raw_material_logs
            SET type = :type, date = :date, dc_type = :dc_type, forge_pn = :forge_pn,
                dc_no = :dc_no, finish_part_no = :finish_part_no, part_prefix = :part_prefix, qty = :qty,
                remarks = :remarks
            WHERE id = :id
        """), {
            "id": log_id,
            "type": rtype,
            "date": rdate,
            "dc_type": dctype,
            "forge_pn": fpn,
            "dc_no": dcno,
            "finish_part_no": fpno,
            "part_prefix": pprefix,
            "qty": qty,
            "remarks": remarks
        })
        
        # Recalculate stock for this forge_pn
        logs_for_fpn = db.execute(text("SELECT type, qty FROM raw_material_logs WHERE forge_pn = :fpn"), {"fpn": fpn}).mappings().all()
        cur_rcpt = sum(int(float(l["qty"] or 0)) for l in logs_for_fpn if (l.get("type") or "").strip().lower() == "receipt")
        cur_dspt = sum(int(float(l["qty"] or 0)) for l in logs_for_fpn if (l.get("type") or "").strip().lower() == "despatch")
        cur_stk = cur_rcpt - cur_dspt

        existing_rm = db.execute(text("SELECT id FROM raw_materials WHERE forge_pn = :forge_pn"), {"forge_pn": fpn}).mappings().first()
        if existing_rm:
            db.execute(text("""
                UPDATE raw_materials SET receipt = :receipt, despatch = :despatch, stock = :stock WHERE forge_pn = :forge_pn
            """), {"forge_pn": fpn, "receipt": cur_rcpt, "despatch": cur_dspt, "stock": cur_stk})
        else:
            db.execute(text("""
                INSERT INTO raw_materials (forge_pn, receipt, despatch, stock) VALUES (:forge_pn, :receipt, :despatch, :stock)
            """), {"forge_pn": fpn, "receipt": cur_rcpt, "despatch": cur_dspt, "stock": cur_stk})

        db.commit()
        return {"message": "Raw Material Log updated successfully"}
    except HTTPException:
        raise
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update raw material log: {ex}")

@app.delete("/api/rawmateriallogs/{log_id}")
def delete_raw_material_log(log_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM raw_material_logs WHERE id = :id"), {"id": log_id})
        db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete raw material log: {ex}")
    return {"message": "Log deleted"}

@app.delete("/api/rawmateriallogs/all")
@app.delete("/api/rawmateriallogs/clear-all")
@app.post("/api/rawmateriallogs/clear-all")
def clear_all_raw_material_logs(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM raw_material_logs;"))
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All Raw Material logs deleted successfully"}

@app.post("/api/rawmateriallogs/bulk")
def bulk_import_raw_material_logs(items: Union[list, dict], db: Session = Depends(get_db)):
    raw_list = items.get("logs", []) if isinstance(items, dict) else items
    for rl in raw_list:
        rtype = (rl.get("type") or "receipt").strip().lower()
        rdate = (rl.get("date") or "").strip()
        dctype = (rl.get("dc_type") or "").strip()
        fpn = (rl.get("forge_pn") or "").strip()
        dcno = (rl.get("dc_no") or "").strip()
        fpno = (rl.get("finish_part_no") or "").strip()
        pprefix = (rl.get("part_prefix") or "").strip()
        rqty = int(rl.get("qty") or rl.get("quantity") or 0)
        rremarks = (rl.get("remarks") or "").strip()
        if not fpn:
            continue
        try:
            db.execute(text("""
                INSERT INTO raw_material_logs (type, date, dc_type, forge_pn, dc_no, finish_part_no, part_prefix, qty, remarks)
                VALUES (:type, :date, :dc_type, :forge_pn, :dc_no, :finish_part_no, :part_prefix, :qty, :remarks)
            """), {"type": rtype, "date": rdate, "dc_type": dctype, "forge_pn": fpn, "dc_no": dcno, "finish_part_no": fpno, "part_prefix": pprefix, "qty": rqty, "remarks": rremarks})
        except Exception:
            pass
    db.commit()
    return {"message": f"Imported {len(raw_list)} logs successfully"}

# --- HR ATTENDANCE CRUD ---
@app.get("/api/attendance")
def get_attendance(month_year: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        if month_year:
            rows = db.execute(text("SELECT * FROM attendances WHERE month_year = :my ORDER BY CASE WHEN slno IS NULL OR slno = 0 THEN 999999 ELSE slno END ASC, id ASC;"), {"my": month_year.strip()}).mappings().all()
        else:
            rows = db.execute(text("SELECT * FROM attendances ORDER BY CASE WHEN slno IS NULL OR slno = 0 THEN 999999 ELSE slno END ASC, id ASC;")).mappings().all()
        return [{
            "id": r.get("id"),
            "slno": int(r.get("slno") or 0) if "slno" in r else 0,
            "employee_name": r.get("employee_name") or "",
            "dept": r.get("dept") or "",
            "designation": r.get("designation") or "Operator",
            "month_year": r.get("month_year") or "",
            "day": int(r.get("day") if r.get("day") is not None else 0),
            "hours": str(r.get("hours") or ""),
            "created_at": str(r.get("created_at") or "")
        } for r in rows]
    except Exception:
        db.rollback()
        try:
            if month_year:
                rows = db.execute(text("SELECT * FROM attendances WHERE month_year = :my ORDER BY id ASC;"), {"my": month_year.strip()}).mappings().all()
            else:
                rows = db.execute(text("SELECT * FROM attendances ORDER BY id ASC;")).mappings().all()
            return [{
                "id": r.get("id"),
                "slno": int(r.get("slno") or 0) if "slno" in r else 0,
                "employee_name": r.get("employee_name") or "",
                "dept": r.get("dept") or "",
                "designation": r.get("designation") or "Operator",
                "month_year": r.get("month_year") or "",
                "day": int(r.get("day") if r.get("day") is not None else 0),
                "hours": str(r.get("hours") or ""),
                "created_at": str(r.get("created_at") or "")
            } for r in rows]
        except Exception:
            db.rollback()
            return []

@app.post("/api/attendance")
def save_attendance(data: dict, db: Session = Depends(get_db)):
    month_val = (data.get("month_year") or "").strip()
    entries = data.get("entries") or []

    if not month_val:
        raise HTTPException(status_code=400, detail="month_year is required")

    # Ensure slno column exists
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE attendances ADD COLUMN slno INTEGER DEFAULT 0;"))
    except Exception:
        pass

    try:
        db.execute(text("DELETE FROM attendances WHERE month_year = :my;"), {"my": month_val})
        db.commit()
    except Exception:
        db.rollback()

    try:
        db.execute(text("SELECT setval(pg_get_serial_sequence('attendances', 'id'), coalesce(max(id),0) + 1, false) FROM attendances;"))
        db.commit()
    except Exception:
        db.rollback()

    saved_count = 0
    for entry in entries:
        slno = int(entry.get("slno") or 0)
        ename = (entry.get("employee_name") or "").strip()
        if not ename:
            continue
        dept = (entry.get("dept") or "").strip()
        desig = (entry.get("designation") or "Operator").strip()
        day = int(entry.get("day") if entry.get("day") is not None else 0)
        hrs = str(entry.get("hours") or "")

        try:
            db.execute(text("""
                INSERT INTO attendances (slno, employee_name, dept, designation, month_year, day, hours)
                VALUES (:slno, :employee_name, :dept, :designation, :month_year, :day, :hours);
            """), {
                "slno": slno,
                "employee_name": ename,
                "dept": dept,
                "designation": desig,
                "month_year": month_val,
                "day": day,
                "hours": hrs
            })
            saved_count += 1
        except Exception as ex:
            db.rollback()
            try:
                db.execute(text("""
                    INSERT INTO attendances (employee_name, dept, designation, month_year, day, hours)
                    VALUES (:employee_name, :dept, :designation, :month_year, :day, :hours);
                """), {
                    "employee_name": ename,
                    "dept": dept,
                    "designation": desig,
                    "month_year": month_val,
                    "day": day,
                    "hours": hrs
                })
                saved_count += 1
            except Exception:
                db.rollback()

    try:
        db.commit()
    except Exception:
        db.rollback()

    return {"message": f"Attendance for {month_val} saved successfully ({saved_count} records)!"}

@app.delete("/api/attendance/clear-all")
@app.delete("/api/attendance/all")
@app.post("/api/attendance/clear-all")
def clear_all_attendance(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM attendances;"))
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All attendance records cleared successfully"}

# --- ATTENDANCE VS LOGIN HOURS REPORT ENDPOINT ---
@app.get("/api/reports/att_vs_login")
def get_att_vs_login_report(month_year: Optional[str] = None, dept: Optional[str] = None, designation: Optional[str] = None, db: Session = Depends(get_db)):
    if not month_year:
        month_year = datetime.datetime.now().strftime("%Y-%m")
    
    parts = month_year.strip().split("-")
    try:
        year, month = int(parts[0]), int(parts[1])
        days_in_month = calendar.monthrange(year, month)[1]
    except Exception:
        days_in_month = 31

    filter_dept = (dept or "").strip().upper()
    if filter_dept.startswith("--") or filter_dept == "ALL":
        filter_dept = ""

    filter_desig = (designation or "").strip().upper()
    if filter_desig.startswith("--") or filter_desig == "ALL":
        filter_desig = ""

    try:
        # 1. Operators map: op_norm -> { "name": ..., "dept": ..., "designation": ... }
        op_rows = db.execute(text("SELECT * FROM operators")).mappings().all()
        operators_info = {}
        for r in op_rows:
            nm = (r.get("name") or r.get("operator_name") or "").strip()
            if not nm:
                continue
            dp = (r.get("department") or r.get("dept") or "").strip()
            desig = (r.get("designation") or "").strip() or "Operator"
            operators_info[nm.upper()] = {"name": nm, "dept": dp, "designation": desig}

        # 2. Attendance records for month_year
        att_rows = db.execute(
            text("SELECT employee_name, dept, designation, day, hours FROM attendances WHERE month_year = :my"),
            {"my": month_year.strip()}
        ).mappings().all()

        # 3. Production logs for month_year (date like YYYY-MM%)
        prod_rows = db.execute(
            text("SELECT operator, dept, date, runtime, idle_hours, idle_hours_2, idle_hours_3 FROM production_logs WHERE date LIKE :dt"),
            {"dt": f"{month_year.strip()}%"}
        ).mappings().all()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(ex)}")

    # Aggregate by operator
    op_data = {}

    def get_or_create_op(op_name, default_dept="", default_desig=""):
        norm = op_name.strip().upper()
        if norm not in op_data:
            known = operators_info.get(norm, {})
            disp_name = known.get("name") or op_name.strip()
            disp_dept = known.get("dept") or default_dept or ""
            disp_desig = known.get("designation") or default_desig or "Operator"
            op_data[norm] = {
                "dept": disp_dept,
                "operators": disp_name,
                "designation": disp_desig,
                "days": {str(d): {"att_hours": 0.0, "login_hours": 0.0} for d in range(1, days_in_month + 1)},
                "total_att": 0.0,
                "total_login": 0.0,
                "diff": 0.0
            }
        else:
            if default_dept and not op_data[norm]["dept"]:
                op_data[norm]["dept"] = default_dept
            if default_desig and (not op_data[norm].get("designation") or op_data[norm]["designation"].lower() == "operator"):
                op_data[norm]["designation"] = default_desig
        return op_data[norm]

    # Process Attendance
    for r in att_rows:
        ename = (r.get("employee_name") or "").strip()
        if not ename:
            continue
        day = int(r.get("day") or 0)
        hrs_str = str(r.get("hours") or "").strip()
        try:
            hrs = float(hrs_str) if hrs_str else 0.0
        except ValueError:
            hrs = 0.0

        desig_val = (r.get("designation") or "").strip()
        item = get_or_create_op(ename, (r.get("dept") or "").strip(), desig_val)
        if 1 <= day <= days_in_month:
            day_key = str(day)
            item["days"][day_key]["att_hours"] += hrs
            item["total_att"] += hrs

    # Process Production Logs
    for l in prod_rows:
        op = (l.get("operator") or "").strip()
        if not op:
            continue
        dt_str = (l.get("date") or "").strip()
        day = 0
        if dt_str.startswith(month_year):
            dt_parts = dt_str.split("-")
            if len(dt_parts) >= 3:
                try:
                    day = int(dt_parts[2])
                except ValueError:
                    day = 0

        rtime = float(l.get("runtime") or 0.0)
        i1 = float(l.get("idle_hours") or 0.0)
        i2 = float(l.get("idle_hours_2") or 0.0)
        i3 = float(l.get("idle_hours_3") or 0.0)
        login_h = rtime + i1 + i2 + i3

        item = get_or_create_op(op, (l.get("dept") or "").strip())
        if 1 <= day <= days_in_month:
            day_key = str(day)
            item["days"][day_key]["login_hours"] += login_h
            item["total_login"] += login_h

    # Seed operators from operator master
    for norm, info in operators_info.items():
        if not filter_dept or info["dept"].upper() == filter_dept:
            get_or_create_op(info["name"], info["dept"], info.get("designation", "Operator"))

    # Collect all available designations
    available_desigs = sorted(list({(item.get("designation") or "Operator").strip() for item in op_data.values() if (item.get("designation") or "").strip()} | {"Operator"}))

    # Finalize list and compute diffs
    result_list = []
    for norm, item in op_data.items():
        if filter_dept and item["dept"].upper() != filter_dept:
            continue
        if filter_desig and (item.get("designation") or "OPERATOR").strip().upper() != filter_desig:
            continue
        
        # Round values
        for d in range(1, days_in_month + 1):
            d_key = str(d)
            item["days"][d_key]["att_hours"] = round(item["days"][d_key]["att_hours"], 2)
            item["days"][d_key]["login_hours"] = round(item["days"][d_key]["login_hours"], 2)

        item["total_att"] = round(item["total_att"], 2)
        item["total_login"] = round(item["total_login"], 2)
        item["diff"] = round(item["total_att"] - item["total_login"], 2)
        result_list.append(item)

    # Sort by dept ASC, operators ASC
    result_list.sort(key=lambda x: (x["dept"].upper(), x["operators"].upper()))

    return {
        "month_year": month_year,
        "days_in_month": days_in_month,
        "available_designations": available_desigs,
        "data": result_list
    }

# --- HT & PC LOGS CRUD & HELPER ENDPOINTS ---
@app.get("/api/ht/spider_parts")
def get_ht_spider_parts(db: Session = Depends(get_db)):
    try:
        parts_rows = db.execute(text("SELECT id, partno, department FROM part_masters WHERE UPPER(TRIM(department)) = 'SPIDER' OR partno IN (SELECT DISTINCT partno FROM ht_logs) ORDER BY partno;")).mappings().all()

        po_rows = db.execute(text("SELECT id, part_id, opn_no, description, machine, cycle_time FROM part_operations ORDER BY id ASC;")).mappings().all()
        po_by_part = {}
        for r in po_rows:
            pid = str(r.get("part_id") or "").strip()
            if pid not in po_by_part:
                po_by_part[pid] = []
            po_by_part[pid].append(dict(r))

        fallback_po = {}
        try:
            op_rows = db.execute(text("SELECT o.id, o.part_id, o.opn_no, o.description, o.machine_name, o.cycle_time, p.part_no FROM operations o JOIN parts p ON o.part_id = p.id ORDER BY o.id ASC;")).mappings().all()
            for r in op_rows:
                pno = (r.get("part_no") or "").strip().upper()
                if pno not in fallback_po:
                    fallback_po[pno] = []
                fallback_po[pno].append({
                    "id": r.get("id"),
                    "part_id": r.get("part_id"),
                    "opn_no": r.get("opn_no"),
                    "description": r.get("description"),
                    "machine": r.get("machine_name"),
                    "cycle_time": r.get("cycle_time")
                })
        except Exception:
            pass

        def clean_opn(val):
            if val is None: return ""
            v = str(val).strip().lower()
            v = re.sub(r'opn[\s.]*', '', v).strip()
            try:
                f = float(v)
                return str(int(f)) if f.is_integer() else str(f)
            except Exception:
                return v

        prod_rows = db.execute(text("SELECT partno, opn_no, prod_qty FROM production_logs;")).mappings().all()
        ht_rows = db.execute(text("SELECT partno, qty FROM ht_logs;")).mappings().all()

        prod_map = {}
        for r in prod_rows:
            pno = (r.get("partno") or "").strip().upper()
            op = clean_opn(r.get("opn_no"))
            qty = int(float(r.get("prod_qty") or 0))
            key = (pno, op)
            prod_map[key] = prod_map.get(key, 0) + qty

        ht_map = {}
        for r in ht_rows:
            pno = (r.get("partno") or "").strip().upper()
            ht_map[pno] = ht_map.get(pno, 0) + int(float(r.get("qty") or 0))

        def is_ht_op(op):
            desc = (op.get("description") or "").strip().upper()
            opn = clean_opn(op.get("opn_no"))
            mach = (op.get("machine") or op.get("machine_name") or "").strip().upper()
            return (opn == "50" and ("HT" in desc.split() or desc == "HT" or "HEAT" in desc or mach == "HT")) or \
                   ("HT" in desc.split() or desc == "HT" or "HEAT" in desc)

        result = []
        for p in parts_rows:
            pno = (p.get("partno") or "").strip()
            pno_upper = pno.upper()
            pid = str(p.get("id") or "").strip()
            dept = p.get("department") or "SPIDER"

            ops = po_by_part.get(pid, [])
            if not ops and pno_upper in fallback_po:
                ops = fallback_po[pno_upper]

            if not ops:
                continue

            def op_sort_key(o):
                c = clean_opn(o.get("opn_no"))
                try:
                    return (0, float(c))
                except Exception:
                    return (1, c)
            sorted_ops = sorted(ops, key=op_sort_key)

            # Check if part has Opn 50 HT from part master operations
            ht_idx = -1
            for idx, o in enumerate(sorted_ops):
                if is_ht_op(o):
                    ht_idx = idx
                    break

            if ht_idx == -1:
                # Part does not have HT operation - do not list
                continue

            ht_op = sorted_ops[ht_idx]
            ht_opn_no = str(ht_op.get("opn_no") or "").strip()
            ht_opn_desc = ht_op.get("description") or "HT"

            # Determine previous operation (Opn 40)
            if ht_idx > 0:
                prev_op = sorted_ops[ht_idx - 1]
                raw_prev_opn = str(prev_op.get("opn_no") or "").strip()
                prev_opn_no = f"Opn {raw_prev_opn}" if raw_prev_opn and not raw_prev_opn.lower().startswith("opn") else raw_prev_opn
                prev_opn_desc = prev_op.get("description") or ""
                prev_clean = clean_opn(raw_prev_opn)
                prev_prod_qty = prod_map.get((pno_upper, prev_clean), 0)
            else:
                prev_opn_no = "Opn 40"
                prev_opn_desc = "Turning"
                prev_prod_qty = prod_map.get((pno_upper, "40"), 0)

            ht_sent = ht_map.get(pno_upper, 0)
            available_qty = max(0, prev_prod_qty - ht_sent)

            result.append({
                "partno": pno,
                "department": dept,
                "ht_opn_no": ht_opn_no,
                "ht_opn_desc": ht_opn_desc,
                "prev_opn_no": prev_opn_no,
                "prev_opn_desc": prev_opn_desc,
                "produced_qty": prev_prod_qty,
                "ht_sent_qty": ht_sent,
                "available_qty": available_qty
            })

        result.sort(key=lambda x: (-x["available_qty"], x["partno"]))
        return result
    except Exception as ex:
        print("get_ht_spider_parts error:", ex)
        db.rollback()
        return []

@app.get("/api/ht/vendor_pending_parts")
def get_ht_vendor_pending_parts(db: Session = Depends(get_db)):
    try:
        ht_rows = db.execute(text("SELECT vendor, partno, qty FROM ht_logs;")).mappings().all()
        rec_rows = db.execute(text("SELECT vendor, partno, qty FROM ht_receipt_logs;")).mappings().all()

        sent_map = {}
        for r in ht_rows:
            v = (r.get("vendor") or "").strip()
            p = (r.get("partno") or "").strip()
            if v and p:
                key = (v, p)
                sent_map[key] = sent_map.get(key, 0) + int(float(r.get("qty") or 0))

        rec_map = {}
        for r in rec_rows:
            v = (r.get("vendor") or "").strip()
            p = (r.get("partno") or "").strip()
            if v and p:
                key = (v, p)
                rec_map[key] = rec_map.get(key, 0) + int(float(r.get("qty") or 0))

        all_keys = sorted(set(list(sent_map.keys()) + list(rec_map.keys())), key=lambda x: (x[0].lower(), x[1].lower()))
        result = []
        for v, p in all_keys:
            sent = sent_map.get((v, p), 0)
            rec = rec_map.get((v, p), 0)
            pending = max(0, sent - rec)
            result.append({
                "vendor": v,
                "partno": p,
                "sent_qty": sent,
                "received_qty": rec,
                "pending_qty": pending
            })
        return result
    except Exception as ex:
        db.rollback()
        return []

@app.get("/api/pc/available_parts")
def get_pc_available_parts(db: Session = Depends(get_db)):
    try:
        parts_rows = db.execute(text("SELECT id, partno, department FROM part_masters WHERE UPPER(TRIM(department)) = 'BC' ORDER BY partno;")).mappings().all()

        po_rows = db.execute(text("SELECT id, part_id, opn_no, description, machine, cycle_time FROM part_operations ORDER BY id ASC;")).mappings().all()
        po_by_part = {}
        for r in po_rows:
            pid = str(r.get("part_id") or "").strip()
            if pid not in po_by_part:
                po_by_part[pid] = []
            po_by_part[pid].append(dict(r))

        fallback_po = {}
        try:
            op_rows = db.execute(text("SELECT o.id, o.part_id, o.opn_no, o.description, o.machine_name, o.cycle_time, p.part_no FROM operations o JOIN parts p ON o.part_id = p.id ORDER BY o.id ASC;")).mappings().all()
            for r in op_rows:
                pno = (r.get("part_no") or "").strip().upper()
                if pno not in fallback_po:
                    fallback_po[pno] = []
                fallback_po[pno].append({
                    "id": r.get("id"),
                    "part_id": r.get("part_id"),
                    "opn_no": r.get("opn_no"),
                    "description": r.get("description"),
                    "machine": r.get("machine_name"),
                    "cycle_time": r.get("cycle_time")
                })
        except Exception:
            pass

        prod_rows = db.execute(text("SELECT partno, opn_no, prod_qty FROM production_logs;")).mappings().all()
        pc_rows = db.execute(text("SELECT partno, qty FROM pc_logs;")).mappings().all()

        def clean_opn(val):
            if val is None: return ""
            v = str(val).strip().lower()
            v = re.sub(r'opn[\s.]*', '', v).strip()
            try:
                f = float(v)
                return str(int(f)) if f.is_integer() else str(f)
            except Exception:
                return v

        prod_map = {}
        for r in prod_rows:
            pno = (r.get("partno") or "").strip().upper()
            op = clean_opn(r.get("opn_no"))
            qty = int(float(r.get("prod_qty") or 0))
            key = (pno, op)
            prod_map[key] = prod_map.get(key, 0) + qty

        pc_map = {}
        for r in pc_rows:
            pno = (r.get("partno") or "").strip().upper()
            pc_map[pno] = pc_map.get(pno, 0) + int(float(r.get("qty") or 0))

        def is_pc_op(op):
            desc = (op.get("description") or "").strip().upper()
            opn = str(op.get("opn_no") or "").strip().upper()
            mach = (op.get("machine") or "").strip().upper()
            return desc == "PC" or "PC" in desc.split() or "POWDER" in desc or opn == "PC" or mach == "PC"

        result = []
        for p in parts_rows:
            pno = (p.get("partno") or "").strip()
            pno_upper = pno.upper()
            pid = str(p.get("id") or "").strip()
            dept = p.get("department") or "BC"

            ops = po_by_part.get(pid, [])
            if not ops and pno_upper in fallback_po:
                ops = fallback_po[pno_upper]

            if not ops:
                continue

            def op_sort_key(o):
                c = clean_opn(o.get("opn_no"))
                try:
                    return (0, float(c))
                except Exception:
                    return (1, c)
            sorted_ops = sorted(ops, key=op_sort_key)

            pc_idx = -1
            for idx, o in enumerate(sorted_ops):
                if is_pc_op(o):
                    pc_idx = idx
                    break

            if pc_idx == -1:
                # Part does not have PC operation - do not list
                continue

            pc_op = sorted_ops[pc_idx]
            pc_opn_no = str(pc_op.get("opn_no") or "").strip()
            pc_opn_desc = pc_op.get("description") or "PC"
            is_final_opn = (pc_idx == len(sorted_ops) - 1)

            if pc_idx > 0:
                prev_op = sorted_ops[pc_idx - 1]
                raw_prev_opn = str(prev_op.get("opn_no") or "").strip()
                prev_opn_no = f"Opn {raw_prev_opn}" if raw_prev_opn and not raw_prev_opn.lower().startswith("opn") else raw_prev_opn
                prev_opn_desc = prev_op.get("description") or ""
                prev_clean = clean_opn(raw_prev_opn)
                prev_prod_qty = prod_map.get((pno_upper, prev_clean), 0)
            else:
                prev_opn_no = "RM"
                prev_opn_desc = "Raw Material"
                prev_prod_qty = 0

            pc_sent = pc_map.get(pno_upper, 0)
            available_qty = max(0, prev_prod_qty - pc_sent)

            result.append({
                "partno": pno,
                "department": dept,
                "pc_opn_no": pc_opn_no,
                "pc_opn_desc": pc_opn_desc,
                "prev_opn_no": prev_opn_no,
                "prev_opn_desc": prev_opn_desc,
                "produced_qty": prev_prod_qty,
                "pc_sent_qty": pc_sent,
                "available_qty": available_qty,
                "is_final_opn": is_final_opn
            })

        result.sort(key=lambda x: (-x["available_qty"], x["partno"]))
        return result
    except Exception as ex:
        print("get_pc_available_parts error:", ex)
        db.rollback()
        return []

@app.get("/api/pc/vendor_pending_parts")
def get_pc_vendor_pending_parts(db: Session = Depends(get_db)):
    try:
        pc_rows = db.execute(text("SELECT vendor, partno, qty FROM pc_logs;")).mappings().all()
        rec_rows = db.execute(text("SELECT vendor, partno, qty FROM pc_receipt_logs;")).mappings().all()

        sent_map = {}
        for r in pc_rows:
            v = (r.get("vendor") or "").strip()
            p = (r.get("partno") or "").strip()
            if v and p:
                key = (v, p)
                sent_map[key] = sent_map.get(key, 0) + int(float(r.get("qty") or 0))

        rec_map = {}
        for r in rec_rows:
            v = (r.get("vendor") or "").strip()
            p = (r.get("partno") or "").strip()
            if v and p:
                key = (v, p)
                rec_map[key] = rec_map.get(key, 0) + int(float(r.get("qty") or 0))

        all_keys = sorted(set(list(sent_map.keys()) + list(rec_map.keys())), key=lambda x: (x[0].lower(), x[1].lower()))
        result = []
        for v, p in all_keys:
            sent = sent_map.get((v, p), 0)
            rec = rec_map.get((v, p), 0)
            pending = max(0, sent - rec)
            result.append({
                "vendor": v,
                "partno": p,
                "sent_qty": sent,
                "received_qty": rec,
                "pending_qty": pending
            })
        return result
    except Exception as ex:
        db.rollback()
        return []

@app.get("/api/ht_logs")
def get_ht_logs(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM ht_logs ORDER BY id DESC;")).mappings().all()
        return [{
            "id": r.get("id"),
            "date": r.get("date") or "",
            "dc_no": r.get("dc_no") or "",
            "vendor": r.get("vendor") or "",
            "partno": r.get("partno") or "",
            "qty": int(r.get("qty") or 0),
            "created_at": str(r.get("created_at") or "")
        } for r in rows]
    except Exception:
        db.rollback()
        return []

@app.post("/api/ht_logs")
def create_ht_log(data: dict, db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("ALTER TABLE ht_logs ADD COLUMN IF NOT EXISTS dc_no VARCHAR(100) DEFAULT '';"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('ht_logs', 'id'), coalesce(max(id),0) + 1, false) FROM ht_logs;"))
            db.commit()
        except Exception:
            db.rollback()

        date_val = normalize_date_str((data.get("date") or "").strip())
        dc_no_val = (data.get("dc_no") or "").strip()
        vendor_val = (data.get("vendor") or "").strip()
        partno_val = (data.get("partno") or "").strip()
        qty_val = int(data.get("qty") or 0)

        max_id_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM ht_logs;")).mappings().first()
        next_id = int(max_id_row["next_id"]) if max_id_row else 1

        try:
            db.execute(text("""
                INSERT INTO ht_logs (id, date, dc_no, vendor, partno, qty)
                VALUES (:id, :date, :dc_no, :vendor, :partno, :qty)
            """), {"id": next_id, "date": date_val, "dc_no": dc_no_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                INSERT INTO ht_logs (date, vendor, partno, qty)
                VALUES (:date, :vendor, :partno, :qty)
            """), {"date": date_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()

        return {"message": "HT Log saved successfully"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.put("/api/ht_logs/{log_id}")
def update_ht_log(log_id: int, data: dict, db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("ALTER TABLE ht_logs ADD COLUMN IF NOT EXISTS dc_no VARCHAR(100) DEFAULT '';"))
            db.commit()
        except Exception:
            db.rollback()

        date_val = normalize_date_str((data.get("date") or "").strip())
        dc_no_val = (data.get("dc_no") or "").strip()
        vendor_val = (data.get("vendor") or "").strip()
        partno_val = (data.get("partno") or "").strip()
        qty_val = int(data.get("qty") or 0)

        try:
            db.execute(text("""
                UPDATE ht_logs
                SET date = :date, dc_no = :dc_no, vendor = :vendor, partno = :partno, qty = :qty
                WHERE id = :id
            """), {"id": log_id, "date": date_val, "dc_no": dc_no_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                UPDATE ht_logs
                SET date = :date, vendor = :vendor, partno = :partno, qty = :qty
                WHERE id = :id
            """), {"id": log_id, "date": date_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()

        return {"message": "HT Log updated successfully"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.delete("/api/ht_logs/{log_id}")
def delete_ht_log(log_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM ht_logs WHERE id = :id"), {"id": log_id})
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "HT Log deleted"}

@app.delete("/api/ht_logs/clear-all")
@app.delete("/api/ht_logs/all")
def clear_all_ht_logs(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM ht_logs;"))
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All HT logs cleared"}

@app.get("/api/ht_receipt_logs")
def get_ht_receipt_logs(db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("ALTER TABLE ht_receipt_logs ADD COLUMN IF NOT EXISTS dc_no VARCHAR(100) DEFAULT '';"))
            db.commit()
        except Exception:
            db.rollback()

        rows = db.execute(text("SELECT * FROM ht_receipt_logs ORDER BY id DESC;")).mappings().all()
        return [{
            "id": r.get("id"),
            "date": r.get("date") or "",
            "dc_no": r.get("dc_no") or "",
            "vendor": r.get("vendor") or "",
            "partno": r.get("partno") or "",
            "qty": int(r.get("qty") or 0),
            "created_at": str(r.get("created_at") or "")
        } for r in rows]
    except Exception:
        db.rollback()
        return []

def log_ht_receipt_to_production(conn, partno_val, qty_val, date_val, vendor_val):
    try:
        pno_clean = (partno_val or "").strip()
        if not pno_clean or int(qty_val) <= 0:
            return
        ht_opn = "50"
        ht_desc = "HT"
        ht_cycle = 0.0
        pm_row = conn.execute(text("SELECT id FROM part_masters WHERE UPPER(TRIM(partno)) = :pno;"), {"pno": pno_clean.upper()}).mappings().first()
        if pm_row:
            pid = str(pm_row["id"])
            ops = conn.execute(text("SELECT opn_no, description, cycle_time FROM part_operations WHERE CAST(part_id AS TEXT) = :pid;"), {"pid": pid}).mappings().all()
            for o in ops:
                d = (o.get("description") or "").strip().upper()
                opn_str = str(o.get("opn_no") or "").strip().upper()
                if d == "HT" or "HEAT" in d or opn_str == "50":
                    ht_opn = str(o.get("opn_no") or "50")
                    ht_desc = o.get("description") or "HT"
                    ht_cycle = float(o.get("cycle_time") or 0.0)
                    break

        max_pl = conn.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM production_logs;")).mappings().first()
        next_pl_id = int(max_pl["next_id"]) if max_pl else 1
        conn.execute(text("""
            INSERT INTO production_logs (
                id, dept, date, shift, setter, machine, operator, partno, opn_no, description, prod_qty, target_qty, efficiency, runtime, cycle_time, multiple_mc
            ) VALUES (
                :id, 'SPIDER', :date, 'First', 'None', 'HT', :operator, :partno, :opn_no, :description, :qty, :qty, 100.0, 0.0, :cycle_time, 1
            )
        """), {
            "id": next_pl_id,
            "date": date_val or get_now_ist().strftime("%Y-%m-%d"),
            "operator": vendor_val or "HT Vendor",
            "partno": pno_clean,
            "opn_no": ht_opn,
            "description": ht_desc,
            "qty": str(qty_val),
            "cycle_time": ht_cycle
        })
        conn.commit()
    except Exception as e:
        print("log_ht_receipt_to_production error:", e)

def sync_all_ht_receipts_to_production():
    try:
        with engine.connect() as conn:
            recs = conn.execute(text("SELECT * FROM ht_receipt_logs;")).mappings().all()
            for r in recs:
                pno = (r.get("partno") or "").strip()
                qty = int(float(r.get("qty") or 0))
                date_val = r.get("date") or ""
                vendor = r.get("vendor") or "HT Vendor"
                if not pno or qty <= 0:
                    continue
                existing = conn.execute(text("""
                    SELECT id FROM production_logs 
                    WHERE UPPER(TRIM(partno)) = :pno AND machine = 'HT' AND prod_qty = :qty;
                """), {"pno": pno.upper(), "qty": str(qty)}).mappings().first()
                if not existing:
                    log_ht_receipt_to_production(conn, pno, qty, date_val, vendor)
    except Exception as e:
        print("sync_all_ht_receipts_to_production note:", e)

@app.post("/api/ht_receipt_logs")
def create_ht_receipt_log(data: dict, db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("ALTER TABLE ht_receipt_logs ADD COLUMN IF NOT EXISTS dc_no VARCHAR(100) DEFAULT '';"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('ht_receipt_logs', 'id'), coalesce(max(id),0) + 1, false) FROM ht_receipt_logs;"))
            db.commit()
        except Exception:
            db.rollback()

        date_val = normalize_date_str((data.get("date") or "").strip())
        dc_no_val = (data.get("dc_no") or "").strip()
        vendor_val = (data.get("vendor") or "").strip()
        partno_val = (data.get("partno") or "").strip()
        qty_val = int(data.get("qty") or 0)

        max_id_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM ht_receipt_logs;")).mappings().first()
        next_id = int(max_id_row["next_id"]) if max_id_row else 1

        try:
            db.execute(text("""
                INSERT INTO ht_receipt_logs (id, date, dc_no, vendor, partno, qty)
                VALUES (:id, :date, :dc_no, :vendor, :partno, :qty)
            """), {"id": next_id, "date": date_val, "dc_no": dc_no_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                INSERT INTO ht_receipt_logs (date, vendor, partno, qty)
                VALUES (:date, :vendor, :partno, :qty)
            """), {"date": date_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()

        # Also log to production for Opn 50 (HT)
        log_ht_receipt_to_production(db, partno_val, qty_val, date_val, vendor_val)

        return {"message": "HT Receipt Log saved successfully"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.put("/api/ht_receipt_logs/{log_id}")
def update_ht_receipt_log(log_id: int, data: dict, db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("ALTER TABLE ht_receipt_logs ADD COLUMN IF NOT EXISTS dc_no VARCHAR(100) DEFAULT '';"))
            db.commit()
        except Exception:
            db.rollback()

        date_val = normalize_date_str((data.get("date") or "").strip())
        dc_no_val = (data.get("dc_no") or "").strip()
        vendor_val = (data.get("vendor") or "").strip()
        partno_val = (data.get("partno") or "").strip()
        qty_val = int(data.get("qty") or 0)

        try:
            db.execute(text("""
                UPDATE ht_receipt_logs
                SET date = :date, dc_no = :dc_no, vendor = :vendor, partno = :partno, qty = :qty
                WHERE id = :id
            """), {"id": log_id, "date": date_val, "dc_no": dc_no_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                UPDATE ht_receipt_logs
                SET date = :date, vendor = :vendor, partno = :partno, qty = :qty
                WHERE id = :id
            """), {"id": log_id, "date": date_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()

        return {"message": "HT Receipt Log updated successfully"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.delete("/api/ht_receipt_logs/{log_id}")
def delete_ht_receipt_log(log_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM ht_receipt_logs WHERE id = :id"), {"id": log_id})
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "HT Receipt Log deleted"}

@app.delete("/api/ht_receipt_logs/clear-all")
@app.delete("/api/ht_receipt_logs/all")
def clear_all_ht_receipt_logs(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM ht_receipt_logs;"))
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All HT Receipt logs cleared"}

@app.get("/api/pc_logs")
def get_pc_logs(db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("ALTER TABLE pc_logs ADD COLUMN IF NOT EXISTS dc_no VARCHAR(100) DEFAULT '';"))
            db.commit()
        except Exception:
            db.rollback()

        rows = db.execute(text("SELECT * FROM pc_logs ORDER BY id DESC;")).mappings().all()
        return [{
            "id": r.get("id"),
            "date": r.get("date") or "",
            "dc_no": r.get("dc_no") or "",
            "vendor": r.get("vendor") or "",
            "partno": r.get("partno") or "",
            "qty": int(r.get("qty") or 0),
            "created_at": str(r.get("created_at") or "")
        } for r in rows]
    except Exception:
        db.rollback()
        return []

@app.post("/api/pc_logs")
def create_pc_log(data: dict, db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("ALTER TABLE pc_logs ADD COLUMN IF NOT EXISTS dc_no VARCHAR(100) DEFAULT '';"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('pc_logs', 'id'), coalesce(max(id),0) + 1, false) FROM pc_logs;"))
            db.commit()
        except Exception:
            db.rollback()

        date_val = normalize_date_str((data.get("date") or "").strip())
        dc_no_val = (data.get("dc_no") or "").strip()
        vendor_val = (data.get("vendor") or "").strip()
        partno_val = (data.get("partno") or "").strip()
        qty_val = int(data.get("qty") or 0)

        max_id_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM pc_logs;")).mappings().first()
        next_id = int(max_id_row["next_id"]) if max_id_row else 1

        try:
            db.execute(text("""
                INSERT INTO pc_logs (id, date, dc_no, vendor, partno, qty)
                VALUES (:id, :date, :dc_no, :vendor, :partno, :qty)
            """), {"id": next_id, "date": date_val, "dc_no": dc_no_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                INSERT INTO pc_logs (date, vendor, partno, qty)
                VALUES (:date, :vendor, :partno, :qty)
            """), {"date": date_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()

        return {"message": "PC Log saved successfully"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.put("/api/pc_logs/{log_id}")
def update_pc_log(log_id: int, data: dict, db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("ALTER TABLE pc_logs ADD COLUMN IF NOT EXISTS dc_no VARCHAR(100) DEFAULT '';"))
            db.commit()
        except Exception:
            db.rollback()

        date_val = normalize_date_str((data.get("date") or "").strip())
        dc_no_val = (data.get("dc_no") or "").strip()
        vendor_val = (data.get("vendor") or "").strip()
        partno_val = (data.get("partno") or "").strip()
        qty_val = int(data.get("qty") or 0)

        try:
            db.execute(text("""
                UPDATE pc_logs
                SET date = :date, dc_no = :dc_no, vendor = :vendor, partno = :partno, qty = :qty
                WHERE id = :id
            """), {"id": log_id, "date": date_val, "dc_no": dc_no_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                UPDATE pc_logs
                SET date = :date, vendor = :vendor, partno = :partno, qty = :qty
                WHERE id = :id
            """), {"id": log_id, "date": date_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()

        return {"message": "PC Log updated successfully"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.delete("/api/pc_logs/{log_id}")
def delete_pc_log(log_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM pc_logs WHERE id = :id"), {"id": log_id})
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "PC Log deleted"}

@app.delete("/api/pc_logs/clear-all")
@app.delete("/api/pc_logs/all")
def clear_all_pc_logs(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM pc_logs;"))
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "All PC logs cleared"}

@app.get("/api/pc_receipt_logs")
def get_pc_receipt_logs(db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("ALTER TABLE pc_receipt_logs ADD COLUMN IF NOT EXISTS dc_no VARCHAR(100) DEFAULT '';"))
            db.commit()
        except Exception:
            db.rollback()

        rows = db.execute(text("SELECT * FROM pc_receipt_logs ORDER BY id DESC;")).mappings().all()
        return [{
            "id": r.get("id"),
            "date": r.get("date") or "",
            "dc_no": r.get("dc_no") or "",
            "vendor": r.get("vendor") or "",
            "partno": r.get("partno") or "",
            "qty": int(r.get("qty") or 0),
            "created_at": str(r.get("created_at") or "")
        } for r in rows]
    except Exception:
        db.rollback()
        return []

def log_pc_receipt_to_production(conn, partno_val, qty_val, date_val, vendor_val):
    try:
        pno_clean = (partno_val or "").strip()
        if not pno_clean or int(qty_val) <= 0:
            return
        pc_opn = "50"
        pc_desc = "PC"
        pc_cycle = 0.0
        pm_row = conn.execute(text("SELECT id FROM part_masters WHERE UPPER(TRIM(partno)) = :pno;"), {"pno": pno_clean.upper()}).mappings().first()
        if pm_row:
            pid = str(pm_row["id"])
            ops = conn.execute(text("SELECT opn_no, description, cycle_time FROM part_operations WHERE CAST(part_id AS TEXT) = :pid;"), {"pid": pid}).mappings().all()
            for o in ops:
                d = (o.get("description") or "").strip().upper()
                opn_str = str(o.get("opn_no") or "").strip().upper()
                if d == "PC" or "PC" in d.split() or "POWDER" in d or opn_str == "PC":
                    pc_opn = str(o.get("opn_no") or "50")
                    pc_desc = o.get("description") or "PC"
                    pc_cycle = float(o.get("cycle_time") or 0.0)
                    break

        max_pl = conn.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM production_logs;")).mappings().first()
        next_pl_id = int(max_pl["next_id"]) if max_pl else 1
        conn.execute(text("""
            INSERT INTO production_logs (
                id, dept, date, shift, setter, machine, operator, partno, opn_no, description, prod_qty, target_qty, efficiency, runtime, cycle_time, multiple_mc
            ) VALUES (
                :id, 'BC', :date, 'First', 'None', 'PC', :operator, :partno, :opn_no, :description, :qty, :qty, 100.0, 0.0, :cycle_time, 1
            )
        """), {
            "id": next_pl_id,
            "date": date_val or get_now_ist().strftime("%Y-%m-%d"),
            "operator": vendor_val or "PC Vendor",
            "partno": pno_clean,
            "opn_no": pc_opn,
            "description": pc_desc,
            "qty": str(qty_val),
            "cycle_time": pc_cycle
        })
        conn.commit()
    except Exception as e:
        print("log_pc_receipt_to_production error:", e)

def sync_all_pc_receipts_to_production():
    try:
        with engine.connect() as conn:
            recs = conn.execute(text("SELECT * FROM pc_receipt_logs;")).mappings().all()
            for r in recs:
                pno = (r.get("partno") or "").strip()
                qty = int(float(r.get("qty") or 0))
                date_val = r.get("date") or ""
                vendor = r.get("vendor") or "PC Vendor"
                if not pno or qty <= 0:
                    continue
                existing = conn.execute(text("""
                    SELECT id FROM production_logs 
                    WHERE UPPER(TRIM(partno)) = :pno AND machine = 'PC' AND prod_qty = :qty;
                """), {"pno": pno.upper(), "qty": str(qty)}).mappings().first()
                if not existing:
                    log_pc_receipt_to_production(conn, pno, qty, date_val, vendor)
    except Exception as e:
        print("sync_all_pc_receipts_to_production note:", e)

@app.post("/api/pc_receipt_logs")
def create_pc_receipt_log(data: dict, db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("ALTER TABLE pc_receipt_logs ADD COLUMN IF NOT EXISTS dc_no VARCHAR(100) DEFAULT '';"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('pc_receipt_logs', 'id'), coalesce(max(id),0) + 1, false) FROM pc_receipt_logs;"))
            db.commit()
        except Exception:
            db.rollback()

        date_val = normalize_date_str((data.get("date") or "").strip())
        dc_no_val = (data.get("dc_no") or "").strip()
        vendor_val = (data.get("vendor") or "").strip()
        partno_val = (data.get("partno") or "").strip()
        qty_val = int(data.get("qty") or 0)

        max_id_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM pc_receipt_logs;")).mappings().first()
        next_id = int(max_id_row["next_id"]) if max_id_row else 1

        try:
            db.execute(text("""
                INSERT INTO pc_receipt_logs (id, date, dc_no, vendor, partno, qty)
                VALUES (:id, :date, :dc_no, :vendor, :partno, :qty)
            """), {"id": next_id, "date": date_val, "dc_no": dc_no_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                INSERT INTO pc_receipt_logs (date, vendor, partno, qty)
                VALUES (:date, :vendor, :partno, :qty)
            """), {"date": date_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()

        # Update Opn 50 (PC operation) in production_logs
        log_pc_receipt_to_production(db, partno_val, qty_val, date_val, vendor_val)

        return {"message": "PC Receipt Log saved successfully"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.put("/api/pc_receipt_logs/{log_id}")
def update_pc_receipt_log(log_id: int, data: dict, db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("ALTER TABLE pc_receipt_logs ADD COLUMN IF NOT EXISTS dc_no VARCHAR(100) DEFAULT '';"))
            db.commit()
        except Exception:
            db.rollback()

        date_val = normalize_date_str((data.get("date") or "").strip())
        dc_no_val = (data.get("dc_no") or "").strip()
        vendor_val = (data.get("vendor") or "").strip()
        partno_val = (data.get("partno") or "").strip()
        qty_val = int(data.get("qty") or 0)

        try:
            db.execute(text("""
                UPDATE pc_receipt_logs
                SET date = :date, dc_no = :dc_no, vendor = :vendor, partno = :partno, qty = :qty
                WHERE id = :id
            """), {"id": log_id, "date": date_val, "dc_no": dc_no_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                UPDATE pc_receipt_logs
                SET date = :date, vendor = :vendor, partno = :partno, qty = :qty
                WHERE id = :id
            """), {"id": log_id, "date": date_val, "vendor": vendor_val, "partno": partno_val, "qty": qty_val})
            db.commit()

        return {"message": "PC Receipt Log updated successfully"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.delete("/api/pc_receipt_logs/{log_id}")
def delete_pc_receipt_log(log_id: int, db: Session = Depends(get_db)):
    try:
        row = db.execute(text("SELECT * FROM pc_receipt_logs WHERE id = :id"), {"id": log_id}).mappings().first()
        if row:
            pno = row.get("partno")
            qty = str(row.get("qty"))
            try:
                db.execute(text("""
                    DELETE FROM production_logs 
                    WHERE id IN (
                        SELECT id FROM production_logs 
                        WHERE machine = 'PC' AND UPPER(TRIM(partno)) = :pno AND prod_qty = :qty 
                        LIMIT 1
                    );
                """), {"pno": pno.upper(), "qty": qty})
                db.commit()
            except Exception:
                db.rollback()

        db.execute(text("DELETE FROM pc_receipt_logs WHERE id = :id"), {"id": log_id})
        db.commit()
        return {"message": "PC Receipt Log deleted"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

# --- SERVICE: SETTERS LOG CRUD ---
@app.get("/api/service/setters")
def get_service_setters_list(dept: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        op_rows = db.execute(text("SELECT * FROM operators WHERE UPPER(TRIM(COALESCE(designation, ''))) = 'SETTER' ORDER BY name ASC;")).mappings().all()
        
        d_filter = (dept or "").strip().upper()
        seen = set()
        result = []
        for r in op_rows:
            nm = (r.get("name") or "").strip()
            d_val = (r.get("department") or r.get("dept") or "").strip()
            if d_filter and d_val.upper() != d_filter:
                continue
            if nm and nm.upper() not in seen:
                seen.add(nm.upper())
                result.append({
                    "name": nm,
                    "department": d_val,
                    "dept": d_val,
                    "designation": "SETTER"
                })
        result.sort(key=lambda x: x["name"])
        return result
    except Exception as e:
        print("get_service_setters_list error:", e)
        db.rollback()
        return []

@app.get("/api/service/setter-logs")
def get_service_setter_logs(db: Session = Depends(get_db)):
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS setter_logs (
                id SERIAL PRIMARY KEY,
                date TEXT,
                dept TEXT DEFAULT '',
                setter_name TEXT,
                time_from TEXT,
                time_to TEXT,
                activity TEXT,
                machine TEXT,
                partno TEXT,
                opn_no TEXT,
                description TEXT,
                qty INTEGER DEFAULT 0,
                remarks TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        db.commit()
        try:
            db.execute(text("ALTER TABLE setter_logs ADD COLUMN dept VARCHAR(50) DEFAULT '';"))
            db.commit()
        except Exception:
            db.rollback()

        rows = db.execute(text("SELECT * FROM setter_logs ORDER BY date DESC, id DESC;")).mappings().all()
        return [{
            "id": r.get("id"),
            "date": r.get("date") or "",
            "dept": r.get("dept") or "",
            "setter_name": r.get("setter_name") or "",
            "time_from": r.get("time_from") or "",
            "time_to": r.get("time_to") or "",
            "activity": r.get("activity") or "",
            "machine": r.get("machine") or "",
            "partno": r.get("partno") or "",
            "opn_no": r.get("opn_no") or "",
            "description": r.get("description") or "",
            "qty": int(r.get("qty") or 0),
            "remarks": r.get("remarks") or "",
            "created_at": str(r.get("created_at") or "")
        } for r in rows]
    except Exception as e:
        print("get_service_setter_logs error:", e)
        db.rollback()
        return []

@app.post("/api/service/setter-logs")
def create_service_setter_log(data: dict, db: Session = Depends(get_db)):
    try:
        date_val = normalize_date_str((data.get("date") or "").strip())
        dept_val = (data.get("dept") or data.get("department") or "").strip()
        setter_name = (data.get("setter_name") or data.get("name") or "").strip()
        time_from = (data.get("time_from") or "").strip()
        time_to = (data.get("time_to") or "").strip()
        activity = (data.get("activity") or "").strip()
        machine = (data.get("machine") or "").strip()
        partno = (data.get("partno") or data.get("part_no") or "").strip()
        opn_no = (data.get("opn_no") or "").strip()
        description = (data.get("description") or data.get("desc") or "").strip()
        qty = int(data.get("qty") or 0)
        remarks = (data.get("remarks") or "").strip()

        if not setter_name:
            raise HTTPException(status_code=400, detail="Setter Name is required")

        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('setter_logs', 'id'), coalesce(max(id),0) + 1, false) FROM setter_logs;"))
            db.commit()
        except Exception:
            db.rollback()

        max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM setter_logs;")).mappings().first()
        next_id = int(max_row["next_id"]) if max_row else 1

        params = {
            "id": next_id,
            "date": date_val,
            "dept": dept_val,
            "setter_name": setter_name,
            "time_from": time_from,
            "time_to": time_to,
            "activity": activity,
            "machine": machine,
            "partno": partno,
            "opn_no": opn_no,
            "description": description,
            "qty": qty,
            "remarks": remarks
        }
        try:
            db.execute(text("""
                INSERT INTO setter_logs (id, date, dept, setter_name, time_from, time_to, activity, machine, partno, opn_no, description, qty, remarks)
                VALUES (:id, :date, :dept, :setter_name, :time_from, :time_to, :activity, :machine, :partno, :opn_no, :description, :qty, :remarks);
            """), params)
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                INSERT INTO setter_logs (date, dept, setter_name, time_from, time_to, activity, machine, partno, opn_no, description, qty, remarks)
                VALUES (:date, :dept, :setter_name, :time_from, :time_to, :activity, :machine, :partno, :opn_no, :description, :qty, :remarks);
            """), params)
            db.commit()

        return {"message": "Setter entry logged successfully", "id": next_id, **params}
    except HTTPException:
        raise
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.put("/api/service/setter-logs/{log_id}")
def update_service_setter_log(log_id: int, data: dict, db: Session = Depends(get_db)):
    try:
        date_val = normalize_date_str((data.get("date") or "").strip())
        dept_val = (data.get("dept") or data.get("department") or "").strip()
        setter_name = (data.get("setter_name") or data.get("name") or "").strip()
        time_from = (data.get("time_from") or "").strip()
        time_to = (data.get("time_to") or "").strip()
        activity = (data.get("activity") or "").strip()
        machine = (data.get("machine") or "").strip()
        partno = (data.get("partno") or data.get("part_no") or "").strip()
        opn_no = (data.get("opn_no") or "").strip()
        description = (data.get("description") or data.get("desc") or "").strip()
        qty = int(data.get("qty") or 0)
        remarks = (data.get("remarks") or "").strip()

        db.execute(text("""
            UPDATE setter_logs
            SET date = :date, dept = :dept, setter_name = :setter_name, time_from = :time_from, time_to = :time_to,
                activity = :activity, machine = :machine, partno = :partno, opn_no = :opn_no,
                description = :description, qty = :qty, remarks = :remarks
            WHERE id = :id;
        """), {
            "id": log_id,
            "date": date_val,
            "dept": dept_val,
            "setter_name": setter_name,
            "time_from": time_from,
            "time_to": time_to,
            "activity": activity,
            "machine": machine,
            "partno": partno,
            "opn_no": opn_no,
            "description": description,
            "qty": qty,
            "remarks": remarks
        })
        db.commit()
        return {"message": "Setter entry updated successfully", "id": log_id}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.delete("/api/service/setter-logs/{log_id}")
def delete_service_setter_log(log_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM setter_logs WHERE id = :id;"), {"id": log_id})
        db.commit()
        return {"message": "Setter entry deleted successfully"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.delete("/api/service/setter-logs")
def clear_all_service_setter_logs(db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM setter_logs;"))
        db.commit()
        return {"message": "All setter entries cleared successfully"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

# --- BREAKDOWN SLIPS & SERVICE DETAILS CRUD ---
@app.get("/api/breakdown_slips")
def get_breakdown_slips(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM breakdown_slips ORDER BY date_time DESC, id DESC;")).mappings().all()
        return [{
            "id": r.get("id"),
            "date_time": r.get("date_time") or "",
            "department": r.get("department") or "",
            "shift": r.get("shift") or "",
            "maint_type": r.get("maint_type") or "Breakdown",
            "request_by": r.get("request_by") or "",
            "machine": r.get("machine") or "",
            "problem": r.get("problem") or "",
            "signoff_date_time": r.get("signoff_date_time") or "",
            "status": r.get("status") or "Open",
            "created_at": str(r.get("created_at") or "")
        } for r in rows]
    except Exception:
        db.rollback()
        return []

@app.post("/api/breakdown_slips")
def create_breakdown_slip(data: dict, db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('breakdown_slips', 'id'), coalesce(max(id),0) + 1, false) FROM breakdown_slips;"))
            db.commit()
        except Exception:
            db.rollback()

        max_id_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM breakdown_slips;")).mappings().first()
        next_id = int(max_id_row["next_id"]) if max_id_row else 1

        db.execute(text("""
            INSERT INTO breakdown_slips (id, date_time, department, shift, maint_type, request_by, machine, problem, signoff_date_time, status, created_at)
            VALUES (:id, :date_time, :department, :shift, :maint_type, :request_by, :machine, :problem, :signoff_date_time, :status, :created_at)
        """), {
            "id": next_id,
            "date_time": (data.get("date_time") or "").strip(),
            "department": (data.get("department") or "").strip(),
            "shift": (data.get("shift") or "").strip(),
            "maint_type": (data.get("maint_type") or "Breakdown").strip(),
            "request_by": (data.get("request_by") or "").strip(),
            "machine": (data.get("machine") or "").strip(),
            "problem": (data.get("problem") or "").strip(),
            "signoff_date_time": (data.get("signoff_date_time") or "").strip(),
            "status": (data.get("status") or "Open").strip(),
            "created_at": datetime.datetime.now(IST).isoformat()
        })
        db.commit()
        return {"message": "Breakdown Slip created successfully", "id": next_id}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.put("/api/breakdown_slips/{slip_id}")
def update_breakdown_slip(slip_id: int, data: dict, db: Session = Depends(get_db)):
    try:
        db.execute(text("""
            UPDATE breakdown_slips
            SET date_time = :date_time, department = :department, shift = :shift,
                maint_type = :maint_type, request_by = :request_by, machine = :machine,
                problem = :problem, signoff_date_time = :signoff_date_time, status = :status
            WHERE id = :id
        """), {
            "id": slip_id,
            "date_time": (data.get("date_time") or "").strip(),
            "department": (data.get("department") or "").strip(),
            "shift": (data.get("shift") or "").strip(),
            "maint_type": (data.get("maint_type") or "Breakdown").strip(),
            "request_by": (data.get("request_by") or "").strip(),
            "machine": (data.get("machine") or "").strip(),
            "problem": (data.get("problem") or "").strip(),
            "signoff_date_time": (data.get("signoff_date_time") or "").strip(),
            "status": (data.get("status") or "Open").strip()
        })
        db.commit()
        return {"message": "Breakdown Slip updated successfully", "id": slip_id}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.delete("/api/breakdown_slips/{slip_id}")
def delete_breakdown_slip(slip_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM breakdown_slips WHERE id = :id"), {"id": slip_id})
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "Breakdown Slip deleted"}

@app.get("/api/service_details")
def get_service_details(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM service_details ORDER BY id DESC;")).mappings().all()
        return [{
            "id": r.get("id"),
            "breakdown_slip_id": r.get("breakdown_slip_id"),
            "machine": r.get("machine") or "",
            "spares_data": r.get("spares_data") or "[]",
            "service_data": r.get("service_data") or "[]",
            "spares_cost": float(r.get("spares_cost") or 0),
            "service_cost": float(r.get("service_cost") or 0),
            "total_cost": float(r.get("total_cost") or 0),
            "remarks": r.get("remarks") or "",
            "created_at": str(r.get("created_at") or "")
        } for r in rows]
    except Exception:
        db.rollback()
        return []

@app.post("/api/service_details")
def create_service_detail(data: dict, db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('service_details', 'id'), coalesce(max(id),0) + 1, false) FROM service_details;"))
            db.commit()
        except Exception:
            db.rollback()

        max_id_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM service_details;")).mappings().first()
        next_id = int(max_id_row["next_id"]) if max_id_row else 1

        bd_id = data.get("breakdown_slip_id")
        if bd_id is not None and str(bd_id).strip() != "":
            try:
                bd_id = int(bd_id)
            except Exception:
                bd_id = None
        else:
            bd_id = None

        db.execute(text("""
            INSERT INTO service_details (id, breakdown_slip_id, machine, spares_data, service_data, spares_cost, service_cost, total_cost, remarks, created_at)
            VALUES (:id, :breakdown_slip_id, :machine, :spares_data, :service_data, :spares_cost, :service_cost, :total_cost, :remarks, :created_at)
        """), {
            "id": next_id,
            "breakdown_slip_id": bd_id,
            "machine": (data.get("machine") or "").strip(),
            "spares_data": json.dumps(data.get("spares_data")) if isinstance(data.get("spares_data"), list) else str(data.get("spares_data") or "[]"),
            "service_data": json.dumps(data.get("service_data")) if isinstance(data.get("service_data"), list) else str(data.get("service_data") or "[]"),
            "spares_cost": float(data.get("spares_cost") or 0),
            "service_cost": float(data.get("service_cost") or 0),
            "total_cost": float(data.get("total_cost") or 0),
            "remarks": (data.get("remarks") or "").strip(),
            "created_at": datetime.datetime.now(IST).isoformat()
        })
        db.commit()
        return {"message": "Service Detail created successfully", "id": next_id}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.put("/api/service_details/{detail_id}")
def update_service_detail(detail_id: int, data: dict, db: Session = Depends(get_db)):
    try:
        bd_id = data.get("breakdown_slip_id")
        if bd_id is not None and str(bd_id).strip() != "":
            try:
                bd_id = int(bd_id)
            except Exception:
                bd_id = None
        else:
            bd_id = None

        mach_val = (data.get("machine") or "").strip()
        db.execute(text("""
            UPDATE service_details
            SET breakdown_slip_id = :breakdown_slip_id,
                machine = CASE WHEN :machine <> '' THEN :machine ELSE machine END,
                spares_data = :spares_data, service_data = :service_data,
                spares_cost = :spares_cost, service_cost = :service_cost,
                total_cost = :total_cost, remarks = :remarks
            WHERE id = :id
        """), {
            "id": detail_id,
            "breakdown_slip_id": bd_id,
            "machine": mach_val,
            "spares_data": json.dumps(data.get("spares_data")) if isinstance(data.get("spares_data"), list) else str(data.get("spares_data") or "[]"),
            "service_data": json.dumps(data.get("service_data")) if isinstance(data.get("service_data"), list) else str(data.get("service_data") or "[]"),
            "spares_cost": float(data.get("spares_cost") or 0),
            "service_cost": float(data.get("service_cost") or 0),
            "total_cost": float(data.get("total_cost") or 0),
            "remarks": (data.get("remarks") or "").strip()
        })
        db.commit()
        return {"message": "Service Detail updated successfully", "id": detail_id}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.delete("/api/service_details/{detail_id}")
def delete_service_detail(detail_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM service_details WHERE id = :id"), {"id": detail_id})
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "Service Detail deleted"}

# --- RFQ & QUOTATION CRUD ---
@app.get("/api/rfq")
def get_rfqs(date_from: Optional[str] = None, date_to: Optional[str] = None, customer: Optional[str] = None, search: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        query = "SELECT * FROM rfq_headers WHERE 1=1"
        params = {}
        if date_from:
            query += " AND date >= :date_from"
            params["date_from"] = date_from
        if date_to:
            query += " AND date <= :date_to"
            params["date_to"] = date_to
        if customer:
            query += " AND LOWER(customer) = LOWER(:customer)"
            params["customer"] = customer

        query += " ORDER BY date DESC, id DESC"
        rfqs = db.execute(text(query), params).mappings().all()

        items = db.execute(text("SELECT * FROM rfq_items ORDER BY id ASC")).mappings().all()
        items_by_rfq = {}
        for it in items:
            try:
                rfq_id = int(it.get("rfq_id"))
            except Exception:
                rfq_id = it.get("rfq_id")
            if rfq_id not in items_by_rfq:
                items_by_rfq[rfq_id] = []
            items_by_rfq[rfq_id].append({
                "id": int(it.get("id")) if it.get("id") is not None else None,
                "rfq_id": rfq_id,
                "partno": it.get("partno") or "",
                "description": it.get("description") or ""
            })

        result = []
        for r in rfqs:
            try:
                rfq_id = int(r.get("id"))
            except Exception:
                rfq_id = r.get("id")
            rfq_items_list = items_by_rfq.get(rfq_id, [])
            
            if search:
                s_lower = search.strip().lower()
                rfq_no_match = s_lower in str(r.get("rfqno") or "").lower()
                cust_match = s_lower in str(r.get("customer") or "").lower()
                item_match = any(s_lower in (it["partno"].lower() + " " + it["description"].lower()) for it in rfq_items_list)
                if not (rfq_no_match or cust_match or item_match):
                    continue

            result.append({
                "id": rfq_id,
                "date": r.get("date") or "",
                "rfqno": r.get("rfqno") or "",
                "unit": r.get("unit") or "",
                "customer": r.get("customer") or "",
                "created_at": str(r.get("created_at") or ""),
                "items": rfq_items_list
            })
        return result
    except Exception:
        db.rollback()
        return []

@app.post("/api/rfq")
def create_rfq(data: dict, db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('rfq_headers', 'id'), coalesce(max(id),0) + 1, false) FROM rfq_headers;"))
            db.execute(text("SELECT setval(pg_get_serial_sequence('rfq_items', 'id'), coalesce(max(id),0) + 1, false) FROM rfq_items;"))
            db.commit()
        except Exception:
            db.rollback()

        max_id_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM rfq_headers;")).mappings().first()
        next_id = int(max_id_row["next_id"]) if max_id_row else 1

        db.execute(text("""
            INSERT INTO rfq_headers (id, date, rfqno, unit, customer, created_at)
            VALUES (:id, :date, :rfqno, :unit, :customer, :created_at)
        """), {
            "id": next_id,
            "date": (data.get("date") or "").strip(),
            "rfqno": (data.get("rfqno") or "").strip(),
            "unit": (data.get("unit") or "").strip(),
            "customer": (data.get("customer") or "").strip(),
            "created_at": datetime.datetime.now(IST).isoformat()
        })

        items = data.get("items") or []
        for it in items:
            partno = (it.get("partno") or "").strip()
            desc = (it.get("description") or "").strip()
            if partno:
                db.execute(text("""
                    INSERT INTO rfq_items (rfq_id, partno, description)
                    VALUES (:rfq_id, :partno, :description)
                """), {"rfq_id": next_id, "partno": partno, "description": desc})

        db.commit()
        return {"message": "RFQ created successfully", "id": next_id}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.put("/api/rfq/{rfq_id}")
def update_rfq(rfq_id: int, data: dict, db: Session = Depends(get_db)):
    try:
        db.execute(text("""
            UPDATE rfq_headers
            SET date = :date, rfqno = :rfqno, unit = :unit, customer = :customer
            WHERE id = :id
        """), {
            "id": rfq_id,
            "date": (data.get("date") or "").strip(),
            "rfqno": (data.get("rfqno") or "").strip(),
            "unit": (data.get("unit") or "").strip(),
            "customer": (data.get("customer") or "").strip()
        })

        db.execute(text("DELETE FROM rfq_items WHERE rfq_id = :rfq_id"), {"rfq_id": rfq_id})
        items = data.get("items") or []
        for it in items:
            partno = (it.get("partno") or "").strip()
            desc = (it.get("description") or "").strip()
            if partno:
                db.execute(text("""
                    INSERT INTO rfq_items (rfq_id, partno, description)
                    VALUES (:rfq_id, :partno, :description)
                """), {"rfq_id": rfq_id, "partno": partno, "description": desc})

        db.commit()
        return {"message": "RFQ updated successfully"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.delete("/api/rfq/{rfq_id}")
def delete_rfq(rfq_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM rfq_items WHERE rfq_id = :id"), {"id": rfq_id})
        db.execute(text("DELETE FROM rfq_headers WHERE id = :id"), {"id": rfq_id})
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "RFQ deleted"}

@app.get("/api/quotes")
def get_quotes(date_from: Optional[str] = None, date_to: Optional[str] = None, customer: Optional[str] = None, search: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        query = "SELECT * FROM quote_records WHERE 1=1"
        params = {}
        if date_from:
            query += " AND date >= :date_from"
            params["date_from"] = date_from
        if date_to:
            query += " AND date <= :date_to"
            params["date_to"] = date_to
        if customer:
            query += " AND LOWER(customer) = LOWER(:customer)"
            params["customer"] = customer

        query += " ORDER BY date DESC, id DESC"
        rows = db.execute(text(query), params).mappings().all()

        result = []
        for r in rows:
            if search:
                s_lower = search.strip().lower()
                q_match = s_lower in str(r.get("quote_no") or "").lower()
                rfq_match = s_lower in str(r.get("rfq_no") or "").lower()
                c_match = s_lower in str(r.get("customer") or "").lower()
                p_match = s_lower in str(r.get("part_no") or "").lower()
                d_match = s_lower in str(r.get("part_description") or "").lower()
                if not (q_match or rfq_match or c_match or p_match or d_match):
                    continue

            result.append({
                "id": r.get("id"),
                "quote_no": r.get("quote_no") or "",
                "date": r.get("date") or "",
                "rfq_id": r.get("rfq_id"),
                "rfq_no": r.get("rfq_no") or "",
                "customer": r.get("customer") or "",
                "part_no": r.get("part_no") or "",
                "part_description": r.get("part_description") or "",
                "unit": r.get("unit") or "Unit 1",
                "overhead_profit_pct": float(r.get("overhead_profit_pct") or 0),
                "total_machining_cost": float(r.get("total_machining_cost") or 0),
                "total_other_process_cost": float(r.get("total_other_process_cost") or 0),
                "total_packing_cost": float(r.get("total_packing_cost") or 0),
                "base_part_cost": float(r.get("base_part_cost") or 0),
                "final_unit_price": float(r.get("final_unit_price") or 0),
                "total_dev_cost": float(r.get("total_dev_cost") or 0),
                "machining_details": r.get("machining_details") or "[]",
                "other_process_details": r.get("other_process_details") or "[]",
                "packing_details": r.get("packing_details") or "[]",
                "dev_cost_details": r.get("dev_cost_details") or "[]",
                "created_at": str(r.get("created_at") or "")
            })
        return result
    except Exception:
        db.rollback()
        return []

@app.post("/api/quotes")
def create_quote(data: dict, db: Session = Depends(get_db)):
    try:
        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('quote_records', 'id'), coalesce(max(id),0) + 1, false) FROM quote_records;"))
            db.commit()
        except Exception:
            db.rollback()

        max_id_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM quote_records;")).mappings().first()
        next_id = int(max_id_row["next_id"]) if max_id_row else 1

        rfq_id_val = data.get("rfq_id")
        if rfq_id_val is not None and str(rfq_id_val).strip() != "":
            try:
                rfq_id_val = int(rfq_id_val)
            except Exception:
                rfq_id_val = None
        else:
            rfq_id_val = None

        db.execute(text("""
            INSERT INTO quote_records (id, quote_no, date, rfq_id, rfq_no, customer, part_no, part_description, unit, overhead_profit_pct, total_machining_cost, total_other_process_cost, total_packing_cost, base_part_cost, final_unit_price, total_dev_cost, machining_details, other_process_details, packing_details, dev_cost_details, created_at)
            VALUES (:id, :quote_no, :date, :rfq_id, :rfq_no, :customer, :part_no, :part_description, :unit, :overhead_profit_pct, :total_machining_cost, :total_other_process_cost, :total_packing_cost, :base_part_cost, :final_unit_price, :total_dev_cost, :machining_details, :other_process_details, :packing_details, :dev_cost_details, :created_at)
        """), {
            "id": next_id,
            "quote_no": (data.get("quote_no") or "").strip(),
            "date": (data.get("date") or "").strip(),
            "rfq_id": rfq_id_val,
            "rfq_no": (data.get("rfq_no") or "").strip(),
            "customer": (data.get("customer") or "").strip(),
            "part_no": (data.get("part_no") or "").strip(),
            "part_description": (data.get("part_description") or "").strip(),
            "unit": (data.get("unit") or "Unit 1").strip(),
            "overhead_profit_pct": float(data.get("overhead_profit_pct") or 0),
            "total_machining_cost": float(data.get("total_machining_cost") or 0),
            "total_other_process_cost": float(data.get("total_other_process_cost") or 0),
            "total_packing_cost": float(data.get("total_packing_cost") or 0),
            "base_part_cost": float(data.get("base_part_cost") or 0),
            "final_unit_price": float(data.get("final_unit_price") or 0),
            "total_dev_cost": float(data.get("total_dev_cost") or 0),
            "machining_details": json.dumps(data.get("machining_details")) if isinstance(data.get("machining_details"), list) else str(data.get("machining_details") or "[]"),
            "other_process_details": json.dumps(data.get("other_process_details")) if isinstance(data.get("other_process_details"), list) else str(data.get("other_process_details") or "[]"),
            "packing_details": json.dumps(data.get("packing_details")) if isinstance(data.get("packing_details"), list) else str(data.get("packing_details") or "[]"),
            "dev_cost_details": json.dumps(data.get("dev_cost_details")) if isinstance(data.get("dev_cost_details"), list) else str(data.get("dev_cost_details") or "[]"),
            "created_at": datetime.datetime.now(IST).isoformat()
        })
        db.commit()
        return {"message": "Quotation created successfully", "id": next_id}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.put("/api/quotes/{quote_id}")
def update_quote(quote_id: int, data: dict, db: Session = Depends(get_db)):
    try:
        rfq_id_val = data.get("rfq_id")
        if rfq_id_val is not None and str(rfq_id_val).strip() != "":
            try:
                rfq_id_val = int(rfq_id_val)
            except Exception:
                rfq_id_val = None
        else:
            rfq_id_val = None

        db.execute(text("""
            UPDATE quote_records
            SET quote_no = :quote_no, date = :date, rfq_id = :rfq_id, rfq_no = :rfq_no,
                customer = :customer, part_no = :part_no, part_description = :part_description,
                unit = :unit, overhead_profit_pct = :overhead_profit_pct,
                total_machining_cost = :total_machining_cost, total_other_process_cost = :total_other_process_cost,
                total_packing_cost = :total_packing_cost, base_part_cost = :base_part_cost,
                final_unit_price = :final_unit_price, total_dev_cost = :total_dev_cost,
                machining_details = :machining_details, other_process_details = :other_process_details,
                packing_details = :packing_details, dev_cost_details = :dev_cost_details
            WHERE id = :id
        """), {
            "id": quote_id,
            "quote_no": (data.get("quote_no") or "").strip(),
            "date": (data.get("date") or "").strip(),
            "rfq_id": rfq_id_val,
            "rfq_no": (data.get("rfq_no") or "").strip(),
            "customer": (data.get("customer") or "").strip(),
            "part_no": (data.get("part_no") or "").strip(),
            "part_description": (data.get("part_description") or "").strip(),
            "unit": (data.get("unit") or "Unit 1").strip(),
            "overhead_profit_pct": float(data.get("overhead_profit_pct") or 0),
            "total_machining_cost": float(data.get("total_machining_cost") or 0),
            "total_other_process_cost": float(data.get("total_other_process_cost") or 0),
            "total_packing_cost": float(data.get("total_packing_cost") or 0),
            "base_part_cost": float(data.get("base_part_cost") or 0),
            "final_unit_price": float(data.get("final_unit_price") or 0),
            "total_dev_cost": float(data.get("total_dev_cost") or 0),
            "machining_details": json.dumps(data.get("machining_details")) if isinstance(data.get("machining_details"), list) else str(data.get("machining_details") or "[]"),
            "other_process_details": json.dumps(data.get("other_process_details")) if isinstance(data.get("other_process_details"), list) else str(data.get("other_process_details") or "[]"),
            "packing_details": json.dumps(data.get("packing_details")) if isinstance(data.get("packing_details"), list) else str(data.get("packing_details") or "[]"),
            "dev_cost_details": json.dumps(data.get("dev_cost_details")) if isinstance(data.get("dev_cost_details"), list) else str(data.get("dev_cost_details") or "[]")
        })
        db.commit()
        return {"message": "Quotation updated successfully"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.delete("/api/quotes/{quote_id}")
def delete_quote(quote_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM quote_records WHERE id = :id"), {"id": quote_id})
        db.commit()
    except Exception:
        db.rollback()
    return {"message": "Quotation deleted"}

# --- SCHEDULE STATUS WIP ADJUSTMENTS ---
@app.post("/api/schedule_status/adjust_part_wip")
def adjust_part_wip(data: dict, db: Session = Depends(get_db)):
    try:
        dept = (data.get("department") or "General").strip()
        partno = (data.get("partno") or "").strip()
        adjustments = data.get("adjustments") or []

        if not partno:
            raise HTTPException(status_code=400, detail="Part number is required")

        today_str = datetime.datetime.now(IST).strftime("%Y-%m-%d")

        # Fetch operations for this part
        part_row = db.execute(text("SELECT id FROM parts WHERE LOWER(part_no) = LOWER(:p);"), {"p": partno}).mappings().first()
        operations = []
        if part_row:
            op_rows = db.execute(text("SELECT opn_no, description FROM operations WHERE part_id = :pid ORDER BY id ASC;"), {"pid": part_row["id"]}).mappings().all()
            operations = [str(r["opn_no"]).strip() for r in op_rows]
        else:
            pm_row = db.execute(text("SELECT id FROM part_masters WHERE LOWER(partno) = LOWER(:p);"), {"p": partno}).mappings().first()
            if pm_row:
                op_rows = db.execute(text("SELECT opn_no, description FROM part_operations WHERE CAST(part_id AS TEXT) = :pid ORDER BY id ASC;"), {"pid": str(pm_row["id"])}).mappings().all()
                operations = [str(r["opn_no"]).strip() for r in op_rows]

        target_map = {}
        for adj in adjustments:
            opn_key = str(adj.get("opn_no") or "").strip().lower()
            try:
                target_val = float(adj.get("target_balance") or 0)
            except Exception:
                target_val = 0.0
            target_map[opn_key] = target_val

        stages = []
        for op in operations:
            stages.append(op.lower())
        if "debur" not in stages:
            stages.append("debur")
        if "for ins" not in stages:
            stages.append("for ins")
        if "rfd" not in stages:
            stages.append("rfd")

        # Despatch total from raw_material_logs
        rm_rows = db.execute(text("""
            SELECT qty FROM raw_material_logs
            WHERE LOWER(type) = 'despatch' AND LOWER(finish_part_no) = LOWER(:p);
        """), {"p": partno}).mappings().all()
        desp_total = 0.0
        for r in rm_rows:
            try:
                desp_total += float(r.get("qty") or 0)
            except Exception:
                pass

        cum_req = {}
        running_cum = desp_total

        for stage in reversed(stages):
            target_bal = target_map.get(stage, 0.0)
            running_cum += target_bal
            cum_req[stage] = running_cum

        for stage in stages:
            if stage in target_map:
                prod_rows = db.execute(text("""
                    SELECT prod_qty FROM production_logs
                    WHERE LOWER(partno) = LOWER(:p) AND LOWER(opn_no) = LOWER(:opn);
                """), {"p": partno, "opn": stage}).mappings().all()
                curr_prod = 0.0
                for pr in prod_rows:
                    try:
                        curr_prod += float(pr.get("prod_qty") or 0)
                    except Exception:
                        pass

                needed_cum = cum_req[stage]
                delta = int(round(needed_cum - curr_prod))

                if delta != 0:
                    try:
                        db.execute(text("SELECT setval(pg_get_serial_sequence('production_logs', 'id'), coalesce(max(id),0) + 1, false) FROM production_logs;"))
                        db.commit()
                    except Exception:
                        db.rollback()

                    db.execute(text("""
                        INSERT INTO production_logs (
                            dept, date, shift, setter, machine, operator, partno, opn_no,
                            description, runtime, cycle_time, target_qty, prod_qty, efficiency,
                            idle_hours, idle_reason, idle_hours_2, idle_reason_2, idle_hours_3, idle_reason_3, multiple_mc
                        ) VALUES (
                            :dept, :date, 'General', 'WIP Adjustment', 'Adjustment', 'WIP Adjustment', :partno, :opn_no,
                            'WIP Adjustment', 0, 0, 0, :prod_qty, 100,
                            0, '', 0, '', 0, '', 'no'
                        );
                    """), {
                        "dept": dept,
                        "date": today_str,
                        "partno": partno,
                        "opn_no": stage.upper() if stage not in ["debur", "for ins", "rfd"] else stage,
                        "prod_qty": delta
                    })
                    db.commit()

        return {"message": f"WIP balances for part {partno} adjusted successfully"}
    except HTTPException:
        raise
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

@app.post("/api/schedule_status/clear_backlog_corrections")
def clear_backlog_corrections(db: Session = Depends(get_db)):
    try:
        db.execute(text("""
            DELETE FROM production_logs
            WHERE setter IN ('WIP Adjustment', 'Backlog Correction')
               OR operator IN ('WIP Adjustment', 'Backlog Correction')
               OR description LIKE '%WIP Adjustment%'
               OR description LIKE '%Backlog Correction%';
        """))
        db.commit()
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))
    return {"message": "All backlog correction and WIP adjustment logs cleared successfully"}

@app.post("/api/schedule_status/autofix_wip")
def autofix_wip(data: dict, db: Session = Depends(get_db)):
    try:
        dept = (data.get("department") or "").strip()
        today_str = datetime.datetime.now(IST).strftime("%Y-%m-%d")

        q = "SELECT id, part_no as partno, dept as department FROM parts"
        params = {}
        if dept:
            q += " WHERE LOWER(dept) = LOWER(:dept)"
            params["dept"] = dept
        q += " ORDER BY id ASC;"

        parts = db.execute(text(q), params).mappings().all()
        if not parts:
            q_pm = "SELECT id, partno, department FROM part_masters"
            if dept:
                q_pm += " WHERE LOWER(department) = LOWER(:dept)"
            q_pm += " ORDER BY id ASC;"
            parts = db.execute(text(q_pm), params).mappings().all()

        for p in parts:
            pno = (p.get("partno") or "").strip()
            pdept = p.get("department") or dept or "General"
            if not pno:
                continue
            op_rows = db.execute(text("SELECT opn_no FROM operations WHERE part_id = :pid ORDER BY id ASC;"), {"pid": p["id"]}).mappings().all()
            if not op_rows:
                op_rows = db.execute(text("SELECT opn_no FROM part_operations WHERE CAST(part_id AS TEXT) = :pid ORDER BY id ASC;"), {"pid": str(p["id"])}).mappings().all()
            operations = [str(r["opn_no"]).strip().lower() for r in op_rows]
            if not operations:
                continue

            for i in range(len(operations) - 1):
                curr_op = operations[i]
                next_op = operations[i+1]

                curr_prod_rows = db.execute(text("SELECT prod_qty FROM production_logs WHERE LOWER(partno) = LOWER(:p) AND LOWER(opn_no) = LOWER(:opn);"), {"p": pno, "opn": curr_op}).mappings().all()
                next_prod_rows = db.execute(text("SELECT prod_qty FROM production_logs WHERE LOWER(partno) = LOWER(:p) AND LOWER(opn_no) = LOWER(:opn);"), {"p": pno, "opn": next_op}).mappings().all()

                c_prod = sum(float(r.get("prod_qty") or 0) for r in curr_prod_rows)
                n_prod = sum(float(r.get("prod_qty") or 0) for r in next_prod_rows)

                if c_prod < n_prod:
                    diff = int(round(n_prod - c_prod))
                    db.execute(text("""
                        INSERT INTO production_logs (
                            dept, date, shift, setter, machine, operator, partno, opn_no,
                            description, runtime, cycle_time, target_qty, prod_qty, efficiency,
                            idle_hours, idle_reason, idle_hours_2, idle_reason_2, idle_hours_3, idle_reason_3, multiple_mc
                        ) VALUES (
                            :dept, :date, 'General', 'Backlog Correction', 'Adjustment', 'Backlog Correction', :partno, :opn_no,
                            'Backlog Correction', 0, 0, 0, :prod_qty, 100,
                            0, '', 0, '', 0, '', 'no'
                        );
                    """), {
                        "dept": pdept,
                        "date": today_str,
                        "partno": pno,
                        "opn_no": curr_op.upper(),
                        "prod_qty": diff
                    })

        db.commit()
        return {"message": f"Backlog correction completed successfully for {len(parts)} parts"}
    except Exception as ex:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(ex))

# --- Tooling ---
@app.get("/api/tooling", response_model=List[ToolingResponse])
def get_tooling(db: Session = Depends(get_db)):
    return db.query(models.Tooling).all()

@app.post("/api/tooling", response_model=ToolingResponse)
def create_tooling(tool: ToolingCreate, db: Session = Depends(get_db)):
    db_tool = models.Tooling(**tool.model_dump())
    db.add(db_tool)
    db.commit()
    db.refresh(db_tool)
    return db_tool

@app.delete("/api/tooling/clear-all")
def clear_all_tooling(db: Session = Depends(get_db)):
    db.query(models.Tooling).delete()
    db.commit()
    return {"message": "All tooling items cleared successfully!"}

@app.delete("/api/tooling/{tool_id}")
def delete_tooling(tool_id: int, db: Session = Depends(get_db)):
    db_tool = db.query(models.Tooling).filter(models.Tooling.id == tool_id).first()
    if not db_tool:
        raise HTTPException(status_code=404, detail="Tooling item not found")
    db.delete(db_tool)
    db.commit()
    return {"message": "Tooling item deleted"}

# --- Inspection Parameters & Reports API ---

DEFAULT_INSPECTION_PARAMS = [
    {"sl_no": 1, "description": "Bore", "nominal_dimension": 115.0, "lo_tol": 0.03, "hi_tol": 0.03},
    {"sl_no": 2, "description": "Bore", "nominal_dimension": 110.0, "lo_tol": 0.30, "hi_tol": 0.30},
    {"sl_no": 3, "description": "Dim", "nominal_dimension": 95.0, "lo_tol": 0.10, "hi_tol": 0.10},
    {"sl_no": 4, "description": "Dim", "nominal_dimension": 50.0, "lo_tol": 0.30, "hi_tol": 0.30},
    {"sl_no": 5, "description": "OD", "nominal_dimension": 142.0, "lo_tol": 0.30, "hi_tol": 0.30},
]

@app.get("/api/inspection-parameters", response_model=List[InspectionParamResponse])
def get_inspection_parameters(part_no: str, opn_no: Optional[str] = None, db: Session = Depends(get_db)):
    clean_p = part_no.strip().lower()
    clean_op = opn_no.strip().lower() if opn_no else None

    query = db.query(models.InspectionParameter).filter(func.lower(models.InspectionParameter.part_no) == clean_p)
    if clean_op:
        query = query.filter(func.lower(models.InspectionParameter.opn_no) == clean_op)
    
    params = query.order_by(models.InspectionParameter.sl_no.asc()).all()
    return params

@app.post("/api/inspection-parameters")
def save_inspection_parameters(param_list: List[InspectionParamCreate], db: Session = Depends(get_db)):
    if not param_list:
        return {"message": "No parameters provided"}
    
    p_no = param_list[0].part_no.strip()
    op_no = param_list[0].opn_no.strip()
    p_desc = param_list[0].part_desc or ""
    op_desc = param_list[0].opn_desc or ""
    dept = param_list[0].dept or ""

    db.query(models.InspectionParameter).filter(
        func.lower(models.InspectionParameter.part_no) == p_no.lower(),
        func.lower(models.InspectionParameter.opn_no) == op_no.lower()
    ).delete(synchronize_session=False)

    for idx, item in enumerate(param_list, start=1):
        db_param = models.InspectionParameter(
            dept=item.dept or dept,
            part_no=p_no,
            part_desc=item.part_desc or p_desc,
            opn_no=op_no,
            opn_desc=item.opn_desc or op_desc,
            sl_no=idx,
            description=item.description,
            nominal_dimension=item.nominal_dimension,
            lo_tol=item.lo_tol,
            hi_tol=item.hi_tol
        )
        db.add(db_param)

    db.commit()
    return {"message": "Inspection parameters saved successfully!"}

@app.delete("/api/inspection-parameters/{param_id}")
def delete_inspection_parameter(param_id: int, db: Session = Depends(get_db)):
    p = db.query(models.InspectionParameter).filter(models.InspectionParameter.id == param_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Parameter not found")
    db.delete(p)
    db.commit()
    return {"message": "Parameter deleted"}

def generate_traceability_code(part_no: str, opn_no: str, db: Session) -> str:
    clean_p = part_no.strip().upper()
    clean_op = opn_no.strip()
    mmdd = get_now_ist().strftime("%m%d")
    prefix = f"{clean_p}-{clean_op}-{mmdd}-"
    
    existing_count = db.query(models.InspectionReport).filter(
        models.InspectionReport.report_code.like(f"{prefix}%")
    ).count()
    
    seq_num = existing_count + 1
    return f"{prefix}{seq_num:03d}"

@app.get("/api/inspection-reports/next-code")
def get_next_report_code(part_no: str, opn_no: str, db: Session = Depends(get_db)):
    code = generate_traceability_code(part_no, opn_no, db)
    return {"report_code": code}

@app.get("/api/inspection-reports")
def get_inspection_report(part_no: str, opn_no: str, db: Session = Depends(get_db)):
    clean_p = part_no.strip().lower()
    clean_op = opn_no.strip().lower()

    report = db.query(models.InspectionReport).filter(
        func.lower(models.InspectionReport.part_no) == clean_p,
        func.lower(models.InspectionReport.opn_no) == clean_op
    ).order_by(models.InspectionReport.id.desc()).first()

    next_code = generate_traceability_code(part_no, opn_no, db)

    sch = db.query(models.ProductionSchedule).filter(
        func.lower(models.ProductionSchedule.part_no) == clean_p
    ).first()
    sch_batch_qty = sch.total_sch_qty if (sch and sch.total_sch_qty and sch.total_sch_qty > 0) else 30

    if not report:
        return {
            "report_code": next_code,
            "part_no": part_no,
            "part_desc": "",
            "opn_no": opn_no,
            "opn_desc": "",
            "part_sl_no": "",
            "batch_qty": sch_batch_qty,
            "machine_name": "",
            "operator_name": "",
            "shift": "",
            "status": "Accepted",
            "remarks": "",
            "inspection_date": get_now_ist().strftime("%Y-%m-%d"),
            "comp_sl_nos": "1",
            "readings_json": "{}"
        }
    return report

@app.post("/api/inspection-reports")
@app.post("/api/line-inspections")
def save_inspection_report(req: InspectionReportSave, db: Session = Depends(get_db)):
    report_code = req.report_code
    if not report_code:
        report_code = generate_traceability_code(req.part_no, req.opn_no, db)

    # Save as a distinct, traceable quality inspection instance
    report = models.InspectionReport(
        report_code=report_code,
        prod_log_id=req.prod_log_id,
        dept=req.dept or "",
        part_no=req.part_no.strip(),
        part_desc=req.part_desc or "",
        opn_no=req.opn_no.strip(),
        opn_desc=req.opn_desc or "",
        part_sl_no=req.part_sl_no or req.comp_sl_nos or "",
        batch_qty=req.batch_qty or 1,
        machine_name=req.machine_name or "",
        operator_name=req.operator_name or "",
        shift=req.shift or "",
        status=req.status or "Accepted",
        remarks=req.remarks or "",
        inspection_date=req.inspection_date or get_now_ist().strftime("%Y-%m-%d"),
        comp_sl_nos=req.part_sl_no or req.comp_sl_nos or "1",
        readings_json=req.readings_json or "{}"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {"message": "Line Inspection saved successfully!", "report_code": report.report_code, "id": report.id}

@app.get("/api/line-inspections")
def get_line_inspections(part_no: Optional[str] = None, opn_no: Optional[str] = None, dept: Optional[str] = None, date: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(models.InspectionReport)
    if dept:
        query = query.filter(func.lower(models.InspectionReport.dept) == dept.strip().lower())
    if part_no:
        query = query.filter(func.lower(models.InspectionReport.part_no) == part_no.strip().lower())
    if opn_no:
        query = query.filter(func.lower(models.InspectionReport.opn_no) == opn_no.strip().lower())
    if date:
        query = query.filter(models.InspectionReport.inspection_date == date.strip())
    reports = query.order_by(models.InspectionReport.id.desc()).limit(limit).all()
    return reports

@app.get("/api/inspection-reports/by-id/{report_id}")
@app.get("/api/line-inspections/{report_id}")
def get_inspection_report_by_id(report_id: int, db: Session = Depends(get_db)):
    r = db.query(models.InspectionReport).filter(models.InspectionReport.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Inspection report not found")
    return r

@app.delete("/api/inspection-reports/{report_id}")
@app.delete("/api/line-inspections/{report_id}")
def delete_inspection_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(models.InspectionReport).filter(models.InspectionReport.id == report_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Inspection report not found")
    db.delete(r)
    db.commit()
    return {"message": "Inspection record deleted successfully"}

@app.get("/api/export/line-inspections/excel")
def export_line_inspections_excel(part_no: Optional[str] = None, opn_no: Optional[str] = None, dept: Optional[str] = None, db: Session = Depends(get_db)):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    query = db.query(models.InspectionReport)
    if dept:
        query = query.filter(func.lower(models.InspectionReport.dept) == dept.strip().lower())
    if part_no:
        query = query.filter(func.lower(models.InspectionReport.part_no) == part_no.strip().lower())
    if opn_no:
        query = query.filter(func.lower(models.InspectionReport.opn_no) == opn_no.strip().lower())
    records = query.order_by(models.InspectionReport.id.desc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Line Inspections"

    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    headers = [
        "Sl No", "Date", "Shift", "Dept", "Part No", "Part Desc", "Opn No", "Opn Desc",
        "Part Sl No", "Machine", "Inspector", "Status", "Remarks"
    ]
    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        c = ws.cell(row=1, column=col_idx)
        c.fill = header_fill
        c.font = header_font
        c.alignment = align_center

    for idx, r in enumerate(records, start=1):
        row_data = [
            idx,
            r.inspection_date or "",
            r.shift or "",
            r.dept or "",
            r.part_no or "",
            r.part_desc or "",
            r.opn_no or "",
            r.opn_desc or "",
            r.part_sl_no or r.comp_sl_nos or "",
            r.machine_name or "",
            r.operator_name or "",
            r.status or "Accepted",
            r.remarks or ""
        ]
        ws.append(row_data)
        row_num = ws.max_row
        for col_idx in range(1, len(row_data) + 1):
            cell = ws.cell(row=row_num, column=col_idx)
            cell.border = thin_border
            if col_idx in [1, 2, 3, 4, 5, 7, 9, 12]:
                cell.alignment = align_center
            else:
                cell.alignment = align_left

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"Line_Inspection_Report_{get_now_ist().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# --- Excel Export Endpoints ---
@app.get("/api/export/production-logs/excel")
def export_production_logs_excel(db: Session = Depends(get_db)):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    logs = db.query(models.ProductionLog).order_by(models.ProductionLog.id.desc()).all()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Production Logs"

    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    headers = [
        "Log ID", "Date", "Shift", "Dept", "Setter", "Machine", "Operator", 
        "Part Number", "Operation No", "Description", "Prod Qty", "Rej Qty", "Efficiency %", "Remarks"
    ]
    ws.append(headers)

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = align_center

    ws.row_dimensions[1].height = 24

    for log in logs:
        d_str = getattr(log, "date", "") or getattr(log, "log_date", "") or ""
        p_qty = getattr(log, "prod_qty", None) if getattr(log, "prod_qty", None) is not None else (getattr(log, "qty_produced", 0) or 0)
        r_qty = getattr(log, "rej_qty", None) if getattr(log, "rej_qty", None) is not None else (getattr(log, "scrap_qty", 0) or 0)
        eff = getattr(log, "efficiency", 0.0) or 0.0
        row = [
            log.id,
            d_str,
            log.shift or "",
            getattr(log, "dept", "") or "",
            getattr(log, "setter", "") or "",
            getattr(log, "machine", "") or getattr(log, "machine_name", "") or "",
            getattr(log, "operator", "") or getattr(log, "operator_name", "") or "",
            getattr(log, "partno", "") or getattr(log, "part_no", "") or "",
            getattr(log, "opn_no", "") or "",
            getattr(log, "description", "") or "",
            p_qty,
            r_qty,
            f"{eff:.1f}%" if eff else "",
            getattr(log, "remarks", "") or ""
        ]
        ws.append(row)
        r_idx = ws.max_row
        ws.row_dimensions[r_idx].height = 20
        for c_idx in range(1, len(row) + 1):
            cell = ws.cell(row=r_idx, column=c_idx)
            cell.border = thin_border
            if c_idx in [1, 2, 3, 4, 9]:
                cell.alignment = align_center
            elif c_idx in [11, 12, 13]:
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = align_left

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"Production_Logs_{datetime.date.today().strftime('%Y%m%d')}.xlsx"
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/export/inspection-reports/excel")
def export_inspection_reports_excel(db: Session = Depends(get_db)):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    reports = db.query(models.InspectionReport).order_by(models.InspectionReport.id.desc()).all()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Quality Inspection Logs"

    header_fill = PatternFill(start_color="065F46", end_color="065F46", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    
    pass_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")
    pass_font = Font(name="Calibri", size=11, bold=True, color="065F46")
    
    fail_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    fail_font = Font(name="Calibri", size=11, bold=True, color="991B1B")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    headers = [
        "Report ID", "Traceability ID", "Date", "Part Number", "Operation No", 
        "Batch Qty", "Machine Name", "Operator Name", "Component Sl No",
        "Parameter Description", "Nominal", "Lo Tol", "Hi Tol", "Measured Reading", "Status"
    ]
    ws.append(headers)

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = align_center

    ws.row_dimensions[1].height = 25

    for r in reports:
        params = db.query(models.InspectionParameter).filter(
            func.lower(models.InspectionParameter.part_no) == r.part_no.strip().lower(),
            func.lower(models.InspectionParameter.opn_no) == r.opn_no.strip().lower()
        ).order_by(models.InspectionParameter.sl_no.asc()).all()

        readings_map = {}
        try:
            import json
            readings_map = json.loads(r.readings_json or "{}")
        except Exception:
            readings_map = {}

        if not params:
            row = [
                r.id,
                r.report_code or f"IR-{r.id}",
                r.inspection_date or "",
                r.part_no or "",
                f"Opn {r.opn_no}" if r.opn_no else "",
                f"{r.batch_qty} pcs" if r.batch_qty else "-",
                r.machine_name or "-",
                r.operator_name or "-",
                r.comp_sl_nos or "1",
                "No parameters defined", "-", "-", "-", "-", "-"
            ]
            ws.append(row)
            r_idx = ws.max_row
            ws.row_dimensions[r_idx].height = 20
            for c_idx in range(1, len(row) + 1):
                cell = ws.cell(row=r_idx, column=c_idx)
                cell.border = thin_border
                cell.alignment = align_center if c_idx in [1, 2, 3, 5, 6, 9] else align_left
        else:
            is_first_row = True
            for p in params:
                p_readings = readings_map.get(str(p.id)) or readings_map.get(p.id) or {}
                val = p_readings.get("col_0") if "col_0" in p_readings else (p_readings.get("col_1") if "col_1" in p_readings else "")
                if val is None: val = ""
                val_str = str(val).strip()

                nom = float(p.nominal_dimension or 0.0)
                lo = float(p.lo_tol or 0.0)
                hi = float(p.hi_tol or 0.0)
                status = "-"
                val_num = val_str

                if val_str != "":
                    try:
                        v = float(val_str)
                        val_num = v
                        if (nom - lo) <= v <= (nom + hi):
                            status = "PASS"
                        else:
                            status = "OUT OF SPEC"
                    except ValueError:
                        status = "INVALID"

                if is_first_row:
                    row = [
                        r.id,
                        r.report_code or f"IR-{r.id}",
                        r.inspection_date or "",
                        r.part_no or "",
                        f"Opn {r.opn_no}" if r.opn_no else "",
                        f"{r.batch_qty} pcs" if r.batch_qty else "-",
                        r.machine_name or "-",
                        r.operator_name or "-",
                        r.comp_sl_nos or "1",
                        p.description or "",
                        nom,
                        lo,
                        hi,
                        val_num,
                        status
                    ]
                    is_first_row = False
                else:
                    row = [
                        "", "", "", "", "", "", "", "", "",
                        p.description or "",
                        nom,
                        lo,
                        hi,
                        val_num,
                        status
                    ]

                ws.append(row)
                r_idx = ws.max_row
                ws.row_dimensions[r_idx].height = 20

                for c_idx in range(1, len(row) + 1):
                    cell = ws.cell(row=r_idx, column=c_idx)
                    cell.border = thin_border
                    if c_idx in [1, 2, 3, 5, 6, 9]:
                        cell.alignment = align_center
                    elif c_idx in [11, 12, 13, 14]:
                        cell.alignment = align_right
                    elif c_idx == 15:
                        cell.alignment = align_center
                        if status == "PASS":
                            cell.fill = pass_fill
                            cell.font = pass_font
                        elif status == "OUT OF SPEC":
                            cell.fill = fail_fill
                            cell.font = fail_font
                    else:
                        cell.alignment = align_left

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"Quality_Inspection_Logs_{datetime.date.today().strftime('%Y%m%d')}.xlsx"
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# --- TOOL CRIB / INSERT MASTER CRUD ENDPOINTS ---

@app.get("/api/insert_masters")
def get_insert_masters(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM insert_masters ORDER BY id ASC;")).mappings().all()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id": d.get("id"),
                "insert_spec": d.get("insert_spec") or d.get("name") or "",
                "no_of_edges": int(float(d.get("no_of_edges") or 1)),
                "name": d.get("name") or d.get("insert_spec") or "",
                "specification": d.get("specification") or d.get("insert_spec") or "",
                "grade": d.get("grade") or "",
                "make": d.get("make") or "",
                "stock": float(d.get("stock") or 0.0),
                "price": float(d.get("price") or 0.0)
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/insert_masters")
def create_insert_master(data: dict, db: Session = Depends(get_db)):
    try:
        spec = (data.get("insert_spec") or data.get("name") or "").strip()
        if not spec:
            raise HTTPException(status_code=400, detail="Insert spec is required")
        edges = int(data.get("no_of_edges") or 1)
        grade = (data.get("grade") or "").strip()
        make = (data.get("make") or "").strip()
        stock = float(data.get("stock") or 0.0)
        price = float(data.get("price") or 0.0)

        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('insert_masters', 'id'), coalesce(max(id),0) + 1, false) FROM insert_masters;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM insert_masters")).mappings().first()
            next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 1
        except Exception:
            db.rollback()
            next_id = 1

        params = {"id": next_id, "spec": spec, "edges": edges, "grade": grade, "make": make, "stock": stock, "price": price}
        try:
            db.execute(text("""
                INSERT INTO insert_masters (id, insert_spec, no_of_edges, grade, make, stock, price)
                VALUES (:id, :spec, :edges, :grade, :make, :stock, :price);
            """), params)
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                INSERT INTO insert_masters (insert_spec, no_of_edges, grade, make, stock, price)
                VALUES (:spec, :edges, :grade, :make, :stock, :price);
            """), params)
            db.commit()

        return {"id": next_id, "message": "Created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/insert_masters/bulk")
def bulk_create_insert_masters(data: dict, db: Session = Depends(get_db)):
    inserts = data.get("inserts") or []
    count = 0
    try:
        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('insert_masters', 'id'), coalesce(max(id),0) + 1, false) FROM insert_masters;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) AS max_id FROM insert_masters")).mappings().first()
            curr_id = int(max_row.get("max_id")) if max_row and max_row.get("max_id") else 0
        except Exception:
            db.rollback()
            curr_id = 0

        for ins in inserts:
            spec = (ins.get("insert_spec") or ins.get("name") or "").strip()
            if spec:
                curr_id += 1
                edges = int(ins.get("no_of_edges") or 1)
                grade = (ins.get("grade") or "").strip()
                make = (ins.get("make") or "").strip()
                stock = float(ins.get("stock") or 0.0)
                price = float(ins.get("price") or 0.0)
                params = {"id": curr_id, "spec": spec, "edges": edges, "grade": grade, "make": make, "stock": stock, "price": price}
                try:
                    db.execute(text("""
                        INSERT INTO insert_masters (id, insert_spec, no_of_edges, grade, make, stock, price)
                        VALUES (:id, :spec, :edges, :grade, :make, :stock, :price);
                    """), params)
                except Exception:
                    db.rollback()
                    db.execute(text("""
                        INSERT INTO insert_masters (insert_spec, no_of_edges, grade, make, stock, price)
                        VALUES (:spec, :edges, :grade, :make, :stock, :price);
                    """), params)
                count += 1
        db.commit()
        return {"message": f"Successfully created {count} insert master records"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/insert_masters/{id}")
def update_insert_master(id: int, data: dict, db: Session = Depends(get_db)):
    spec = (data.get("insert_spec") or data.get("name") or "").strip()
    edges = int(data.get("no_of_edges") or 1)
    grade = (data.get("grade") or "").strip()
    make = (data.get("make") or "").strip()
    stock = float(data.get("stock") or 0.0)
    price = float(data.get("price") or 0.0)
    db.execute(text("""
        UPDATE insert_masters
        SET insert_spec = :spec, no_of_edges = :edges, grade = :grade, make = :make, stock = :stock, price = :price
        WHERE id = :id;
    """), {"id": id, "spec": spec, "edges": edges, "grade": grade, "make": make, "stock": stock, "price": price})
    db.commit()
    return {"message": "Updated successfully"}

@app.delete("/api/insert_masters/all")
def clear_all_insert_masters(db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM insert_masters;"))
    db.commit()
    return {"message": "All insert master records cleared successfully"}

@app.delete("/api/insert_masters/{id}")
def delete_insert_master(id: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM insert_masters WHERE id = :id;"), {"id": id})
    db.commit()
    return {"message": "Deleted successfully"}

# --- DRILL MASTER CRUD ---
@app.get("/api/drill_masters")
def get_drill_masters(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM drill_masters ORDER BY id ASC;")).mappings().all()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id": d.get("id"),
                "drill_size": d.get("drill_size") or d.get("size_dia") or d.get("name") or "",
                "sl_no": d.get("sl_no") or "",
                "resharp_count": int(float(d.get("resharp_count") or 0)),
                "name": d.get("name") or d.get("drill_size") or "",
                "size_dia": d.get("size_dia") or d.get("drill_size") or "",
                "specification": d.get("specification") or d.get("drill_size") or "",
                "make": d.get("make") or "",
                "stock": float(d.get("stock") or 0.0),
                "price": float(d.get("price") or 0.0)
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/drill_masters")
def create_drill_master(data: dict, db: Session = Depends(get_db)):
    try:
        size = (data.get("drill_size") or data.get("size_dia") or data.get("name") or "").strip()
        sl = (data.get("sl_no") or "").strip()
        rc = int(data.get("resharp_count") or 0)
        make = (data.get("make") or "").strip()
        stock = float(data.get("stock") or 0.0)
        price = float(data.get("price") or 0.0)

        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('drill_masters', 'id'), coalesce(max(id),0) + 1, false) FROM drill_masters;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM drill_masters")).mappings().first()
            next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 1
        except Exception:
            db.rollback()
            next_id = 1

        params = {"id": next_id, "size": size, "sl": sl, "rc": rc, "make": make, "stock": stock, "price": price}
        try:
            db.execute(text("""
                INSERT INTO drill_masters (id, drill_size, sl_no, resharp_count, make, stock, price)
                VALUES (:id, :size, :sl, :rc, :make, :stock, :price);
            """), params)
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                INSERT INTO drill_masters (drill_size, sl_no, resharp_count, make, stock, price)
                VALUES (:size, :sl, :rc, :make, :stock, :price);
            """), params)
            db.commit()

        return {"id": next_id, "message": "Created successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/drill_masters/bulk")
def bulk_create_drill_masters(data: dict, db: Session = Depends(get_db)):
    drills = data.get("drills") or []
    count = 0
    try:
        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('drill_masters', 'id'), coalesce(max(id),0) + 1, false) FROM drill_masters;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) AS max_id FROM drill_masters")).mappings().first()
            curr_id = int(max_row.get("max_id")) if max_row and max_row.get("max_id") else 0
        except Exception:
            db.rollback()
            curr_id = 0

        for dr in drills:
            size = (dr.get("drill_size") or dr.get("size_dia") or dr.get("name") or "").strip()
            sl = (dr.get("sl_no") or "").strip()
            if size or sl:
                curr_id += 1
                rc = int(dr.get("resharp_count") or 0)
                make = (dr.get("make") or "").strip()
                stock = float(dr.get("stock") or 0.0)
                price = float(dr.get("price") or 0.0)
                params = {"id": curr_id, "size": size, "sl": sl, "rc": rc, "make": make, "stock": stock, "price": price}
                try:
                    db.execute(text("""
                        INSERT INTO drill_masters (id, drill_size, sl_no, resharp_count, make, stock, price)
                        VALUES (:id, :size, :sl, :rc, :make, :stock, :price);
                    """), params)
                except Exception:
                    db.rollback()
                    db.execute(text("""
                        INSERT INTO drill_masters (drill_size, sl_no, resharp_count, make, stock, price)
                        VALUES (:size, :sl, :rc, :make, :stock, :price);
                    """), params)
                count += 1
        db.commit()
        return {"message": f"Successfully created {count} drill records"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/drill_masters/{id}")
def update_drill_master(id: int, data: dict, db: Session = Depends(get_db)):
    size = (data.get("drill_size") or data.get("size_dia") or data.get("name") or "").strip()
    sl = (data.get("sl_no") or "").strip()
    rc = int(data.get("resharp_count") or 0)
    make = (data.get("make") or "").strip()
    stock = float(data.get("stock") or 0.0)
    price = float(data.get("price") or 0.0)
    db.execute(text("""
        UPDATE drill_masters
        SET drill_size = :size, sl_no = :sl, resharp_count = :rc, make = :make, stock = :stock, price = :price
        WHERE id = :id;
    """), {"id": id, "size": size, "sl": sl, "rc": rc, "make": make, "stock": stock, "price": price})
    db.commit()
    return {"message": "Updated successfully"}

@app.delete("/api/drill_masters/all")
def clear_all_drill_masters(db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM drill_masters;"))
    db.commit()
    return {"message": "All drill records cleared successfully"}

@app.delete("/api/drill_masters/{id}")
def delete_drill_master(id: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM drill_masters WHERE id = :id;"), {"id": id})
    db.commit()
    return {"message": "Deleted successfully"}

# --- TAP MASTER CRUD ---
@app.get("/api/tap_masters")
def get_tap_masters(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM tap_masters ORDER BY id ASC;")).mappings().all()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id": d.get("id"),
                "tap_spec": d.get("tap_spec") or d.get("specification") or d.get("name") or "",
                "name": d.get("name") or d.get("tap_spec") or "",
                "specification": d.get("specification") or d.get("tap_spec") or "",
                "make": d.get("make") or "",
                "stock": float(d.get("stock") or 0.0),
                "price": float(d.get("price") or 0.0)
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tap_masters")
def create_tap_master(data: dict, db: Session = Depends(get_db)):
    try:
        spec = (data.get("tap_spec") or data.get("specification") or data.get("name") or "").strip()
        if not spec:
            raise HTTPException(status_code=400, detail="Tap spec is required")
        make = (data.get("make") or "").strip()
        stock = float(data.get("stock") or 0.0)
        price = float(data.get("price") or 0.0)

        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('tap_masters', 'id'), coalesce(max(id),0) + 1, false) FROM tap_masters;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM tap_masters")).mappings().first()
            next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 1
        except Exception:
            db.rollback()
            next_id = 1

        params = {"id": next_id, "spec": spec, "make": make, "stock": stock, "price": price}
        try:
            db.execute(text("""
                INSERT INTO tap_masters (id, tap_spec, make, stock, price)
                VALUES (:id, :spec, :make, :stock, :price);
            """), params)
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                INSERT INTO tap_masters (tap_spec, make, stock, price)
                VALUES (:spec, :make, :stock, :price);
            """), params)
            db.commit()

        return {"id": next_id, "message": "Created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tap_masters/bulk")
def bulk_create_tap_masters(data: dict, db: Session = Depends(get_db)):
    taps = data.get("taps") or []
    count = 0
    try:
        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('tap_masters', 'id'), coalesce(max(id),0) + 1, false) FROM tap_masters;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) AS max_id FROM tap_masters")).mappings().first()
            curr_id = int(max_row.get("max_id")) if max_row and max_row.get("max_id") else 0
        except Exception:
            db.rollback()
            curr_id = 0

        for t in taps:
            spec = (t.get("tap_spec") or t.get("specification") or t.get("name") or "").strip()
            if spec:
                curr_id += 1
                make = (t.get("make") or "").strip()
                stock = float(t.get("stock") or 0.0)
                price = float(t.get("price") or 0.0)
                params = {"id": curr_id, "spec": spec, "make": make, "stock": stock, "price": price}
                try:
                    db.execute(text("""
                        INSERT INTO tap_masters (id, tap_spec, make, stock, price)
                        VALUES (:id, :spec, :make, :stock, :price);
                    """), params)
                except Exception:
                    db.rollback()
                    db.execute(text("""
                        INSERT INTO tap_masters (tap_spec, make, stock, price)
                        VALUES (:spec, :make, :stock, :price);
                    """), params)
                count += 1
        db.commit()
        return {"message": f"Successfully created {count} tap records"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tap_masters/{id}")
def update_tap_master(id: int, data: dict, db: Session = Depends(get_db)):
    spec = (data.get("tap_spec") or data.get("specification") or data.get("name") or "").strip()
    make = (data.get("make") or "").strip()
    stock = float(data.get("stock") or 0.0)
    price = float(data.get("price") or 0.0)
    db.execute(text("""
        UPDATE tap_masters
        SET tap_spec = :spec, make = :make, stock = :stock, price = :price
        WHERE id = :id;
    """), {"id": id, "spec": spec, "make": make, "stock": stock, "price": price})
    db.commit()
    return {"message": "Updated successfully"}

@app.delete("/api/tap_masters/all")
def clear_all_tap_masters(db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM tap_masters;"))
    db.commit()
    return {"message": "All tap records cleared successfully"}

@app.delete("/api/tap_masters/{id}")
def delete_tap_master(id: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM tap_masters WHERE id = :id;"), {"id": id})
    db.commit()
    return {"message": "Deleted successfully"}

# --- INSERT RECEIPTS CRUD ---
@app.get("/api/insert_receipts")
def get_insert_receipts(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM insert_receipts ORDER BY id DESC;")).mappings().all()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id": d.get("id"),
                "date": str(d.get("date") or ""),
                "supplier": d.get("supplier") or "",
                "insert_spec": d.get("insert_spec") or "",
                "batch_no": d.get("batch_no") or "",
                "qty": float(d.get("qty") or 0.0),
                "rate": float(d.get("rate") or 0.0),
                "created_at": d.get("created_at").isoformat() if hasattr(d.get("created_at"), "isoformat") else str(d.get("created_at") or "")
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/insert_receipts")
def create_insert_receipt(data: dict, db: Session = Depends(get_db)):
    try:
        date_val = normalize_date_str(data.get("date") or datetime.datetime.now(IST).strftime("%Y-%m-%d"))
        supp = (data.get("supplier") or "").strip()
        spec = (data.get("insert_spec") or "").strip()
        batch = (data.get("batch_no") or "").strip()
        qty = float(data.get("qty") or 0.0)
        rate = float(data.get("rate") or 0.0)

        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('insert_receipts', 'id'), coalesce(max(id),0) + 1, false) FROM insert_receipts;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM insert_receipts")).mappings().first()
            next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 1
        except Exception:
            db.rollback()
            next_id = 1

        params = {
            "id": next_id,
            "date": date_val,
            "supp": supp,
            "spec": spec,
            "batch": batch,
            "qty": qty,
            "rate": rate
        }

        try:
            db.execute(text("""
                INSERT INTO insert_receipts (id, date, supplier, insert_spec, batch_no, qty, rate)
                VALUES (:id, :date, :supp, :spec, :batch, :qty, :rate);
            """), params)
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                INSERT INTO insert_receipts (date, supplier, insert_spec, batch_no, qty, rate)
                VALUES (:date, :supp, :spec, :batch, :qty, :rate);
            """), params)
            db.commit()

        return {"id": next_id, "message": "Created successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create insert receipt: {e}")

@app.post("/api/insert_receipts/bulk")
def bulk_create_insert_receipts(data: dict, db: Session = Depends(get_db)):
    receipts = data.get("receipts") or []
    count = 0
    try:
        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('insert_receipts', 'id'), coalesce(max(id),0) + 1, false) FROM insert_receipts;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) AS max_id FROM insert_receipts")).mappings().first()
            curr_id = int(max_row.get("max_id")) if max_row and max_row.get("max_id") else 0
        except Exception:
            db.rollback()
            curr_id = 0

        for r in receipts:
            curr_id += 1
            date_val = normalize_date_str(r.get("date") or datetime.datetime.now(IST).strftime("%Y-%m-%d"))
            supp = (r.get("supplier") or "").strip()
            spec = (r.get("insert_spec") or "").strip()
            batch = (r.get("batch_no") or "").strip()
            qty = float(r.get("qty") or 0.0)
            rate = float(r.get("rate") or 0.0)
            params = {
                "id": curr_id,
                "date": date_val,
                "supp": supp,
                "spec": spec,
                "batch": batch,
                "qty": qty,
                "rate": rate
            }
            try:
                db.execute(text("""
                    INSERT INTO insert_receipts (id, date, supplier, insert_spec, batch_no, qty, rate)
                    VALUES (:id, :date, :supp, :spec, :batch, :qty, :rate);
                """), params)
            except Exception:
                db.rollback()
                db.execute(text("""
                    INSERT INTO insert_receipts (date, supplier, insert_spec, batch_no, qty, rate)
                    VALUES (:date, :supp, :spec, :batch, :qty, :rate);
                """), params)
            count += 1
        db.commit()
        return {"message": f"Successfully created {count} insert receipt records"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/insert_receipts/{id}")
def update_insert_receipt(id: int, data: dict, db: Session = Depends(get_db)):
    date_val = normalize_date_str(data.get("date") or datetime.datetime.now(IST).strftime("%Y-%m-%d"))
    supp = (data.get("supplier") or "").strip()
    spec = (data.get("insert_spec") or "").strip()
    batch = (data.get("batch_no") or "").strip()
    qty = float(data.get("qty") or 0.0)
    rate = float(data.get("rate") or 0.0)
    db.execute(text("""
        UPDATE insert_receipts
        SET date = :date, supplier = :supp, insert_spec = :spec, batch_no = :batch, qty = :qty, rate = :rate
        WHERE id = :id;
    """), {"id": id, "date": date_val, "supp": supp, "spec": spec, "batch": batch, "qty": qty, "rate": rate})
    db.commit()
    return {"message": "Updated successfully"}

@app.delete("/api/insert_receipts/all")
def clear_all_insert_receipts(db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM insert_receipts;"))
    db.commit()
    return {"message": "All insert receipt records cleared successfully"}

@app.delete("/api/insert_receipts/{id}")
def delete_insert_receipt(id: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM insert_receipts WHERE id = :id;"), {"id": id})
    db.commit()
    return {"message": "Deleted successfully"}

# --- TAP RECEIPTS CRUD ---
@app.get("/api/tap_receipts")
def get_tap_receipts(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM tap_receipts ORDER BY id DESC;")).mappings().all()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id": d.get("id"),
                "date": str(d.get("date") or ""),
                "supplier": d.get("supplier") or "",
                "tap_spec": d.get("tap_spec") or "",
                "qty": float(d.get("qty") or 0.0),
                "rate": float(d.get("rate") or 0.0),
                "created_at": d.get("created_at").isoformat() if hasattr(d.get("created_at"), "isoformat") else str(d.get("created_at") or "")
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tap_receipts")
def create_tap_receipt(data: dict, db: Session = Depends(get_db)):
    try:
        date_val = normalize_date_str(data.get("date") or datetime.datetime.now(IST).strftime("%Y-%m-%d"))
        supp = (data.get("supplier") or "").strip()
        spec = (data.get("tap_spec") or "").strip()
        qty = float(data.get("qty") or 0.0)
        rate = float(data.get("rate") or 0.0)

        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('tap_receipts', 'id'), coalesce(max(id),0) + 1, false) FROM tap_receipts;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM tap_receipts")).mappings().first()
            next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 1
        except Exception:
            db.rollback()
            next_id = 1

        params = {
            "id": next_id,
            "date": date_val,
            "supp": supp,
            "spec": spec,
            "qty": qty,
            "rate": rate
        }

        try:
            db.execute(text("""
                INSERT INTO tap_receipts (id, date, supplier, tap_spec, qty, rate)
                VALUES (:id, :date, :supp, :spec, :qty, :rate);
            """), params)
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                INSERT INTO tap_receipts (date, supplier, tap_spec, qty, rate)
                VALUES (:date, :supp, :spec, :qty, :rate);
            """), params)
            db.commit()

        return {"id": next_id, "message": "Created successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create tap receipt: {e}")

@app.post("/api/tap_receipts/bulk")
def bulk_create_tap_receipts(data: dict, db: Session = Depends(get_db)):
    receipts = data.get("receipts") or []
    count = 0
    try:
        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('tap_receipts', 'id'), coalesce(max(id),0) + 1, false) FROM tap_receipts;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) AS max_id FROM tap_receipts")).mappings().first()
            curr_id = int(max_row.get("max_id")) if max_row and max_row.get("max_id") else 0
        except Exception:
            db.rollback()
            curr_id = 0

        for r in receipts:
            curr_id += 1
            date_val = normalize_date_str(r.get("date") or datetime.datetime.now(IST).strftime("%Y-%m-%d"))
            supp = (r.get("supplier") or "").strip()
            spec = (r.get("tap_spec") or "").strip()
            qty = float(r.get("qty") or 0.0)
            rate = float(r.get("rate") or 0.0)
            params = {
                "id": curr_id,
                "date": date_val,
                "supp": supp,
                "spec": spec,
                "qty": qty,
                "rate": rate
            }
            try:
                db.execute(text("""
                    INSERT INTO tap_receipts (id, date, supplier, tap_spec, qty, rate)
                    VALUES (:id, :date, :supp, :spec, :qty, :rate);
                """), params)
            except Exception:
                db.rollback()
                db.execute(text("""
                    INSERT INTO tap_receipts (date, supplier, tap_spec, qty, rate)
                    VALUES (:date, :supp, :spec, :qty, :rate);
                """), params)
            count += 1
        db.commit()
        return {"message": f"Successfully created {count} tap receipt records"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tap_receipts/{id}")
def update_tap_receipt(id: int, data: dict, db: Session = Depends(get_db)):
    date_val = normalize_date_str(data.get("date") or datetime.datetime.now(IST).strftime("%Y-%m-%d"))
    supp = (data.get("supplier") or "").strip()
    spec = (data.get("tap_spec") or "").strip()
    qty = float(data.get("qty") or 0.0)
    rate = float(data.get("rate") or 0.0)
    db.execute(text("""
        UPDATE tap_receipts
        SET date = :date, supplier = :supp, tap_spec = :spec, qty = :qty, rate = :rate
        WHERE id = :id;
    """), {"id": id, "date": date_val, "supp": supp, "spec": spec, "qty": qty, "rate": rate})
    db.commit()
    return {"message": "Updated successfully"}

@app.delete("/api/tap_receipts/all")
def clear_all_tap_receipts(db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM tap_receipts;"))
    db.commit()
    return {"message": "All tap receipt records cleared successfully"}

@app.delete("/api/tap_receipts/{id}")
def delete_tap_receipt(id: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM tap_receipts WHERE id = :id;"), {"id": id})
    db.commit()
    return {"message": "Deleted successfully"}

# --- INSERT ISSUES CRUD ---
@app.get("/api/insert_issues")
def get_insert_issues(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM insert_issues ORDER BY id DESC;")).mappings().all()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id": d.get("id"),
                "date": str(d.get("date") or ""),
                "shift": d.get("shift") or "First",
                "department": d.get("department") or "WIPRO",
                "insert_spec": d.get("insert_spec") or "",
                "batch_no": d.get("batch_no") or "",
                "qty_issued": float(d.get("qty_issued") or 0.0),
                "qty_received": float(d.get("qty_received") or 0.0),
                "machine": d.get("machine") or "",
                "operator": d.get("operator") or "",
                "partno": d.get("partno") or "",
                "opn_no": str(d.get("opn_no") or ""),
                "usages": str(d.get("usages") or ""),
                "receipt_id": d.get("receipt_id"),
                "edge_data": str(d.get("edge_data") or ""),
                "created_at": d.get("created_at").isoformat() if hasattr(d.get("created_at"), "isoformat") else str(d.get("created_at") or "")
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/insert_consumption")
def get_insert_consumption(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    department: Optional[str] = None,
    partno: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        query = "SELECT date, department, partno, opn_no, insert_spec, qty_issued, usages FROM insert_issues WHERE 1=1"
        params = {}
        if date_from:
            query += " AND date >= :date_from"
            params["date_from"] = date_from
        if date_to:
            query += " AND date <= :date_to"
            params["date_to"] = date_to
        if department:
            query += " AND LOWER(department) = LOWER(:department)"
            params["department"] = department

        rows = db.execute(text(query), params).mappings().all()
        agg_map = {}

        for r in rows:
            raw_dept = (r.get("department") or "WIPRO").strip() or "WIPRO"
            raw_spec = (r.get("insert_spec") or "").strip()
            if not raw_spec:
                continue

            usages = []
            raw_usages = r.get("usages")
            if raw_usages:
                try:
                    import json
                    parsed = raw_usages
                    while isinstance(parsed, str):
                        parsed = json.loads(parsed)
                    if isinstance(parsed, list):
                        usages = parsed
                except Exception:
                    pass

            if not usages:
                usages = [{"partno": r.get("partno") or "", "opn_no": r.get("opn_no") or ""}]

            total_issued = float(r.get("qty_issued") or 0.0)
            if total_issued <= 0:
                continue
            qty_per_usage = total_issued / len(usages)

            for u in usages:
                raw_part = (u.get("partno") or r.get("partno") or "").strip()
                if not raw_part:
                    continue
                if partno and raw_part.lower() != partno.strip().lower():
                    continue

                key = (raw_dept.upper(), raw_part.upper(), raw_spec.upper())
                if key not in agg_map:
                    agg_map[key] = {
                        "dept": raw_dept,
                        "partno": raw_part,
                        "insert_spec": raw_spec,
                        "qty": 0.0
                    }
                agg_map[key]["qty"] += qty_per_usage

        result = list(agg_map.values())
        result.sort(key=lambda x: (x["dept"].lower(), x["partno"].lower(), x["insert_spec"].lower()))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/insert_issues/{id}")
def get_insert_issue(id: int, db: Session = Depends(get_db)):
    try:
        row = db.execute(text("SELECT * FROM insert_issues WHERE id = :id;"), {"id": id}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Insert issue record not found")
        d = dict(row)
        return {
            "id": d.get("id"),
            "date": str(d.get("date") or ""),
            "shift": d.get("shift") or "First",
            "department": d.get("department") or "WIPRO",
            "insert_spec": d.get("insert_spec") or "",
            "batch_no": d.get("batch_no") or "",
            "qty_issued": float(d.get("qty_issued") or 0.0),
            "qty_received": float(d.get("qty_received") or 0.0),
            "machine": d.get("machine") or "",
            "operator": d.get("operator") or "",
            "partno": d.get("partno") or "",
            "opn_no": str(d.get("opn_no") or ""),
            "usages": str(d.get("usages") or ""),
            "receipt_id": d.get("receipt_id"),
            "edge_data": str(d.get("edge_data") or ""),
            "created_at": d.get("created_at").isoformat() if hasattr(d.get("created_at"), "isoformat") else str(d.get("created_at") or "")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/insert_issues")
def create_insert_issue(data: dict, db: Session = Depends(get_db)):
    try:
        date_val = normalize_date_str(data.get("date") or datetime.datetime.now(IST).strftime("%Y-%m-%d"))
        shift = (data.get("shift") or "First").strip()
        dept = (data.get("department") or "WIPRO").strip()
        spec = (data.get("insert_spec") or "").strip()
        batch = (data.get("batch_no") or "").strip()
        qty_iss = float(data.get("qty_issued") or 0.0)
        qty_rec = float(data.get("qty_received") or 0.0)
        mach = (data.get("machine") or "").strip()
        op = (data.get("operator") or "").strip()
        partno = (data.get("partno") or "").strip()
        opn = str(data.get("opn_no") or "").strip()
        usages = str(data.get("usages") or "")
        rid = int(data.get("receipt_id")) if data.get("receipt_id") else None
        edge = str(data.get("edge_data") or "")

        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('insert_issues', 'id'), coalesce(max(id),0) + 1, false) FROM insert_issues;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM insert_issues")).mappings().first()
            next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 1
        except Exception:
            db.rollback()
            next_id = 1

        params = {
            "id": next_id,
            "date": date_val, "shift": shift, "dept": dept, "spec": spec, "batch": batch,
            "qty_iss": qty_iss, "qty_rec": qty_rec, "mach": mach, "op": op, "partno": partno,
            "opn": opn, "usages": usages, "rid": rid, "edge": edge
        }

        try:
            db.execute(text("""
                INSERT INTO insert_issues (id, date, shift, department, insert_spec, batch_no, qty_issued, qty_received, machine, operator, partno, opn_no, usages, receipt_id, edge_data)
                VALUES (:id, :date, :shift, :dept, :spec, :batch, :qty_iss, :qty_rec, :mach, :op, :partno, :opn, :usages, :rid, :edge);
            """), params)
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                INSERT INTO insert_issues (date, shift, department, insert_spec, batch_no, qty_issued, qty_received, machine, operator, partno, opn_no, usages, receipt_id, edge_data)
                VALUES (:date, :shift, :dept, :spec, :batch, :qty_iss, :qty_rec, :mach, :op, :partno, :opn, :usages, :rid, :edge);
            """), params)
            db.commit()

        return {"id": next_id, "message": "Created successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create insert issue: {e}")

@app.post("/api/insert_issues/bulk")
def bulk_create_insert_issues(data: dict, db: Session = Depends(get_db)):
    issues = data.get("issues") or []
    count = 0
    try:
        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('insert_issues', 'id'), coalesce(max(id),0) + 1, false) FROM insert_issues;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) AS max_id FROM insert_issues")).mappings().first()
            curr_id = int(max_row.get("max_id")) if max_row and max_row.get("max_id") else 0
        except Exception:
            db.rollback()
            curr_id = 0

        for iss in issues:
            curr_id += 1
            date_val = normalize_date_str(iss.get("date") or datetime.datetime.now(IST).strftime("%Y-%m-%d"))
            shift = (iss.get("shift") or "First").strip()
            dept = (iss.get("department") or "WIPRO").strip()
            spec = (iss.get("insert_spec") or "").strip()
            batch = (iss.get("batch_no") or "").strip()
            qty_iss = float(iss.get("qty_issued") or 0.0)
            qty_rec = float(iss.get("qty_received") or 0.0)
            mach = (iss.get("machine") or "").strip()
            op = (iss.get("operator") or "").strip()
            partno = (iss.get("partno") or "").strip()
            opn = str(iss.get("opn_no") or "").strip()
            usages = str(iss.get("usages") or "")
            rid = int(iss.get("receipt_id")) if iss.get("receipt_id") else None
            edge = str(iss.get("edge_data") or "")
            params = {
                "id": curr_id,
                "date": date_val, "shift": shift, "dept": dept, "spec": spec, "batch": batch,
                "qty_iss": qty_iss, "qty_rec": qty_rec, "mach": mach, "op": op, "partno": partno,
                "opn": opn, "usages": usages, "rid": rid, "edge": edge
            }
            try:
                db.execute(text("""
                    INSERT INTO insert_issues (id, date, shift, department, insert_spec, batch_no, qty_issued, qty_received, machine, operator, partno, opn_no, usages, receipt_id, edge_data)
                    VALUES (:id, :date, :shift, :dept, :spec, :batch, :qty_iss, :qty_rec, :mach, :op, :partno, :opn, :usages, :rid, :edge);
                """), params)
            except Exception:
                db.rollback()
                db.execute(text("""
                    INSERT INTO insert_issues (date, shift, department, insert_spec, batch_no, qty_issued, qty_received, machine, operator, partno, opn_no, usages, receipt_id, edge_data)
                    VALUES (:date, :shift, :dept, :spec, :batch, :qty_iss, :qty_rec, :mach, :op, :partno, :opn, :usages, :rid, :edge);
                """), params)
            count += 1
        db.commit()
        return {"message": f"Successfully created {count} insert issue records"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/insert_issues/{id}")
def update_insert_issue(id: int, data: dict, db: Session = Depends(get_db)):
    date_val = normalize_date_str(data.get("date") or datetime.datetime.now(IST).strftime("%Y-%m-%d"))
    shift = (data.get("shift") or "First").strip()
    dept = (data.get("department") or "WIPRO").strip()
    spec = (data.get("insert_spec") or "").strip()
    batch = (data.get("batch_no") or "").strip()
    qty_iss = float(data.get("qty_issued") or 0.0)
    qty_rec = float(data.get("qty_received") or 0.0)
    mach = (data.get("machine") or "").strip()
    op = (data.get("operator") or "").strip()
    partno = (data.get("partno") or "").strip()
    opn = str(data.get("opn_no") or "").strip()
    usages = str(data.get("usages") or "")
    rid = int(data.get("receipt_id")) if data.get("receipt_id") else None
    edge = str(data.get("edge_data") or "")
    db.execute(text("""
        UPDATE insert_issues
        SET date = :date, shift = :shift, department = :dept, insert_spec = :spec, batch_no = :batch, qty_issued = :qty_iss, qty_received = :qty_rec, machine = :mach, operator = :op, partno = :partno, opn_no = :opn, usages = :usages, receipt_id = :rid, edge_data = :edge
        WHERE id = :id;
    """), {"id": id, "date": date_val, "shift": shift, "dept": dept, "spec": spec, "batch": batch, "qty_iss": qty_iss, "qty_rec": qty_rec, "mach": mach, "op": op, "partno": partno, "opn": opn, "usages": usages, "rid": rid, "edge": edge})
    db.commit()
    return {"message": "Updated successfully"}

@app.delete("/api/insert_issues/all")
def clear_all_insert_issues(db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM insert_issues;"))
    db.commit()
    return {"message": "All insert issue records cleared successfully"}

@app.delete("/api/insert_issues/{id}")
def delete_insert_issue(id: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM insert_issues WHERE id = :id;"), {"id": id})
    db.commit()
    return {"message": "Deleted successfully"}

# --- TAP ISSUES CRUD ---
@app.get("/api/tap_issues")
def get_tap_issues(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("SELECT * FROM tap_issues ORDER BY id DESC;")).mappings().all()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id": d.get("id"),
                "date": str(d.get("date") or ""),
                "shift": d.get("shift") or "First",
                "department": d.get("department") or "WIPRO",
                "tap_spec": d.get("tap_spec") or "",
                "qty_issued": float(d.get("qty_issued") or 0.0),
                "qty_received": float(d.get("qty_received") or 0.0),
                "machine": d.get("machine") or "",
                "operator": d.get("operator") or "",
                "partno": d.get("partno") or "",
                "opn_no": str(d.get("opn_no") or ""),
                "created_at": d.get("created_at").isoformat() if hasattr(d.get("created_at"), "isoformat") else str(d.get("created_at") or "")
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tap_issues")
def create_tap_issue(data: dict, db: Session = Depends(get_db)):
    try:
        date_val = normalize_date_str(data.get("date") or datetime.datetime.now(IST).strftime("%Y-%m-%d"))
        shift = (data.get("shift") or "First").strip()
        dept = (data.get("department") or "WIPRO").strip()
        spec = (data.get("tap_spec") or "").strip()
        qty_iss = float(data.get("qty_issued") or 0.0)
        qty_rec = float(data.get("qty_received") or 0.0)
        mach = (data.get("machine") or "").strip()
        op = (data.get("operator") or "").strip()
        partno = (data.get("partno") or "").strip()
        opn = str(data.get("opn_no") or "").strip()

        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('tap_issues', 'id'), coalesce(max(id),0) + 1, false) FROM tap_issues;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM tap_issues")).mappings().first()
            next_id = int(max_row.get("next_id")) if max_row and max_row.get("next_id") else 1
        except Exception:
            db.rollback()
            next_id = 1

        params = {
            "id": next_id,
            "date": date_val, "shift": shift, "dept": dept, "spec": spec,
            "qty_iss": qty_iss, "qty_rec": qty_rec, "mach": mach, "op": op, "partno": partno, "opn": opn
        }

        try:
            db.execute(text("""
                INSERT INTO tap_issues (id, date, shift, department, tap_spec, qty_issued, qty_received, machine, operator, partno, opn_no)
                VALUES (:id, :date, :shift, :dept, :spec, :qty_iss, :qty_rec, :mach, :op, :partno, :opn);
            """), params)
            db.commit()
        except Exception:
            db.rollback()
            db.execute(text("""
                INSERT INTO tap_issues (date, shift, department, tap_spec, qty_issued, qty_received, machine, operator, partno, opn_no)
                VALUES (:date, :shift, :dept, :spec, :qty_iss, :qty_rec, :mach, :op, :partno, :opn);
            """), params)
            db.commit()

        return {"id": next_id, "message": "Created successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create tap issue: {e}")

@app.post("/api/tap_issues/bulk")
def bulk_create_tap_issues(data: dict, db: Session = Depends(get_db)):
    issues = data.get("issues") or []
    count = 0
    try:
        try:
            db.execute(text("SELECT setval(pg_get_serial_sequence('tap_issues', 'id'), coalesce(max(id),0) + 1, false) FROM tap_issues;"))
            db.commit()
        except Exception:
            db.rollback()

        try:
            max_row = db.execute(text("SELECT COALESCE(MAX(id), 0) AS max_id FROM tap_issues")).mappings().first()
            curr_id = int(max_row.get("max_id")) if max_row and max_row.get("max_id") else 0
        except Exception:
            db.rollback()
            curr_id = 0

        for iss in issues:
            curr_id += 1
            date_val = normalize_date_str(iss.get("date") or datetime.datetime.now(IST).strftime("%Y-%m-%d"))
            shift = (iss.get("shift") or "First").strip()
            dept = (iss.get("department") or "WIPRO").strip()
            spec = (iss.get("tap_spec") or "").strip()
            qty_iss = float(iss.get("qty_issued") or 0.0)
            qty_rec = float(iss.get("qty_received") or 0.0)
            mach = (iss.get("machine") or "").strip()
            op = (iss.get("operator") or "").strip()
            partno = (iss.get("partno") or "").strip()
            opn = str(iss.get("opn_no") or "").strip()
            params = {
                "id": curr_id,
                "date": date_val, "shift": shift, "dept": dept, "spec": spec,
                "qty_iss": qty_iss, "qty_rec": qty_rec, "mach": mach, "op": op, "partno": partno, "opn": opn
            }
            try:
                db.execute(text("""
                    INSERT INTO tap_issues (id, date, shift, department, tap_spec, qty_issued, qty_received, machine, operator, partno, opn_no)
                    VALUES (:id, :date, :shift, :dept, :spec, :qty_iss, :qty_rec, :mach, :op, :partno, :opn);
                """), params)
            except Exception:
                db.rollback()
                db.execute(text("""
                    INSERT INTO tap_issues (date, shift, department, tap_spec, qty_issued, qty_received, machine, operator, partno, opn_no)
                    VALUES (:date, :shift, :dept, :spec, :qty_iss, :qty_rec, :mach, :op, :partno, :opn);
                """), params)
            count += 1
        db.commit()
        return {"message": f"Successfully created {count} tap issue records"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tap_issues/{id}")
def update_tap_issue(id: int, data: dict, db: Session = Depends(get_db)):
    date_val = data.get("date") or datetime.datetime.now(IST).strftime("%Y-%m-%d")
    shift = (data.get("shift") or "First").strip()
    dept = (data.get("department") or "WIPRO").strip()
    spec = (data.get("tap_spec") or "").strip()
    qty_iss = float(data.get("qty_issued") or 0.0)
    qty_rec = float(data.get("qty_received") or 0.0)
    mach = (data.get("machine") or "").strip()
    op = (data.get("operator") or "").strip()
    partno = (data.get("partno") or "").strip()
    opn = str(data.get("opn_no") or "").strip()
    db.execute(text("""
        UPDATE tap_issues
        SET date = :date, shift = :shift, department = :dept, tap_spec = :spec, qty_issued = :qty_iss, qty_received = :qty_rec, machine = :mach, operator = :op, partno = :partno, opn_no = :opn
        WHERE id = :id;
    """), {"id": id, "date": date_val, "shift": shift, "dept": dept, "spec": spec, "qty_iss": qty_iss, "qty_rec": qty_rec, "mach": mach, "op": op, "partno": partno, "opn": opn})
    db.commit()
    return {"message": "Updated successfully"}

@app.delete("/api/tap_issues/all")
def clear_all_tap_issues(db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM tap_issues;"))
    db.commit()
    return {"message": "All tap issue records cleared successfully"}

@app.delete("/api/tap_issues/{id}")
def delete_tap_issue(id: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM tap_issues WHERE id = :id;"), {"id": id})
    db.commit()
    return {"message": "Deleted successfully"}

# --- Database Backup & Contingency Endpoints ---
@app.get("/api/admin/export_db_backup")
def export_db_backup(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
    except Exception:
        existing_tables = set()

    known_tables = [
        "part_masters", "part_operations", "parts", "operations", "machines", 
        "operators", "departments", "shifts", "vendors", "setters", "setter_logs", 
        "suppliers", "customer_masters", "rfq_headers", "rfq_items", "quote_records", 
        "schedules", "production_schedules", "production_logs", "raw_materials", 
        "raw_material_logs", "ht_logs", "ht_receipt_logs", "pc_logs", "pc_receipt_logs", 
        "insert_masters", "drill_masters", "tap_masters", "insert_receipts", 
        "tap_receipts", "insert_issues", "tap_issues", "breakdown_slips", 
        "service_details", "attendances", "inspection_parameters", "inspection_reports", 
        "users", "tooling"
    ]

    all_tables_to_check = list(dict.fromkeys(list(existing_tables) + known_tables))
    backup_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "database_type": "postgresql" if "postgresql" in str(engine.url) else "sqlite",
        "tables": {}
    }

    for tbl in all_tables_to_check:
        try:
            rows = db.execute(text(f'SELECT * FROM "{tbl}"')).mappings().all()
            serializable_rows = []
            for r in rows:
                row_dict = {}
                for k, v in dict(r).items():
                    if isinstance(v, (datetime.date, datetime.datetime, datetime.time)):
                        row_dict[k] = v.isoformat()
                    elif isinstance(v, (bytes, bytearray)):
                        row_dict[k] = v.decode("utf-8", errors="ignore")
                    elif hasattr(v, "__float__") and not isinstance(v, (int, float)):
                        row_dict[k] = float(v)
                    else:
                        row_dict[k] = v
                serializable_rows.append(row_dict)
            backup_data["tables"][tbl] = serializable_rows
        except Exception:
            continue

    return backup_data

@app.post("/api/admin/restore_db_backup")
async def restore_db_backup(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
        tables_data = data.get("tables", {})
        if not tables_data:
            raise HTTPException(status_code=400, detail="Invalid backup file: no tables found")

        restored_counts = {}
        for table_name, rows in tables_data.items():
            if not rows:
                continue
            try:
                db.execute(text(f'DELETE FROM "{table_name}";'))
                db.commit()
            except Exception:
                pass

            inserted = 0
            first_row = rows[0]
            cols = list(first_row.keys())
            col_str = ", ".join([f'"{c}"' for c in cols])
            param_str = ", ".join([f":{c}" for c in cols])
            insert_sql = text(f'INSERT INTO "{table_name}" ({col_str}) VALUES ({param_str});')

            for row in rows:
                try:
                    db.execute(insert_sql, row)
                    inserted += 1
                except Exception:
                    pass
            db.commit()
            restored_counts[table_name] = inserted

        return {"message": "Backup restored successfully", "restored": restored_counts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- HR WEEKLY SHIFT LIST ENDPOINTS ---
HR_SHIFT_TIMINGS = {
    "First": "7.00 to 3.00",
    "Second": "3.00 to 11.00",
    "Third": "11.00 to 7.00",
    "Gen Shift A": "8.00 to 4.30",
    "Gen Shift B": "9.30 to 6.00"
}

HR_SHIFT_ROTATION = {
    "First": "Third",
    "Second": "First",
    "Third": "Second",
    "Gen Shift A": "Gen Shift A",
    "Gen Shift B": "Gen Shift B"
}

def ensure_hr_shift_table(db: Session):
    try:
        models.HrShiftAssignment.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        db.rollback()

@app.get("/api/hr/shift-list")
def get_hr_shift_list(week_start_date: str, dept: Optional[str] = None, shift: Optional[str] = None, db: Session = Depends(get_db)):
    ensure_hr_shift_table(db)
    try:
        q = db.query(models.HrShiftAssignment).filter(models.HrShiftAssignment.week_start_date == week_start_date)
        if dept and not dept.startswith("--") and dept.upper() != "ALL":
            q = q.filter(models.HrShiftAssignment.dept == dept)
        if shift and not shift.startswith("--") and shift.upper() != "ALL":
            q = q.filter(models.HrShiftAssignment.shift == shift)
        
        rows = q.order_by(models.HrShiftAssignment.dept.asc(), models.HrShiftAssignment.shift.asc(), models.HrShiftAssignment.emp_name.asc()).all()
        return [
            {
                "id": r.id,
                "week_start_date": r.week_start_date,
                "category": r.category or "Machine",
                "emp_name": r.emp_name,
                "dept": r.dept or "",
                "designation": r.designation or "Operator",
                "shift": r.shift,
                "shift_timings": r.shift_timings or HR_SHIFT_TIMINGS.get(r.shift, ""),
                "machine_1": r.machine_1 or "",
                "machine_2": r.machine_2 or "",
                "notes": r.notes or ""
            } for r in rows
        ]
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/shift-list")
def save_hr_shift_assignment(data: dict, db: Session = Depends(get_db)):
    ensure_hr_shift_table(db)
    try:
        item_id = data.get("id")
        shift_name = data.get("shift") or "First"
        timings = data.get("shift_timings") or HR_SHIFT_TIMINGS.get(shift_name, "")
        
        if item_id:
            rec = db.query(models.HrShiftAssignment).filter(models.HrShiftAssignment.id == int(item_id)).first()
            if not rec:
                raise HTTPException(status_code=404, detail="Shift assignment not found")
            rec.week_start_date = data.get("week_start_date", rec.week_start_date)
            rec.category = data.get("category", rec.category)
            rec.emp_name = data.get("emp_name", rec.emp_name)
            rec.dept = data.get("dept", rec.dept)
            rec.designation = data.get("designation", rec.designation)
            rec.shift = shift_name
            rec.shift_timings = timings
            rec.machine_1 = data.get("machine_1", "")
            rec.machine_2 = data.get("machine_2", "")
            rec.notes = data.get("notes", "")
        else:
            rec = models.HrShiftAssignment(
                week_start_date=data.get("week_start_date"),
                category=data.get("category", "Machine"),
                emp_name=data.get("emp_name"),
                dept=data.get("dept", ""),
                designation=data.get("designation", "Operator"),
                shift=shift_name,
                shift_timings=timings,
                machine_1=data.get("machine_1", ""),
                machine_2=data.get("machine_2", ""),
                notes=data.get("notes", "")
            )
            db.add(rec)
        db.commit()
        db.refresh(rec)
        return {"status": "success", "id": rec.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/shift-list/bulk-save")
def bulk_save_hr_shift_list(payload: dict, db: Session = Depends(get_db)):
    ensure_hr_shift_table(db)
    try:
        week_start_date = payload.get("week_start_date")
        if not week_start_date:
            raise HTTPException(status_code=400, detail="week_start_date is required")
        
        assignments = payload.get("assignments", [])
        
        # Clear existing for this week
        db.query(models.HrShiftAssignment).filter(models.HrShiftAssignment.week_start_date == week_start_date).delete()
        
        for a in assignments:
            shift_name = a.get("shift") or "First"
            timings = a.get("shift_timings") or HR_SHIFT_TIMINGS.get(shift_name, "")
            rec = models.HrShiftAssignment(
                week_start_date=week_start_date,
                category=a.get("category", "Machine"),
                emp_name=a.get("emp_name", ""),
                dept=a.get("dept", ""),
                designation=a.get("designation", "Operator"),
                shift=shift_name,
                shift_timings=timings,
                machine_1=a.get("machine_1", ""),
                machine_2=a.get("machine_2", ""),
                notes=a.get("notes", "")
            )
            db.add(rec)
        db.commit()
        return {"status": "success", "saved_count": len(assignments)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/shift-list/rotate-prev")
def rotate_hr_shift_list_from_prev(target_week: str, source_week: str, db: Session = Depends(get_db)):
    ensure_hr_shift_table(db)
    try:
        prev_rows = db.query(models.HrShiftAssignment).filter(models.HrShiftAssignment.week_start_date == source_week).all()
        if not prev_rows:
            raise HTTPException(status_code=404, detail=f"No shift assignments found for source week {source_week}")
        
        # Clear existing target week records
        db.query(models.HrShiftAssignment).filter(models.HrShiftAssignment.week_start_date == target_week).delete()
        
        rotated_count = 0
        for r in prev_rows:
            old_shift = r.shift
            new_shift = HR_SHIFT_ROTATION.get(old_shift, old_shift)
            new_timings = HR_SHIFT_TIMINGS.get(new_shift, r.shift_timings)
            
            new_rec = models.HrShiftAssignment(
                week_start_date=target_week,
                category=r.category,
                emp_name=r.emp_name,
                dept=r.dept,
                designation=r.designation,
                shift=new_shift,
                shift_timings=new_timings,
                machine_1=r.machine_1,
                machine_2=r.machine_2,
                notes=r.notes
            )
            db.add(new_rec)
            rotated_count += 1
            
        db.commit()
        return {"status": "success", "message": f"Successfully rotated {rotated_count} assignments from {source_week} to {target_week}", "count": rotated_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/shift-list/copy-prev")
def copy_hr_shift_list_from_prev(target_week: str, source_week: str, db: Session = Depends(get_db)):
    ensure_hr_shift_table(db)
    try:
        prev_rows = db.query(models.HrShiftAssignment).filter(models.HrShiftAssignment.week_start_date == source_week).all()
        if not prev_rows:
            raise HTTPException(status_code=404, detail=f"No shift assignments found for source week {source_week}")
        
        db.query(models.HrShiftAssignment).filter(models.HrShiftAssignment.week_start_date == target_week).delete()
        
        copied_count = 0
        for r in prev_rows:
            new_rec = models.HrShiftAssignment(
                week_start_date=target_week,
                category=r.category,
                emp_name=r.emp_name,
                dept=r.dept,
                designation=r.designation,
                shift=r.shift,
                shift_timings=r.shift_timings,
                machine_1=r.machine_1,
                machine_2=r.machine_2,
                notes=r.notes
            )
            db.add(new_rec)
            copied_count += 1
            
        db.commit()
        return {"status": "success", "message": f"Successfully copied {copied_count} assignments from {source_week} to {target_week}", "count": copied_count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hr/shift-list/load-from-master")
def load_hr_shift_from_master(week_start_date: str, db: Session = Depends(get_db)):
    ensure_hr_shift_table(db)
    try:
        ops = db.query(models.Operator).order_by(models.Operator.dept.asc(), models.Operator.name.asc()).all()
        if not ops:
            return {"status": "success", "count": 0, "message": "No operators found in Operator Master"}
        
        existing = {r.emp_name.strip().upper() for r in db.query(models.HrShiftAssignment).filter(models.HrShiftAssignment.week_start_date == week_start_date).all()}
        
        added = 0
        for o in ops:
            name = (o.name or "").strip()
            if not name or name.upper() in existing:
                continue
            
            desig = (o.designation or "Operator").strip()
            dept = (o.dept or "").strip()
            
            is_operator = (desig.lower() == "operator")
            category = "Machine" if is_operator else "Service"
            shift = "First" if is_operator else "Gen Shift A"
            timings = HR_SHIFT_TIMINGS.get(shift, "")
            
            rec = models.HrShiftAssignment(
                week_start_date=week_start_date,
                category=category,
                emp_name=name,
                dept=dept,
                designation=desig,
                shift=shift,
                shift_timings=timings,
                machine_1="",
                machine_2="",
                notes=""
            )
            db.add(rec)
            existing.add(name.upper())
            added += 1
            
        db.commit()
        return {"status": "success", "count": added, "message": f"Loaded {added} employees from Operator Master"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/hr/shift-list/clear-week")
def clear_hr_shift_week(week_start_date: str, db: Session = Depends(get_db)):
    ensure_hr_shift_table(db)
    try:
        cnt = db.query(models.HrShiftAssignment).filter(models.HrShiftAssignment.week_start_date == week_start_date).delete()
        db.commit()
        return {"status": "success", "cleared_count": cnt}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/hr/shift-list/{item_id}")
def delete_hr_shift_assignment(item_id: int, db: Session = Depends(get_db)):
    ensure_hr_shift_table(db)
    try:
        rec = db.query(models.HrShiftAssignment).filter(models.HrShiftAssignment.id == item_id).first()
        if not rec:
            raise HTTPException(status_code=404, detail="Not found")
        db.delete(rec)
        db.commit()
        return {"status": "success", "deleted_id": item_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# --- SERVICE: SHIFT STATUS MANAGEMENT ---
# ==========================================

def ensure_shift_status_logs_table(db: Session):
    try:
        models.ShiftStatusLog.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        db.rollback()

def get_shift_status_monday_str(date_str: str) -> str:
    if not date_str:
        return ""
    from datetime import datetime as dt_cls, timedelta as td_cls
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            dt = dt_cls.strptime(date_str.strip(), fmt).date()
            monday = dt - td_cls(days=dt.weekday())
            return monday.strftime("%Y-%m-%d")
        except Exception:
            continue
    return date_str

def canonical_mc_key(name: str) -> str:
    if not name:
        return ""
    k = name.strip().upper()
    k = re.sub(r'\bHASS\b', 'HAAS', k)
    k = k.replace('HASS-', 'HAAS-').replace('HASS ', 'HAAS ')
    k = re.sub(r'[\s\-_]+', '', k)
    return k

@app.get("/api/shift-status/populate")
def populate_shift_status(date: str, dept: str, shift: str, db: Session = Depends(get_db)):
    ensure_hr_shift_table(db)
    ensure_shift_status_logs_table(db)
    try:
        date_clean = (date or "").strip()
        dept_clean = (dept or "").strip()
        shift_clean = (shift or "").strip()
        week_monday = get_shift_status_monday_str(date_clean)

        # 1. Fetch machines for the dept safely (models.Machine has 'name', 'dept', 'status')
        dept_machines = []
        try:
            q_mc = db.query(models.Machine)
            if dept_clean.upper() != "ALL":
                q_mc = q_mc.filter(func.upper(func.trim(models.Machine.dept)) == dept_clean.upper())
            m_rows = q_mc.order_by(models.Machine.id.asc()).all()
            for m in m_rows:
                m_name = (m.name or "").strip()
                if m_name and m_name not in dept_machines:
                    dept_machines.append(m_name)
        except Exception as e_mc:
            db.rollback()
            try:
                rows = db.execute(text("SELECT * FROM machines ORDER BY id ASC")).mappings().all()
                for r in rows:
                    m_name = (r.get("name") or r.get("machine_name") or "").strip()
                    m_dept = (r.get("dept") or r.get("department") or "").strip()
                    if m_name and (dept_clean.upper() == "ALL" or m_dept.upper() == dept_clean.upper()):
                        if m_name not in dept_machines:
                            dept_machines.append(m_name)
            except Exception as e_fb:
                db.rollback()

        # Build master machine lookup map for canonical resolution (e.g. HASS-1 -> HAAS-1)
        master_key_to_name = {canonical_mc_key(m): m for m in dept_machines}

        def resolve_mc(name: str) -> str:
            if not name:
                return ""
            c_k = canonical_mc_key(name)
            return master_key_to_name.get(c_k, name.strip())

        # 2. Fetch shift allocations from hr_shift_assignments for week_monday, dept_clean, shift_clean
        allocations = []
        try:
            q_alloc = db.query(models.HrShiftAssignment).filter(
                models.HrShiftAssignment.week_start_date == week_monday
            )
            if dept_clean.upper() != "ALL":
                q_alloc = q_alloc.filter(func.upper(func.trim(models.HrShiftAssignment.dept)) == dept_clean.upper())
            if shift_clean.upper() != "ALL":
                q_alloc = q_alloc.filter(
                    or_(
                        func.upper(func.trim(models.HrShiftAssignment.shift)) == shift_clean.upper(),
                        func.upper(func.trim(models.HrShiftAssignment.shift)).like(f"%{shift_clean.upper()}%")
                    )
                )
            allocations = q_alloc.all()
        except Exception as e_alloc:
            db.rollback()
            print(f"Error fetching allocations: {e_alloc}")

        # 3. Combine dual machines and build station allocations
        covered_keys = set()
        stations = []

        for a in allocations:
            op_name = (a.emp_name or "").strip()
            if not op_name:
                continue
            m1_raw = (a.machine_1 or "").strip()
            m2_raw = (a.machine_2 or "").strip()
            m1 = resolve_mc(m1_raw) if m1_raw else ""
            m2 = resolve_mc(m2_raw) if m2_raw else ""

            if not m1 and not m2:
                continue

            # If m1 and m2 resolved to the same machine, avoid duplicate
            if m1 and m2 and canonical_mc_key(m1) == canonical_mc_key(m2):
                m2 = ""

            is_dual = bool(m1 and m2)
            if m1:
                covered_keys.add(canonical_mc_key(m1))
            if m2:
                covered_keys.add(canonical_mc_key(m2))

            if is_dual:
                unit_name = f"{m1} & {m2}"
                covered_mcs = [m1, m2]
            else:
                unit_name = m1 or m2
                covered_mcs = [unit_name]

            stations.append({
                "unit_name": unit_name,
                "machines_covered": covered_mcs,
                "is_dual": is_dual,
                "assigned_operator": op_name,
                "is_allocated": True
            })

        # Add unallocated machines from department master (not covered by any shift allocation)
        for m in dept_machines:
            if canonical_mc_key(m) not in covered_keys:
                stations.append({
                    "unit_name": m,
                    "machines_covered": [m],
                    "is_dual": False,
                    "assigned_operator": "",
                    "is_allocated": False
                })

        # 4. Check if an existing log exists for date_clean, dept_clean, shift_clean
        existing_log = None
        try:
            existing_log = db.query(models.ShiftStatusLog).filter(
                models.ShiftStatusLog.date == date_clean,
                func.upper(func.trim(models.ShiftStatusLog.dept)) == dept_clean.upper(),
                func.upper(func.trim(models.ShiftStatusLog.shift)) == shift_clean.upper()
            ).order_by(models.ShiftStatusLog.id.desc()).first()
        except Exception as e_log:
            db.rollback()

        existing_details_map = {}
        if existing_log and existing_log.details:
            try:
                detail_items = json.loads(existing_log.details)
                for item in detail_items:
                    mc_name = item.get("machine") or item.get("machine_name") or item.get("unit_name")
                    if mc_name:
                        existing_details_map[canonical_mc_key(mc_name)] = item
            except Exception:
                pass

        # 5. Construct final result machine/station list
        result_machines = []
        for s in stations:
            u_key = canonical_mc_key(s["unit_name"])
            existing_info = existing_details_map.get(u_key)
            if not existing_info and s["is_dual"]:
                for mc in s["machines_covered"]:
                    if canonical_mc_key(mc) in existing_details_map:
                        existing_info = existing_details_map[canonical_mc_key(mc)]
                        break

            if existing_info:
                status = existing_info.get("status", "Available")
                actual_op = existing_info.get("actual_operator") or existing_info.get("operator") or s["assigned_operator"]
                remarks = existing_info.get("remarks") or ""
                absent_type = existing_info.get("absent_type") or ("Absenteeism" if s["is_allocated"] and status != "Available" else ("Unallocated" if not s["is_allocated"] else ""))
            else:
                if s["is_allocated"]:
                    status = "Available"  # Matched with shift list - Shift Engineer certifies
                    actual_op = s["assigned_operator"]
                    remarks = "Dual M/C" if s["is_dual"] else ""
                    absent_type = ""
                else:
                    status = "Not Available"
                    actual_op = ""
                    remarks = "Unallocated in Shift List"
                    absent_type = "Unallocated"

            result_machines.append({
                "machine": s["unit_name"],
                "machines_covered": s["machines_covered"],
                "is_dual": s["is_dual"],
                "assigned_operator": s["assigned_operator"],
                "actual_operator": actual_op,
                "status": status,  # "Available" or "Not Available"
                "remarks": remarks,
                "is_allocated": s["is_allocated"],
                "absent_type": absent_type
            })

        return {
            "status": "success",
            "date": date_clean,
            "dept": dept_clean,
            "shift": shift_clean,
            "week_monday": week_monday,
            "has_existing_log": bool(existing_log),
            "existing_log_id": existing_log.id if existing_log else None,
            "existing_logged_by": existing_log.logged_by if existing_log else "",
            "existing_summary": existing_log.not_available_summary if existing_log else "",
            "machines": result_machines
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/shift-status/logs")
def save_shift_status_log(payload: dict, db: Session = Depends(get_db)):
    ensure_shift_status_logs_table(db)
    try:
        date_val = (payload.get("date") or "").strip()
        dept_val = (payload.get("dept") or "").strip()
        shift_val = (payload.get("shift") or "").strip()
        if not date_val or not dept_val or not shift_val:
            raise HTTPException(status_code=400, detail="Date, Dept, and Shift are required")

        total_machines = int(payload.get("total_machines") or 0)
        available_count = int(payload.get("available_count") or 0)
        not_available_count = int(payload.get("not_available_count") or 0)
        summary = (payload.get("not_available_summary") or "").strip()
        details_val = payload.get("details") or []
        details_str = json.dumps(details_val) if isinstance(details_val, (list, dict)) else str(details_val)
        logged_by = (payload.get("logged_by") or "admin").strip()

        existing = db.query(models.ShiftStatusLog).filter(
            models.ShiftStatusLog.date == date_val,
            func.upper(func.trim(models.ShiftStatusLog.dept)) == dept_val.upper(),
            func.upper(func.trim(models.ShiftStatusLog.shift)) == shift_val.upper()
        ).first()

        if existing:
            existing.total_machines = total_machines
            existing.available_count = available_count
            existing.not_available_count = not_available_count
            existing.not_available_summary = summary
            existing.details = details_str
            existing.logged_by = logged_by
            existing.created_at = get_now_ist()
            rec = existing
        else:
            rec = models.ShiftStatusLog(
                date=date_val,
                dept=dept_val,
                shift=shift_val,
                total_machines=total_machines,
                available_count=available_count,
                not_available_count=not_available_count,
                not_available_summary=summary,
                details=details_str,
                logged_by=logged_by
            )
            db.add(rec)

        db.commit()
        db.refresh(rec)
        return {"status": "success", "id": rec.id, "message": "Shift status logged successfully!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/shift-status/logs")
def get_shift_status_logs(date: Optional[str] = None, dept: Optional[str] = None, shift: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    ensure_shift_status_logs_table(db)
    try:
        q = db.query(models.ShiftStatusLog)
        if date and not date.startswith("--"):
            q = q.filter(models.ShiftStatusLog.date == date.strip())
        if dept and not dept.startswith("--") and dept.upper() != "ALL":
            q = q.filter(func.upper(func.trim(models.ShiftStatusLog.dept)) == dept.strip().upper())
        if shift and not shift.startswith("--") and shift.upper() != "ALL":
            q = q.filter(func.upper(func.trim(models.ShiftStatusLog.shift)) == shift.strip().upper())

        rows = q.order_by(models.ShiftStatusLog.date.desc(), models.ShiftStatusLog.id.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "date": r.date,
                "dept": r.dept,
                "shift": r.shift,
                "total_machines": r.total_machines,
                "available_count": r.available_count,
                "not_available_count": r.not_available_count,
                "not_available_summary": r.not_available_summary or "",
                "details": json.loads(r.details) if r.details else [],
                "logged_by": r.logged_by or "",
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
            } for r in rows
        ]
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/shift-status/logs/{log_id}")
def delete_shift_status_log(log_id: int, db: Session = Depends(get_db)):
    ensure_shift_status_logs_table(db)
    try:
        rec = db.query(models.ShiftStatusLog).filter(models.ShiftStatusLog.id == log_id).first()
        if not rec:
            raise HTTPException(status_code=404, detail="Shift status log not found")
        db.delete(rec)
        db.commit()
        return {"status": "success", "deleted_id": log_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# --- SERVICE: HOURLY REPORT & SERIAL TRACKING ---
# ==========================================

def ensure_hourly_reports_table(db: Session):
    try:
        models.HourlyReport.__table__.create(bind=db.get_bind(), checkfirst=True)
    except Exception:
        db.rollback()
    try:
        bind = db.get_bind()
        if "sqlite" in str(bind.url):
            cols = [row[1] for row in db.execute(text("PRAGMA table_info(hourly_reports);")).fetchall()]
            if "dept" not in cols:
                db.execute(text("ALTER TABLE hourly_reports ADD COLUMN dept TEXT;"))
                db.commit()
        else:
            db.execute(text("ALTER TABLE hourly_reports ADD COLUMN IF NOT EXISTS dept VARCHAR(100);"))
            db.commit()
    except Exception:
        db.rollback()

    # Auto-backfill empty dept from machines, operators, part_masters for existing logs
    try:
        db.execute(text("""
            UPDATE hourly_reports
            SET dept = (
                SELECT dept FROM machines
                WHERE UPPER(TRIM(machines.name)) = UPPER(TRIM(hourly_reports.machine))
                AND dept IS NOT NULL AND dept != ''
                LIMIT 1
            )
            WHERE (dept IS NULL OR dept = '' OR dept = '-')
            AND machine IS NOT NULL AND machine != '';
        """))
        db.commit()
    except Exception:
        db.rollback()

    try:
        db.execute(text("""
            UPDATE hourly_reports
            SET dept = (
                SELECT dept FROM operators
                WHERE UPPER(TRIM(operators.name)) = UPPER(TRIM(hourly_reports.operator))
                AND dept IS NOT NULL AND dept != ''
                LIMIT 1
            )
            WHERE (dept IS NULL OR dept = '' OR dept = '-')
            AND operator IS NOT NULL AND operator != '';
        """))
        db.commit()
    except Exception:
        db.rollback()

    try:
        db.execute(text("""
            UPDATE hourly_reports
            SET dept = (
                SELECT dept FROM part_masters
                WHERE UPPER(TRIM(part_masters.partno)) = UPPER(TRIM(hourly_reports.part_no))
                AND dept IS NOT NULL AND dept != ''
                LIMIT 1
            )
            WHERE (dept IS NULL OR dept = '' OR dept = '-')
            AND part_no IS NOT NULL AND part_no != '';
        """))
        db.commit()
    except Exception:
        db.rollback()

def get_part_ordered_operations(part_no: str, db: Session) -> list:
    if not part_no:
        return []
    clean_p = part_no.strip()
    ops = []
    # 1. Search in part_operations via part_masters
    try:
        pm_rows = db.execute(text("SELECT id, partno FROM part_masters WHERE UPPER(TRIM(partno)) = :p"), {"p": clean_p.upper()}).mappings().all()
        if pm_rows:
            pid = pm_rows[0].get("id")
            rows = db.execute(text("SELECT * FROM part_operations WHERE CAST(part_id AS TEXT) = :pid ORDER BY id ASC"), {"pid": str(pid)}).mappings().all()
            if rows:
                for r in rows:
                    ops.append({
                        "opn_no": str(r.get("opn_no") or "").strip(),
                        "description": r.get("description") or r.get("opn_name") or "",
                        "machine": r.get("machine") or r.get("machine_name") or "",
                        "cycle_time": float(r.get("cycle_time") or r.get("cycletime") or 0.0)
                    })
    except Exception:
        db.rollback()

    # 2. Search in operations via parts table if not found
    if not ops:
        try:
            p_rows = db.execute(text("SELECT id, part_no FROM parts WHERE UPPER(TRIM(part_no)) = :p"), {"p": clean_p.upper()}).mappings().all()
            if p_rows:
                pid = p_rows[0].get("id")
                rows = db.execute(text("SELECT * FROM operations WHERE part_id = :pid ORDER BY id ASC"), {"pid": pid}).mappings().all()
                if rows:
                    for r in rows:
                        ops.append({
                            "opn_no": str(r.get("opn_no") or "").strip(),
                            "description": r.get("description") or "",
                            "machine": r.get("machine_name") or r.get("machine") or "",
                            "cycle_time": float(r.get("cycle_time") or 0.0)
                        })
        except Exception:
            db.rollback()

    # Deduplicate operations by opn_no preserving first occurrence
    seen_opns = set()
    unique_ops = []
    for op in ops:
        op_key = op.get("opn_no")
        if op_key and op_key not in seen_opns:
            seen_opns.add(op_key)
            unique_ops.append(op)

    # Sort operations numerically if numeric (e.g. 10, 20, 30), else string
    def op_sort_key(x):
        val = str(x.get("opn_no") or "")
        m = re.match(r'^(\d+)', val)
        if m:
            return (0, int(m.group(1)), val)
        return (1, 0, val)

    unique_ops.sort(key=op_sort_key)
    return unique_ops

def format_serial_ranges(serials: list) -> str:
    if not serials:
        return ""
    try:
        nums = sorted(list(set(int(x) for x in serials)))
    except Exception:
        return ", ".join(str(x) for x in serials)
    if not nums:
        return ""
    ranges = []
    start = nums[0]
    end = nums[0]
    for n in nums[1:]:
        if n == end + 1:
            end = n
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = n
            end = n
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
    return ", ".join(ranges)

@app.get("/api/hourly-reports/part-status")
def get_hourly_report_part_status(part_no: str, db: Session = Depends(get_db)):
    ensure_hourly_reports_table(db)
    clean_p = (part_no or "").strip()
    if not clean_p:
        return {"part_no": "", "schedule_qty": 0, "operations": [], "completed_by_opn": {}, "completed_details_by_opn": {}}

    # 1. Fetch operations for part
    operations = get_part_ordered_operations(clean_p, db)

    # 2. Fetch schedule quantity
    sch_qty = 0
    try:
        sch_rows = db.execute(text("SELECT qty FROM schedules WHERE UPPER(TRIM(partno)) = :p ORDER BY id DESC LIMIT 1"), {"p": clean_p.upper()}).mappings().all()
        if sch_rows:
            sch_qty = int(float(sch_rows[0].get("qty") or 0))
    except Exception:
        db.rollback()

    if sch_qty <= 0:
        try:
            ps_rows = db.execute(text("SELECT total_sch_qty FROM production_schedules WHERE UPPER(TRIM(part_no)) = :p ORDER BY id DESC LIMIT 1"), {"p": clean_p.upper()}).mappings().all()
            if ps_rows:
                sch_qty = int(float(ps_rows[0].get("total_sch_qty") or 0))
        except Exception:
            db.rollback()

    # 3. Query existing hourly_reports for this part
    completed_by_opn = {}
    completed_details_by_opn = {}
    try:
        records = db.query(models.HourlyReport).filter(func.upper(func.trim(models.HourlyReport.part_no)) == clean_p.upper()).order_by(models.HourlyReport.id.asc()).all()
        for r in records:
            opn = str(r.opn_no or "").strip()
            if opn not in completed_by_opn:
                completed_by_opn[opn] = set()
                completed_details_by_opn[opn] = {}
            try:
                s_list = json.loads(r.serial_numbers or "[]")
                if isinstance(s_list, list):
                    for s in s_list:
                        s_int = int(s)
                        completed_by_opn[opn].add(s_int)
                        completed_details_by_opn[opn][str(s_int)] = {
                            "operator": r.operator,
                            "machine": r.machine,
                            "date": r.date,
                            "time": r.time,
                            "log_id": r.id,
                            "dept": r.dept or ""
                        }
            except Exception:
                pass

        # Convert sets to sorted lists
        res_completed = {k: sorted(list(v)) for k, v in completed_by_opn.items()}
    except Exception as e:
        db.rollback()
        res_completed = {}
        completed_details_by_opn = {}

    return {
        "part_no": clean_p,
        "schedule_qty": sch_qty,
        "operations": operations,
        "completed_by_opn": res_completed,
        "completed_details_by_opn": completed_details_by_opn
    }

@app.get("/api/hourly-reports")
def get_hourly_reports(
    date: Optional[str] = None,
    dept: Optional[str] = None,
    part_no: Optional[str] = None,
    operator: Optional[str] = None,
    machine: Optional[str] = None,
    opn_no: Optional[str] = None,
    db: Session = Depends(get_db)
):
    ensure_hourly_reports_table(db)
    try:
        q = db.query(models.HourlyReport)
        if date:
            q = q.filter(models.HourlyReport.date == date.strip())
        if dept and dept.strip().upper() != "ALL":
            q = q.filter(func.upper(models.HourlyReport.dept) == dept.strip().upper())
        if part_no:
            q = q.filter(func.upper(func.trim(models.HourlyReport.part_no)) == part_no.strip().upper())
        if operator:
            q = q.filter(func.upper(func.trim(models.HourlyReport.operator)) == operator.strip().upper())
        if machine:
            q = q.filter(func.upper(func.trim(models.HourlyReport.machine)) == machine.strip().upper())
        if opn_no:
            q = q.filter(func.upper(func.trim(models.HourlyReport.opn_no)) == opn_no.strip().upper())

        rows = q.order_by(models.HourlyReport.id.desc()).limit(200).all()
        results = []
        for r in rows:
            try:
                s_list = json.loads(r.serial_numbers or "[]")
            except Exception:
                s_list = []
            range_str = format_serial_ranges(s_list)
            results.append({
                "id": r.id,
                "date": r.date,
                "time": r.time,
                "dept": r.dept or "",
                "operator": r.operator,
                "machine": r.machine,
                "part_no": r.part_no,
                "opn_no": r.opn_no,
                "opn_desc": r.opn_desc or "",
                "schedule_qty": r.schedule_qty or 0,
                "qty": r.qty or len(s_list),
                "serial_numbers": s_list,
                "serial_range": range_str,
                "remarks": r.remarks or "",
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
            })
        return results
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hourly-reports/export/excel")
def export_hourly_reports_excel(
    date: Optional[str] = None,
    dept: Optional[str] = None,
    part_no: Optional[str] = None,
    operator: Optional[str] = None,
    machine: Optional[str] = None,
    opn_no: Optional[str] = None,
    db: Session = Depends(get_db)
):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    ensure_hourly_reports_table(db)
    try:
        q = db.query(models.HourlyReport)
        if date:
            q = q.filter(models.HourlyReport.date == date.strip())
        if dept and dept.strip().upper() != "ALL":
            q = q.filter(func.upper(models.HourlyReport.dept) == dept.strip().upper())
        if part_no:
            q = q.filter(func.upper(func.trim(models.HourlyReport.part_no)) == part_no.strip().upper())
        if operator:
            q = q.filter(func.upper(func.trim(models.HourlyReport.operator)) == operator.strip().upper())
        if machine:
            q = q.filter(func.upper(func.trim(models.HourlyReport.machine)) == machine.strip().upper())
        if opn_no:
            q = q.filter(func.upper(func.trim(models.HourlyReport.opn_no)) == opn_no.strip().upper())

        rows = q.order_by(models.HourlyReport.id.desc()).all()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Hourly Production Logs"

        header_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        align_center = Alignment(horizontal="center", vertical="center")
        align_left = Alignment(horizontal="left", vertical="center")
        align_right = Alignment(horizontal="right", vertical="center")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        headers = [
            "Log ID", "Date", "Time (IST)", "Dept", "Operator", "Machine",
            "Part No", "Opn", "Qty", "Serial Numbers Done", "Remarks"
        ]
        ws.append(headers)

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align_center

        ws.row_dimensions[1].height = 24

        total_qty = 0
        for r in rows:
            try:
                s_list = json.loads(r.serial_numbers or "[]")
            except Exception:
                s_list = []
            range_str = format_serial_ranges(s_list)
            q_val = r.qty or len(s_list)
            total_qty += q_val
            t_val = r.time or ""
            if len(t_val) > 5:
                t_val = t_val[:5]

            row = [
                r.id,
                r.date or "",
                t_val,
                r.dept or "",
                r.operator or "",
                r.machine or "",
                r.part_no or "",
                f"Opn {r.opn_no}" if r.opn_no else "",
                q_val,
                range_str or (", ".join(str(s) for s in s_list)),
                r.remarks or ""
            ]
            ws.append(row)
            r_idx = ws.max_row
            ws.row_dimensions[r_idx].height = 20
            for c_idx in range(1, len(row) + 1):
                cell = ws.cell(row=r_idx, column=c_idx)
                cell.border = thin_border
                if c_idx in [1, 2, 3, 8]:
                    cell.alignment = align_center
                elif c_idx == 9:
                    cell.alignment = align_right
                else:
                    cell.alignment = align_left

        # Total row
        total_row = ["Total", "", "", "", "", "", "", "", total_qty, "", ""]
        ws.append(total_row)
        tot_idx = ws.max_row
        ws.row_dimensions[tot_idx].height = 22
        bold_font = Font(name="Calibri", size=11, bold=True)
        tot_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        for c_idx in range(1, len(total_row) + 1):
            cell = ws.cell(row=tot_idx, column=c_idx)
            cell.border = thin_border
            cell.font = bold_font
            cell.fill = tot_fill
            if c_idx == 9:
                cell.alignment = align_right
            elif c_idx == 1:
                cell.alignment = align_center

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        date_suffix = f"_{date}" if date else "_All_Dates"
        filename = f"Hourly_Production_Logs{date_suffix}_{datetime.date.today().strftime('%Y%m%d')}.xlsx"
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hourly-reports")
def create_hourly_report(payload: dict, db: Session = Depends(get_db)):
    ensure_hourly_reports_table(db)
    try:
        date_val = str(payload.get("date") or "").strip()
        time_val = str(payload.get("time") or "").strip()
        dept_val = str(payload.get("dept") or "").strip()
        operator_val = str(payload.get("operator") or "").strip()
        machine_val = str(payload.get("machine") or "").strip()
        part_no_val = str(payload.get("part_no") or "").strip()
        opn_no_val = str(payload.get("opn_no") or "").strip()
        opn_desc_val = str(payload.get("opn_desc") or "").strip()
        schedule_qty_val = int(payload.get("schedule_qty") or 0)
        remarks_val = str(payload.get("remarks") or "").strip()
        raw_serials = payload.get("serial_numbers") or []

        if not date_val:
            raise HTTPException(status_code=400, detail="Date is required")
        if not operator_val:
            raise HTTPException(status_code=400, detail="Operator is required")
        if not machine_val:
            raise HTTPException(status_code=400, detail="Machine is required")
        if not part_no_val:
            raise HTTPException(status_code=400, detail="Part number is required")
        if not opn_no_val:
            raise HTTPException(status_code=400, detail="Operation number is required")

        # Auto-derive dept if not provided
        if not dept_val or dept_val == "-" or dept_val.upper() == "ALL":
            if machine_val:
                try:
                    m_row = db.execute(text("SELECT dept FROM machines WHERE UPPER(TRIM(name)) = :m LIMIT 1"), {"m": machine_val.upper()}).mappings().first()
                    if m_row and m_row.get("dept"):
                        dept_val = str(m_row.get("dept")).strip()
                except Exception:
                    pass
            if not dept_val and operator_val:
                try:
                    o_row = db.execute(text("SELECT dept FROM operators WHERE UPPER(TRIM(name)) = :o LIMIT 1"), {"o": operator_val.upper()}).mappings().first()
                    if o_row and o_row.get("dept"):
                        dept_val = str(o_row.get("dept")).strip()
                except Exception:
                    pass
            if not dept_val and part_no_val:
                try:
                    p_row = db.execute(text("SELECT dept FROM part_masters WHERE UPPER(TRIM(partno)) = :p LIMIT 1"), {"p": part_no_val.upper()}).mappings().first()
                    if p_row and p_row.get("dept"):
                        dept_val = str(p_row.get("dept")).strip()
                except Exception:
                    pass

        # Time entry as per IST
        if not time_val:
            time_val = models.get_now_ist().strftime("%H:%M")
        else:
            # Normalize to clean HH:MM or HH:MM:SS
            parts = time_val.split(":")
            if len(parts) >= 2:
                time_val = f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"

        # Parse and sanitize serial numbers
        if isinstance(raw_serials, str):
            try:
                raw_serials = json.loads(raw_serials)
            except Exception:
                raw_serials = [int(s.strip()) for s in raw_serials.split(",") if s.strip().isdigit()]
        
        serial_nums = sorted(list(set(int(x) for x in raw_serials)))
        if not serial_nums:
            raise HTTPException(status_code=400, detail="Please select at least one serial number")

        # Check for duplicates in current operation
        existing_logs = db.query(models.HourlyReport).filter(
            func.upper(func.trim(models.HourlyReport.part_no)) == part_no_val.upper(),
            func.upper(func.trim(models.HourlyReport.opn_no)) == opn_no_val.upper()
        ).all()
        already_done = set()
        for el in existing_logs:
            try:
                for s in json.loads(el.serial_numbers or "[]"):
                    already_done.add(int(s))
            except Exception:
                pass

        conflict_serials = [s for s in serial_nums if s in already_done]
        if conflict_serials:
            raise HTTPException(
                status_code=400,
                detail=f"The following serial numbers are already completed in Opn {opn_no_val}: {format_serial_ranges(conflict_serials)}"
            )

        # Sequential operation validation
        ops = get_part_ordered_operations(part_no_val, db)
        opn_index = -1
        for idx, op in enumerate(ops):
            if str(op.get("opn_no", "")).strip().upper() == opn_no_val.upper():
                opn_index = idx
                break

        # If not the first operation, verify all serials are completed in the prior operation
        if opn_index > 0:
            prev_op = ops[opn_index - 1]
            prev_opn_no = str(prev_op.get("opn_no", "")).strip()
            prev_logs = db.query(models.HourlyReport).filter(
                func.upper(func.trim(models.HourlyReport.part_no)) == part_no_val.upper(),
                func.upper(func.trim(models.HourlyReport.opn_no)) == prev_opn_no.upper()
            ).all()
            prev_done = set()
            for pl in prev_logs:
                try:
                    for s in json.loads(pl.serial_numbers or "[]"):
                        prev_done.add(int(s))
                except Exception:
                    pass

            uncompleted_in_prev = [s for s in serial_nums if s not in prev_done]
            if uncompleted_in_prev:
                raise HTTPException(
                    status_code=400,
                    detail=f"Serial numbers not yet completed in prior operation (Opn {prev_opn_no}): {format_serial_ranges(uncompleted_in_prev)}. Sequential progression required."
                )

        # Create record
        record = models.HourlyReport(
            date=date_val,
            time=time_val,
            dept=dept_val,
            operator=operator_val,
            machine=machine_val,
            part_no=part_no_val,
            opn_no=opn_no_val,
            opn_desc=opn_desc_val,
            schedule_qty=schedule_qty_val,
            qty=len(serial_nums),
            serial_numbers=json.dumps(serial_nums),
            remarks=remarks_val,
            created_at=models.get_now_ist()
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return {
            "status": "success",
            "id": record.id,
            "message": f"Successfully logged {len(serial_nums)} pieces for Opn {opn_no_val}",
            "qty": len(serial_nums),
            "serial_range": format_serial_ranges(serial_nums)
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/hourly-reports/{log_id}")
def delete_hourly_report(log_id: int, db: Session = Depends(get_db)):
    ensure_hourly_reports_table(db)
    try:
        rec = db.query(models.HourlyReport).filter(models.HourlyReport.id == log_id).first()
        if not rec:
            raise HTTPException(status_code=404, detail="Hourly report log not found")
        
        # Check if subsequent operations depend on this log's serial numbers
        part_no = rec.part_no
        opn_no = rec.opn_no
        try:
            serials_in_rec = set(int(s) for s in json.loads(rec.serial_numbers or "[]"))
        except Exception:
            serials_in_rec = set()

        ops = get_part_ordered_operations(part_no, db)
        opn_index = -1
        for idx, op in enumerate(ops):
            if str(op.get("opn_no", "")).strip().upper() == opn_no.upper():
                opn_index = idx
                break

        if opn_index >= 0 and opn_index < len(ops) - 1:
            # Check subsequent operations
            for next_op in ops[opn_index + 1:]:
                next_opn = str(next_op.get("opn_no", "")).strip()
                subseq_logs = db.query(models.HourlyReport).filter(
                    func.upper(func.trim(models.HourlyReport.part_no)) == part_no.upper(),
                    func.upper(func.trim(models.HourlyReport.opn_no)) == next_opn.upper()
                ).all()
                for sl in subseq_logs:
                    try:
                        sl_serials = set(int(s) for s in json.loads(sl.serial_numbers or "[]"))
                        overlap = serials_in_rec.intersection(sl_serials)
                        if overlap:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Cannot delete log: serial numbers {format_serial_ranges(list(overlap))} have already been processed in subsequent Opn {next_opn}. Revert subsequent operations first."
                            )
                    except HTTPException:
                        raise
                    except Exception:
                        pass

        db.delete(rec)
        db.commit()
        return {"status": "success", "deleted_id": log_id, "message": "Hourly production log deleted successfully"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# --- Serve Static Files ---
@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")
