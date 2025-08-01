import os
import json
import re

# --- Configuration ---
INPUT_DIR = "input"
OUTPUT_DIR = "output"

# --- Helper Functions ---

def apply_styles(text: str, style_ranges: list) -> str:
    """
    Applies markdown styling (like bold) to a text string based on style ranges.
    """
    if not style_ranges:
        return text
        
    # Process styles in reverse order to maintain correct character offsets
    style_ranges.sort(key=lambda r: r.get('offset', 0), reverse=True)
    
    for style_range in style_ranges:
        offset = style_range.get('offset', 0)
        length = style_range.get('length', 0)
        style = style_range.get('style', '')

        if offset + length > len(text):
            continue

        original_text_slice = text[offset : offset + length]
        
        if style == 'BOLD':
            styled_text = f"**{original_text_slice}**"
        else:
            styled_text = original_text_slice

        text = text[:offset] + styled_text + text[offset + length:]
        
    return text

def parse_rich_text_block(content_block: dict) -> str:
    """
    Parses a rich text block from a card's content field.
    Handles multiple blocks if they exist.
    """
    if not content_block or 'blocks' not in content_block or not content_block['blocks']:
        return ""

    processed_blocks = []
    for block in content_block['blocks']:
        text = block.get('text', '')
        style_ranges = block.get('inlineStyleRanges', [])

        if style_ranges:
            text = apply_styles(text, style_ranges)
        
        if text: # Only add blocks that have text content
            processed_blocks.append(text)
            
    return "\n".join(processed_blocks).strip()

def process_card(card: dict, version_key: str) -> str:
    """
    Identifies a card's type and processes the specified version of its content,
    applying suitable Markdown formatting based on the type.
    """
    card_type = card.get('type')
    
    # Determine which content block to parse, with a fallback to the original 'content'
    content_to_parse = card.get(version_key)
    if not content_to_parse:
        content_to_parse = card.get('content')

    if not content_to_parse:
        return "" # Card is empty

    # --- Type-Specific Markdown Generation ---
    
    md_text = parse_rich_text_block(content_to_parse)
    
    # Only generate output if there is actual text content
    if not md_text:
        # Still handle content-less types like dividers
        if card_type == 'divider':
            return "\n---\n"
        elif card_type == 'divider_noline':
            return "\n"
        elif card_type == 'image':
             img_src = content_to_parse.get('src', '')
             return f"![Image]({img_src})" if img_src else ""
        return ""

    # Apply formatting based on the identified type
    if card_type == 'alphabetical':
        # 'alphabetical' is used for titles, so make it a heading
        return f"### {md_text}"
        
    elif card_type == 'important_text':
        # 'important_text' should stand out. A blockquote is suitable.
        return f"> {md_text}"
        
    elif card_type == 'paragraph':
        # 'paragraph' is standard text content
        return md_text
        
    elif card_type == 'image':
        img_src = content_to_parse.get('src', '')
        return f"![Image]({img_src})" if img_src else ""
        
    elif card_type == 'divider':
        return "\n---\n"
        
    elif card_type == 'divider_noline':
        return "\n"
        
    return md_text # Fallback for any other unknown types

def save_markdown_file(output_path: str, markdown_parts: list):
    """
    Joins markdown parts into a final string and saves it to a file.
    """
    # Filter out any None or empty strings from the list before joining
    final_markdown = "\n\n".join(filter(lambda x: x is not None, markdown_parts))
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_markdown)
        print(f"  -> [SUCCESS] Saved Markdown to '{output_path}'")
    except Exception as e:
        print(f"  -> [ERROR] Could not write file: {e}")

def analyze_and_migrate_json(input_path: str, output_base_path: str):
    """
    Reads a JSON file, analyzes its content versions, and creates separate 
    Markdown files for master, adapted, and translated versions.
    """
    print(f"-> Analyzing '{os.path.basename(input_path)}'...")
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  -> [ERROR] Could not read or parse file: {e}")
        return

    versions = {"master": [], "adapted": [], "translated": []}
    has_adapted_content = False
    has_translated_content = False

    main_title = data.get('description', 'Untitled Document')
    for v_list in versions.values():
        v_list.append(f"# {main_title}\n")

    for chapter in data.get('chapters', []):
        chapter_title = chapter.get('description', 'Untitled Chapter')
        for v_list in versions.values():
            v_list.append(f"## {chapter_title}\n")
        
        for card in chapter.get('cards', []):
            versions["master"].append(process_card(card, 'content'))
            versions["adapted"].append(process_card(card, 'adapted'))
            versions["translated"].append(process_card(card, 'translated'))
            
            if card.get('adapted'): has_adapted_content = True
            if card.get('translated'): has_translated_content = True

    # --- Save the final files ---
    save_markdown_file(f"{output_base_path}_master.md", versions["master"])
    
    if has_adapted_content:
        save_markdown_file(f"{output_base_path}_adapted.md", versions["adapted"])
    else:
        print("  -> [INFO] No 'adapted' content found. Skipping adapted.md file.")
        
    if has_translated_content:
        save_markdown_file(f"{output_base_path}_translated.md", versions["translated"])
    else:
        print("  -> [INFO] No 'translated' content found. Skipping translated.md file.")


def main():
    """Main function to find and process all JSON files."""
    print("--- JSON Rich Text to Multi-Version Markdown Converter ---")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not os.path.exists(INPUT_DIR):
        print(f"[ERROR] Input directory '{INPUT_DIR}' not found.")
        return

    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".json"):
            input_path = os.path.join(INPUT_DIR, filename)
            
            base_name = os.path.splitext(filename)[0]
            output_base_path = os.path.join(OUTPUT_DIR, base_name)
            
            analyze_and_migrate_json(input_path, output_base_path)
            
    print("\n--- Conversion Complete ---")

if __name__ == "__main__":
    main()
