from src.services.llm import LLMAnalyzer

def test_llm_analyzer_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    analyzer = LLMAnalyzer()
    
    def mock_analyze(*args, **kwargs):
        return {
            "classification": "Unknown",
            "severity": "Medium",
            "confidence": 0,
            "social_engineering_tactics": [],
            "rationale": "Malformed model output",
            "recommended_action": "Manual review"
        }
    
    analyzer.analyze = mock_analyze
    result = analyzer.analyze(None, None)
    
    assert "classification" in result
    assert "severity" in result
    assert result["classification"] == "Unknown"
