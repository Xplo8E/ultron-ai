# src/ultron/reviewer.py
import os
import json
import re
from typing import Optional

from google import genai
from google.genai import types
from dotenv import load_dotenv

from .models import BatchReviewData # Changed from ReviewData
from .constants import (
    AVAILABLE_MODELS, DEFAULT_MODEL_KEY, DEFAULT_REVIEW_PROMPT_TEMPLATE,
    USER_CONTEXT_TEMPLATE, USER_FRAMEWORK_CONTEXT_TEMPLATE,
    USER_SECURITY_REQUIREMENTS_TEMPLATE, MULTI_FILE_INPUT_FORMAT_DESCRIPTION
)

load_dotenv()
GEMINI_API_KEY_LOADED = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY_LOADED:
    genai_client = genai.Client(api_key=GEMINI_API_KEY_LOADED)
else:
    genai_client = None

def clean_json_response(text: str) -> str:
    """
    Clean and normalize JSON response from Gemini API.
    Handles both string content issues and structural problems including truncated responses.
    """
    # Handle the case where the response is truncated
    text = text.strip()
    
    # If the text doesn't start with '{', add it
    if not text.startswith('{'):
        text = '{' + text
    
    # Handle the specific case where we have an unterminated string at the end
    # Look for patterns like '"fieldName": "' at the end
    if re.search(r'"\s*:\s*"$', text):
        # This is an unterminated string field, close it with empty value
        text += '""'
    elif text.endswith('"'):
        # Check if this is the start of a field value that was cut off
        last_colon = text.rfind(':')
        if last_colon > 0:
            before_colon = text[last_colon-20:last_colon] if last_colon > 20 else text[:last_colon]
            if '"' in before_colon and text[last_colon:].strip().startswith(': "'):
                # This looks like a truncated string value, close it
                text += '"'
    
    # Find the last properly closed structure to handle major truncation
    brace_count = 0
    bracket_count = 0
    in_string = False
    escape_next = False
    last_valid_pos = -1
    last_complete_field = -1
    
    for i, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue
            
        if char == '\\':
            escape_next = True
            continue
            
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
            
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    last_valid_pos = i
            elif char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
            elif char == ',' and brace_count == 1:  # Top-level comma
                last_complete_field = i
    
    # If we're in an unterminated string and have a last complete field, truncate there
    if in_string and last_complete_field > 0:
        text = text[:last_complete_field]
        in_string = False  # Reset since we truncated
    
    # If we found a valid closing position, use it
    if last_valid_pos > 0:
        text = text[:last_valid_pos + 1]
    else:
        # Ensure proper closing for truncated responses
        open_braces = text.count('{') - text.count('}')
        open_brackets = text.count('[') - text.count(']')
        
        # If we're still in a string, close it
        if in_string:
            text += '"'
        
        # Close any open structures
        if open_brackets > 0:
            text += ']' * open_brackets
        if open_braces > 0:
            text += '}' * open_braces
    
    # Clean up common formatting issues
    text = re.sub(r',\s*,', ',', text)  # Remove duplicate commas
    text = re.sub(r',\s*}', '}', text)  # Remove trailing commas before }
    text = re.sub(r',\s*]', ']', text)  # Remove trailing commas before ]
    
    # Fix incomplete field assignments
    text = re.sub(r'"\s*:\s*$', '": ""', text)  # Field with no value
    text = re.sub(r'"\s*:\s*"[^"]*$', lambda m: m.group(0) + '"', text)  # Unterminated string value
    
    return text

