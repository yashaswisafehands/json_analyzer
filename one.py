import os
import json
import re

INPUT_DIR = "input"
OUTPUT_DIR = "output1"

def apply_styles(text: str, style_ranges: list) -> str:
    """Apply inline styles to text based on style ranges."""
    if not style_ranges:
        return text
    
    # Sort by offset in reverse order to avoid position shifts
    style_ranges.sort(key=lambda r: r.get('offset', 0), reverse=True)
    
    for style_range in style_ranges:
        offset = style_range.get('offset', 0)
        length = style_range.get('length', 0)
        style = style_range.get('style', '')
        
        if offset + length > len(text):
            continue
        
        original_text_slice = text[offset : offset + length]
        
        # Apply styling based on type
        if style == 'BOLD':
            styled_text = f"**{original_text_slice}**"
        elif style == 'ITALIC':
            styled_text = f"*{original_text_slice}*"
        elif style == 'CODE':
            styled_text = f"`{original_text_slice}`"
        else:
            styled_text = original_text_slice
        
        text = text[:offset] + styled_text + text[offset + length:]
    
    return text

def parse_rich_text_block(content_block: dict) -> str:
    """Parse DraftJS-style rich text blocks into plain text with markdown formatting."""
    if not content_block or 'blocks' not in content_block or not content_block['blocks']:
        return ""
    
    processed_blocks = []
    
    for block in content_block['blocks']:
        text = block.get('text', '')
        style_ranges = block.get('inlineStyleRanges', [])
        
        # Apply inline styles
        if style_ranges:
            text = apply_styles(text, style_ranges)
        
        # Handle block-level styles
        block_type = block.get('type', 'unstyled')
        if block_type == 'header-one':
            text = f"# {text}"
        elif block_type == 'header-two':
            text = f"## {text}"
        elif block_type == 'header-three':
            text = f"### {text}"
        elif block_type == 'unordered-list-item':
            text = f"* {text}"
        elif block_type == 'ordered-list-item':
            text = f"1. {text}"
        elif block_type == 'blockquote':
            text = f"> {text}"
        elif block_type == 'code-block':
            text = f"```\n{text}\n```"
        
        if text.strip():
            processed_blocks.append(text)
    
    return "\n".join(processed_blocks).strip()

def enhance_clinical_content(text: str) -> str:
    """Enhance clinical content by bolding important keywords and formatting."""
    if not text:
        return text
    
    # Bold common clinical keywords if not already styled
    clinical_keywords = [
        r'\bOR\b', r'\bAND\b', r'\bIF\b', r'\bTHEN\b',
        r'\bmg\b', r'\bkg\b', r'\bIV\b', r'\bIM\b', r'\bPO\b',
        r'\bdaily\b', r'\btwice\b', r'\bthree times\b', r'\bfour times\b',
        r'\bhour\b', r'\bhours\b', r'\bday\b', r'\bdays\b',
        r'\bweek\b', r'\bweeks\b', r'\bmonth\b', r'\bmonths\b'
    ]
    
    for keyword in clinical_keywords:
        # Only bold if not already in markdown formatting
        text = re.sub(f'(?<!\\*)\\b({keyword.strip("\\b")})\\b(?!\\*)', r'**\1**', text, flags=re.IGNORECASE)
    
    # Format dosages (e.g., "50 mg/kg" becomes "**50 mg/kg**")
    text = re.sub(r'(\d+\.?\d*\s*(?:mg|g|ml|L|kg|lb)(?:/(?:kg|day|hour|h))?)', r'**\1**', text)
    
    return text

def process_card(card: dict, version_key: str) -> str:
    """Process a single card and return its markdown representation."""
    card_type = card.get('type', 'paragraph')
    
    # Get content based on version preference
    content_to_parse = card.get(version_key) or card.get('content')
    
    if not content_to_parse:
        # Handle special card types without content
        if card_type == 'divider':
            return "---"
        elif card_type == 'divider_noline':
            return ""
        return ""
    
    # Handle different content structures
    if isinstance(content_to_parse, dict):
        if 'src' in content_to_parse:  # Image content
            img_src = content_to_parse.get('src', '')
            alt_text = content_to_parse.get('alt', 'Image')
            return f"![{alt_text}]({img_src})" if img_src else ""
        else:  # Rich text content
            md_text = parse_rich_text_block(content_to_parse)
    elif isinstance(content_to_parse, str):
        md_text = content_to_parse
    else:
        return ""
    
    if not md_text and card_type in ['divider', 'divider_noline']:
        return "---" if card_type == 'divider' else ""
    
    if not md_text:
        return ""
    
    # Apply clinical content enhancement
    md_text = enhance_clinical_content(md_text)
    
    # Format based on card type
    if card_type == 'alphabetical':
        return f"### {md_text.upper()}"
    elif card_type == 'important_text':
        return f"> {md_text}"
    elif card_type == 'styled':
        return f"**{md_text}**"
    elif card_type == 'paragraph':
        return md_text
    elif card_type == 'divider':
        return "---"
    elif card_type == 'divider_noline':
        return ""
    
    return md_text

