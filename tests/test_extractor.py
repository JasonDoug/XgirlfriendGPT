from app.services.personality_extractor import PersonalityExtractorService
from app.services.prompt_builder import PromptBuilderService

def test_personality_extractor_from_logs():
    sample_texts = [
        "Hey! What's up? lol ngl I'm so excited for gaming tonight 🔥",
        "brb getting some coffee, vibes are immaculate ✨",
        "yo bet! see ya soon bruh 😂"
    ]
    
    traits = PersonalityExtractorService.extract_traits(raw_texts=sample_texts)
    
    assert traits.formality in ["casual", "balanced"]
    assert "lol" in traits.slang_tokens or "ngl" in traits.slang_tokens
    assert traits.average_response_length == "short"
    assert traits.emoji_frequency in ["moderate", "high"]
    assert "gaming" in traits.top_topics or "coffee" in traits.top_topics

def test_personality_extractor_from_description():
    desc = "A witty, sarcastic tech enthusiast who loves gaming and coffee. Uses slang like 'brb' and 'ngl', and keeps replies short and energetic."
    
    traits = PersonalityExtractorService.extract_traits(personality_description=desc)
    
    assert "brb" in traits.slang_tokens or "ngl" in traits.slang_tokens
    assert traits.average_response_length == "short"
    assert traits.custom_description == desc

def test_prompt_builder_with_description():
    desc = "A witty tech enthusiast who loves coding."
    traits = PersonalityExtractorService.extract_traits(personality_description=desc)
    
    system_prompt = PromptBuilderService.build_system_prompt("Luna", "friend", traits)
    
    assert "Luna" in system_prompt
    assert "CHARACTER DIRECTIVES" in system_prompt
    assert "witty tech enthusiast" in system_prompt

def test_personality_extractor_overrides():
    desc = "A calm mentor."
    traits = PersonalityExtractorService.extract_traits(
        personality_description=desc,
        formality_override="formal",
        response_length_override="verbose"
    )
    assert traits.formality == "formal"
    assert traits.average_response_length == "verbose"
    
    system_prompt = PromptBuilderService.build_system_prompt("Professor", "mentor", traits)
    assert "verbose" in system_prompt

def test_personality_extractor_with_appearance():
    p_desc = "A witty programmer."
    a_desc = "Long blonde hair, blue eyes, athletic build, wearing a black leather jacket."
    
    traits = PersonalityExtractorService.extract_traits(
        personality_description=p_desc,
        appearance_description=a_desc
    )
    
    assert traits.custom_description == p_desc
    assert traits.physical_appearance == a_desc
    
    system_prompt = PromptBuilderService.build_system_prompt("Aria", "friend", traits)
    assert "Long blonde hair" in system_prompt
    assert "Physical Appearance" in system_prompt
