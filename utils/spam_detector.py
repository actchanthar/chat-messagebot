import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict, Counter
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config import MAX_EMOJI_COUNT, MAX_LINKS_COUNT, SPAM_KEYWORDS, SPAM_PATTERNS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class SpamDetector:
    def __init__(self):
        self.user_message_cache = defaultdict(list)
        self.recent_messages = []
        
    async def check_spam(self, message_text: str, user_history: List[datetime], user_id: str = None) -> Dict[str, Any]:
        """Advanced spam detection"""
        try:
            spam_score = 0
            reasons = []
            
            text = message_text.strip()
            if not text:
                return {"is_spam": False, "confidence": 0, "reason": "Empty message"}
            
            current_time = datetime.utcnow()
            if user_id:
                self.user_message_cache[user_id].append({
                    'text': text,
                    'time': current_time
                })
                self.user_message_cache[user_id] = self.user_message_cache[user_id][-20:]
            
            self.recent_messages.append({
                'text': text,
                'time': current_time,
                'user_id': user_id
            })
            self.recent_messages = self.recent_messages[-500:]
            
            # Content analysis
            content_score, content_reasons = self._analyze_content(text)
            spam_score += content_score
            reasons.extend(content_reasons)
            
            # Behavior analysis
            if user_id:
                behavior_score, behavior_reasons = self._analyze_behavior(text, user_id, user_history)
                spam_score += behavior_score
                reasons.extend(behavior_reasons)
            
            # Similarity analysis
            similarity_score, similarity_reasons = self._analyze_similarity(text, user_id)
            spam_score += similarity_score
            reasons.extend(similarity_reasons)
            
            # Pattern analysis
            pattern_score, pattern_reasons = self._analyze_patterns(text)
            spam_score += pattern_score
            reasons.extend(pattern_reasons)
            
            # Statistical analysis
            stats_score, stats_reasons = self._analyze_statistics(text)
            spam_score += stats_score
            reasons.extend(stats_reasons)
            
            is_spam = spam_score >= 50
            confidence = min(spam_score * 2, 100)
            
            return {
                "is_spam": is_spam,
                "confidence": confidence,
                "reason": "; ".join(reasons[:3]) if reasons else "Clean message",
                "method": "advanced_algorithmic",
                "spam_score": spam_score
            }
            
        except Exception as e:
            logger.error(f"Error in spam detection: {e}")
            return {"is_spam": False, "confidence": 0, "reason": "Detection error"}
    
    def _analyze_content(self, text: str) -> tuple[int, List[str]]:
        score = 0
        reasons = []
        
        # Spam keywords
        text_lower = text.lower()
        keyword_matches = [kw for kw in SPAM_KEYWORDS if kw in text_lower]
        if keyword_matches:
            score += len(keyword_matches) * 10
            reasons.append(f"Spam keywords: {', '.join(keyword_matches[:2])}")
        
        # Links
        links = re.findall(r'https?://[^\s]+', text)
        if len(links) > MAX_LINKS_COUNT:
            score += 20
            reasons.append(f"Too many links ({len(links)})")
        
        # Emojis
        emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', text))
        if emoji_count > MAX_EMOJI_COUNT:
            score += 15
            reasons.append(f"Too many emojis ({emoji_count})")
        
        # Capitals
        if len(text) > 10:
            caps_count = sum(1 for c in text if c.isupper())
            caps_ratio = caps_count / len(text)
            if caps_ratio > 0.6:
                score += 20
                reasons.append("Excessive capitals")
        
        return score, reasons
    
    def _analyze_behavior(self, text: str, user_id: str, user_history: List[datetime]) -> tuple[int, List[str]]:
        score = 0
        reasons = []
        
        user_messages = self.user_message_cache.get(user_id, [])
        if len(user_messages) < 2:
            return 0, reasons
        
        current_time = datetime.utcnow()
        recent_messages = [msg for msg in user_messages 
                          if (current_time - msg['time']).total_seconds() < 60]
        
        if len(recent_messages) > 5:
            score += 25
            reasons.append("Rapid messaging")
        
        recent_texts = [msg['text'] for msg in user_messages[-5:]]
        if recent_texts.count(text) > 1:
            score += 30
            reasons.append("Repeated message")
        
        return score, reasons
    
    def _analyze_similarity(self, text: str, user_id: str) -> tuple[int, List[str]]:
        score = 0
        reasons = []
        
        current_time = datetime.utcnow()
        recent_global = [msg for msg in self.recent_messages 
                        if (current_time - msg['time']).total_seconds() < 1800
                        and msg['user_id'] != user_id]
        
        identical_count = sum(1 for msg in recent_global if msg['text'] == text)
        if identical_count >= 2:
            score += 35
            reasons.append("Mass messaging")
        elif identical_count == 1:
            score += 15
            reasons.append("Duplicate message")
        
        return score, reasons
    
    def _analyze_patterns(self, text: str) -> tuple[int, List[str]]:
        score = 0
        reasons = []
        
        for pattern in SPAM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                score += 15
                reasons.append("Spam pattern")
                break
        
        return score, reasons
    
    def _analyze_statistics(self, text: str) -> tuple[int, List[str]]:
        score = 0
        reasons = []
        
        if len(text) < 3:
            return 0, reasons
        
        char_counts = Counter(text.lower())
        most_common_char, max_count = char_counts.most_common(1)[0]
        
        if max_count > len(text) * 0.4:
            score += 20
            reasons.append("Repetitive characters")
        
        return score, reasons

# Create global instance
spam_detector = SpamDetector()
