from addgene_fetcher import fetch_plasmid_info
import streamlit as st
import openai

# --- page setup ---
st.set_page_config(page_title="LabMate", layout="wide")
st.title("🧪 LabMate: AI Copilot for Wet Lab Protocols")
st.write("1. Pick or customize the instruction/template. 2. Paste your protocol. 3. Click Optimize. You can save reusable instruction templates or full presets (type + instruction).")

# --- base prompt presets ---
protocol_type = st.selectbox("Protocol type (preset)", ["General wet lab", "PCR", "Rodent brain surgery","RNA extraction","Cell transfection", "Histology","Flow Cytometry", "Synthetic biology assay",
"Organoid culture","DNA extraction","cDNA synthesis","Western blot","ELISA","qPCR","CRISPR genome editing","Gel electrophoresis","Bacterial transformation","Plasmid purification","Immunoprecipitation",
"Immunofluorescence","Live cell imaging","Single-cell RNA-seq","Chromatin immunoprecipitation (ChIP)","Tissue staining","In vivo imaging","Optogenetics","Stereotaxic injection",
"Yeast transformation","NGS library prep","Cell cycle assay","Time-course experiment setup"
])

st.caption("Pick the context that best matches your protocol; this seeds a starting instruction. You can edit it below.")

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

# --- session persistence for instructions and full presets ---
if "saved_instructions" not in st.session_state:
    st.session_state.saved_instructions = {}  # name -> prompt string
if "saved_full_presets" not in st.session_state:
    st.session_state.saved_full_presets = {}  # name -> {type, prompt}

# --- instruction/template selection/loading ---
st.markdown("### 1. Instruction Template / Context")
instr_cols = st.columns([3, 2, 2])
with instr_cols[0]:
    saved_instr_choice = st.selectbox("Load saved instruction only (template)", ["-- none --"] + list(st.session_state.saved_instructions.keys()))
with instr_cols[1]:
    saved_preset_choice = st.selectbox("Load saved full preset (type + instruction)", ["-- none --"] + list(st.session_state.saved_full_presets.keys()))
with instr_cols[2]:
    if st.button("Reset to default for selected type"):
        st.session_state.current_prompt = default_prompts[protocol_type]
        # safe rerun so UI refreshes with the reset template
        st.experimental_rerun()

# Determine base prompt safely
if saved_preset_choice != "-- none --" and saved_preset_choice in st.session_state.saved_full_presets:
    preset_obj = st.session_state.saved_full_presets[saved_preset_choice]
    base_prompt = preset_obj["prompt"]
    protocol_type = preset_obj["type"]  # reflect loaded preset's type
elif saved_instr_choice != "-- none --" and saved_instr_choice in st.session_state.saved_instructions:
    base_prompt = st.session_state.saved_instructions[saved_instr_choice]
else:
    base_prompt = st.session_state.get("current_prompt", default_prompts[protocol_type])

st.caption("Edit the instruction below to tell LabMate how to interpret the protocol. You can emphasize safety, time savings, missing details, etc.")
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
            st.experimental_rerun()

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
            st.experimental_rerun()

st.markdown("---")

# --- protocol input ---
st.markdown("### 2. Protocol")
st.caption("Paste the raw protocol steps here. Don't duplicate instructions; the assistant will apply the instruction/template to this protocol.")
protocol = st.text_area("Protocol text", height=220)

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
# --- protocol input ---
st.markdown("### 2. Protocol")
st.caption("Paste the raw protocol steps here...")
protocol = st.text_area("Protocol text", height=220)

# --- plasmid input & enrichment ---
plasmid_id = st.text_input("Enter Addgene Plasmid ID")
if plasmid_id:
    data = fetch_plasmid_info(plasmid_id)
    st.write(f"**Name**: {data['name']}")
    st.write(f"**Features**: {', '.join(data['features'])}")
    st.write(f"[View on Addgene]({data['url']})")

    protocol += f"\n\n[Plasmid Context] {data['name']} with features: {', '.join(data['features'])}"
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
