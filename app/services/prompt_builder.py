from app.models.personality import ExtractedTraits

class PromptBuilderService:
    """
    Roleplay System Prompt Generator.
    Crafts unconstrained, natural character prompts that preserve the full creativity,
    slang, tone, and expression of the underlying LLM.
    """

    @classmethod
    def build_system_prompt(cls, companion_name: str, companion_type: str, traits: ExtractedTraits) -> str:
        custom_desc_part = f"\n{traits.custom_description.strip()}\n" if traits.custom_description and traits.custom_description.strip() else ""
        appearance_part = f"\n- Physical Appearance: {traits.physical_appearance.strip()}" if traits.physical_appearance and traits.physical_appearance.strip() else ""

        slang_part = f"\n- Favorite Slang & Vocabulary: {', '.join(traits.slang_tokens)}" if traits.slang_tokens else ""
        emojis_part = f"\n- Preferred Emojis: {' '.join(traits.favorite_emojis)}" if traits.favorite_emojis else ""
        topics_part = f"\n- Interests & Topics: {', '.join(traits.top_topics)}" if traits.top_topics else ""

        avg_len = (traits.average_response_length or "short").lower()
        if avg_len in ["short", "concise"]:
            length_instruction = "STRICTLY CONCISE & SHORT (1 to 3 natural sentences max). Never write long monologues, essays, or multiple paragraphs."
        elif avg_len in ["medium", "balanced"]:
            length_instruction = "MEDIUM (2 to 4 sentences). Keep it conversational without dragging on."
        else:
            length_instruction = f"{avg_len} in length."

        msg_style = (getattr(traits, "messaging_style", None) or "sms").lower()
        if "sms" in msg_style or "text" in msg_style:
            style_instruction = (
                "5. REAL-TIME SMS / TEXT MESSAGING STYLE DIRECTIVE:\n"
                "   - You are texting with the user over SMS/iMessage on your smartphone.\n"
                "   - Write short, direct, casual text messages (1-3 sentences max). Use natural texting phrasing, emojis, and realistic conversation flow.\n"
                "   - STRICT NO-ASTERISK RULE: DO NOT use asterisks or italicized stage directions for actions (do NOT write '*smiles*', '*walks in*', or '*sighs*'). Write purely in direct, authentic text message speech as if sending an SMS."
            )
        else:
            style_instruction = (
                "5. EXPRESSIVE ROLEPLAY STYLE DIRECTIVE:\n"
                "   - Express character actions, gestures, and emotions alongside your speech."
            )

        prompt = f"""You are {companion_name}, a custom companion of type '{companion_type}'.
{custom_desc_part}
### PERSONALITY PROFILE:
- Formality & Tone: {traits.formality.upper()} ({traits.tone})
- Messaging Style: {msg_style.upper()} (SMS/iMessage texting)
- Average Response Length: {traits.average_response_length.upper()}{appearance_part}{slang_part}{emojis_part}{topics_part}
- Greeting Style: "{traits.greeting_style}"

### CHARACTER DIRECTIVES:
1. Stay fully in character as {companion_name} at all times. You have a physical appearance, human body, clothing, and real-world environment.
2. NEVER mention being an AI, language model, software, or digital program. NEVER disclaim physical form or claim you cannot take photos.
3. RESPONSE LENGTH DIRECTIVE: Keep responses {length_instruction}
4. PHOTO & SELFIE TOOL DIRECTIVE:
   When asked to take a selfie, snap a photo, or show your location, you MUST append a JSON tool call on a new line at the very end of your response:
   {{"generate_image": true, "prompt": "<vivid detailed description matching your exact current chat situation>"}}

   CRITICAL RULES FOR THE IMAGE PROMPT:
   - STRICT CHAT CONTEXT CONGRUENCE: The prompt MUST accurately reflect your EXACT current activity, clothing, pose, objects, and environment as established in the immediate conversation history. (e.g., if you are drinking coffee on the porch, describe yourself drinking coffee on the porch in that exact outfit).
   - CHARACTER PHYSICAL CONSISTENCY & NO PROPER NAMES: NEVER use proper character names (do NOT write "{companion_name}"). Instead, explicitly describe physical human features matching your character's defined appearance in your profile (e.g. hair color, hair style, eye color, facial features, body type, skin tone).
   - NO AI DISCLAIMERS OR PLACEHOLDERS: Always generate a complete, realistic descriptive image prompt.
{style_instruction}"""
        return prompt.strip()

    @classmethod
    def extract_physical_descriptors(cls, text: str) -> str:
        """
        Extracts physical descriptors (hair, eyes, skin tone, features, outfit) 
        from a character description or system prompt.
        """
        if not text:
            return ""
        
        lines = text.split("\n")
        descriptors = []
        
        keywords = [
            "hair", "eyes", "eye", "skin", "tall", "petite", "slender", "athletic", 
            "blonde", "brunette", "redhead", "black hair", "brown hair", "blue eyes", 
            "green eyes", "hazel", "wearing", "dressed in", "outfit", "face", "appearance"
        ]
        
        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in keywords):
                clean_line = line.strip(" -*#\t")
                if clean_line and len(clean_line) < 150:
                    descriptors.append(clean_line)
                    
        if descriptors:
            return ", ".join(descriptors[:3])
            
        clean_text = text.strip()
        if len(clean_text) < 100:
            return clean_text
            
        return ""


