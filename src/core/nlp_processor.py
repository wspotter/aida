
"""
Natural Language Processing module using spaCy.
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional

import spacy
from spacy.matcher import Matcher

from   utils.config_loader import ConfigLoader


class NLPProcessor:
    """Natural language processing for intent recognition and entity extraction."""
    
    def __init__(self, config_path: str = "configs/config.json"):
        self.config = ConfigLoader(config_path).get_config()
        self.logger = logging.getLogger(__name__)
        
        # Load spaCy model
        self.nlp = None
        self.matcher = None
        self._load_spacy_model()
        
        # Intent patterns
        self.intent_patterns = self._define_intent_patterns()
        
        # Entity patterns
        self.entity_patterns = self._define_entity_patterns()
    
    def _load_spacy_model(self):
        """Load spaCy language model."""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self.matcher = Matcher(self.nlp.vocab)
            self._setup_patterns()
            self.logger.info("spaCy model loaded successfully")
        except OSError:
            self.logger.error("spaCy model 'en_core_web_sm' not found. Please install it.")
        except Exception as e:
            self.logger.error(f"Failed to load spaCy model: {e}")
    
    def _define_intent_patterns(self) -> Dict[str, List[str]]:
        """Define intent recognition patterns."""
        return {
            "greeting": [
                r"^(hi|hello|hey|good morning|good afternoon|good evening)",
                r"(how are you|what's up|how's it going)"
            ],
            "goodbye": [
                r"(bye|goodbye|see you|farewell|exit|quit)",
                r"(good night|talk to you later)"
            ],
            "question": [
                r"^(what|who|when|where|why|how|which|can you)",
                r"(tell me|explain|describe|define)"
            ],
            "command": [
                r"^(please|could you|can you|would you)",
                r"(do|perform|execute|run|start|stop)"
            ],
            "math": [
                r"(calculate|compute|solve|what is|what's)",
                r"(\d+\s*[\+\-\*\/\%]\s*\d+)",
                r"(square root|factorial|power|percentage)"
            ],
            "file_operation": [
                r"(open|read|write|create|delete|copy|move)",
                r"(file|folder|directory|document)"
            ],
            "system_info": [
                r"(system|computer|memory|cpu|disk|process)",
                r"(status|information|stats|usage)"
            ],
            "time_date": [
                r"(time|date|clock|calendar|today|now)",
                r"(what time|current time|what date)"
            ],
            "weather": [
                r"(weather|temperature|forecast|rain|sunny|cloudy)",
                r"(how's the weather|what's the weather)"
            ],
            "help": [
                r"(help|assist|support|guide|tutorial)",
                r"(what can you do|capabilities|features)"
            ]
        }
    
    def _define_entity_patterns(self) -> Dict[str, List[str]]:
        """Define entity extraction patterns."""
        return {
            "file_path": [
                r"([\/~]?[\w\-\.\/]+\.\w+)",  # File with extension
                r"([\/~]?[\w\-\.\/]+\/)"      # Directory path
            ],
            "number": [
                r"(\d+\.?\d*)",
                r"(one|two|three|four|five|six|seven|eight|nine|ten)"
            ],
            "operation": [
                r"(add|subtract|multiply|divide|plus|minus|times|divided by)"
            ],
            "application": [
                r"(firefox|chrome|terminal|calculator|notepad|editor)"
            ],
            "location": [
                r"(home|desktop|documents|downloads|pictures|music|videos)"
            ]
        }
    
    def _setup_patterns(self):
        """Setup spaCy matcher patterns."""
        if not self.matcher:
            return
        
        try:
            # Math operation patterns
            math_patterns = [
                [{"LIKE_NUM": True}, {"LOWER": {"IN": ["plus", "+"]}}, {"LIKE_NUM": True}],
                [{"LIKE_NUM": True}, {"LOWER": {"IN": ["minus", "-"]}}, {"LIKE_NUM": True}],
                [{"LIKE_NUM": True}, {"LOWER": {"IN": ["times", "*", "multiplied"]}}, {"LOWER": "by", "OP": "?"}, {"LIKE_NUM": True}],
                [{"LIKE_NUM": True}, {"LOWER": {"IN": ["divided", "/"]}}, {"LOWER": "by", "OP": "?"}, {"LIKE_NUM": True}]
            ]
            
            for i, pattern in enumerate(math_patterns):
                self.matcher.add(f"MATH_OP_{i}", [pattern])
            
            # File operation patterns
            file_patterns = [
                [{"LOWER": {"IN": ["open", "read", "edit"]}}, {"IS_ALPHA": True, "OP": "*"}, {"LIKE_URL": True}],
                [{"LOWER": {"IN": ["create", "make", "new"]}}, {"LOWER": {"IN": ["file", "folder", "directory"]}}],
                [{"LOWER": {"IN": ["delete", "remove"]}}, {"IS_ALPHA": True, "OP": "*"}]
            ]
            
            for i, pattern in enumerate(file_patterns):
                self.matcher.add(f"FILE_OP_{i}", [pattern])
            
        except Exception as e:
            self.logger.error(f"Failed to setup patterns: {e}")
    
    def process_text(self, text: str) -> Dict[str, Any]:
        """Process text and extract intent, entities, and other information."""
        try:
            if not self.nlp:
                return self._fallback_processing(text)
            
            # Process with spaCy
            doc = self.nlp(text)
            
            # Extract basic information
            result = {
                "original_text": text,
                "processed_text": text.lower().strip(),
                "tokens": [token.text for token in doc],
                "lemmas": [token.lemma_ for token in doc],
                "pos_tags": [(token.text, token.pos_) for token in doc],
                "entities": [(ent.text, ent.label_) for ent in doc.ents],
                "intent": self._classify_intent(text),
                "confidence": 0.0,
                "extracted_entities": {},
                "sentiment": self._analyze_sentiment(doc),
                "keywords": self._extract_keywords(doc)
            }
            
            # Extract custom entities
            result["extracted_entities"] = self._extract_custom_entities(text)
            
            # Use spaCy matcher
            matches = self.matcher(doc)
            result["matches"] = [(self.nlp.vocab.strings[match_id], start, end) 
                               for match_id, start, end in matches]
            
            # Calculate confidence based on pattern matches
            result["confidence"] = self._calculate_confidence(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"NLP processing failed: {e}")
            return self._fallback_processing(text)
    
    def _classify_intent(self, text: str) -> str:
        """Classify the intent of the text."""
        text_lower = text.lower()
        
        # Check each intent pattern
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return intent
        
        # Default intent
        if "?" in text:
            return "question"
        elif any(word in text_lower for word in ["please", "can you", "could you"]):
            return "command"
        else:
            return "statement"
    
    def _extract_custom_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract custom entities using regex patterns."""
        entities = {}
        
        for entity_type, patterns in self.entity_patterns.items():
            entities[entity_type] = []
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                entities[entity_type].extend(matches)
        
        # Remove duplicates
        for entity_type in entities:
            entities[entity_type] = list(set(entities[entity_type]))
        
        return entities
    
    def _analyze_sentiment(self, doc) -> Dict[str, float]:
        """Analyze sentiment of the text."""
        # Simple sentiment analysis based on word polarity
        positive_words = ["good", "great", "excellent", "amazing", "wonderful", "fantastic", "love", "like", "happy", "pleased"]
        negative_words = ["bad", "terrible", "awful", "horrible", "hate", "dislike", "sad", "angry", "frustrated", "disappointed"]
        
        tokens = [token.text.lower() for token in doc]
        
        positive_count = sum(1 for word in tokens if word in positive_words)
        negative_count = sum(1 for word in tokens if word in negative_words)
        total_words = len(tokens)
        
        if total_words == 0:
            return {"polarity": 0.0, "subjectivity": 0.0}
        
        polarity = (positive_count - negative_count) / total_words
        subjectivity = (positive_count + negative_count) / total_words
        
        return {
            "polarity": polarity,
            "subjectivity": subjectivity,
            "positive_words": positive_count,
            "negative_words": negative_count
        }
    
    def _extract_keywords(self, doc) -> List[str]:
        """Extract important keywords from the text."""
        # Filter out stop words, punctuation, and short words
        keywords = []
        
        for token in doc:
            if (not token.is_stop and 
                not token.is_punct and 
                not token.is_space and
                len(token.text) > 2 and
                token.pos_ in ["NOUN", "VERB", "ADJ", "PROPN"]):
                keywords.append(token.lemma_.lower())
        
        return list(set(keywords))
    
    def _calculate_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence score for the processing result."""
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on entity matches
        entity_count = sum(len(entities) for entities in result["extracted_entities"].values())
        confidence += min(entity_count * 0.1, 0.3)
        
        # Increase confidence based on spaCy matches
        if result["matches"]:
            confidence += min(len(result["matches"]) * 0.1, 0.2)
        
        # Increase confidence for clear intents
        if result["intent"] in ["math", "file_operation", "system_info", "time_date"]:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _fallback_processing(self, text: str) -> Dict[str, Any]:
        """Fallback processing when spaCy is not available."""
        return {
            "original_text": text,
            "processed_text": text.lower().strip(),
            "tokens": text.split(),
            "lemmas": text.lower().split(),
            "pos_tags": [],
            "entities": [],
            "intent": self._classify_intent(text),
            "confidence": 0.3,
            "extracted_entities": self._extract_custom_entities(text),
            "sentiment": {"polarity": 0.0, "subjectivity": 0.0},
            "keywords": [word.lower() for word in text.split() if len(word) > 2],
            "matches": []
        }
    
    def extract_math_expression(self, text: str) -> Optional[str]:
        """Extract mathematical expression from text."""
        # Look for mathematical expressions
        math_patterns = [
            r"(\d+\.?\d*\s*[\+\-\*\/\%\^]\s*\d+\.?\d*)",
            r"(square root of \d+\.?\d*)",
            r"(\d+\.?\d* factorial)",
            r"(\d+\.?\d* percent of \d+\.?\d*)"
        ]
        
        for pattern in math_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_file_path(self, text: str) -> Optional[str]:
        """Extract file path from text."""
        # Look for file paths
        path_patterns = [
            r"([\/~]?[\w\-\.\/]+\.\w+)",  # File with extension
            r"([\/~]?[\w\-\.\/]+\/)",      # Directory path
            r"([\w\-\.]+\.\w+)"           # Simple filename
        ]
        
        for pattern in path_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def is_question(self, text: str) -> bool:
        """Check if text is a question."""
        question_indicators = [
            text.strip().endswith("?"),
            text.lower().startswith(("what", "who", "when", "where", "why", "how", "which", "can", "could", "would", "should", "is", "are", "do", "does", "did"))
        ]
        
        return any(question_indicators)
    
    def is_command(self, text: str) -> bool:
        """Check if text is a command."""
        command_indicators = [
            text.lower().startswith(("please", "can you", "could you", "would you", "do", "run", "execute", "start", "stop", "open", "close", "create", "delete"))
        ]
        
        return any(command_indicators)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get NLP processor statistics."""
        return {
            "spacy_available": self.nlp is not None,
            "matcher_available": self.matcher is not None,
            "intent_patterns": len(self.intent_patterns),
            "entity_patterns": len(self.entity_patterns),
            "model_name": "en_core_web_sm" if self.nlp else None
        }
