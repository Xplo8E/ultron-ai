# ultron/engine/reviewer.py
import os
import json
import re
from typing import Optional, List

from google import genai
from google.genai import types
from dotenv import load_dotenv

from ..models.data_models import BatchReviewData
from ..core.constants import (
    AVAILABLE_MODELS, DEFAULT_MODEL_KEY, DEFAULT_REVIEW_PROMPT_TEMPLATE,
    USER_CONTEXT_TEMPLATE, USER_FRAMEWORK_CONTEXT_TEMPLATE,
    USER_SECURITY_REQUIREMENTS_TEMPLATE, MULTI_FILE_INPUT_FORMAT_DESCRIPTION,
    MODELS_SUPPORTING_THINKING  # MODIFIED: Import the new set
)

load_dotenv()
GEMINI_API_KEY_LOADED = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY_LOADED:
    genai_client = genai.Client(api_key=GEMINI_API_KEY_LOADED)
else:
    genai_client = None


def clean_json_response(text: str) -> str:
    """
    Cleans and repairs a JSON string from an LLM response.
    This function is designed to be robust against common LLM-generated syntax errors.
    """
    # Remove any text before the first '{' and after the last '}'
    try:
        text = text[text.find('{') : text.rfind('}') + 1]
    except IndexError:
        return "" # Return empty if no JSON object is found

    # Add missing commas between adjacent JSON objects in arrays.
    # e.g., transforms '[{...} {...}]' to '[{...}, {...}]'
    text = re.sub(r'}\s*\{', '},{', text)
    
    # Add missing commas between adjacent arrays in arrays.
    # e.g., transforms '[[...][...]]' to '[[...],[...]]'
    text = re.sub(r']\s*\[', '],[', text)

    # Add missing commas after a closing brace/bracket followed by a new key.
    # e.g., transforms '{...} "key": ...' to '{...}, "key": ...'
    text = re.sub(r'([}\]])\s*(")', r'\1,\2', text)

    # Add missing commas after a string value followed by a new key.
    # e.g., transforms '"value" "key": ...' to '"value", "key": ...'
    text = re.sub(r'("\s*:\s*".*?")\s*(")', r'\1,\2', text)
    
    # Add missing commas after a number/boolean/null value followed by a new key.
    text = re.sub(r'(true|false|null|-?\d+(\.\d+)?)\s*(")', r'\1,\2', text)

    # Remove trailing commas before a closing brace or bracket.
    text = re.sub(r',\s*([}\]])', r'\1', text)

    return text