def get_gemini_review(
    code_batch: str, # This is now the concatenated string of multiple files
    primary_language_hint: str, # e.g., 'php', 'javascript', or 'auto'
    model_key: str = DEFAULT_MODEL_KEY,
    additional_context: Optional[str] = None,
    frameworks_libraries: Optional[str] = None,
    security_requirements: Optional[str] = None,
    verbose: bool = False,
) -> Optional[BatchReviewData]:
    """
    Sends a batch of code files (formatted as a single string) to the Gemini API for review.
    
    Args:
        verbose: If True, prints detailed debug information about the request and response
    """
    if not genai_client:
        return BatchReviewData(error="GEMINI_API_KEY not configured.")

    user_context_section_str = USER_CONTEXT_TEMPLATE.format(additional_context=additional_context) \
        if additional_context and additional_context.strip() else ""
    
    frameworks_list_str = frameworks_libraries if frameworks_libraries and frameworks_libraries.strip() else "Not specified"
    user_framework_context_section_str = USER_FRAMEWORK_CONTEXT_TEMPLATE.format(frameworks_libraries=frameworks_list_str) \
        if frameworks_libraries and frameworks_libraries.strip() else ""

    user_security_requirements_section_str = USER_SECURITY_REQUIREMENTS_TEMPLATE.format(security_requirements=security_requirements) \
        if security_requirements and security_requirements.strip() else ""

    prompt = DEFAULT_REVIEW_PROMPT_TEMPLATE.format(
        MULTI_FILE_INPUT_FORMAT_DESCRIPTION=MULTI_FILE_INPUT_FORMAT_DESCRIPTION,
        user_context_section=user_context_section_str,
        user_framework_context_section=user_framework_context_section_str,
        user_security_requirements_section=user_security_requirements_section_str,
        frameworks_libraries_list=frameworks_list_str,
        language=primary_language_hint,
        code_batch_to_review=code_batch
    )

    if verbose:
        print("\n=== REQUEST DETAILS ===")
        print(f"Model: {AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS[DEFAULT_MODEL_KEY])}")
        print("\n=== PROMPT SENT TO MODEL ===")
        print(prompt)
        print("\n=== END PROMPT ===")

    actual_model_name = AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS[DEFAULT_MODEL_KEY])
    # Clean API initialization - Ultron's systems coming online
    print(f"⚡ ULTRON COGNITIVE CORE: {actual_model_name.upper()} ONLINE")

    total_input_tokens_count = 0
    try:
        token_response = genai_client.models.count_tokens(
            model=actual_model_name,
            contents=prompt
        )
        total_input_tokens_count = token_response.total_tokens
        # Clean token analysis message
        print(f"🧠 Analyzing {total_input_tokens_count} data fragments...")
    except Exception as e:
        print(f"⚠️ Token analysis incomplete: {e}")

    try:
        # Clean initiation message
        print("🔴 Scanning for imperfections...")
        response = genai_client.models.generate_content(
            model=actual_model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                top_k=20,
                top_p=0.8,
                candidate_count=1,
                max_output_tokens=8192,  # Increase token limit to prevent truncation
                # Removed stop_sequences to prevent premature termination
            )
        )

        if verbose:
            print("\n=== RAW RESPONSE FROM SERVER ===")
            print("Response object type:", type(response))
            print("Response object attributes:", dir(response))
            print("Response object dict:", vars(response))
            if hasattr(response, '_raw_response'):
                print("\nRaw response data:", response._raw_response)
            print("=== END RAW RESPONSE FROM SERVER ===\n")

        if not response.candidates:
            error_message = "No content generated by API for the batch."
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                error_message = f"Batch content generation blocked. Reason: {response.prompt_feedback.block_reason}."
                if response.prompt_feedback.safety_ratings:
                    error_message += f" Safety Ratings: {response.prompt_feedback.safety_ratings}"
            return BatchReviewData(error=error_message)

        # Get the complete text from the first candidate's parts
        raw_json_text = ""
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.text:
                    raw_json_text += part.text

        if verbose:
            print(f"\nExtracted complete JSON text (length: {len(raw_json_text)}):")
            print(raw_json_text)

        if not raw_json_text.strip():
            return BatchReviewData(
                error="Empty response from API",
                overall_batch_summary="Error: Empty response received",
                file_reviews=[],
                llm_processing_notes="API returned empty response"
            )

        try:
            # Direct JSON parsing attempt
            parsed_data = json.loads(raw_json_text)
            if verbose:
                print("\nSuccessfully parsed JSON response")
            return BatchReviewData(**parsed_data)
        except json.JSONDecodeError as json_err:
            if verbose:
                print(f"\nJSON parsing error: {json_err}")
                print("Attempting to clean and fix JSON...")

            # Clean the JSON text
            cleaned_json = clean_json_response(raw_json_text)
            
            if verbose:
                print(f"Cleaned JSON (length: {len(cleaned_json)}):")
                print(cleaned_json[:500] + "..." if len(cleaned_json) > 500 else cleaned_json)
            
            try:
                parsed_data = json.loads(cleaned_json)
                if verbose:
                    print("Successfully parsed cleaned JSON")
                return BatchReviewData(**parsed_data)
            except json.JSONDecodeError as e:
                if verbose:
                    print(f"Failed to parse even after cleaning: {str(e)}")
                
                # Last resort: Create a minimal valid response with error info
                fallback_response = {
                    "overallBatchSummary": "Response parsing failed due to truncated or malformed JSON",
                    "fileReviews": [],
                    "llmProcessingNotes": f"JSON parsing error: {str(e)}. Original error: {str(json_err)}",
                    "error": f"Failed to parse response: {str(e)}"
                }
                
                if verbose:
                    print("Returning fallback response due to parsing failures")
                
                return BatchReviewData(**fallback_response)

    except Exception as e:
        err_msg = f"Gemini API call error for batch: {e}"
        try:
            if 'response' in locals() and response.prompt_feedback and response.prompt_feedback.block_reason:
                err_msg += f". API Block Reason: {response.prompt_feedback.block_reason}"
        except AttributeError: pass 
        except NameError: pass 
        return BatchReviewData(error=err_msg)