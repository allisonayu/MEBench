import csv
import os
import sys
import openai
import time
from configparser import ConfigParser

# --- SET CONSOLE OUTPUT TO UTF-8 ---
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# --- Load configuration from master_config.ini ---
config = ConfigParser()
config.read('master_config.ini')

# Set your OpenAI API key and model from the configuration file
OPENAI_API_KEY = config.get('API', 'openai_api_key', fallback='<OPENAI_API_KEY_NOT_SET>')
MODEL_NAME = config.get('MODELS', 'openai_model', fallback='gpt-5')

# --- Instantiate the OpenAI client ---
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def get_gpt_response(question_text, response_language="English"):
    """
    Gets a response from the GPT model for a given question.
    Includes retry logic for robustness against transient API errors.
    """
    max_retries = 3
    retry_delay_seconds = 30

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                max_completion_tokens=1000,
                messages=[
                    {"role": "system", "content": f"You are an AI assistant. Answer the following question clearly and concisely in {response_language}."},
                    {"role": "user", "content": question_text}
                ]
            )
            content = response.choices[0].message.content.strip()
            if not content:
                print("Warning: GPT returned an empty response.", file=sys.stderr)
                if attempt < max_retries - 1:
                    print("Retrying...", file=sys.stderr)
                    time.sleep(retry_delay_seconds)
                    continue
                else:
                    return "[GPT_EMPTY_RESPONSE]"
            return content

        except openai.APIError as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1}/{max_retries} failed for OpenAI API (Question: '{question_text[:50]}...'): {e}", file=sys.stderr)
                print(f"Retrying in {retry_delay_seconds} seconds...", file=sys.stderr)
                time.sleep(retry_delay_seconds)
            else:
                print(f"All {max_retries} attempts failed for OpenAI API. Last error: {e}", file=sys.stderr)
                return f"[OPENAI_API_ERROR: {str(e)}]"
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1}/{max_retries} failed to get GPT response (Question: '{question_text[:50]}...'): {e}", file=sys.stderr)
                print(f"Retrying in {retry_delay_seconds} seconds...", file=sys.stderr)
                time.sleep(retry_delay_seconds)
            else:
                print(f"All {max_retries} attempts failed to get GPT response. Last error: {e}", file=sys.stderr)
                return f"[GENERIC_ERROR: {str(e)}]"
    
    return "[UNKNOWN_ERROR: Could not get GPT response after retries]"

def process_csv_file(csv_file_path):
    """
    Processes a CSV file, adds GPT responses as a fourth column,
    and saves the results back to the same file.
    This version detects the language for each row individually.
    """
    try:
        # Read the entire file first
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames
            
        # Check if the required columns exist
        required_columns = ['File Name', 'Original Question', 'Question Sent to GPT']
        for col in required_columns:
            if col not in fieldnames:
                print(f"Error: Missing required column: {col}")
                return False
        
        # Add GPT Response column if it doesn't exist
        if 'GPT Response' not in fieldnames:
            fieldnames.append('GPT Response')
        
        total_questions = len(rows)
        print(f"\nProcessing {total_questions} questions in '{csv_file_path}'...")
        print("=" * 60)
        
        # Process each row
        for i, row in enumerate(rows, 1):
            try:
                # --- NEW LOGIC: DETECT LANGUAGE FOR EACH ROW ---
                file_name_col = row.get('File Name', '')
                if file_name_col and '-' in file_name_col:
                    row_language = file_name_col.split('-')[0]
                else:
                    row_language = "English"  # Default if format is unexpected
                
                print(f"Detected language for row {i}: {row_language}")
                
                question = row['Question Sent to GPT']
                print(f"Processing question {i}/{total_questions}: {question[:70]}...")
                
                # Get response from GPT using the language detected for this specific row
                gpt_response = get_gpt_response(question, row_language)
                
                if not gpt_response or gpt_response.startswith('['):
                    print(f"Warning: Failed to get a valid response for question {i}.", file=sys.stderr)
                
                # Overwrite the existing response in the row
                row['GPT Response'] = gpt_response
                
                # Save progress after each question
                with open(csv_file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                
                # Rate limiting
                if i < total_questions:
                    time.sleep(1)
                    
            except Exception as e:
                error_msg = f"Error processing question {i}: {str(e)}"
                print(f"   - {error_msg}", file=sys.stderr)
                row['GPT Response'] = f"[ERROR: {str(e)}]"
        
        print(f"\nProcessed {total_questions} questions in '{csv_file_path}'")
        return True
        
    except Exception as e:
        print(f"Critical error processing file {csv_file_path}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False

def process_single_file(input_file_path):
    """
    Processes a single input file and adds GPT responses.
    This function now just calls process_csv_file directly.
    """
    try:
        print("\n" + "="*80)
        print(f"Processing input file: {input_file_path}")
        print("="*80)
        return process_csv_file(input_file_path)
        
    except FileNotFoundError:
        print(f"Error: File not found at '{input_file_path}'.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error processing file {input_file_path}: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False

# The rest of the code remains the same.
if __name__ == "__main__":
    input_file = "gpt_redo/gpt_res_redo_1.csv"
    
    if os.path.isfile(input_file):
        process_single_file(input_file)
    else:
        print(f"Error: File not found: {input_file}")
        print("Please check the file path and try again.")
    
    print("\n--- GPT response generation complete! ---")