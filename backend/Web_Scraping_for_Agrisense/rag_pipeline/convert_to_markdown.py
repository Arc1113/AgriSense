"""
Convert Cleaned Text to Industry-Standard Markdown Knowledge Base
Transforms plain .txt files into structured .md files with YAML frontmatter,
proper headings, and semantic sections.

Industry Standard: Markdown with YAML frontmatter is the preferred format for
RAG knowledge bases because:
1. Headers provide natural chunking boundaries
2. YAML frontmatter carries metadata without polluting content
3. Structure is preserved during chunking (parent-child relationships)
4. Human-readable and version-control friendly
"""

import os
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Source metadata mapping
SOURCE_MAP = {
    'alisea_fao': {'org': 'FAO', 'full_name': 'Food and Agriculture Organization', 'region': 'Global'},
    'avrdc': {'org': 'WorldVeg (AVRDC)', 'full_name': 'World Vegetable Center', 'region': 'South Asia'},
    'da_ati': {'org': 'DA-ATI', 'full_name': 'Department of Agriculture - Agricultural Training Institute', 'region': 'Philippines'},
    'da_cagayanvalley': {'org': 'DA Region II', 'full_name': 'Department of Agriculture - Cagayan Valley', 'region': 'Philippines'},
    'fao_tomato': {'org': 'FAO', 'full_name': 'Food and Agriculture Organization', 'region': 'Southeast Asia'},
    'pcaarrd': {'org': 'PCAARRD', 'full_name': 'Philippine Council for Agriculture, Aquatic and Natural Resources Research and Development', 'region': 'Philippines'},
    'ucipm': {'org': 'UC IPM', 'full_name': 'University of California Integrated Pest Management', 'region': 'California, USA'},
    'uplb': {'org': 'UPLB', 'full_name': 'University of the Philippines Los Baños', 'region': 'Philippines'},
    'worldveg': {'org': 'WorldVeg', 'full_name': 'World Vegetable Center', 'region': 'Philippines'},
    'test_': {'org': 'Test', 'full_name': 'Test Data', 'region': 'Global'},
}

# Disease detection from filename
DISEASE_MAP = {
    'early_blight': 'Early Blight',
    'late_blight': 'Late Blight',
    'bacterial_spot': 'Bacterial Spot',
    'bacterial_wilt': 'Bacterial Wilt',
    'fusarium_wilt': 'Fusarium Wilt',
    'septoria_leaf_spot': 'Septoria Leaf Spot',
    'mosaic_virus': 'Tomato Mosaic Virus',
    'yellow_leaf_curl': 'Tomato Yellow Leaf Curl Virus',
    'powdery_mildew': 'Powdery Mildew',
    'diseases': 'Multiple Diseases',
    'ipm': 'Integrated Pest Management',
    'tomato_collection': 'General Tomato',
    'tomato_production': 'General Production',
    'tomato_productivity': 'General Production',
    'tomato_icm': 'Integrated Crop Management',
    'tomato_training': 'General Production',
    'tomato_index': 'Multiple Diseases',
    'organic_tomato': 'Organic Production',
    'disease_samples': 'Disease Sampling',
    'ipm_field_days': 'Integrated Pest Management',
}


def detect_source(filename: str) -> Dict[str, str]:
    """Detect source organization from filename."""
    filename_lower = filename.lower()
    for prefix, info in SOURCE_MAP.items():
        if filename_lower.startswith(prefix):
            return info
    return {'org': 'Unknown', 'full_name': 'Unknown Source', 'region': 'Global'}


def detect_disease(filename: str) -> str:
    """Detect disease topic from filename."""
    filename_lower = filename.lower()
    for keyword, disease in DISEASE_MAP.items():
        if keyword in filename_lower:
            return disease
    return 'General'