def create_chapter_separator(next_chapter_title: str = None) -> str:
    """Create a visual separator between chapters for frontend presentation."""
    if next_chapter_title:
        return f"\n---\n\n# Chapter: {next_chapter_title.upper()}\n"
    else:
        return "\n---\n\n# [New Chapter Begins]\n"

def save_markdown_file(output_path: str, markdown_content: str):
    """Save the final markdown content to file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"  -> [SUCCESS] Saved Markdown to '{output_path}'")
    except Exception as e:
        print(f"  -> [ERROR] Could not write file: {e}")

def analyze_and_migrate_json(input_path: str, output_base_path: str):
    """Main function to convert JSON action cards to structured markdown."""
    print(f"-> Analyzing '{os.path.basename(input_path)}'...")
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  -> [ERROR] Could not read or parse file: {e}")
        return
    
    # Track available content versions
    versions = {"master": [], "adapted": [], "translated": []}
    has_adapted_content = False
    has_translated_content = False
    
    # Main document title
    main_title = data.get('description', data.get('title', 'Untitled Document'))
    
    # Add document header with metadata comment for frontend
    header_comment = f"<!-- \nGenerated from: {os.path.basename(input_path)}\nFor: Frontend Course Presentation\nGenerated on: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n-->\n\n"
    
    for version in versions:
        versions[version].append(header_comment)
        versions[version].append(f"# {main_title}\n")
    
    chapters = data.get('chapters', [])
    total_chapters = len(chapters)
    
    for chapter_idx, chapter in enumerate(chapters):
        chapter_title = chapter.get('description', chapter.get('title', 'Untitled Chapter'))
        
        # Add chapter header
        for version in versions:
            versions[version].append(f"### {chapter_title.upper()}\n")
        
        # Process cards in this chapter
        cards = chapter.get('cards', [])
        chapter_content = {"master": [], "adapted": [], "translated": []}
        
        for card in cards:
            master_content = process_card(card, 'content')
            adapted_content = process_card(card, 'adapted')
            translated_content = process_card(card, 'translated')
            
            if master_content:
                chapter_content["master"].append(master_content)
            if adapted_content:
                chapter_content["adapted"].append(adapted_content)
                has_adapted_content = True
            else:
                chapter_content["adapted"].append(master_content)  # Fallback to master
            if translated_content:
                chapter_content["translated"].append(translated_content)
                has_translated_content = True
            else:
                chapter_content["translated"].append(master_content)  # Fallback to master
        
        # Add chapter content
        for version in versions:
            if chapter_content[version]:
                versions[version].extend(chapter_content[version])
        
        # Add chapter separator (except for last chapter)
        if chapter_idx < total_chapters - 1:
            next_chapter_title = chapters[chapter_idx + 1].get('description', chapters[chapter_idx + 1].get('title', 'Next Chapter'))
            separator = create_chapter_separator(next_chapter_title)
            for version in versions:
                versions[version].append(separator)
    
    # Generate final markdown content
    for version_name, content_parts in versions.items():
        if version_name == "master" or (version_name == "adapted" and has_adapted_content) or (version_name == "translated" and has_translated_content):
            final_markdown = "\n\n".join(filter(None, [part.strip() for part in content_parts if part]))
            
            # Clean up extra whitespace and ensure consistent spacing
            final_markdown = re.sub(r'\n{3,}', '\n\n', final_markdown)
            final_markdown = final_markdown.strip()
            
            output_path = f"{output_base_path}_{version_name}.md"
            save_markdown_file(output_path, final_markdown)
    
    # Info messages for skipped versions
    if not has_adapted_content:
        print("  -> [INFO] No 'adapted' content found. Skipping adapted.md file.")
    if not has_translated_content:
        print("  -> [INFO] No 'translated' content found. Skipping translated.md file.")

def main():
    """Main entry point for the converter."""
    print("--- Enhanced JSON Rich Text to Multi-Version Markdown Converter ---")
    print("--- Optimized for Frontend Course Presentation ---\n")
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not os.path.exists(INPUT_DIR):
        print(f"[ERROR] Input directory '{INPUT_DIR}' not found.")
        return
    
    json_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".json")]
    
    if not json_files:
        print(f"[INFO] No JSON files found in '{INPUT_DIR}' directory.")
        return
    
    print(f"Found {len(json_files)} JSON file(s) to process:\n")
    
    for filename in json_files:
        input_path = os.path.join(INPUT_DIR, filename)
        base_name = os.path.splitext(filename)[0]
        output_base_path = os.path.join(OUTPUT_DIR, base_name)
        analyze_and_migrate_json(input_path, output_base_path)
        print()  # Empty line between files
    
    print("--- Conversion Complete ---")
    print(f"Output files saved in '{OUTPUT_DIR}' directory.")
    print("Ready for frontend integration! 🚀")

if __name__ == "__main__":
    main()
