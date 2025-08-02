import streamlit as st
import openai

st.set_page_config(page_title="LabMate", layout="wide")
st.title("🧪 LabMate: AI Copilot for Wet Lab Protocols")
st.write("Paste a protocol and customize the instruction before optimization.")

# Protocol-type presets
protocol_type = st.selectbox("Protocol type (preset)", ["General wet lab", "PCR", "Rodent brain surgery"])
default_prompts = {
    "General wet lab": """You are a practical wet lab assistant. Given the protocol below, do the following clearly and concisely:

1. **Issues / Ambiguities:** Bullet any missing parameters (volumes, concentrations, equipment), unclear sequencing, or potential errors.
2. **Parallelization Opportunities:** Exactly state which steps can overlap and why.
3. **Reordered Optimized Protocol:** Provide a step-by-step version that minimizes idle time, annotate each with estimated duration and saved time.
4. **Checklist:** Condensed actionable checklist with checkboxes.

Protocol:
{protocol_text}""",
    "PCR": """You are a practical wet lab assistant focused on PCR workflows. Given the protocol below, do the following:

1. List missing reagent volumes, thermal cycling parameters, and ambiguity.
2. Point out what can be parallelized (e.g., tube preparation during machine warm-up).
3. Reorder to minimize idle time and annotate estimated duration.
4. Give a concise checklist.

Protocol:
{protocol_text}""",
    "Rodent brain surgery": """You are an expert surgical lab assistant for rodent brain surgery. Given the protocol below, do the following with safety focus:

1. Issues/Ambiguities: missing doses, sterility lapses, monitoring gaps.
2. Parallelization: prep that can happen while anesthesia stabilizes.
3. Optimized Protocol: minimize anesthesia time with rationale.
4. Safety & Recovery Checklist.
5. Contingencies: brief mitigation steps.

Protocol:
{protocol_text}"""
}

# Editable prompt area
base_prompt = default_prompts[protocol_type]
custom_prompt = st.text_area("Instruction template (you can edit)", base_prompt, height=340)

# Protocol input
protocol = st.text_area("Paste your protocol here", height=220)

# Show a small toggle to reset to preset
if st.button("Reset to preset"):
    st.experimental_rerun()

def detect_and_optimize(protocol_text, prompt_template):
    prompt = prompt_template.replace("{protocol_text}", protocol_text.strip())
    client = openai.OpenAI()
    model_sequence = ["gpt-4", "gpt-4-0613", "gpt-3.5-turbo"]
    last_error = None
    for model in model_sequence:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            content = resp.choices[0].message.content
            return f"**Used model:** {model}\n\n" + content
        except Exception as e:
            last_error = e
    return (
        f"All model attempts failed. Last error: {last_error}\n\n"
        "**Fallback example:**\n"
        "- Issues: unclear volumes or missing prep steps.\n"
        "- Parallelization: do setup while waiting for incubation.\n"
        "- Optimized Protocol: combine reagent prep with equipment warm-up.\n"
        "- Checklist: [ ] Ready, [ ] Started, [ ] Monitored."
    )

st.markdown("---")
if st.button("Optimize"):
    if not protocol.strip():
        st.warning("Paste a protocol first.")
    else:
        if "OPENAI_API_KEY" not in st.secrets:
            st.error("Missing OpenAI key in secrets.")
        else:
            openai.api_key = st.secrets["OPENAI_API_KEY"]
            with st.spinner("Optimizing..."):
                output = detect_and_optimize(protocol, custom_prompt)
                st.markdown(output)
                st.download_button("Download Output", output, file_name="optimized_protocol.txt")
