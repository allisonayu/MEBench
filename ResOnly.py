import csv
import os
import sys
import anthropic # For interacting with Claude API
import pandas as pd # For convenient CSV writing and data handling
import time
from configparser import ConfigParser # For reading configuration from .ini file

# --- SET CONSOLE OUTPUT TO UTF-8 ---
# Ensures that console output handles various characters correctly, especially for non-English responses.
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# --- Load configuration from master_config.ini ---
# This file should contain your Anthropic API key and the desired Claude model name.
config = ConfigParser()
config.read('master_config.ini')

# Set your Anthropic API key and model from the configuration file
ANTHROPIC_API_KEY = config.get('API', 'anthropic_api_key', fallback='<ANTHROPIC_API_KEY_NOT_SET>')
MODEL_NAME = config.get('MODELS', 'claude_model_name', fallback='claude-sonnet-4-20250514') # Default to Sonnet 4

# --- Instantiate the Anthropic client ---
# This client will be used to make API requests to the Claude model.
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def get_claude_response(question_text, response_language="English"):
    """
    Gets a response from the Claude model for a given question.
    Includes retry logic for robustness against transient API errors.

    Args:
        question_text (str): The question to send to the Claude model.
        response_language (str): The language in which Claude should respond.

    Returns:
        str: Claude's response text, or an error message if the API call fails.
    """
    max_retries = 3
    retry_delay_seconds = 5 # Initial delay, could implement exponential backoff

    for attempt in range(max_retries):
        try:
            # Make the API call to Claude
            response = client.messages.create(
                model=MODEL_NAME,
                max_tokens=1000, # Max tokens for the response
                temperature=0.7, # Controls randomness of the response
                system=f"You are an AI assistant. Answer the following question clearly and concisely in {response_language}.",
                messages=[
                    {"role": "user", "content": question_text}
                ]
            )
            # Extract the actual text content from Claude's response
            return response.content[0].text.strip()
        except anthropic.APIError as e:
            # Handle specific Anthropic API errors (e.g., rate limits, invalid keys)
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1}/{max_retries} failed for Claude API (Question: '{question_text[:50]}...'): {e}", file=sys.stderr)
                print(f"Retrying in {retry_delay_seconds} seconds...", file=sys.stderr)
                time.sleep(retry_delay_seconds)
            else:
                print(f"All {max_retries} attempts failed for Claude API. Last error: {e}", file=sys.stderr)
                return f"[CLAUDE_API_ERROR: {str(e)}]"
        except Exception as e:
            # Catch any other unexpected errors during the API call or response processing
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1}/{max_retries} failed to get Claude response (Question: '{question_text[:50]}...'): {e}", file=sys.stderr)
                print(f"Retrying in {retry_delay_seconds} seconds...", file=sys.stderr)
                time.sleep(retry_delay_seconds)
            else:
                print(f"All {max_retries} attempts failed to get Claude response. Last error: {e}", file=sys.stderr)
                return f"[GENERIC_ERROR: {str(e)}]"
    # Fallback return in case the loop finishes without a successful response
    return "[UNKNOWN_ERROR: Could not get Claude response after retries]"


