#!/usr/bin/env python3
"""
Luxand Cloud API Test Script
Tests person enrollment and face recognition functionality
"""

import os
import sys
import requests
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LuxandCloudTest:
    def __init__(self):
        """Initialize Luxand Cloud API client"""
        self.api_key = os.getenv('LUXAND_API_KEY')
        
        if not self.api_key:
            print("❌ Error: LUXAND_API_KEY not found in .env file")
            sys.exit(1)
        
        # Luxand Cloud API configuration based on code examples
        self.base_url = 'https://api.luxand.cloud'
        self.headers = {'token': self.api_key}
        
        print("✅ Luxand Cloud API client initialized")
        print(f"🔑 Using API Key: {self.api_key[:8]}...")
    
    def add_person(self, name: str, image_path: str, collections: str = "") -> dict:
        """Add a person to the database with their face image"""
        print(f"\n📤 Adding person: {name}")
        
        if not os.path.exists(image_path):
            print(f"❌ Image file not found: {image_path}")
            return {"success": False, "message": "Image file not found"}
        
        try:
            # Use correct endpoint and parameters from code examples
            url = f"{self.base_url}/v2/person"
            
            # Prepare files and data as per Luxand API format
            if image_path.startswith("https://"):
                files = {"photos": image_path}
            else:
                files = {"photos": open(image_path, "rb")}
            
            data = {
                "name": name,
                "store": "1",
                "collections": collections
            }
            
            print(f"🔄 POST {url}")
            response = requests.post(url, headers=self.headers, data=data, files=files, timeout=30)
            
            # Close file if it was opened
            if not image_path.startswith("https://"):
                files["photos"].close()
            
            if response.status_code == 200:
                person = response.json()
                print(f"✅ Added person {name} with UUID {person['uuid']}")
                return {"success": True, "uuid": person["uuid"], "data": person}
            else:
                print(f"❌ Can't add person {name}: {response.text}")
                return {"success": False, "message": response.text}
                
        except Exception as e:
            print(f"❌ Error adding person: {e}")
            return {"success": False, "message": str(e)}
    
    def add_face(self, person_uuid: str, image_path: str) -> dict:
        """Add additional face to improve recognition accuracy"""
        print(f"\n📤 Adding additional face for UUID: {person_uuid}")
        
        if not os.path.exists(image_path):
            print(f"❌ Image file not found: {image_path}")
            return {"success": False, "message": "Image file not found"}
        
        try:
            url = f"{self.base_url}/v2/person/{person_uuid}"
            
            # Prepare files and data
            if image_path.startswith("https://"):
                files = {"photo": image_path}
            else:
                files = {"photo": open(image_path, "rb")}
            
            data = {"store": "1"}
            
            print(f"🔄 POST {url}")
            response = requests.post(url, headers=self.headers, data=data, files=files, timeout=30)
            
            # Close file if it was opened
            if not image_path.startswith("https://"):
                files["photo"].close()
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Additional face added successfully")
                return {"success": True, "data": result}
            else:
                print(f"❌ Can't add face: {response.text}")
                return {"success": False, "message": response.text}
                
        except Exception as e:
            print(f"❌ Error adding face: {e}")
            return {"success": False, "message": str(e)}
    
    def recognize_face(self, image_path: str) -> dict:
        """Recognize a face in the given image"""
        print(f"\n🔍 Recognizing face in: {image_path}")
        
        if not os.path.exists(image_path):
            print(f"❌ Image file not found: {image_path}")
            return {"success": False, "message": "Image file not found"}
        
        try:
            url = f"{self.base_url}/photo/search/v2"
            
            # Prepare files
            if image_path.startswith("https://"):
                files = {"photo": image_path}
            else:
                files = {"photo": open(image_path, "rb")}
            
            print(f"🔄 POST {url}")
            response = requests.post(url, headers=self.headers, files=files, timeout=30)
            
            # Close file if it was opened
            if not image_path.startswith("https://"):
                files["photo"].close()
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Face recognition completed!")
                print(f"📋 Response: {result}")
                return {"success": True, "data": result}
            else:
                print(f"❌ Can't recognize people: {response.text}")
                return {"success": False, "message": response.text}
                
        except Exception as e:
            print(f"❌ Error recognizing face: {e}")
            return {"success": False, "message": str(e)}
    
    def delete_person(self, person_uuid: str) -> dict:
        """Delete a person from the database by UUID"""
        print(f"\n🗑️ Deleting person with UUID: {person_uuid}")
        
        try:
            url = f"{self.base_url}/person/{person_uuid}"
            
            print(f"🔄 DELETE {url}")
            response = requests.delete(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                print(f"✅ Person deleted successfully")
                return {"success": True, "message": "Person deleted successfully"}
            else:
                print(f"❌ Can't delete person: {response.text}")
                return {"success": False, "message": response.text}
                
        except Exception as e:
            print(f"❌ Error deleting person: {e}")
            return {"success": False, "message": str(e)}

def main():
    """Main interactive menu"""
    print("🏥 Luxand Cloud API Test Script")
    print("=" * 50)
    
    # Initialize API client
    try:
        luxand = LuxandCloudTest()
    except SystemExit:
        return
    
    while True:
        print("\n📋 Menu:")
        print("1. Add person with face (complete enrollment)")
        print("2. Add additional face to existing person")
        print("3. Recognize face from image")
        print("4. Delete person from database")
        print("5. Exit")
        
        try:
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                print("\n📤 Person Creation and Face Enrollment")
                name = input("Enter person name: ").strip()
                if not name:
                    print("❌ Name cannot be empty")
                    continue
                
                image_path = input("Enter path to enrollment image: ").strip()
                if not image_path:
                    print("❌ Image path cannot be empty")
                    continue
                
                collections = input("Enter collections (optional): ").strip()
                
                result = luxand.add_person(name, image_path, collections)
                if not result["success"]:
                    print(f"❌ Failed to add person: {result['message']}")
                
            elif choice == '2':
                print("\n📤 Add Additional Face")
                person_uuid = input("Enter person UUID: ").strip()
                if not person_uuid:
                    print("❌ Person UUID cannot be empty")
                    continue
                
                image_path = input("Enter path to additional face image: ").strip()
                if not image_path:
                    print("❌ Image path cannot be empty")
                    continue
                
                result = luxand.add_face(person_uuid, image_path)
                if not result["success"]:
                    print(f"❌ Failed to add face: {result['message']}")
                
            elif choice == '3':
                print("\n🔍 Face Recognition")
                image_path = input("Enter path to recognition image: ").strip()
                if not image_path:
                    print("❌ Image path cannot be empty")
                    continue
                
                result = luxand.recognize_face(image_path)
                if not result["success"]:
                    print(f"❌ Failed to recognize face: {result['message']}")
                
            elif choice == '4':
                print("\n🗑️ Delete Person")
                person_uuid = input("Enter person UUID to delete: ").strip()
                if not person_uuid:
                    print("❌ Person UUID cannot be empty")
                    continue
                
                # Confirmation prompt
                confirm = input(f"⚠️ Are you sure you want to delete person {person_uuid}? (y/N): ").strip().lower()
                if confirm != 'y':
                    print("❌ Deletion cancelled")
                    continue
                
                result = luxand.delete_person(person_uuid)
                if not result["success"]:
                    print(f"❌ Failed to delete person: {result['message']}")
                
            elif choice == '5':
                print("\n👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please enter 1-5.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
