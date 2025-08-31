"""
Test script to verify Supabase connection and fetch patient data
"""

import asyncio
import sys
import os

# Add the parent directory to the path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.supabase_service import supabase_service

async def test_supabase_connection():
    """Test Supabase connection and fetch patient with onehat_patient_id 52349"""
    
    print("🔍 Testing Supabase Connection...")
    
    # Test basic connection
    if supabase_service.test_connection():
        print("✅ Supabase connection successful!")
    else:
        print("❌ Supabase connection failed!")
        return
    
    print("\n📋 Fetching patient with onehat_patient_id: 52349...")
    
    try:
        # Fetch specific patient
        patient = await supabase_service.get_patient_by_onehat_id(52349)
        
        if patient:
            print("✅ Patient found!")
            print(f"📝 Patient Details:")
            print(f"   - ID: {patient.get('id')}")
            print(f"   - OneHat Patient ID: {patient.get('onehat_patient_id')}")
            print(f"   - Full Name: {patient.get('full_name')}")
            print(f"   - Phone: {patient.get('phone_number')}")
            print(f"   - Age: {patient.get('age')}")
            print(f"   - Gender: {patient.get('gender')}")
            print(f"   - Date of Birth: {patient.get('date_of_birth')}")
        else:
            print("❌ Patient not found with onehat_patient_id: 52349")
            
            # Try to fetch all patients to see what's available
            print("\n📋 Fetching all patients to check available data...")
            all_patients = await supabase_service.get_all_patients()
            
            if all_patients:
                print(f"✅ Found {len(all_patients)} patients in database:")
                for p in all_patients[:5]:  # Show first 5 patients
                    print(f"   - OneHat ID: {p.get('onehat_patient_id')}, Name: {p.get('full_name')}")
                if len(all_patients) > 5:
                    print(f"   ... and {len(all_patients) - 5} more patients")
            else:
                print("❌ No patients found in database")
                
    except Exception as e:
        print(f"❌ Error during patient fetch: {e}")

if __name__ == "__main__":
    asyncio.run(test_supabase_connection())
