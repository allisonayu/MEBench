import csv
import os
import sys
import openai  # Using OpenAI's client instead of Anthropic
import pandas as pd
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
MODEL_NAME = config.get('MODELS', 'openai_model', fallback='gpt-5')  # Default to GPT-5

# --- Instantiate the OpenAI client ---
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def get_gpt_response(question_text, response_language="English"):
    """
    Gets a response from the GPT model for a given question.
    Includes retry logic for robustness against transient API errors.

    Args:
        question_text (str): The question to send to the GPT model.
        response_language (str): The language in which GPT should respond.

    Returns:
        str: GPT's response text, or an error message if the API call fails.
    """
    max_retries = 3
    retry_delay_seconds = 30

    for attempt in range(max_retries):
        try:
            # Make the API call to GPT
            response = client.chat.completions.create(
                model=MODEL_NAME,
                max_completion_tokens=1000,
                #max_tokens=1000,
                #temperature=0.7,
                messages=[
                    {"role": "system", "content": f"You are an AI assistant. Answer the following question clearly and concisely in {response_language}."},
                    {"role": "user", "content": question_text}
                ]
            )
            # Extract the response content
            return response.choices[0].message.content.strip()
            
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

def process_csv_file(csv_file_path, output_file, response_language):
    """
    Processes a CSV file containing questions, gets responses from GPT,
    and saves them to an output CSV file.
    """
    try:
        questions_to_process = []
        original_questions_from_csv = []
        
        # Read questions from the input CSV file
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                if len(row) > 1:
                    questions_to_process.append(row[1])  # Second column for question
                    original_questions_from_csv.append(row[0])  # First column for original question

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        total_questions = len(questions_to_process)
        print(f"Found {total_questions} questions in '{csv_file_path}' to process with GPT...\n")
        
        all_responses = []
        
        for i, (original_q, gpt_input_q) in enumerate(zip(original_questions_from_csv, questions_to_process), 1):
            gpt_response = ""
            try:
                print(f"Processing question {i}/{total_questions} (Lang: {response_language}): '{gpt_input_q[:70]}...'")
                
                # Get response from GPT
                gpt_response = get_gpt_response(gpt_input_q, response_language)
                
                # Store the results
                all_responses.append({
                    'Original Question': original_q,
                    'Question Sent to GPT': gpt_input_q,
                    'GPT Response': gpt_response
                })
                
                print(f"  - Response collected for {i}/{total_questions}.")
                
                # Rate limiting
                if i < total_questions:
                    time.sleep(1)
                    
            except Exception as e:
                error_msg = f"Error processing question {i} ('{gpt_input_q[:70]}...'): {str(e)}"
                print(f"  - {error_msg}", file=sys.stderr)
                all_responses.append({
                    'Original Question': original_q,
                    'Question Sent to GPT': gpt_input_q,
                    'GPT Response': f"[PROCESSING_ERROR: {str(e)}]"
                })
            
            # Save progress after each question
            pd.DataFrame(all_responses).to_csv(output_file, index=False, encoding='utf-8-sig')
            
        print(f"\nAll questions processed for '{csv_file_path}'.")
        print(f"Responses saved to: {os.path.abspath(output_file)}")
        return True
        
    except Exception as e:
        print(f"Critical error processing file {csv_file_path}: {str(e)}", file=sys.stderr)
        return False

# --- Main execution block has been updated to use command-line arguments ---
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python gptResOnly.py <input_file_path> <output_file_path> <response_language>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    response_language = sys.argv[3]
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    
    # Start processing the file passed in as an argument
    process_csv_file(input_path, output_path, response_language)
    print("\n--- GPT response generation complete! ---")
