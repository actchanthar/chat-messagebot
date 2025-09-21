import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict, Counter
from config import MAX_EMOJI_COUNT, MAX_LINKS_COUNT, SPAM_KEYWORDS, SPAM_PATTERNS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class SpamDetector:
    def __init__(self):
        self.user_message_cache = defaultdict(list)  # Store recent messages per user
        self.recent_messages = []  # Global recent messages for similarity check
        
    async def check_spam(self, message_text: str, user_history: List[datetime], user_id: str = None) -> Dict[str, Any]:
        """
        Advanced spam detection using multiple algorithms - No AI APIs needed!
        """
        try:
            spam_score = 0
            reasons = []
            
            # Clean and normalize text
            text = message_text.strip()
            if not text:
                return {"is_spam": False, "confidence": 0, "reason": "Empty message"}
            
            # Store message for pattern analysis
            current_time = datetime.utcnow()
            if user_id:
                self.user_message_cache[user_id].append({
                    'text': text,
                    'time': current_time
                })
                # Keep only last 20 messages per user
                self.user_message_cache[user_id] = self.user_message_cache[user_id][-20:]
            
            # Store in global cache
            self.recent_messages.append({
                'text': text,
                'time': current_time,
                'user_id': user_id
            })
            # Keep only last 500 global messages
            self.recent_messages = self.recent_messages[-500:]
            
            # 1. BASIC CONTENT ANALYSIS
            content_score, content_reasons = self._analyze_content(text)
            spam_score += content_score
            reasons.extend(content_reasons)
            
            # 2. USER BEHAVIOR ANALYSIS
            if user_id:
                behavior_score, behavior_reasons = self._analyze_behavior(text, user_id, user_history)
                spam_score += behavior_score
                reasons.extend(behavior_reasons)
            
            # 3. SIMILARITY ANALYSIS
            similarity_score, similarity_reasons = self._analyze_similarity(text, user_id)
            spam_score += similarity_score
            reasons.extend(similarity_reasons)
            
            # 4. PATTERN MATCHING
            pattern_score, pattern_reasons = self._analyze_patterns(text)
            spam_score += pattern_score
            reasons.extend(pattern_reasons)
            
            # 5. STATISTICAL ANALYSIS
            stats_score, stats_reasons = self._analyze_statistics(text)
            spam_score += stats_score
            reasons.extend(stats_reasons)
            
            # Final decision
            is_spam = spam_score >= 50  # Threshold for spam
            confidence = min(spam_score * 2, 100)  # Convert to percentage
            
            result = {
                "is_spam": is_spam,
                "confidence": confidence,
                "reason": "; ".join(reasons[:3]) if reasons else "Clean message",
                "method": "advanced_algorithmic",
                "spam_score": spam_score
            }
            
            logger.info(f"Spam check for user {user_id}: score={spam_score}, spam={is_spam}")
            return result
            
        except Exception as e:
            logger.error(f"Error in spam detection: {e}")
            return {
                "is_spam": False,
                "confidence": 0,
                "reason": "Detection error",
                "method": "error"
            }
    
    def _analyze_content(self, text: str) -> tuple[int, List[str]]:
        """Analyze message content for spam indicators"""
        score = 0
        reasons = []
        
        # 1. Check spam keywords
        text_lower = text.lower()
        keyword_matches = [kw for kw in SPAM_KEYWORDS if kw in text_lower]
        if keyword_matches:
            score += len(keyword_matches) * 10
            reasons.append(f"Spam keywords: {', '.join(keyword_matches[:2])}")
        
        # 2. Link analysis
        links = re.findall(r'https?://[^\s]+', text)
        if len(links) > MAX_LINKS_COUNT:
            score += 20
            reasons.append(f"Too many links ({len(links)})")
        
        # Check for suspicious links
        suspicious_domains = ['bit.ly', 'tinyurl.com', 't.me', 'telegram.me']
        for link in links:
            if any(domain in link.lower() for domain in suspicious_domains):
                score += 15
                reasons.append("Suspicious links")
                break
        
        # 3. Emoji analysis
        emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', text))
        if emoji_count > MAX_EMOJI_COUNT:
            score += 15
            reasons.append(f"Too many emojis ({emoji_count})")
        
        # 4. Capitalization check
        if len(text) > 10:
            caps_count = sum(1 for c in text if c.isupper())
            caps_ratio = caps_count / len(text)
            if caps_ratio > 0.6:  # 60% capitals
                score += 20
                reasons.append("Excessive capitals")
        
        # 5. Special characters
        special_chars = len(re.findall(r'[!@#$%^&*()_+=\[\]{}|;:,.<>?]', text))
        if special_chars > len(text) * 0.3:  # 30% special chars
            score += 15
            reasons.append("Too many special characters")
        
        # 6. Phone numbers in promotional context
        phone_pattern = r'\b(?:\+?95|09)\d{7,9}\b'
        if re.search(phone_pattern, text) and any(word in text_lower for word in ['call', 'contact', 'whatsapp']):
            score += 15
            reasons.append("Phone number promotion")
        
        return score, reasons
    
    def _analyze_behavior(self, text: str, user_id: str, user_history: List[datetime]) -> tuple[int, List[str]]:
        """Analyze user behavioral patterns"""
        score = 0
        reasons = []
        
        user_messages = self.user_message_cache.get(user_id, [])
        if len(user_messages) < 2:
            return 0, reasons
        
        current_time = datetime.utcnow()
        
        # 1. Rate limiting check
        recent_messages = [msg for msg in user_messages 
                          if (current_time - msg['time']).total_seconds() < 60]  # Last minute
        
        if len(recent_messages) > 5:  # More than 5 messages per minute
            score += 25
            reasons.append("Rapid messaging")
        
        # 2. Message similarity check
        recent_texts = [msg['text'] for msg in user_messages[-5:]]  # Last 5 messages
        
        # Check for identical messages
        if recent_texts.count(text) > 1:
            score += 30
            reasons.append("Repeated identical message")
        
        # Check for very similar messages
        similar_count = 0
        for old_text in recent_texts[:-1]:  # Exclude current message
            # Simple similarity check
            if len(text) > 10 and len(old_text) > 10:
                # Check if 80% of words are the same
                text_words = set(text.lower().split())
                old_words = set(old_text.lower().split())
                if len(text_words & old_words) / max(len(text_words), len(old_words)) > 0.8:
                    similar_count += 1
        
        if similar_count >= 2:
            score += 20
            reasons.append("Very similar messages")
        
        return score, reasons
    
    def _analyze_similarity(self, text: str, user_id: str) -> tuple[int, List[str]]:
        """Check similarity with recent global messages"""
        score = 0
        reasons = []
        
        current_time = datetime.utcnow()
        
        # Check recent global messages (last 30 minutes)
        recent_global = [msg for msg in self.recent_messages 
                        if (current_time - msg['time']).total_seconds() < 1800  # 30 minutes
                        and msg['user_id'] != user_id]  # Different users
        
        # Check for identical messages from different users
        identical_count = sum(1 for msg in recent_global if msg['text'] == text)
        if identical_count >= 2:
            score += 35
            reasons.append("Mass messaging detected")
        elif identical_count == 1:
            score += 15
            reasons.append("Duplicate message from different user")
        
        return score, reasons
    
    def _analyze_patterns(self, text: str) -> tuple[int, List[str]]:
        """Advanced pattern matching"""
        score = 0
        reasons = []
        
        # Check predefined spam patterns
        for pattern in SPAM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                score += 15
                reasons.append("Spam pattern detected")
        
        # Additional pattern checks
        spam_patterns = [
            (r'\b(?:free|win|prize)\b.*\b(?:click|join|visit)\b', "Prize/click spam"),
            (r'\b(?:earn|make)\s+(?:money|cash|income)\b', "Money-making spam"),
            (r'\b(?:guaranteed|100%|sure)\b.*\b(?:profit|return|win)\b', "Guarantee spam"),
            (r'(?:join|follow).*(?:channel|group|page)', "Channel promotion"),
            (r'\b\d{1,3}%\s+(?:profit|return|gain)\b', "Investment scam"),
        ]
        
        for pattern, description in spam_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 12
                reasons.append(description)
        
        return score, reasons
    
    def _analyze_statistics(self, text: str) -> tuple[int, List[str]]:
        """Statistical analysis of message"""
        score = 0
        reasons = []
        
        if len(text) < 3:
            return 0, reasons
        
        # 1. Character repetition analysis
        char_counts = Counter(text.lower())
        most_common_char, max_count = char_counts.most_common(1)[0]
        
        if max_count > len(text) * 0.4:  # 40% same character
            score += 20
            reasons.append("Repetitive characters")
        
        # 2. Word repetition analysis
        words = text.lower().split()
        if len(words) > 2:
            word_counts = Counter(words)
            most_common_word, max_word_count = word_counts.most_common(1)[0]
            
            if max_word_count > len(words) * 0.5:  # 50% same word
                score += 15
                reasons.append("Repetitive words")
        
        # 3. Number density check
        numbers = len(re.findall(r'\d', text))
        if numbers > len(text) * 0.5:  # 50% numbers
            score += 15
            reasons.append("Too many numbers")
        
        # 4. Length-based checks
        if len(text) > 500:  # Very long message
            score += 10
            reasons.append("Excessively long message")
        
        return score, reasons

# Create global instance
spam_detector = SpamDetector()
