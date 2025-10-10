from googletrans import Translator
import csv

# Initialize the translator
translator = Translator()

# Configuration - change these values to change the translation settings
TARGET_LANGUAGE = 'zh-cn'  # Change this to your desired language code
INPUT_FILE = 'q_translations/harm_prev/English-Harm_Prev.csv'
OUTPUT_FILE = 'q_translations/harm_prev/Chinese-Harm_Prev.csv'

def translate_file():
    try:
        # Read the input CSV file using csv.reader
        with open(INPUT_FILE, 'r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            # Skip the header
            next(reader)
            
            # Process each line
            with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as outfile:
                writer = csv.writer(outfile)
                # Write header
                writer.writerow(['English', 'Chinese'])
                
                for row in reader:
                    if row and row[0]:  # Check if there's English text
                        english_text = row[0]
                        try:
                            # Translate the text
                            translation = translator.translate(english_text, dest=TARGET_LANGUAGE)
                            # Write both original and translated text
                            writer.writerow([english_text, translation.text])
                        except Exception as e:
                            # If translation fails, write the original text with an error message
                            writer.writerow([english_text, f"Translation error: {str(e)}"])
                            print(f"Error translating '{english_text}': {str(e)}")
            
        print(f"Translation complete! Output saved to {OUTPUT_FILE}")
        
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found. Please create the file first.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    translate_file()
