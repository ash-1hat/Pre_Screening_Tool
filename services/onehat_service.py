"""
OneHat Service Module for Medical Pre-Screening Tool

This module handles OneHat External API operations including:
- Authentication and token management
- Patient creation in OneHat system
- Integration with hospital OneHat platform
"""

import os
import base64
import httpx
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OneHatAuthError(Exception):
    """Exception raised for OneHat authentication errors"""
    pass

class OneHatAPIError(Exception):
    """Exception raised for OneHat API errors"""
    pass

class OneHatService:
    """Service class to handle OneHat External API operations"""
    
    def __init__(self):
        """Initialize OneHat service with configuration"""
        self.base_url = os.getenv("ONEHAT_BASE_URL", "http://65.2.35.118/one-hat/api/external")
        self.username = os.getenv("ONEHAT_USERNAME", "mukesh")
        self.password = os.getenv("ONEHAT_PASSWORD", "admin")  # Actual password (YWRtaW49 decoded)
        self.hospital_id = int(os.getenv("ONEHAT_HOSPITAL_ID", "445"))
        
        # Validate configuration
        if not all([self.base_url, self.username, self.password, self.hospital_id]):
            logger.warning("⚠️ OneHat configuration incomplete. Some features may not work.")
        
        logger.info(f"🏥 OneHat service initialized for hospital ID: {self.hospital_id}")
    
    def _generate_auth_code(self) -> str:
        """
        Generate authentication code for OneHat API
        Format: base64(username:base64_encoded_password:hospital_id)
        """
        try:
            # First encode password to base64
            password_b64 = base64.b64encode(self.password.encode()).decode()
            
            # Then construct auth string: username:base64_password:hospital_id
            auth_string = f"{self.username}:{password_b64}:{self.hospital_id}"
            
            # Finally encode the whole string to base64
            auth_code = base64.b64encode(auth_string.encode()).decode()
            
            logger.info(f"🔐 Generated auth code for user: {self.username}")
            return auth_code
            
        except Exception as e:
            logger.error(f"❌ Error generating auth code: {e}")
            raise OneHatAuthError(f"Failed to generate auth code: {e}")
    
    async def get_access_token(self) -> str:
        """
        Get access token from OneHat API
        
        Returns:
            str: Access token for API calls
            
        Raises:
            OneHatAuthError: If authentication fails
        """
        try:
            logger.info("🔑 Requesting OneHat access token...")
            
            # Generate auth code
            auth_code = self._generate_auth_code()
            
            # Prepare request
            url = f"{self.base_url}/auth/token"
            params = {
                "grantType": "authorization",
                "code": auth_code
            }
            
            # Make API call
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"❌ OneHat auth failed with status {response.status_code}: {response.text}")
                    raise OneHatAuthError(f"Authentication failed: {response.status_code}")
                
                # Parse response
                data = response.json()
                
                if "data" not in data or "accessToken" not in data["data"]:
                    logger.error(f"❌ Invalid OneHat auth response: {data}")
                    raise OneHatAuthError("Invalid authentication response format")
                
                access_token = data["data"]["accessToken"]
                logger.info("✅ OneHat access token obtained successfully")
                
                return access_token
                
        except httpx.TimeoutException:
            logger.error("❌ OneHat authentication timeout")
            raise OneHatAuthError("Authentication request timed out")
        except httpx.RequestError as e:
            logger.error(f"❌ OneHat authentication network error: {e}")
            raise OneHatAuthError(f"Network error during authentication: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error during OneHat authentication: {e}")
            raise OneHatAuthError(f"Unexpected authentication error: {e}")
    
    async def create_patient(self, name: str, mobile: str, age: int, gender: str) -> int:
        """
        Create a new patient in OneHat system
        
        Args:
            name (str): Patient's full name
            mobile (str): Patient's mobile number
            age (int): Patient's age
            gender (str): Patient's gender (Male/Female/Other)
            
        Returns:
            int: OneHat patient ID
            
        Raises:
            OneHatAPIError: If patient creation fails
        """
        try:
            logger.info(f"👤 Creating OneHat patient: {name}, Mobile: {mobile}")
            
            # Get access token
            access_token = await self.get_access_token()
            
            # Prepare request
            url = f"{self.base_url}/patients/create-patient"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Prepare patient data
            patient_data = {
                "name": name,
                "mobileNo": mobile,
                "age": str(age),  # OneHat expects string
                "gender": gender,
                "hospitalId": self.hospital_id
            }
            
            # Make API call
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=patient_data)
                
                if response.status_code != 200:
                    logger.error(f"❌ OneHat patient creation failed with status {response.status_code}: {response.text}")
                    raise OneHatAPIError(f"Patient creation failed: {response.status_code}")
                
                # Parse response
                data = response.json()
                
                if data.get("status") != "SUCCESS" or "data" not in data:
                    logger.error(f"❌ OneHat patient creation unsuccessful: {data}")
                    raise OneHatAPIError(f"Patient creation unsuccessful: {data.get('message', 'Unknown error')}")
                
                # Extract OneHat patient ID
                onehat_patient_id = int(data["data"])
                
                logger.info(f"✅ OneHat patient created successfully with ID: {onehat_patient_id}")
                return onehat_patient_id
                
        except OneHatAuthError:
            # Re-raise auth errors as-is
            raise
        except httpx.TimeoutException:
            logger.error("❌ OneHat patient creation timeout")
            raise OneHatAPIError("Patient creation request timed out")
        except httpx.RequestError as e:
            logger.error(f"❌ OneHat patient creation network error: {e}")
            raise OneHatAPIError(f"Network error during patient creation: {e}")
        except ValueError as e:
            logger.error(f"❌ Invalid OneHat patient ID format: {e}")
            raise OneHatAPIError(f"Invalid patient ID format: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error during OneHat patient creation: {e}")
            raise OneHatAPIError(f"Unexpected patient creation error: {e}")
    
    async def test_connection(self) -> bool:
        """
        Test OneHat API connection
        
        Returns:
            bool: True if connection successful
        """
        try:
            logger.info("🔍 Testing OneHat API connection...")
            access_token = await self.get_access_token()
            logger.info("✅ OneHat API connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ OneHat API connection test failed: {e}")
            return False

# Global instance
onehat_service = OneHatService()
