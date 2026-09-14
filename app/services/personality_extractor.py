import re
from typing import List, Optional, Dict, Any
from collections import Counter
from app.models.personality import ExtractedTraits

class PersonalityExtractorService:
    """
    Automated Extraction Pass: Parses text messages, emails, chat logs,
    or natural language personality descriptions to extract tone, slang,
    response length, emojis, topics, and greeting style.
    """

    COMMON_SLANG = {
        "lol", "lmao", "rofl", "ngl", "tbh", "brb", "btw", "omg", "idk",
        "smh", "btw", "afaik", "imo", "imho", "icymi", "fr", "cap", "no cap",
        "bet", "slay", "fam", "vibe", "vibes", "flex", "sus", "bruh", "y'all"
    }

    FORMAL_INDICATORS = {
        "sincerely", "regards", "dear", "furthermore", "however", "therefore",
        "consequently", "cordially", "appreciate", "kindly", "attached", "formal", "polite"
    }

    EMOJI_PATTERN = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U0001F900-\U0001F9FF"
        "\U00002600-\U000026FF"
        "\U00002700-\U000027BF"
        "]+", 
        flags=re.UNICODE
    )

    @classmethod
    def extract_traits(
        cls, 
        raw_texts: Optional[List[str]] = None, 
        personality_description: Optional[str] = None,
        formality_override: Optional[str] = None,
        response_length_override: Optional[str] = None
    ) -> ExtractedTraits:
        
        text_sources = []
        if raw_texts:
            text_sources.extend(raw_texts)
        if personality_description:
            text_sources.append(personality_description)

        eff_formality = formality_override if formality_override and formality_override != "auto" else "casual"
        eff_length = response_length_override if response_length_override and response_length_override != "auto" else "short"

        if not text_sources:
            return ExtractedTraits(formality=eff_formality, average_response_length=eff_length)

        combined_text = " ".join(text_sources)
        words = re.findall(r'\b\w+\b', combined_text.lower())
        total_words = len(words)

        if total_words == 0:
            return ExtractedTraits(formality=eff_formality, average_response_length=eff_length)

        # 1. Slang Tokens Detection
        found_slang = [w for w in words if w in cls.COMMON_SLANG]
        slang_counter = Counter(found_slang)
        top_slang = [item[0] for item in slang_counter.most_common(8)]

        # Check for explicitly mentioned slang words in description text
        if personality_description:
            desc_words = re.findall(r'\b\w+\b', personality_description.lower())
            for w in desc_words:
                if w in cls.COMMON_SLANG and w not in top_slang:
                    top_slang.append(w)

        # 2. Formality Analysis (Use explicit override if provided and not 'auto')
        if formality_override and formality_override.lower() != "auto":
            formality = formality_override.lower()
        elif "formal" in words or "professional" in words:
            formality = "formal"
        elif "sarcastic" in words or "witty" in words:
            formality = "witty & sarcastic"
        elif "pirate" in words or "matey" in words:
            formality = "pirate & adventurous"
        elif sum(1 for w in words if w in cls.FORMAL_INDICATORS) > len(found_slang) and total_words > 10:
            formality = "formal"
        elif len(found_slang) > 0 or "casual" in words:
            formality = "casual"
        else:
            formality = "expressive"

        # 3. Average Response Length (Use explicit override if provided and not 'auto')
        if response_length_override and response_length_override.lower() != "auto":
            length_category = response_length_override.lower()
        elif "short" in words or "brief" in words or "concise" in words:
            length_category = "short"
        elif "long" in words or "detailed" in words or "verbose" in words:
            length_category = "verbose"
        else:
            avg_len = total_words / max(len(text_sources), 1)
            if avg_len < 12:
                length_category = "short"
            elif avg_len < 35:
                length_category = "medium"
            else:
                length_category = "verbose"

        # 4. Emoji Analysis
        emojis_found = cls.EMOJI_PATTERN.findall(combined_text)
        emoji_counter = Counter(emojis_found)
        fav_emojis = [item[0] for item in emoji_counter.most_common(5)]
        
        if len(emojis_found) == 0 and "emoji" not in words:
            emoji_freq = "low" if personality_description else "none"
        elif len(emojis_found) < 3:
            emoji_freq = "moderate"
        else:
            emoji_freq = "high"

        # 5. Top Topics / Keywords
        stopwords = {
            "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
            "to", "in", "of", "on", "for", "with", "at", "by", "from", "it",
            "this", "that", "you", "i", "me", "my", "we", "your", "have", "be",
            "so", "just", "if", "not", "no", "can", "do", "what", "how", "like",
            "uses", "loves", "enjoys", "companion", "personality", "traits", "wants"
        }
        filtered_words = [w for w in words if w not in stopwords and len(w) > 3 and w not in cls.COMMON_SLANG]
        topic_counter = Counter(filtered_words)
        top_topics = [item[0] for item in topic_counter.most_common(5)]

        # 6. Greeting Style & Tone
        greeting = "Hey!"
        for text in text_sources:
            first_line = text.strip().split("\n")[0].strip()
            if re.match(r'^(hey|hi|hello|yo|good morning|sup)\b', first_line, re.IGNORECASE):
                greeting = first_line
                break

        tone_parts = [formality]
        if len(found_slang) > 0 or top_slang:
            tone_parts.append("expressive")
        tone_summary = ", ".join(tone_parts)

        return ExtractedTraits(
            formality=formality,
            slang_tokens=top_slang,
            average_response_length=length_category,
            emoji_frequency=emoji_freq,
            favorite_emojis=fav_emojis,
            tone=tone_summary,
            sentiment_bias="positive" if "happy" in words or "great" in words or "love" in words or "friendly" in words else "neutral",
            top_topics=top_topics,
            greeting_style=greeting,
            custom_description=personality_description
        )
