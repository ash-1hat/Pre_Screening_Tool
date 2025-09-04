"""
Test script to test Gemini API integration
"""

import os
from google import genai
from google.genai import types
from core.config import settings

class GeminiTester:
    def __init__(self):
        # Load environment variables from .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=api_key)
        self.model = 'gemini-2.5-flash'
        print(f"🔧 Testing with Gemini model: {self.model}")
        print(f"🔑 API Key loaded: {'*' * 20}{api_key[-8:] if len(api_key) > 8 else '***'}")
        
    def test_simple_prompt(self):
        """Test with a simple, non-medical prompt"""
        print("\n" + "="*50)
        print("TEST 1: Simple Non-Medical Prompt")
        print("="*50)
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents='What is 2+2? Give me a one sentence answer.',
                config=types.GenerateContentConfig(
                    max_output_tokens=50,
                    temperature=0.1
                )
            )
            
            # Debug response object
            print(f"🔍 Response object: {type(response)}")
            print(f"🔍 Response text: {response.text}")
            
            result = response.text.strip() if response.text else ""
            print(f"✅ Response: '{result}'")
            print(f"📊 Length: {len(result)} characters")
            
            if not result:
                print("❌ EMPTY RESPONSE DETECTED!")
                print(f"🔍 Full response: {response}")
            
            return result, "gemini-simple"
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None, None
    
    def test_medical_prompt(self):
        """Test with a medical prompt similar to our use case"""
        print("\n" + "="*50)
        print("TEST 2: Medical Prompt (Similar to our use case)")
        print("="*50)
        
        try:
            medical_input = """You are a medical expert conducting a patient interview.

PATIENT: John, 30y, Male
QUESTION NUMBER: 1/6

Ask ONE focused medical question to understand their main health concern.
Return only the question text, no additional commentary."""

            response = self.client.models.generate_content(
                model=self.model,
                contents=medical_input,
                config=types.GenerateContentConfig(
                    system_instruction="You are a helpful medical assistant conducting patient interviews.",
                    max_output_tokens=250,
                    temperature=0.3
                )
            )
            
            result = response.text.strip() if response.text else ""
            print(f"✅ Response: '{result}'")
            print(f"📊 Length: {len(result)} characters")
            
            if not result:
                print("❌ EMPTY RESPONSE DETECTED!")
                print(f"🔍 Full response: {response}")
            
            return result, "gemini-medical"
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None, None
    
    def test_follow_up_medical_prompt(self, previous_response_id):
        """Test follow-up medical question (this was problematic with GPT-5)"""
        print("\n" + "="*50)
        print("TEST 3: Follow-up Medical Question")
        print("="*50)
        
        try:
            followup_input = """Generate the next medical question based on:

PATIENT: John, 30y, Male
QUESTION NUMBER: 2/6
"I DON'T KNOW" COUNT: 0/2

CONVERSATION HISTORY:
Q1: What is your main health concern today?
A1: I have severe knee pain

INSTRUCTIONS:
- Ask ONE focused medical question only
- Focus on understanding the knee pain better
- Keep question clear, specific, and empathetic

Return only the question text, no additional commentary."""

            print(f"🔗 Previous context: {previous_response_id}")
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=followup_input,
                config=types.GenerateContentConfig(
                    system_instruction="You are a medical expert. Ask focused diagnostic questions to understand patient symptoms.",
                    max_output_tokens=250,
                    temperature=0.3
                )
            )
            
            result = response.text.strip() if response.text else ""
            print(f"✅ Response: '{result}'")
            print(f"📊 Length: {len(result)} characters")
            
            if not result:
                print("❌ EMPTY RESPONSE DETECTED!")
                print("🔍 This would be a Gemini issue!")
                print(f"🔍 Full response: {response}")
            else:
                print("🎉 SUCCESS! Gemini handled follow-up medical question!")
            
            return result, "gemini-followup"
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None, None
    
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Gemini API Tests")
        google_api_key = os.getenv('GOOGLE_API_KEY', '')
        print(f"🔑 API Key: {'*' * 20}{google_api_key[-8:] if len(google_api_key) > 8 else '***'}")
        
        # Test 1: Simple prompt
        simple_result, simple_id = self.test_simple_prompt()
        
        # Test 2: Medical prompt
        medical_result, medical_id = self.test_medical_prompt()
        
        # Test 3: Follow-up (this was problematic with GPT-5)
        followup_result, followup_id = self.test_follow_up_medical_prompt(medical_id)
        
        # Summary
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        print(f"Test 1 (Simple): {'✅ PASS' if simple_result else '❌ FAIL'}")
        print(f"Test 2 (Medical): {'✅ PASS' if medical_result else '❌ FAIL'}")
        print(f"Test 3 (Follow-up): {'✅ PASS' if followup_result else '❌ FAIL'}")
        
        if followup_result:
            print("\n🎉 SUCCESS:")
            print("- Gemini successfully handles follow-up medical questions")
            print("- No empty response issues like GPT-5")
            print("- Ready to replace GPT-5 in production!")
        else:
            print("\n❌ ISSUE DETECTED:")
            print("- Gemini also has issues with medical questions")
            print("- Need to investigate further")

def main():
    tester = GeminiTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