def get_gemini_review(
    code_batch: str,
    primary_language_hint: str,
    model_key: str = DEFAULT_MODEL_KEY,
    additional_context: Optional[str] = None,
    frameworks_libraries: Optional[str] = None,
    security_requirements: Optional[str] = None,
    verbose: bool = False,
) -> Optional[BatchReviewData]:
    """
    Sends a batch of code files (formatted as a single string) to the Gemini API for review.
    """
    if not genai_client:
        return BatchReviewData(error="GEMINI_API_KEY not configured.")

    user_context_section_str = USER_CONTEXT_TEMPLATE.format(additional_context=additional_context) if additional_context and additional_context.strip() else ""
    frameworks_list_str = frameworks_libraries if frameworks_libraries and frameworks_libraries.strip() else "Not specified"
    user_framework_context_section_str = USER_FRAMEWORK_CONTEXT_TEMPLATE.format(frameworks_libraries=frameworks_list_str) if frameworks_libraries and frameworks_libraries.strip() else ""
    user_security_requirements_section_str = USER_SECURITY_REQUIREMENTS_TEMPLATE.format(security_requirements=security_requirements) if security_requirements and security_requirements.strip() else ""

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
    print(f"⚡ ULTRON COGNITIVE CORE: {actual_model_name.upper()} ONLINE")

    total_input_tokens_count = 0
    try:
        token_response = genai_client.models.count_tokens(
            model=actual_model_name,
            contents=prompt
        )
        total_input_tokens_count = token_response.total_tokens
        print(f"🧠 Analyzing {total_input_tokens_count} data fragments...")
    except Exception as e:
        print(f"⚠️ Token analysis incomplete: {e}")

    try:
        print("🔴 Scanning for imperfections...")
        
        # ==================== MODIFIED: CONDITIONAL THINKING CONFIG ====================
        
        # Start with the base configuration
        generation_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
            top_k=20,
            top_p=0.8,
            candidate_count=1,
            max_output_tokens=8192,
        )

        # Conditionally add the thinking_config if the model supports it
        if model_key in MODELS_SUPPORTING_THINKING:
            if verbose:
                print("[dim]🤖 Thinking-enabled model detected. Activating cognitive feedback loop...[/dim]")
            generation_config.thinking_config=types.GenerationConfigThinkingConfig(
                include_thoughts=True,
                thinking_budget=2048,
            )
        
        # =============================================================================

        response = genai_client.models.generate_content(
            model=actual_model_name,
            contents=prompt,
            config=generation_config # Use the conditionally built config
        )

        thought_parts: List[str] = []
        payload_parts: List[str] = []
        
        # This parsing logic is now naturally robust. If thinking wasn't enabled,
        # part.thought will never be true, and all text goes into payload_parts.
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.thought:
                    # This is part of the model's thought process
                    if part.text:
                        thought_parts.append(part.text)
                else:
                    # This is part of the final JSON payload
                    if part.text:
                        payload_parts.append(part.text)
                        
        # Combine the collected parts into final strings
        full_thoughts_text = "".join(thought_parts)
        raw_json_text = "".join(payload_parts)
        
        # =================================================================================

        if verbose:
            print("\n=== RAW RESPONSE FROM SERVER ===")
            print(f"Response object type: {type(response)}")
            # Conditionally print the thinking-related metadata
            if model_key in MODELS_SUPPORTING_THINKING:
                print(f"Token count for `Thinking`: {response.usage_metadata.thoughts_token_count}")
                print("Model thoughts:")
                if full_thoughts_text:
                    print(full_thoughts_text)
                else:
                    print("(No thoughts were returned by the model for this request)")
            else:
                 print("Model thoughts: (Not requested for this model)")
                 
            print(f"\nResponse object dict: {vars(response)}")
            print("=== END RAW RESPONSE FROM SERVER ===\n")

        if not response.candidates:
            error_message = "No content generated by API for the batch."
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                error_message = f"Batch content generation blocked. Reason: {response.prompt_feedback.block_reason}."
                if response.prompt_feedback.safety_ratings:
                    error_message += f" Safety Ratings: {response.prompt_feedback.safety_ratings}"
            return BatchReviewData(error=error_message)
        
        if verbose:
            print(f"\nExtracted complete JSON text (length: {len(raw_json_text)}):")
            print(raw_json_text)

        if not raw_json_text.strip():
            return BatchReviewData(
                error="Empty response from API (JSON payload was empty)",
                overall_batch_summary="Error: Empty response received",
                file_reviews=[],
                llm_processing_notes="API returned an empty payload."
            )

        try:
            # First, try to parse directly
            parsed_data = json.loads(raw_json_text)
            if verbose:
                print("\nSuccessfully parsed raw JSON response")
            return BatchReviewData(**parsed_data)
        except json.JSONDecodeError as json_err:
            if verbose:
                print(f"\nJSON parsing error: {json_err}")
                print("Attempting to clean and fix JSON...")

            # If it fails, use our new robust cleaner
            cleaned_json = clean_json_response(raw_json_text)
            
            if verbose:
                print(f"Cleaned JSON (length: {len(cleaned_json)}):")
                print(cleaned_json[:500] + "..." if len(cleaned_json) > 500 else cleaned_json)
            
            try:
                # Retry parsing with the cleaned string
                parsed_data = json.loads(cleaned_json)
                if verbose:
                    print("Successfully parsed cleaned JSON")
                # Add a note that the response was repaired
                review_data = BatchReviewData(**parsed_data)
                notes = "LLM response required JSON syntax correction before parsing."
                review_data.llm_processing_notes = f"{notes}\n{review_data.llm_processing_notes}" if review_data.llm_processing_notes else notes
                return review_data
            except json.JSONDecodeError as e:
                # If it still fails, return a detailed error
                error_msg = f"Failed to parse response: {str(e)}"
                if verbose:
                    print(f"Failed to parse even after cleaning: {error_msg}")
                fallback_response = {
                    "overallBatchSummary": "Response parsing failed due to truncated or malformed JSON that could not be repaired.",
                    "fileReviews": [],
                    "llmProcessingNotes": f"JSON parsing error: {str(e)}. Original error: {str(json_err)}.",
                    "error": error_msg
                }
                if verbose:
                    print("Returning fallback response due to parsing failures")
                return BatchReviewData(**fallback_response)

    except Exception as e:
        err_msg = f"Gemini API call error for batch: {e}"
        try:
            if 'response' in locals() and response.prompt_feedback and response.prompt_feedback.block_reason:
                err_msg += f". API Block Reason: {response.prompt_feedback.block_reason}"
        except (AttributeError, NameError): pass 
        return BatchReviewData(error=err_msg)