"""
Helix — HuggingFace Spaces demo.
Calls the Helix synthesis pipeline directly and renders results in Gradio.
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import gradio as gr
from helix.tools.synthesis import synthesizeEvidence


def runSynthesis(condition: str, age: int, location: str, sex: str) -> str:
    if not condition or not condition.strip():
        return "Please enter a medical condition."
    if not (0 <= age <= 130):
        return "Please enter a valid age (0–130)."
    sexParam = sex if sex != "Any" else None
    locationParam = location.strip() if location and location.strip() else None
    try:
        result = asyncio.run(
            synthesizeEvidence(condition.strip(), int(age), locationParam, sexParam)
        )
        return json.dumps(result, indent=2)
    except Exception as error:
        return f"Error: {error}"


with gr.Blocks(title="Helix — Clinical Evidence Synthesis", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🧬 Helix
        **Clinical evidence synthesis engine** — queries ClinicalTrials.gov, PubMed, and openFDA
        simultaneously and returns scored, ranked trials with full explainability vectors.
        No API key needed.
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            conditionInput = gr.Textbox(
                label="Medical Condition",
                placeholder="e.g. T2D, NSCLC, Alzheimer's Disease, COPD",
                info="Medical abbreviations are automatically expanded (T2D → Type 2 Diabetes)",
            )
            ageInput = gr.Number(label="Patient Age", value=45, minimum=0, maximum=130, precision=0)
            locationInput = gr.Textbox(
                label="Location (optional)",
                placeholder="e.g. Boston, MA  or  London, UK",
            )
            sexInput = gr.Dropdown(
                label="Sex Filter (optional)",
                choices=["Any", "MALE", "FEMALE"],
                value="Any",
            )
            submitButton = gr.Button("Synthesize Evidence", variant="primary")

        with gr.Column(scale=2):
            outputBox = gr.Code(
                label="Synthesis Result",
                language="json",
                lines=30,
            )

    gr.Examples(
        examples=[
            ["T2D", 45, "Boston, MA", "MALE"],
            ["NSCLC", 62, "London, UK", "FEMALE"],
            ["Alzheimer's Disease", 70, "", "Any"],
            ["COPD", 58, "Chicago, IL", "Any"],
        ],
        inputs=[conditionInput, ageInput, locationInput, sexInput],
    )

    submitButton.click(
        fn=runSynthesis,
        inputs=[conditionInput, ageInput, locationInput, sexInput],
        outputs=outputBox,
    )

if __name__ == "__main__":
    demo.launch()
