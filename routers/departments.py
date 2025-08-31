"""
Department and doctor management API endpoints
"""

from fastapi import APIRouter, HTTPException
import csv
from typing import Dict, List

from models.hospital import DepartmentList, DoctorList, Department
from core.config import settings

router = APIRouter()

def load_departments_doctors() -> Dict[str, List[str]]:
    """Load departments and doctors from CSV file"""
    departments_doctors = {}
    csv_path = settings.departments_csv_path
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get('Department') and row.get('Doctor Name'):
                    dept = row['Department'].strip()
                    doctor = row['Doctor Name'].strip()
                    
                    if dept not in departments_doctors:
                        departments_doctors[dept] = []
                    departments_doctors[dept].append(doctor)
        
        return departments_doctors
    except FileNotFoundError:
        # Fallback data if CSV not found
        return {
            "Cardiology": ["Dr. Smith", "Dr. Johnson"],
            "Orthopedics": ["Dr. Brown", "Dr. Wilson"],
            "Neurology": ["Dr. Davis", "Dr. Miller"],
            "General Medicine": ["Dr. Garcia", "Dr. Rodriguez"]
        }

@router.get("/departments", response_model=DepartmentList)
async def get_departments():
    """Get list of available departments"""
    try:
        departments_doctors = load_departments_doctors()
        departments = list(departments_doctors.keys())
        
        return DepartmentList(departments=departments)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading departments: {str(e)}")

@router.get("/departments/{department}/doctors", response_model=DoctorList)
async def get_doctors_by_department(department: str):
    """Get list of doctors in a specific department"""
    try:
        departments_doctors = load_departments_doctors()
        
        if department not in departments_doctors:
            raise HTTPException(status_code=404, detail="Department not found")
        
        doctors = departments_doctors[department]
        
        return DoctorList(department=department, doctors=doctors)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading doctors: {str(e)}")

@router.get("/get-doctor-id/{doctor_name}")
async def get_doctor_id(doctor_name: str):
    """Get onehat_doctor_id for a specific doctor name"""
    try:
        csv_path = settings.departments_csv_path
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get('Doctor Name', '').strip() == doctor_name.strip():
                    return {
                        "doctor_name": doctor_name,
                        "onehat_doctor_id": row.get('onehat_doctor_id')
                    }
        
        raise HTTPException(status_code=404, detail="Doctor not found")
        
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="CSV file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading doctor ID: {str(e)}")

@router.get("/departments/all")
async def get_all_departments_with_doctors():
    """Get all departments with their doctors"""
    try:
        departments_doctors = load_departments_doctors()
        
        result = []
        for dept, doctors in departments_doctors.items():
            result.append({
                "department": dept,
                "doctors": doctors,
                "doctor_count": len(doctors)
            })
        
        return {
            "success": True,
            "departments": result,
            "total_departments": len(result)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading hospital data: {str(e)}")
