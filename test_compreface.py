#!/usr/bin/env python3
"""
CompreFace Test Script for Patient Face Recognition
This script allows you to:
1. Upload patient faces with their IDs
2. Recognize patients from uploaded photos
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from compreface import CompreFace
from compreface.service import RecognitionService
from compreface.collections import FaceCollection

# Load environment variables
load_dotenv()

class CompreFacePatientTest:
    def __init__(self):
        # CompreFace configuration
        self.domain = 'http://localhost'
        self.port = '8000'
        self.api_key = os.getenv('COMPREFACE_API_KEY')
        
        if not self.api_key:
            print("❌ Error: COMPREFACE_API_KEY not found in .env file")
            sys.exit(1)
        
        # Initialize CompreFace
        try:
            self.compre_face = CompreFace(self.domain, self.port)
            self.recognition = self.compre_face.init_face_recognition(self.api_key)
            self.face_collection = self.recognition.get_face_collection()
            print("✅ CompreFace initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing CompreFace: {e}")
            sys.exit(1)
    
    def add_patient_face(self, patient_id: str, image_path: str):
        """Add a patient's face to the CompreFace collection"""
        try:
            if not os.path.exists(image_path):
                print(f"❌ Error: Image file not found: {image_path}")
                return False
            
            print(f"📤 Adding face for Patient ID: {patient_id}")
            result = self.face_collection.add(image_path=image_path, subject=patient_id)
            
            if result.get('image_id'):
                print(f"✅ Successfully added face for Patient {patient_id}")
                print(f"   Image ID: {result['image_id']}")
                return True
            else:
                print(f"❌ Failed to add face for Patient {patient_id}")
                print(f"   Response: {result}")
                return False
                
        except Exception as e:
            print(f"❌ Error adding patient face: {e}")
            return False
    
    def recognize_patient(self, image_path: str, confidence_threshold: float = 0.85):
        """Recognize a patient from an image"""
        try:
            if not os.path.exists(image_path):
                print(f"❌ Error: Image file not found: {image_path}")
                return None
            
            print(f"🔍 Recognizing patient from: {image_path}")
            
            result = self.recognition.recognize(
                image_path=image_path,
                options={
                    "limit": 3,  # Return top 3 matches
                    "det_prob_threshold": 0.8,  # Face detection confidence
                    "prediction_count": 1,
                    "face_plugins": "age,gender",  # Additional info
                    "status": "true"
                }
            )
            
            if not result.get('result'):
                print("❌ No faces detected in the image")
                return None
            
            faces = result['result']
            print(f"👤 Found {len(faces)} face(s) in the image")
            
            for i, face in enumerate(faces, 1):
                print(f"\n--- Face {i} ---")
                
                # Face detection info
                box = face.get('box', {})
                print(f"Face Detection Confidence: {box.get('probability', 'N/A')}")
                
                # Age and gender info if available
                if 'age' in face:
                    age_info = face['age']
                    print(f"Estimated Age: {age_info.get('low', 'N/A')}-{age_info.get('high', 'N/A')} years")
                
                if 'gender' in face:
                    gender_info = face['gender']
                    print(f"Gender: {gender_info.get('value', 'N/A')} (confidence: {gender_info.get('probability', 'N/A'):.2f})")
                
                # Recognition results
                subjects = face.get('subjects', [])
                if subjects:
                    print(f"🎯 Patient Recognition Results:")
                    for j, subject in enumerate(subjects, 1):
                        patient_id = subject['subject']
                        similarity = subject['similarity']
                        
                        if similarity >= confidence_threshold:
                            print(f"   {j}. ✅ Patient ID: {patient_id} (Confidence: {similarity:.3f})")
                        else:
                            print(f"   {j}. ⚠️  Patient ID: {patient_id} (Confidence: {similarity:.3f}) - Below threshold")
                    
                    # Return the best match if above threshold
                    best_match = subjects[0]
                    if best_match['similarity'] >= confidence_threshold:
                        return {
                            'patient_id': best_match['subject'],
                            'confidence': best_match['similarity'],
                            'face_info': {
                                'age': face.get('age'),
                                'gender': face.get('gender')
                            }
                        }
                else:
                    print("❌ No matching patients found in the database")
            
            return None
            
        except Exception as e:
            print(f"❌ Error recognizing patient: {e}")
            return None
    
    def list_patients(self):
        """List all patients in the face collection"""
        try:
            subjects = self.recognition.get_subjects()
            result = subjects.list()
            
            if result.get('subjects'):
                print(f"📋 Registered Patients ({len(result['subjects'])}):")
                for subject in result['subjects']:
                    print(f"   - Patient ID: {subject}")
            else:
                print("📋 No patients registered yet")
                
        except Exception as e:
            print(f"❌ Error listing patients: {e}")

def main():
    print("🏥 CompreFace Patient Recognition Test")
    print("=" * 50)
    
    # Initialize CompreFace
    cf_test = CompreFacePatientTest()
    
    while True:
        print("\n📋 Menu:")
        print("1. Add patient face")
        print("2. Recognize patient from photo")
        print("3. List registered patients")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            print("\n📤 Add Patient Face")
            patient_id = input("Enter Patient ID: ").strip()
            image_path = input("Enter image file path: ").strip()
            
            if patient_id and image_path:
                cf_test.add_patient_face(patient_id, image_path)
            else:
                print("❌ Please provide both Patient ID and image path")
        
        elif choice == '2':
            print("\n🔍 Recognize Patient")
            image_path = input("Enter image file path: ").strip()
            
            if image_path:
                result = cf_test.recognize_patient(image_path)
                if result:
                    print(f"\n🎉 Patient Identified!")
                    print(f"   Patient ID: {result['patient_id']}")
                    print(f"   Confidence: {result['confidence']:.3f}")
                else:
                    print("\n❌ Patient not recognized or confidence too low")
            else:
                print("❌ Please provide image path")
        
        elif choice == '3':
            print("\n📋 Registered Patients")
            cf_test.list_patients()
        
        elif choice == '4':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1-4.")

if __name__ == "__main__":
    main()
