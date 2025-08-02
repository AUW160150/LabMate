import streamlit as st
st.write("Has key?", "OPENAI_API_KEY" in st.secrets)

import openai

st.set_page_config(page_title="LabMate", layout="wide")
st.title("🧪 LabMate: AI Copilot for Wet Lab Protocols")
st.write("Paste a protocol and get optimization suggestions (parallelization, missing steps, improved order).")

protocol = st.text_area("Paste your protocol here", height=300)

def detect_and_optimize(protocol_text):
    # Try GPT-4 first, fallback to 3.5
    prompt = f"""You are an expert wet lab assistant. Here's a protocol:

{protocol_text}

Tasks:
1. List any unclear or missing reagents/steps.
2. Suggest which steps can be parallelized or reordered to save time.
3. Provide an optimized step-by-step version with estimated time savings.
Format with headers: Issues, Suggestions, Optimized Protocol."""
    model_sequence = ["gpt-4", "gpt-4-0613", "gpt-3.5-turbo"]
    for model in model_sequence:
        try:
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return f"**Used model:** {model}\n\n" + resp["choices"][0]["message"]["content"]
        except Exception as e:
            # try next model
            last_err = e
    return f"All model calls failed. Last error: {last_err}\n\nFallback example:\n**Issues:** Incubation time overlaps.\n**Suggestions:** Parallelize reagent prep with spin steps.\n**Optimized Protocol:** 1. Prep reagents (5m); 2. Start lysis (10m) while setting up gel..."

if st.button("Optimize"):
    if not protocol.strip():
        st.warning("Paste a protocol first.")
    else:
        if "OPENAI_API_KEY" not in st.secrets:
            st.error("Missing OpenAI key in secrets. Add it in Streamlit app settings.")
        else:
            openai.api_key = st.secrets["OPENAI_API_KEY"]
            with st.spinner("Optimizing protocol..."):
                output = detect_and_optimize(protocol)
                st.markdown(output)
                st.download_button("Download Output", output, file_name="optimized_protocol.txt")
