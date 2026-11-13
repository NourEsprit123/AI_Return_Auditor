import os

# Self-Consistency Parameters
NUM_SAMPLES = 5           # Number of independent reasoning paths to generate
TEMPERATURE = 0.7            # Higher temperature to ensure diversity in CoT trajectories
MIN_CONSENSUS_RATIO = 0.60   # Minimum majority agreement required (e.g., 3 out of 5)
top_p=0.9  

# Business Guardrail Limits
HIGH_VALUE_THRESHOLD_USD = 500.00  # Orders above this automatically route to human review

# Model Selection
GROQ_MODEL = "openai/gpt-oss-20b"