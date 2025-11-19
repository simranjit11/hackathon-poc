"""
PII Masking Module using Presidio
==================================
Optional PII masking functionality for the LiveKit voice agent.
Can be enabled/disabled via ENABLE_PII_MASKING environment variable.
"""

import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global analyzer and anonymizer instances (lazy-loaded)
_analyzer = None
_anonymizer = None
_pii_masking_enabled = None


def is_pii_masking_enabled() -> bool:
    """Check if PII masking is enabled via environment variable."""
    global _pii_masking_enabled
    if _pii_masking_enabled is None:
        _pii_masking_enabled = os.getenv("ENABLE_PII_MASKING", "false").lower() in ("true", "1", "yes")
    return _pii_masking_enabled


def get_analyzer():
    """
    Get Presidio Analyzer instance (lazy-loaded).
    Returns None if PII masking is disabled or Presidio is not available.
    """
    global _analyzer
    
    if not is_pii_masking_enabled():
        return None
    
    if _analyzer is None:
        try:
            from presidio_analyzer import AnalyzerEngine
            _analyzer = AnalyzerEngine()
            logger.info("Presidio Analyzer initialized successfully")
        except ImportError:
            logger.warning(
                "Presidio not installed. PII masking disabled. "
                "Install with: pip install presidio-analyzer presidio-anonymizer spacy"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Presidio Analyzer: {e}")
            return None
    
    return _analyzer


def get_anonymizer():
    """
    Get Presidio Anonymizer instance (lazy-loaded).
    Returns None if PII masking is disabled or Presidio is not available.
    """
    global _anonymizer
    
    if not is_pii_masking_enabled():
        return None
    
    if _anonymizer is None:
        try:
            from presidio_anonymizer import AnonymizerEngine
            from presidio_anonymizer.entities import OperatorConfig
            _anonymizer = AnonymizerEngine()
            logger.info("Presidio Anonymizer initialized successfully")
        except ImportError:
            logger.warning(
                "Presidio not installed. PII masking disabled. "
                "Install with: pip install presidio-analyzer presidio-anonymizer spacy"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Presidio Anonymizer: {e}")
            return None
    
    return _anonymizer


def sanitize_text(text: str) -> str:
    """
    Sanitize text by masking PII using Presidio.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text with PII masked, or original text if masking is disabled/failed
    """
    if not text or text.strip() == "":
        return text
    
    # If PII masking is disabled, return text as-is
    if not is_pii_masking_enabled():
        return text
    
    # Get analyzer and anonymizer
    analyzer = get_analyzer()
    anonymizer = get_anonymizer()
    
    # If Presidio is not available, return text as-is
    if analyzer is None or anonymizer is None:
        return text
    
    try:
        # 1. Analyze (Detect PII)
        # Include OTP and other sensitive entities
        results = analyzer.analyze(
            text=text,
            entities=[
                "OTP",
                "PERSON",
                "EMAIL_ADDRESS",
                "PHONE_NUMBER",
                "CREDIT_CARD",
                "SSN",
                "IBAN_CODE",
                "US_DRIVER_LICENSE",
                "US_PASSPORT",
                "US_BANK_NUMBER",
            ],
            language='en'
        )
        
        # 2. Anonymize (Redact PII)
        from presidio_anonymizer.entities import OperatorConfig
        anonymized_result = anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators={"DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"})}
        )
        
        if len(results) > 0:
            logger.info(f"🛡️ Guardrail triggered. Redacted {len(results)} entities.")
        
        return anonymized_result.text
        
    except Exception as e:
        logger.error(f"Error during PII masking: {e}")
        # Return original text if masking fails
        return text