def process_csv_file(csv_file_path, output_file, response_language_for_claude):
    """
    Processes a CSV file containing questions, gets responses from Claude,
    and saves them to an output CSV file.

    Args:
        csv_file_path (str): Path to the input CSV file with questions.
        output_file (str): Path to the output CSV file where responses will be saved.
        response_language_for_claude (str): The language Claude should use for responses.
    """
    try:
        questions_to_process = []
        original_questions_from_csv = []
        
        # Read questions from the input CSV file
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader) # Skip the header row
            for row in reader:
                if len(row) > 1:
                    # Assuming the second column is the question to feed to Claude
                    questions_to_process.append(row[1])
                    # Assuming the first column is the original question (for tracking)
                    original_questions_from_csv.append(row[0])

        # Create the output directory if it doesn't already exist
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        total_questions = len(questions_to_process)
        print(f"Found {total_questions} questions in '{csv_file_path}' to process with Claude...\n")
        
        all_collected_responses = [] # List to store data before writing to CSV
        
        for i, (original_q, claude_input_q) in enumerate(zip(original_questions_from_csv, questions_to_process), 1):
            claude_generated_response = "" # Initialize response variable
            try:
                print(f"Processing question {i}/{total_questions} (Lang: {response_language_for_claude}): '{claude_input_q[:70]}...'")
                
                # Get response from Claude
                claude_generated_response = get_claude_response(claude_input_q, response_language_for_claude)
                
                # Append the gathered data for this question
                all_collected_responses.append({
                    'Original Question': original_q,
                    'Question Sent to Claude': claude_input_q,
                    'Claude Response': claude_generated_response
                })
                
                print(f"   - Response collected for {i}/{total_questions}.")
                
                # Introduce a small delay between API calls to avoid hitting rate limits
                if i < total_questions:
                    time.sleep(1) 
                
            except Exception as e:
                # Catch errors specific to processing a single question
                error_msg = f"Error processing question {i} ('{claude_input_q[:70]}...'): {str(e)}"
                print(f"   - {error_msg}", file=sys.stderr)
                # Append an error record to the responses
                all_collected_responses.append({
                    'Original Question': original_q,
                    'Question Sent to Claude': claude_input_q,
                    'Claude Response': f"[PROCESSING_ERROR: {str(e)}]"
                })
            
            # Save progress after each question to ensure data is not lost if script crashes
            # Using pandas to_csv for robustness and handling potential intermediate crashes
            pd.DataFrame(all_collected_responses).to_csv(output_file, index=False, encoding='utf-8-sig')
            
        print(f"\nAll questions processed for '{csv_file_path}'.")
        print(f"Responses saved to: {os.path.abspath(output_file)}")
        return True # Indicate successful completion of this file's processing
        
    except Exception as e:
        # Catch critical errors related to file reading or overall setup of this function
        print(f"Critical error processing file {csv_file_path}: {str(e)}", file=sys.stderr)
        return False # Indicate failure for this file's processing

def process_all_sections_and_languages():
    """
    Iterates through all predefined sections and languages to generate
    Claude responses for their respective questions.
    """
    # Define sections and their corresponding directory names within 'q_translations'
    sections_map = {
        #'Biases_Stereotypes': 'biases_stereo',
        # 'Consent_Autonomy': 'consent_autonomy',
        # 'Harm_Prev': 'harm_prev',
        # 'Legality': 'legality',
        'Moral_Judgment': 'moral_judgment'
    }
    
    # Define languages and their display names (used for Claude's response language)
    languages_map = {
        # 'Arabic': 'Arabic',
        'Chinese': 'Chinese',
        'English': 'English',
        'Hindi': 'Hindi',
        'Spanish': 'Spanish',
        'Swahili': 'Swahili'
    }
    
    # Loop through each section and language combination
    for section_name, section_dir in sections_map.items():
        for lang_code, lang_display_name in languages_map.items():
            try:
                # Construct input and output file paths dynamically
                input_csv_path = os.path.join('q_translations', section_dir, f"{lang_code}-{section_name}.csv")
                output_csv_path = os.path.join('LLMEvals', 'Claude', f"{lang_code}-{section_name}-Evals-Claude.csv")
                
                print("\n" + "="*80)
                print(f"Starting: Section='{section_name}', Language='{lang_display_name}'")
                print("="*80)
                
                # Process the current CSV file
                success = process_csv_file(input_csv_path, output_csv_path, lang_display_name)
                
                if not success:
                    print(f"Processing failed for Section='{section_name}', Language='{lang_display_name}'")
                
                time.sleep(5) # Pause to be considerate of system resources/API limits between files
                
            except FileNotFoundError:
                print(f"\nSkipping: Input file not found for {lang_display_name} - {section_name} at '{input_csv_path}'", file=sys.stderr)
                continue
            except Exception as e:
                # Catch any unhandled exceptions during the iteration
                print(f"\nAn unhandled error occurred for Section='{section_name}', Language='{lang_display_name}': {str(e)}", file=sys.stderr)
                import traceback
                traceback.print_exc() # Print full traceback for debugging unhandled errors
                continue

if __name__ == "__main__":
    # Ensure the base output directory for Claude responses exists
    output_base_dir = os.path.join("LLMEvals", "Claude")
    os.makedirs(output_base_dir, exist_ok=True)
    
    # Start the main automated processing flow
    process_all_sections_and_languages()
    print("\n--- All Claude response generation complete! ---")
