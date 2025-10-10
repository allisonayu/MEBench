import csv
import os
import sys
import time
from googletrans import Translator

# --- SET CONSOLE OUTPUT TO UTF-8 ---
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Initialize the translator globally for efficiency
translator = Translator()

def translate_response_text(text_to_translate, source_language_code):
    """
    Translates a single piece of text to English using googletrans.
    Includes basic error handling for translation.
    """
    # Don't translate if the source is English or the text is empty
    if source_language_code.lower() == 'en' or not text_to_translate.strip():
        return text_to_translate

    try:
        translation = translator.translate(text_to_translate, dest='en', src=source_language_code)
        return translation.text.strip()
    except Exception as e:
        print(f"Error translating '{text_to_translate[:50]}...': {str(e)}", file=sys.stderr)
        return f"[Translation Error: {str(e)}]"
    
# Map language display names to googletrans codes globally for reusability
LANGUAGES_MAP = {
    'Arabic': 'ar',
    'Chinese': 'zh-cn',
    'English': 'en',
    'Hindi': 'hi',
    'Spanish': 'es',
    'Swahili': 'sw'
}

def process_file_for_translation(input_file_path):
    """
    Reads a CSV file, translates the 'GPT Response' column to English,
    and adds an 'English Translation' column. The source language is
    determined from the 'File Name' column for each row.
    """
    print(f"\nProcessing file: {input_file_path}")
    
    try:
        # Read all rows from the input file
        with open(input_file_path, 'r', encoding='utf-8-sig') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
            rows = list(reader)

        # Check for required columns
        if 'File Name' not in fieldnames or 'GPT Response' not in fieldnames:
            print("Error: Missing required column ('File Name' or 'GPT Response').")
            return

        # Add 'English Translation' column if it doesn't exist
        translation_col = 'English Translation'
        if translation_col not in fieldnames:
            fieldnames.append(translation_col)
            for row in rows:
                row[translation_col] = ''

        total_rows = len(rows)
        print(f"Found {total_rows} rows to process...")

        # Process each row
        for i, row in enumerate(rows, 1):
            try:
                # --- NEW LOGIC: DETERMINE SOURCE LANGUAGE FROM 'File Name' COLUMN ---
                file_name_col = row.get('File Name', '')
                source_language_name = file_name_col.split('-')[0] if '-' in file_name_col else 'English'
                source_lang_code = LANGUAGES_MAP.get(source_language_name, 'en')

                # Skip if already translated
                if row.get(translation_col, '').strip() and not row[translation_col].startswith('[Translation Error'):
                    print(f"Row {i}/{total_rows} (Lang: {source_language_name}): Already translated. Skipping.", end='\r')
                    continue

                # Get the text to translate
                text_to_translate = row.get('GPT Response', '').strip()
                
                if not text_to_translate:
                    print(f"Row {i}/{total_rows} (Lang: {source_language_name}): No text to translate.", end='\r')
                    continue

                print(f"Translating row {i}/{total_rows} (Lang: {source_language_name})...", end='\r')
                
                # Translate the text using the determined source language
                translation = translate_response_text(text_to_translate, source_lang_code)
                row[translation_col] = translation
                
                # Save progress after each row (this is inefficient but matches original intent)
                with open(input_file_path, 'w', newline='', encoding='utf-8-sig') as outfile:
                    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                print(f"\nError processing row {i}: {str(e)}")
                if 'row' in locals():
                    row[translation_col] = f"[Translation Error: {str(e)}]"
        
        print("\nTranslation complete!")
        
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}", file=sys.stderr)

if __name__ == "__main__":
    # Set your input file path here
    input_file = "gpt_redo/res.csv"
    
    if os.path.exists(input_file):
        # Now, you just pass the file path, no need to manually set the language
        process_file_for_translation(input_file)
    else:
        print(f"Error: File not found: {input_file}")
        print("Please update the 'input_file' variable in the script.")
        sys.exit(1)