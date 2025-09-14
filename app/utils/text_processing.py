import re
import json
from typing import List, Dict, Optional

class TextProcessor:
    """Utility class for processing note content"""
    
    @staticmethod
    def detect_title(content: str) -> Optional[str]:
        """Auto-detect a title from note content"""
        if not content or not content.strip():
            return None
        
        lines = content.strip().split('\n')
        
        # Strategy 1: Look for markdown heading
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line.startswith('#'):
                # Remove markdown syntax
                title = re.sub(r'^#+\s*', '', line).strip()
                if title and len(title) < 100:  # Reasonable title length
                    return title
        
        # Strategy 2: Look for first non-empty line that looks like a title
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if line and len(line) < 100:
                # Check if it looks like a title (not too long, not a sentence)
                if not line.endswith('.') or len(line.split()) <= 8:
                    return line
        
        # Strategy 3: Extract first sentence if it's short enough
        first_sentence = TextProcessor._extract_first_sentence(content)
        if first_sentence and len(first_sentence) <= 60:
            return first_sentence
        
        return None
    
    @staticmethod
    def extract_headings(content: str) -> List[Dict]:
        """Extract all headings from content"""
        if not content:
            return []
        
        headings = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Markdown headings
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                text = line.lstrip('#').strip()
                if text:
                    headings.append({
                        'text': text,
                        'level': min(level, 6),  # Max heading level is 6
                        'line': i + 1,
                        'type': 'markdown'
                    })
            
            # Detect underlined headings (setext-style)
            elif i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and len(next_line) >= 3:
                    if all(c == '=' for c in next_line):
                        # H1 style
                        headings.append({
                            'text': line,
                            'level': 1,
                            'line': i + 1,
                            'type': 'setext'
                        })
                    elif all(c == '-' for c in next_line):
                        # H2 style
                        headings.append({
                            'text': line,
                            'level': 2,
                            'line': i + 1,
                            'type': 'setext'
                        })
        
        return headings
    
    @staticmethod
    def generate_content_schema(content: str) -> Dict:
        """Generate a hierarchical schema of the content"""
        if not content:
            return {'sections': [], 'word_count': 0, 'structure': 'empty'}
        
        headings = TextProcessor.extract_headings(content)
        lines = content.split('\n')
        
        schema = {
            'sections': [],
            'word_count': TextProcessor.count_words(content),
            'line_count': len(lines),
            'has_headings': len(headings) > 0,
            'structure': 'hierarchical' if headings else 'flat',
            'headings_count': len(headings),
            'reading_time': TextProcessor.estimate_reading_time(content)
        }
        
        if not headings:
            # No headings, treat as single section
            schema['sections'] = [{
                'title': 'Content',
                'level': 0,
                'word_count': schema['word_count'],
                'line_start': 1,
                'line_end': len(lines)
            }]
        else:
            # Build hierarchical structure
            current_section = None
            
            for i, heading in enumerate(headings):
                # Calculate word count for this section
                start_line = heading['line']
                end_line = headings[i + 1]['line'] - 1 if i + 1 < len(headings) else len(lines)
                
                section_content = '\n'.join(lines[start_line-1:end_line])
                section_word_count = TextProcessor.count_words(section_content)
                
                section = {
                    'title': heading['text'],
                    'level': heading['level'],
                    'word_count': section_word_count,
                    'line_start': start_line,
                    'line_end': end_line,
                    'subsections': []
                }
                
                schema['sections'].append(section)
        
        return schema
    
    @staticmethod
    def count_words(content: str) -> int:
        """Count words in content"""
        if not content:
            return 0
        
        # Remove markdown syntax for more accurate count
        clean_content = re.sub(r'#+\s*', '', content)  # Remove heading markers
        clean_content = re.sub(r'\*+([^*]+)\*+', r'\1', clean_content)  # Remove bold/italic
        clean_content = re.sub(r'`([^`]+)`', r'\1', clean_content)  # Remove code backticks
        clean_content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean_content)  # Remove links
        
        words = clean_content.split()
        return len([word for word in words if word.strip()])
    
    @staticmethod
    def estimate_reading_time(content: str, wpm: int = 200) -> int:
        """Estimate reading time in minutes (default 200 words per minute)"""
        word_count = TextProcessor.count_words(content)
        return max(1, round(word_count / wpm))
    
    @staticmethod
    def _extract_first_sentence(content: str) -> Optional[str]:
        """Extract the first sentence from content"""
        if not content:
            return None
        
        # Simple sentence extraction
        sentences = re.split(r'[.!?]+', content.strip())
        if sentences and sentences[0].strip():
            return sentences[0].strip()
        
        return None
    
    @staticmethod
    def extract_keywords(content: str, max_keywords: int = 10) -> List[str]:
        """Extract potential keywords from content"""
        if not content:
            return []
        
        # Simple keyword extraction (can be enhanced with NLP libraries)
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'can', 'may', 'might', 'must', 'this', 'that', 'these', 'those'
        }
        
        # Extract words and filter
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        keywords = [word for word in words if word not in stop_words]
        
        # Count frequency
        keyword_freq = {}
        for word in keywords:
            keyword_freq[word] = keyword_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
        return [keyword for keyword, freq in sorted_keywords[:max_keywords]]
    
    @staticmethod
    def detect_lists(content: str) -> Dict:
        """Detect lists in the content"""
        if not content:
            return {'bullet_lists': 0, 'numbered_lists': 0, 'total_items': 0}
        
        lines = content.split('\n')
        bullet_lists = 0
        numbered_lists = 0
        total_items = 0
        
        for line in lines:
            line = line.strip()
            # Bullet lists
            if re.match(r'^[-*+]\s+', line):
                bullet_lists += 1
                total_items += 1
            # Numbered lists
            elif re.match(r'^\d+\.\s+', line):
                numbered_lists += 1
                total_items += 1
        
        return {
            'bullet_lists': bullet_lists,
            'numbered_lists': numbered_lists,
            'total_items': total_items
        }
    
    @staticmethod
    def analyze_content_complexity(content: str) -> Dict:
        """Analyze content complexity metrics"""
        if not content:
            return {'complexity': 'empty', 'score': 0}
        
        word_count = TextProcessor.count_words(content)
        headings = TextProcessor.extract_headings(content)
        lists = TextProcessor.detect_lists(content)
        
        # Simple complexity scoring
        complexity_score = 0
        complexity_score += min(word_count / 100, 5)  # Word count factor (max 5)
        complexity_score += len(headings) * 0.5  # Headings factor
        complexity_score += lists['total_items'] * 0.2  # Lists factor
        
        if complexity_score < 1:
            complexity = 'simple'
        elif complexity_score < 3:
            complexity = 'moderate'
        elif complexity_score < 6:
            complexity = 'complex'
        else:
            complexity = 'very_complex'
        
        return {
            'complexity': complexity,
            'score': round(complexity_score, 1),
            'factors': {
                'word_count': word_count,
                'headings_count': len(headings),
                'list_items': lists['total_items']
            }
        }
