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

1. **Issues / Ambiguities:** Bullet any missing parameters (volumes, concentrations, equipment), unclear sequencing, or potential errors.
2. **Parallelization Opportunities:** Exactly state which steps can overlap and why (e.g., “While incubation runs, prep next reagents”).
3. **Reordered Optimized Protocol:** Provide a step-by-step version that minimizes idle time, annotate each with estimated duration and call out saved time compared to naive ordering.
4. **Checklist:** Condensed actionable checklist with checkboxes.

Example (format to mimic):
Issues / Ambiguities:
- Missing volume for master mix components.
- Template DNA concentration unspecified.

Parallelization Opportunities:
- Master mix prep and tube aliquoting can happen in parallel if two people.
- Workspace cleanup can occur during PCR cycling.

Optimized Protocol:
1. Prepare reagents and preheat machine in parallel (5m prep + 2m heat) [saves 2m].
2. Aliquot and add template DNA (5m).
3. Run PCR cycles (90m).
4. Cleanup during PCR (non-blocking).
5. Final extension (5m).

Checklist:
- [ ] Reagents prepared
- [ ] Machine preheated
- [ ] Tubes aliquoted
- [ ] PCR started
- [ ] Cleanup done

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
