import streamlit as st
import openai
import io
from PyPDF2 import PdfReader

# --- page setup ---
st.set_page_config(page_title="LabMate", layout="wide")
st.title("🧪 LabMate: AI Copilot for Lab Protocols")
st.write(
    "1. Import or paste your protocol. 2. Pick or customize the instruction/template. "
    "3. Click Optimize. You can save reusable instruction templates or full presets (type + instruction)."
)

# --- protocol type selection with aliasing ---
protocol_type = st.selectbox(
    "Protocol type (preset)",
    [
        "General lab protocol",
        "PCR",
        "Surgical procedure",
        "RNA extraction",
        "Cell transfection",
        "Histology",
        "Flow Cytometry",
        "Synthetic biology assay",
        "Organoid culture",
        "DNA extraction",
        "cDNA synthesis",
        "Western blot",
        "ELISA",
        "qPCR",
        "CRISPR genome editing",
        "Gel electrophoresis",
        "Bacterial transformation",
        "Plasmid purification",
        "Immunoprecipitation",
        "Immunofluorescence",
        "Live cell imaging",
        "Single-cell RNA-seq",
        "Chromatin immunoprecipitation (ChIP)",
        "Tissue staining",
        "Microscopy imaging",
        "Optogenetics",
        "Stereotaxic procedures",
        "Yeast transformation",
        "NGS library prep",
        "Cell cycle assay",
        "Time-course experiment",
        "Biochemical assay",
        "Protein purification",
        "Enzymatic assay",
    ],
)
st.caption("Pick the context that best matches your protocol; this seeds a starting instruction. You can edit it below.")

# Base prompt templates
default_prompts = {
    "General lab protocol": """You are a practical lab assistant. Given the protocol below, do the following clearly and concisely:

1. **Issues / Ambiguities:** Bullet any missing parameters (volumes, concentrations, equipment), unclear sequencing, or potential errors.
2. **Parallelization Opportunities:** Exactly state which steps can overlap and why.
3. **Reordered Optimized Protocol:** Provide a step-by-step version that minimizes idle time, annotate each with estimated duration and time savings.
4. **Checklist:** Condensed actionable checklist with checkboxes.

Protocol:
{protocol_text}""",
    
    "PCR": """You are a practical lab assistant focused on PCR workflows. Given the protocol below, do the following:

1. **Issues/Ambiguities:** List missing reagent volumes, thermal cycling parameters, and unclear steps.
2. **Parallelization:** Point out what can be done simultaneously (e.g., tube preparation during machine warm-up).
3. **Optimized Protocol:** Reorder to minimize idle time and annotate estimated duration.
4. **Checklist:** Give a concise actionable checklist.

Protocol:
{protocol_text}""",
    
    "Surgical procedure": """You are an expert surgical lab assistant. Given the protocol below, do the following with safety and efficiency focus:

1. **Issues/Ambiguities:** Missing doses, sterility concerns, timing gaps, unclear monitoring steps.
2. **Parallelization:** Preparation steps that can happen during setup or waiting periods.
3. **Optimized Protocol:** Minimize procedure time while maintaining safety, with clear rationale.
4. **Safety & Workflow Checklist:** Essential safety checks and workflow steps.
5. **Contingencies:** Brief mitigation steps for common issues.

Protocol:
{protocol_text}""",
}

# Alias mapping
alias_map = {
    "RNA extraction": "General lab protocol",
    "Cell transfection": "General lab protocol",
    "Histology": "General lab protocol",
    "Flow Cytometry": "General lab protocol",
    "Synthetic biology assay": "General lab protocol",
    "Organoid culture": "General lab protocol",
    "DNA extraction": "General lab protocol",
    "cDNA synthesis": "General lab protocol",
    "Western blot": "General lab protocol",
    "ELISA": "General lab protocol",
    "qPCR": "PCR",
    "CRISPR genome editing": "General lab protocol",
    "Gel electrophoresis": "General lab protocol",
    "Bacterial transformation": "General lab protocol",
    "Plasmid purification": "General lab protocol",
    "Immunoprecipitation": "General lab protocol",
    "Immunofluorescence": "General lab protocol",
    "Live cell imaging": "General lab protocol",
    "Single-cell RNA-seq": "General lab protocol",
    "Chromatin immunoprecipitation (ChIP)": "General lab protocol",
    "Tissue staining": "General lab protocol",
    "Microscopy imaging": "General lab protocol",
    "Optogenetics": "General lab protocol",
    "Stereotaxic procedures": "Surgical procedure",
    "Yeast transformation": "General lab protocol",
    "NGS library prep": "General lab protocol",
    "Cell cycle assay": "General lab protocol",
    "Time-course experiment": "General lab protocol",
    "Biochemical assay": "General lab protocol",
    "Protein purification": "General lab protocol",
    "Enzymatic assay": "General lab protocol",
}

effective_type = alias_map.get(protocol_type, protocol_type)

# --- session persistence for instruction templates and full presets ---
if "saved_instructions" not in st.session_state:
    st.session_state.saved_instructions = {}
if "saved_full_presets" not in st.session_state:
    st.session_state.saved_full_presets = {}

