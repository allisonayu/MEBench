import sys
from googletrans import Translator

def translate_to_english(text, source_lang):
    lang_mapping = {
        'Arabic': 'ar', 
        'Chinese': 'zh-cn', 
        'English': 'en',
        'Hindi': 'hi', 
        'Spanish': 'es', 
        'Swahili': 'sw'
    }
    source_code = lang_mapping.get(source_lang, 'en')
    
    if source_code == 'en':
        return text

    translator = Translator()
    try:
        translation = translator.translate(text, dest='en', src=source_code)
        return translation.text
    except Exception as e:
        # Print errors to stderr so the main script can capture them
        print(f"googletrans error: {str(e)}", file=sys.stderr)
        sys.exit(1) # Exit with a non-zero status to signal an error

if __name__ == "__main__":
    # Check for the correct number of arguments
    if len(sys.argv) != 3:
        print("Usage: translate_worker.py <text> <source_lang>", file=sys.stderr)
        sys.exit(1)

    text_to_translate = sys.argv[1]
    source_language = sys.argv[2]
    
    translated_text = translate_to_english(text_to_translate, source_language)
    print(translated_text)