def detect_sections(text: str) -> List[Dict[str, str]]:
    """
    Detect semantic sections in text using heuristics.
    Looks for patterns that indicate section headers:
    - Lines that are ALL CAPS
    - Lines followed by blank lines that are short
    - Known section header keywords
    """
    SECTION_KEYWORDS = [
        'symptoms and signs', 'symptoms', 'signs', 'identification',
        'management', 'control', 'treatment', 'recommendations',
        'comments on the disease', 'disease cycle', 'biology',
        'prevention', 'cultural practices', 'cultural control',
        'chemical control', 'biological control', 'organic control',
        'monitoring', 'monitoring and treatment decisions',
        'introduction', 'overview', 'description', 'background',
        'harvest', 'postharvest', 'post-harvest',
        'nursery', 'seedling', 'transplanting',
        'irrigation', 'water management', 'fertigation',
        'soil', 'fertilization', 'nutrient',
        'pest', 'insect', 'disease',
        'integrated pest management', 'ipm',
        'faq', 'questions', 'references',
    ]
    
    lines = text.split('\n')
    sections = []
    current_section = {'title': 'Overview', 'content': []}
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            current_section['content'].append('')
            continue
        
        is_header = False
        
        # Check if line is a known section header
        stripped_lower = stripped.lower().rstrip(':')
        for keyword in SECTION_KEYWORDS:
            if stripped_lower == keyword or stripped_lower.startswith(keyword + ' '):
                is_header = True
                break
        
        # Check if line is ALL CAPS and short (likely a header)
        if not is_header and stripped.isupper() and 3 < len(stripped) < 80:
            is_header = True
        
        # Check for numbered sections like "6.1", "2.3.1"
        if not is_header and re.match(r'^\d+(\.\d+)*\s+[A-Z]', stripped):
            is_header = True
        
        # Check for "On This Page" navigation (skip it)
        if stripped_lower == 'on this page':
            continue
        
        if is_header:
            # Save previous section if it has content
            if current_section['content']:
                sections.append(current_section)
            current_section = {'title': stripped.title(), 'content': []}
        else:
            current_section['content'].append(stripped)
    
    # Save last section
    if current_section['content']:
        sections.append(current_section)
    
    return sections


def text_to_markdown(filename: str, text: str) -> str:
    """
    Convert cleaned text into a structured Markdown document
    with YAML frontmatter and proper heading hierarchy.
    """
    source_info = detect_source(filename)
    disease = detect_disease(filename)
    
    # Create human-readable title
    title = Path(filename).stem.replace('_', ' ').title()
    
    # Detect sections
    sections = detect_sections(text)
    
    # Build YAML frontmatter
    frontmatter = f"""---
title: "{title}"
source: "{source_info['org']}"
source_full: "{source_info['full_name']}"
region: "{source_info['region']}"
crop: "Tomato"
disease: "{disease}"
language: "English"
converted_at: "{datetime.now().isoformat()}"
original_file: "{filename}"
---"""
    
    # Build markdown body
    md_parts = [frontmatter, '']
    md_parts.append(f'# {title}')
    md_parts.append('')
    md_parts.append(f'> **Source:** {source_info["full_name"]} ({source_info["org"]})')
    md_parts.append(f'> **Region:** {source_info["region"]}')
    md_parts.append(f'> **Topic:** {disease}')
    md_parts.append('')
    
    for section in sections:
        title = section['title']
        content_lines = section['content']
        
        # Clean up content
        content = '\n'.join(content_lines).strip()
        if not content:
            continue
        
        # Add section header
        md_parts.append(f'## {title}')
        md_parts.append('')
        
        # Process content - wrap long paragraphs, detect lists
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Detect list items
            lines = para.split('\n')
            is_list = any(re.match(r'^[\-•●]\s', l.strip()) or 
                         re.match(r'^\d+[\.\)]\s', l.strip()) for l in lines)
            
            if is_list:
                for line in lines:
                    line = line.strip()
                    if line:
                        # Normalize bullet format
                        line = re.sub(r'^[•●]\s*', '- ', line)
                        if not line.startswith('-') and not re.match(r'^\d+[\.\)]', line):
                            line = '- ' + line
                        md_parts.append(line)
                md_parts.append('')
            else:
                md_parts.append(para)
                md_parts.append('')
    
    return '\n'.join(md_parts)


def convert_all(input_dir: str = 'processed/cleaned_text', 
                output_dir: str = 'processed/markdown_kb'):
    """
    Convert all cleaned text files to Markdown knowledge base format.
    
    Args:
        input_dir: Directory with cleaned .txt files
        output_dir: Directory for output .md files
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    txt_files = sorted(input_path.glob('*.txt'))
    
    if not txt_files:
        logger.error(f"No .txt files found in {input_dir}")
        return
    
    logger.info(f"Converting {len(txt_files)} text files to Markdown knowledge base")
    logger.info(f"Output directory: {output_dir}")
    
    converted = 0
    for txt_file in txt_files:
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            markdown = text_to_markdown(txt_file.name, text)
            
            out_file = output_path / f"{txt_file.stem}.md"
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(markdown)
            
            converted += 1
            logger.info(f"  ✅ {txt_file.name} → {out_file.name}")
            
        except Exception as e:
            logger.error(f"  ❌ Failed to convert {txt_file.name}: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Converted {converted}/{len(txt_files)} files to Markdown")
    logger.info(f"Output: {output_path}")
    logger.info(f"{'='*50}")


if __name__ == '__main__':
    convert_all()