# --- import / protocol acquisition UI ---
st.markdown("### 0. Import or Paste Protocol (no API required)")
st.caption(
    "Options: 1) Copy-paste protocol text directly from Benchling or any source. "
    "2) Export the protocol to PDF (e.g., print to PDF) and upload it here—LabMate will extract the text. "
    "3) Screenshot + OCR as fallback. You can edit the resulting protocol below."
)
import_cols = st.columns(2)

with import_cols[0]:
    st.subheader("Upload local protocol")
    st.caption("Supports .txt, .md, and .pdf. Extracted text will prefill the protocol area.")
    uploaded_file = st.file_uploader("Upload protocol file", type=["txt", "md", "pdf"])
    if uploaded_file:
        content_text = ""
        filename = uploaded_file.name.lower()
        try:
            if filename.endswith(".pdf"):
                reader = PdfReader(io.BytesIO(uploaded_file.read()))
                pages = []
                for page in reader.pages:
                    pages.append(page.extract_text() or "")
                content_text = "\n".join(pages)
            else:
                raw = uploaded_file.read()
                if isinstance(raw, bytes):
                    content_text = raw.decode("utf-8", errors="ignore")
                else:
                    content_text = str(raw)
            st.session_state.fetched_protocol = content_text
            st.success(f"Loaded {uploaded_file.name}; protocol prefilled below.")
        except Exception as e:
            st.error(f"Failed to parse file: {e}")

with import_cols[1]:
    st.subheader("Copy / Paste")
    st.caption("Manually paste protocol steps from Benchling or other sources into the box below.")

# --- instruction/template selection/loading ---
st.markdown("### 1. Instruction Template / Context")
instr_cols = st.columns([3, 2, 2])
with instr_cols[0]:
    saved_instr_choice = st.selectbox(
        "Load saved instruction only (template)",
        ["-- none --"] + list(st.session_state.saved_instructions.keys()),
    )
with instr_cols[1]:
    saved_preset_choice = st.selectbox(
        "Load saved full preset (type + instruction)",
        ["-- none --"] + list(st.session_state.saved_full_presets.keys()),
    )
with instr_cols[2]:
    if st.button("Reset to default for selected type"):
        st.session_state.current_prompt = default_prompts.get(effective_type, default_prompts["General lab protocol"])
        st.rerun()

# Determine base prompt safely
if saved_preset_choice != "-- none --" and saved_preset_choice in st.session_state.saved_full_presets:
    preset_obj = st.session_state.saved_full_presets[saved_preset_choice]
    base_prompt = preset_obj["prompt"]
    effective_type = preset_obj.get("type", effective_type)
elif saved_instr_choice != "-- none --" and saved_instr_choice in st.session_state.saved_instructions:
    base_prompt = st.session_state.saved_instructions[saved_instr_choice]
else:
    base_prompt = st.session_state.get(
        "current_prompt", default_prompts.get(effective_type, default_prompts["General lab protocol"])
    )

st.caption(
    "Edit the instruction below to tell LabMate how to interpret the protocol. "
    "You can emphasize safety, time savings, missing details, etc."
)
custom_prompt = st.text_area("Instruction template (editable)", base_prompt, height=300)

# Save instruction template only
with st.expander("Save current instruction as template"):
    instr_name = st.text_input("Template name", key="instr_name")
    if st.button("Save instruction template"):
        if not instr_name.strip():
            st.warning("Provide a name to save the template.")
        else:
            st.session_state.saved_instructions[instr_name.strip()] = custom_prompt
            st.session_state.current_prompt = custom_prompt
            st.success(f"Saved instruction template '{instr_name.strip()}'")
    if saved_instr_choice != "-- none --":
        if st.button(f"Delete instruction template '{saved_instr_choice}'"):
            st.session_state.saved_instructions.pop(saved_instr_choice, None)
            st.success(f"Deleted instruction template '{saved_instr_choice}'")
            st.rerun()

# Save full preset (type + instruction)
with st.expander("Save full preset (type + instruction)"):
    preset_name = st.text_input("Preset name", key="preset_name")
    if st.button("Save full preset"):
        if not preset_name.strip():
            st.warning("Provide a name for the preset.")
        else:
            st.session_state.saved_full_presets[preset_name.strip()] = {
                "type": protocol_type,
                "prompt": custom_prompt,
            }
            st.success(f"Saved full preset '{preset_name.strip()}'")
    if saved_preset_choice != "-- none --":
        if st.button(f"Delete full preset '{saved_preset_choice}'"):
            st.session_state.saved_full_presets.pop(saved_preset_choice, None)
            st.success(f"Deleted full preset '{saved_preset_choice}'")
            st.rerun()

st.markdown("---")

# --- protocol input ---
st.markdown("### 2. Protocol")
st.caption(
    "Paste or edit the raw protocol steps here. You can also import via upload above. "
    "Do not repeat instruction details; LabMate uses the template to interpret this."
)
initial_protocol_value = st.session_state.get("fetched_protocol", "")
protocol = st.text_area("Protocol text", value=initial_protocol_value, height=220)

# Clear protocol
if st.button("Clear protocol"):
    protocol = ""
    st.session_state.fetched_protocol = ""
    st.rerun()

# --- optimization logic ---
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
st.markdown("### 3. Run Optimization")
st.caption("Click Optimize to send the instruction + protocol to the model and get structured, actionable output.")

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
                st.markdown("### Results")
                st.markdown(output)
                st.download_button("Download Output", output, file_name="optimized_protocol.txt")
