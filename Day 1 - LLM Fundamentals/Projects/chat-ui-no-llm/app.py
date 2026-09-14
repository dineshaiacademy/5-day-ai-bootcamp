import streamlit as st


st.set_page_config(
    page_title="Prompt space",
    page_icon=":material/forum:",
    layout="centered",
)


def reset_chat():
    st.session_state.messages = []


if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("Prompt space", icon=":material/forum:")
    st.caption("A calm place to explore ideas with an AI interface.")
    st.button(
        "New conversation",
        icon=":material/add:",
        width="stretch",
        on_click=reset_chat,
    )
    st.space("medium")
    st.caption("About this demo")
    st.write("This interface is ready for an LLM connection. For now, it uses a local placeholder reply.")
    st.badge("Offline demo", icon=":material/wifi_off:", color="orange")

st.title("What would you like to explore?", text_alignment="center")
st.caption("A simple Streamlit chat interface for the 5-day AI bootcamp.", text_alignment="center")

if not st.session_state.messages:
    st.space("medium")
    st.subheader("Start with an idea", text_alignment="center")
    suggestion_columns = st.columns(3)
    suggestions = [
        ("Explain an idea", "Explain a complex idea in simple terms"),
        ("Draft something", "Help me draft a concise project brief"),
        ("Learn Streamlit", "Show me how a Streamlit app works"),
    ]
    for column, (label, prompt) in zip(suggestion_columns, suggestions):
        if column.button(label, width="stretch"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()

for message in st.session_state.messages:
    avatar = ":material/person:" if message["role"] == "user" else ":material/smart_toy:"
    with st.chat_message(message["role"], avatar=avatar):
        st.write(message["content"])

user_input = st.chat_input("Message Prompt space")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar=":material/person:"):
        st.write(user_input)

    reply = (
        "Thanks for sharing that. This demo is connected to the interface only, "
        "so its response is a placeholder. Add your model call here to make it smart."
    )
    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant", avatar=":material/smart_toy:"):
        st.write(reply)
