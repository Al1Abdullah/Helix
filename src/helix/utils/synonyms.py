"""
Condition synonym and abbreviation expansion.
Zero external dependencies — pure stdlib dict lookup.
Call expand() before passing any user-supplied condition to an external API.
"""
from __future__ import annotations

_MAP: dict[str, str] = {
    # Diabetes
    "t2d": "Type 2 Diabetes",
    "type2 diabetes": "Type 2 Diabetes",
    "diabetes type 2": "Type 2 Diabetes",
    "dm2": "Type 2 Diabetes",
    "t1d": "Type 1 Diabetes",
    "dm1": "Type 1 Diabetes",
    # Oncology
    "nsclc": "Non-Small Cell Lung Cancer",
    "sclc": "Small Cell Lung Cancer",
    "crc": "Colorectal Cancer",
    "tnbc": "Triple Negative Breast Cancer",
    "hnscc": "Head and Neck Squamous Cell Carcinoma",
    "hcc": "Hepatocellular Carcinoma",
    "rcc": "Renal Cell Carcinoma",
    "dlbcl": "Diffuse Large B-Cell Lymphoma",
    "cll": "Chronic Lymphocytic Leukemia",
    "aml": "Acute Myeloid Leukemia",
    "cml": "Chronic Myeloid Leukemia",
    "mm": "Multiple Myeloma",
    # Cardiology
    "chf": "Congestive Heart Failure",
    "hf": "Heart Failure",
    "afib": "Atrial Fibrillation",
    "af": "Atrial Fibrillation",
    "cad": "Coronary Artery Disease",
    "mi": "Myocardial Infarction",
    "acs": "Acute Coronary Syndrome",
    "pad": "Peripheral Arterial Disease",
    "htn": "Hypertension",
    "svt": "Supraventricular Tachycardia",
    # Pulmonology
    "copd": "Chronic Obstructive Pulmonary Disease",
    "ild": "Interstitial Lung Disease",
    "ards": "Acute Respiratory Distress Syndrome",
    "ph": "Pulmonary Hypertension",
    # Nephrology
    "ckd": "Chronic Kidney Disease",
    "aki": "Acute Kidney Injury",
    "esrd": "End-Stage Renal Disease",
    "fsgs": "Focal Segmental Glomerulosclerosis",
    # Gastroenterology
    "nash": "Non-Alcoholic Steatohepatitis",
    "nafld": "Non-Alcoholic Fatty Liver Disease",
    "ibd": "Inflammatory Bowel Disease",
    "uc": "Ulcerative Colitis",
    "cd": "Crohn's Disease",
    "gerd": "Gastroesophageal Reflux Disease",
    "pbc": "Primary Biliary Cholangitis",
    # Rheumatology / Immunology
    "ra": "Rheumatoid Arthritis",
    "sle": "Systemic Lupus Erythematosus",
    "lupus": "Systemic Lupus Erythematosus",
    "as": "Ankylosing Spondylitis",
    "psa": "Psoriatic Arthritis",
    "ssc": "Systemic Sclerosis",
    "sjogrens": "Sjogren's Syndrome",
    "gpa": "Granulomatosis with Polyangiitis",
    # Neurology
    "ms": "Multiple Sclerosis",
    "ad": "Alzheimer's Disease",
    "pd": "Parkinson's Disease",
    "als": "Amyotrophic Lateral Sclerosis",
    "tbi": "Traumatic Brain Injury",
    # Infectious Disease
    "hiv": "Human Immunodeficiency Virus",
    "hbv": "Hepatitis B",
    "hcv": "Hepatitis C",
    "tb": "Tuberculosis",
    "cdiff": "Clostridioides difficile",
    # Psychiatry
    "mdd": "Major Depressive Disorder",
    "gad": "Generalized Anxiety Disorder",
    "ocd": "Obsessive Compulsive Disorder",
    "ptsd": "Post-Traumatic Stress Disorder",
    "bpd": "Borderline Personality Disorder",
    "adhd": "Attention Deficit Hyperactivity Disorder",
    # Dermatology / Endocrine
    "pso": "Psoriasis",
    "atd": "Atopic Dermatitis",
    "hypo": "Hypothyroidism",
    "hyper": "Hyperthyroidism",
}


def expand(condition: str) -> str:
    """
    Return the canonical condition name for known abbreviations/aliases.
    Comparison is case-insensitive; strips extra whitespace.
    Returns the original string unchanged if no mapping exists.

    Examples:
        expand("T2D")   → "Type 2 Diabetes"
        expand("nsclc") → "Non-Small Cell Lung Cancer"
        expand("Type 2 Diabetes") → "Type 2 Diabetes"   # passthrough
        expand("  COPD  ") → "Chronic Obstructive Pulmonary Disease"
    """
    if not condition:
        return condition
    return _MAP.get(condition.strip().lower(), condition)
