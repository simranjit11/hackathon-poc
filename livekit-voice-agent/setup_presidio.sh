#!/bin/bash
# Setup script for Presidio PII masking

echo "Setting up Presidio for PII masking..."

# Check if we're in a uv project
if [ -f "pyproject.toml" ]; then
    echo "Detected uv project. Using uv to manage dependencies..."
    
    # Install Presidio dependencies (already in pyproject.toml, but sync to ensure they're installed)
    echo "Syncing dependencies with uv..."
    uv sync
    
    # Download the English language model for spaCy (required by Presidio)
    echo "Downloading spaCy English language model..."
    uv run python -m spacy download en_core_web_lg
else
    # Fallback to pip if not using uv
    echo "Installing Presidio packages with pip..."
    pip install presidio-analyzer presidio-anonymizer spacy
    
    # Download the English language model for spaCy (required by Presidio)
    echo "Downloading spaCy English language model..."
    python -m spacy download en_core_web_lg
fi

echo ""
echo "Presidio setup complete!"
echo ""
echo "Note: If you encounter issues, you may need to install the model manually:"
if [ -f "pyproject.toml" ]; then
    echo "  uv run python -m spacy download en_core_web_lg"
else
    echo "  python -m spacy download en_core_web_lg"
fi

