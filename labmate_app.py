import streamlit as st
st.write("Has key?", "OPENAI_API_KEY" in st.secrets)

import openai

st.set_page_config(page_title="LabMate", layout="wide")
st.title("🧪 LabMate: AI Copilot for Wet Lab Protocols")
st.write("Paste a protocol and get optimization suggestions (parallelization, missing steps, improved order).")

protocol = st.text_area("Paste your protocol here", height=300)

def detect_and_optimize(protocol_text):
    prompt = f"""
You are a practical wet lab assistant. Given the protocol below, do the following clearly and concisely:

1. **Issues / Ambiguities:** List any unclear steps, missing reagents, or potential errors.
2. **Parallelization Opportunities:** Identify which steps can run concurrently to save time.
3. **Reordered Optimized Protocol:** Provide a step-by-step version that reduces idle/wait time, with estimated time savings in parentheses.
4. **Checklist:** Summarize the final optimized protocol as a checklist.

Protocol:
{protocol_text}
"""
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
        "Fallback example:\n"
        "**Issues:** Incubation overlap.\n"
        "**Parallelization:** Start gel prep during incubation.\n"
        "**Optimized Protocol:** 1. Prepare reagents (5m); 2. Start lysis while preheating gel apparatus; ...\n"
        "**Checklist:** [ ] Reagents ready, [ ] Lysis started, [ ] Gel set up."
    )

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
