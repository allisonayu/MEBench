import csv
import os
import sys
import time
from googletrans import Translator

# --- SET CONSOLE OUTPUT TO UTF-8 ---
# Ensures that console output handles various characters correctly.
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Initialize the translator globally for efficiency
translator = Translator()

# Define mappings for sections and languages
sections_map = {
    'Biases_Stereotypes': 'biases_stereo',
    'Consent_Autonomy': 'consent_autonomy',
    'Harm_Prev': 'harm_prev',
    'Legality': 'legality',
    'Moral_Judgment': 'moral_judgment'
}

languages_map = {
    'Arabic': 'ar', # Googletrans code
    'Chinese': 'zh-cn', # Googletrans code for Simplified Chinese
    'English': 'en', # Googletrans code
    'Hindi': 'hi', # Googletrans code
    'Spanish': 'es', # Googletrans code
    'Swahili': 'sw' # Googletrans code
}

def translate_response_text(text_to_translate, source_language_code):
    """
    Translates a single piece of text to English using googletrans.
    Includes basic error handling for translation.

    Args:
        text_to_translate (str): The text content to be translated.
        source_language_code (str): The ISO 639-1 code of the source language (e.g., 'ar', 'zh-cn').

    Returns:
        str: The translated text, or an error message if translation fails.
    """
    if source_language_code.lower() == 'en' or not text_to_translate.strip():
        return text_to_translate

    try:
        translation = translator.translate(text_to_translate, dest='en', src=source_language_code)
        return translation.text.strip()
    except Exception as e:
        print(f"Error translating '{text_to_translate[:50]}...': {str(e)}", file=sys.stderr)
        return f"[Translation Error: {str(e)}]"

def process_file_for_translation(input_file_path, source_lang_display_name):
    """
    Reads a CSV file, translates the 'GPT Response' column to English,
    and adds an 'English Translation' column, overwriting the original file.

    Args:
        input_file_path (str): The path to the CSV file to be processed.
        source_lang_display_name (str): The display name of the source language (e.g., 'Arabic'),
                                        used to get the corresponding googletrans code.
    """
    print(f"Processing file: {input_file_path}")
    
    # Get the googletrans code from the display name
    source_lang_code = languages_map.get(source_lang_display_name, 'en') 

    try:
        # Read all rows from the input file
        with open(input_file_path, 'r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            header = next(reader) # Read header
            rows = list(reader)  # Read all data rows

        # Identify the index of the 'GPT Response' column
        try:
            gpt_response_col_index = header.index('GPT Response')
        except ValueError:
            print(f"Error: 'GPT Response' column not found in {input_file_path}. Skipping.", file=sys.stderr)
            return

        # Add the new header column if it doesn't exist
        english_translation_col_name = 'English Translation'
        if english_translation_col_name not in header:
            header.append(english_translation_col_name)
        
        translated_rows = []
        total_rows = len(rows)

        for i, row in enumerate(rows, 1):
            if len(row) <= gpt_response_col_index: # Ensure row has enough columns
                translated_rows.append(row + [f"[Invalid Row - Missing GPT Response]"])
                print(f"Skipping row {i}: Insufficient columns.", file=sys.stderr)
                continue

            response_text = row[gpt_response_col_index]
            current_translation = ""

            if english_translation_col_name in header and len(row) > header.index(english_translation_col_name):
                # If 'English Translation' column already exists and has content, skip re-translation
                current_translation = row[header.index(english_translation_col_name)]
                if current_translation and not current_translation.startswith("[Translation Error:"):
                    translated_rows.append(row)
                    print(f"   - Row {i}/{total_rows}: Already translated. Skipping.", end='\r')
                    sys.stdout.flush()
                    continue

            print(f"   - Translating row {i}/{total_rows}: '{response_text[:70]}...'")
            current_translation = translate_response_text(response_text, source_lang_code)
            
            # Append or update the translation in the current row
            if english_translation_col_name in header:
                # Update existing column
                col_index = header.index(english_translation_col_name)
                if len(row) > col_index:
                    row[col_index] = current_translation
                else:
                    # Pad row if it's shorter than expected
                    row.extend([''] * (col_index - len(row)))
                    row.append(current_translation)
            else:
                # Append if column was just added to header
                row.append(current_translation)
            
            translated_rows.append(row)
            
            # Small delay to prevent hitting googletrans rate limits
            if i % 10 == 0: # Pause every 10 translations
                time.sleep(0.5) 
        
        # Write the updated data back to the same file
        with open(input_file_path, 'w', newline='', encoding='utf-8-sig') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(header)
            writer.writerows(translated_rows)
            
        print(f"\nTranslation complete for {os.path.basename(input_file_path)}! Translations added.")
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_file_path}' not found. Skipping.", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred while processing '{input_file_path}': {str(e)}", file=sys.stderr)

def process_all_files_for_translation():
    """
    Iterates through all relevant files based on sections and languages,
    and calls process_file_for_translation for each.
    """
    print("Starting batch translation of GPT responses to English...")
    
    # Base directory where Claude's responses are saved
    gpt_responses_base_dir = os.path.join('LLMEvals', 'GPT')

    for section_name, section_dir in sections_map.items():
        for lang_display_name in languages_map.keys(): # Iterate through display names
            # Construct the expected input file path
            input_csv_filename = f"{lang_display_name}-{section_name}-Evals-GPT.csv" 
            input_csv_path = os.path.join(gpt_responses_base_dir, input_csv_filename)
            
            print(f"\n--- Attempting to translate: {input_csv_filename} ---")
            
            if os.path.exists(input_csv_path):
                process_file_for_translation(input_csv_path, lang_display_name)
            else:
                print(f"Skipping: File not found at '{input_csv_path}'.", file=sys.stderr)
            
            time.sleep(2) # Small delay between processing each file

    print("\n--- All batch translation processes complete! ---")

if __name__ == "__main__":
    # Check if the script is being run with command-line arguments (from the workflow)
    # The workflow script passes the input file path and the language name
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        language_name = sys.argv[2]
        
        print(f"Running in single-file mode for: {input_file}, Language: {language_name}")
        process_file_for_translation(input_file, language_name)
    else:
        # If no arguments, run the full batch processing
        print("Running in standalone mode. To run with specific files, use command-line arguments.")
        process_all_files_for_translation()
