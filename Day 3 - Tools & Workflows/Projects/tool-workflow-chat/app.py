"""
Tools & Workflows — Live Demo (Dinesh AI Academy, Day 3)

What this app teaches:
    Every "AI agent" or "tool calling" demo you'll ever see boils down to the same
    loop: send the model a JSON menu of functions it's allowed to ask for -> the
    model replies either with plain text OR "please call X with these arguments"
    -> your own code runs the real function -> you send the result back -> repeat
    until the model is happy with plain text.

    This app makes that loop visible. Every reply has a "How this reply was
    generated" panel showing the *exact* request/response JSON at each step, so
    students can see there's no magic — it's just an HTTP request/response loop.

Two independent choices, both togglable live in the sidebar:
    1. Provider  — LM Studio (100% local, free, no signup) or Gemini (cloud, free
       tier). Both speak the same OpenAI-compatible wire format, so the app code
       barely changes between them — only base_url/api_key differ.
    2. Mode      — "Tools + Workflow" (the loop above) vs "Plain Chat" (a single
       request, no tools at all) — so you can ask the *same* question both ways
       and compare.
"""

import ast
import json
import operator
import os
from datetime import datetime, timedelta, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# Reads a local .env file (if present) into environment variables — this is how
# GEMINI_API_KEY gets in without ever being typed into the app or committed to git.
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────

# Gemini's newer models "think" before answering. That hidden reasoning silently
# eats into max_tokens and can come back with an empty reply if you're not
# careful. reasoning_effort="low" keeps replies fast and predictable for a chat
# demo. LM Studio ignores this field entirely (it's a no-op there), so it's safe
# to always send it — we just only bother when the Gemini provider is active.
GEMINI_REASONING_EFFORT = "low"

# Gemini's model list includes image/audio/video/etc. models that can't hold a
# text conversation — filtered out of the dropdown so students don't pick one by
# accident and get a confusing error.
GEMINI_EXCLUDE = (
    "image", "audio", "tts", "live", "transcribe", "computer-use", "robotics",
    "veo", "lyria", "aqa", "deep-research", "antigravity", "nano-banana",
)

# Everything the app needs to know to talk to a provider lives here — base_url,
# how to authenticate, and which model to preselect. Adding a third provider
# later would mean adding one more entry to this dict, nothing else.
PROVIDERS = {
    "LM Studio (local)": {
        "base_url": os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1"),
        "api_key": "local",  # required by the SDK's constructor, ignored by LM Studio
        "needs_key": False,
        "default_model": "lfm2.5-350m",  # small + fast + reliably calls tools
    },
    "Gemini (Google AI)": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": os.getenv("GEMINI_API_KEY") or os.getenv("GAISTUDIO_API_KEY"),
        "needs_key": True,
        "default_model": "gemini-3.6-flash",
    },
}

MAX_TOOL_STEPS = 4  # safety cap on the tool-call loop, in case a model keeps requesting tools

SYSTEM_PROMPT_PLAIN = (
    "You are a helpful, concise assistant. Answer from your own knowledge only — "
    "you have no tools available right now. If you don't know something, say so "
    "instead of guessing."
)
SYSTEM_PROMPT_TOOLS = (
    "You are a helpful assistant with access to a small set of tools (weather, "
    "calculator, currency conversion, current time). Call a tool whenever it would "
    "give a more accurate or current answer than your own knowledge. Never claim to "
    "have looked something up if you didn't actually call a tool."
)

SUGGESTIONS = {
    ":material/partly_cloudy_day: Weather": "What's the weather like in Tokyo right now?",
    ":material/calculate: Math": "What is (348 * 12) minus 900, then add 15% to that?",
    ":material/currency_exchange: Currency": "Convert 250 USD to INR.",
    ":material/schedule: Time": "What time is it right now in Tokyo?",
}

st.set_page_config(page_title="Tools & Workflows", page_icon=":material/precision_manufacturing:", layout="wide")


# ── Simulated tools ──────────────────────────────────────────────────────
# These are plain local Python functions — no network calls, no API keys. They
# exist so students can see a real tool-calling request/response loop without
# needing a paid weather/FX API for a classroom demo. Each one returns a small
# dict, which later gets JSON-encoded and handed back to the model as the
# "result" of the tool it asked for.

WEATHER_DB = {
    "mumbai": {"temp_c": 31, "condition": "humid, partly cloudy"},
    "delhi": {"temp_c": 34, "condition": "sunny"},
    "bengaluru": {"temp_c": 24, "condition": "light rain"},
    "paris": {"temp_c": 18, "condition": "cloudy"},
    "tokyo": {"temp_c": 26, "condition": "sunny"},
    "new york": {"temp_c": 21, "condition": "rainy"},
    "london": {"temp_c": 16, "condition": "overcast"},
}


def get_weather(city: str) -> dict:
    """Look up fake weather for a city. Falls back to a placeholder if it's not in our tiny demo dataset."""
    data = WEATHER_DB.get(city.strip().lower())
    if data is None:
        return {"city": city, "temp_c": 20, "condition": "unknown", "note": "simulated fallback — city not in demo dataset"}
    return {"city": city, **data}


# calculate() uses this tiny ast-based evaluator instead of Python's eval(). eval()
# would happily run arbitrary code hidden inside a crafted expression — the model
# (or a malicious prompt) could pass something like "__import__('os').system(...)"
# as the "expression" argument. Walking the parsed AST and only allowing number
# literals + these six operators makes that impossible: anything else raises.
_SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


def calculate(expression: str) -> dict:
    """Evaluate basic arithmetic safely — real math, just no eval()."""
    try:
        result = _safe_eval(ast.parse(expression, mode="eval").body)
        return {"expression": expression, "result": result}
    except Exception:
        return {"expression": expression, "error": "could not evaluate — only numbers and + - * / % ** ( ) are supported"}


FX_RATES = {  # simulated, fixed rates — not live data
    ("USD", "EUR"): 0.92, ("EUR", "USD"): 1.09,
    ("USD", "INR"): 83.0, ("INR", "USD"): 0.012,
    ("USD", "GBP"): 0.79, ("GBP", "USD"): 1.27,
    ("EUR", "INR"): 90.2, ("INR", "EUR"): 0.011,
}


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert using a small fixed-rate table — good enough to demo the tool-call shape, not real FX."""
    f, t = from_currency.strip().upper(), to_currency.strip().upper()
    rate = 1.0 if f == t else FX_RATES.get((f, t))
    if rate is None:
        return {"error": f"no simulated rate for {f} -> {t}", "note": "demo dataset only covers USD/EUR/INR/GBP"}
    return {"amount": amount, "from": f, "to": t, "rate": rate, "converted": round(amount * rate, 2)}


CITY_UTC_OFFSET = {  # simulated fixed offsets (ignores DST) — for demo purposes only
    "mumbai": 5.5, "delhi": 5.5, "bengaluru": 5.5, "kolkata": 5.5,
    "london": 0, "paris": 1, "tokyo": 9, "new york": -5, "san francisco": -8, "utc": 0,
}


def get_current_time(city: str = "UTC") -> dict:
    """Real current time, just using a simulated fixed UTC offset instead of a real timezone database."""
    offset = CITY_UTC_OFFSET.get(city.strip().lower())
    if offset is None:
        return {"city": city, "error": "unknown city in demo dataset", "known_cities": sorted(CITY_UTC_OFFSET)}
    local = datetime.now(timezone.utc) + timedelta(hours=offset)
    return {"city": city, "utc_offset": offset, "local_time": local.strftime("%Y-%m-%d %H:%M")}


# TOOLBOX and TOOL_SCHEMAS describe the SAME four tools but serve two different
# audiences:
#   - TOOL_SCHEMAS is sent to the model — it's a JSON menu ("here's what you can
#     ask for and what arguments each one needs"). The model can only read this;
#     it never sees the Python source below.
#   - TOOLBOX stays entirely on our side — it's how *our own code* turns a tool
#     name the model asked for back into the real Python function to run.
TOOLBOX = {
    "get_weather": get_weather,
    "calculate": calculate,
    "convert_currency": convert_currency,
    "get_current_time": get_current_time,
}

TOOL_ICONS = {
    "get_weather": ":material/partly_cloudy_day:",
    "calculate": ":material/calculate:",
    "convert_currency": ":material/currency_exchange:",
    "get_current_time": ":material/schedule:",
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "Get the current simulated weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name, e.g. 'Tokyo'"}},
            "required": ["city"],
        },
    }},
    {"type": "function", "function": {
        "name": "calculate",
        "description": "Evaluate a basic arithmetic expression, e.g. '240 * 0.15'.",
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "e.g. '(23 + 4) * 2'"}},
            "required": ["expression"],
        },
    }},
    {"type": "function", "function": {
        "name": "convert_currency",
        "description": "Convert an amount from one currency to another (simulated fixed rates).",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "from_currency": {"type": "string", "description": "e.g. 'USD'"},
                "to_currency": {"type": "string", "description": "e.g. 'EUR'"},
            },
            "required": ["amount", "from_currency", "to_currency"],
        },
    }},
    {"type": "function", "function": {
        "name": "get_current_time",
        "description": "Get the current simulated local time for a city.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "e.g. 'Tokyo'"}},
            "required": ["city"],
        },
    }},
]


# ── LLM client ───────────────────────────────────────────────────────────
# The `openai` SDK works with ANY server that speaks the OpenAI API shape, not
# just OpenAI's own cloud — that's the whole trick behind supporting two
# providers with almost no extra code. LM Studio and Gemini both implement that
# shape, so only base_url + api_key change between them; every call below
# (models.list, chat.completions.create, streaming, tools) stays identical.

@st.cache_resource
def get_client(base_url: str, api_key: str) -> OpenAI:
    # Streamlit reruns this whole script on every click/keystroke. Without
    # caching we'd build a brand-new HTTP client on every rerun for no reason.
    # Caching is keyed on (base_url, api_key), so switching providers
    # automatically gets its own separate cached client.
    return OpenAI(base_url=base_url, api_key=api_key)


@st.cache_data(ttl=30)
def list_models(base_url: str, api_key: str) -> list[str]:
    # Ask the server what's actually available instead of hardcoding model
    # names — LM Studio's list depends on what you've downloaded, and Gemini
    # adds/removes models over time. Cached for 30s so switching sliders
    # doesn't re-hit the network on every rerun.
    client = get_client(base_url, api_key)
    return sorted(m.id.removeprefix("models/") for m in client.models.list().data)


def _plain(message) -> dict:
    """Turn an SDK message object (a Pydantic model) into a plain JSON-serializable dict, for the trace panel."""
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    return message


# ── The two request modes ───────────────────────────────────────────────

def run_plain(client, model, messages, temperature, max_tokens, extra_args):
    """
    Plain Chat: ONE request, no `tools` argument at all.
    The model has never heard of get_weather/calculate/etc. — it can only
    answer from whatever it already knows internally. This is the baseline
    students compare "Tools + Workflow" mode against.
    """
    request = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, **extra_args}
    stream = client.chat.completions.create(
        model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, stream=True, **extra_args,
    )
    # st.write_stream renders each token as it arrives AND returns the full
    # concatenated text once the stream ends — that's what we store as the reply.
    text = st.write_stream(chunk.choices[0].delta.content or "" for chunk in stream if chunk.choices)
    trace = [{"kind": "llm_call", "request": request, "response": {"role": "assistant", "content": text}}]
    return text, trace


def run_with_tools(client, model, messages, temperature, max_tokens, extra_args):
    """
    Tools + Workflow: the actual agentic loop.

    Step by step, each pass through the `for` loop below:
      1. Send the conversation so far PLUS the tool menu (TOOL_SCHEMAS).
      2. The model replies with either:
           a) plain text            -> we're done, return it.
           b) a `tool_calls` list   -> the model is *asking* us to run one or
              more tools. It cannot run them itself — it only ever produces
              text describing what it wants called and with what arguments.
      3. For each requested tool call: look up the real Python function in
         TOOLBOX, call it with the model-supplied arguments, and append the
         JSON result back into the conversation as a `role: "tool"` message.
      4. Loop again — now the model can see the tool's result in its context
         and either answer using it, or ask for another tool.

    MAX_TOOL_STEPS exists purely as a safety net: a weak model can get stuck
    calling the same tool repeatedly instead of answering. Every iteration
    (both the model call and each tool execution) is recorded into `trace`
    so the UI can show exactly what was sent and received at each step.
    """
    trace = []
    working = list(messages)  # local copy — we grow this with tool_calls/results as we go

    for _ in range(MAX_TOOL_STEPS):
        request = {
            "model": model,
            "messages": [_plain(m) for m in working],
            # Logged as just names (not the full JSON schema) to keep the trace
            # readable — the full schema is shown once, in the sidebar, instead.
            "tools": [t["function"]["name"] for t in TOOL_SCHEMAS],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **extra_args,
        }
        response = client.chat.completions.create(
            model=model, messages=working, tools=TOOL_SCHEMAS,
            temperature=temperature, max_tokens=max_tokens, **extra_args,
        )
        message = response.choices[0].message
        trace.append({"kind": "llm_call", "request": request, "response": _plain(message)})
        working.append(message)  # keep the model's own turn in context for the next loop

        if not message.tool_calls:
            # No tool requested — the model considers itself done.
            return message.content or "", trace

        # The model can request multiple tool calls in one turn; handle each.
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}  # a weak model occasionally sends malformed JSON arguments
            func = TOOLBOX.get(name)
            result = func(**args) if func else {"error": f"unknown tool '{name}'"}
            trace.append({"kind": "tool_call", "tool_name": name, "arguments": args, "result": result})
            # `role: "tool"` + the matching tool_call_id is how the API knows
            # which request this result answers, especially when several tool
            # calls happened in the same turn.
            working.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})

    return "I hit the tool-call step limit for this demo — try rephrasing your question.", trace


# ── Workflow pipeline diagram ───────────────────────────────────────────
# Purely a static legend shown above the chat — it doesn't track live progress,
# it just previews what's about to happen for the currently selected mode.

PIPELINE_TOOLS = [
    (":material/chat_bubble: Request", "Your message + tool menu sent to the model"),
    (":material/psychology: Decide", "Model decides: answer directly, or call a tool?"),
    (":material/build: Tool (simulated)", "App runs a local mock function, returns the result"),
    (":material/auto_awesome: Final response", "Model uses the result to answer you"),
]
PIPELINE_PLAIN = [
    (":material/chat_bubble: Request", "Your message sent to the model"),
    (":material/psychology: Model", "Model answers from its own knowledge only"),
    (":material/auto_awesome: Response", "Streamed back to you"),
]


def render_pipeline(stages):
    # Lay out N boxes with a thin "→" column between each pair — done with
    # plain st.columns/st.container so it stays a native, theme-aware widget
    # instead of a custom HTML diagram that could break across themes.
    widths = []
    for i in range(len(stages)):
        widths.append(4)
        if i < len(stages) - 1:
            widths.append(1)
    cols = st.columns(widths)
    ci = 0
    for i, (label, desc) in enumerate(stages):
        with cols[ci]:
            with st.container(border=True):
                st.markdown(f"**{label}**")
                st.caption(desc)
        ci += 1
        if i < len(stages) - 1:
            with cols[ci]:
                st.markdown(
                    "<div style='text-align:center;font-size:1.4rem;padding-top:26px;opacity:0.45'>&rarr;</div>",
                    unsafe_allow_html=True,
                )
            ci += 1


# ── Workflow trace renderer (shown per assistant reply) ─────────────────

def render_trace(trace, mode_label):
    """
    Renders the `trace` list built by run_plain()/run_with_tools() as a
    step-by-step, expandable log — the literal request dict sent to
    chat.completions.create() and the literal response/tool-result that came
    back, as JSON. This IS the request/response the API actually exchanged,
    not a simplified paraphrase of it.
    """
    with st.expander(f":material/route: How this reply was generated  ·  {mode_label}"):
        for i, step in enumerate(trace):
            if step["kind"] == "llm_call":
                tool_calls = (step["response"] or {}).get("tool_calls")
                if tool_calls:
                    names = ", ".join(tc["function"]["name"] for tc in tool_calls)
                    st.markdown(f"**Step {i + 1} · :material/psychology: Model call** — requested tool(s): `{names}`")
                else:
                    st.markdown(f"**Step {i + 1} · :material/psychology: Model call** — answered directly, no tool needed")
                tab_req, tab_res = st.tabs(["Request", "Response"])
                with tab_req:
                    st.code(json.dumps(step["request"], indent=2, default=str, ensure_ascii=False), language="json")
                with tab_res:
                    st.code(json.dumps(step["response"], indent=2, default=str, ensure_ascii=False), language="json")
            else:  # kind == "tool_call"
                icon = TOOL_ICONS.get(step["tool_name"], ":material/build:")
                st.markdown(f"**Step {i + 1} · {icon} Simulated tool call: `{step['tool_name']}`**")
                tab_args, tab_res = st.tabs(["Arguments", "Result"])
                with tab_args:
                    st.code(json.dumps(step["arguments"], indent=2, ensure_ascii=False), language="json")
                with tab_res:
                    st.code(json.dumps(step["result"], indent=2, ensure_ascii=False), language="json")
            if i < len(trace) - 1:
                st.divider()


# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### :material/auto_awesome: Dinesh AI Academy")
    st.caption("Day 3 · Tools & Workflows — live demo")
    st.space("small")

    # ── Provider & model ─────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**:material/cloud: Provider & model**")

        provider_name = st.segmented_control(
            "Provider", list(PROVIDERS), default="LM Studio (local)", required=True, label_visibility="collapsed"
        )
        provider = PROVIDERS[provider_name]

        # Gemini needs an API key from .env; LM Studio never does (it's local).
        # Each provider fails independently — picking the other one still works
        # even if this one's key/server isn't set up yet.
        if provider["needs_key"] and not provider["api_key"]:
            st.error(
                f"No API key found for {provider_name}. Add `GEMINI_API_KEY=...` to your "
                "`.env` file (get a free key at aistudio.google.com/apikey), then reload."
            )
            st.stop()

        client = get_client(provider["base_url"], provider["api_key"])

        try:
            all_models = list_models(provider["base_url"], provider["api_key"])
        except Exception:
            all_models = []

        if not all_models:
            if provider_name.startswith("LM Studio"):
                st.error(
                    f"Can't reach a local LLM server at `{provider['base_url']}`.\n\n"
                    "Start LM Studio, load a **tool-calling capable** chat model "
                    "(Llama 3.1+, Qwen, or Gemma 3/4 instruct family) in the "
                    "**Developer** tab, click **Start Server**, then reload this page."
                )
            else:
                st.error("Couldn't list Gemini models. Check that your API key is valid, then reload.")
            st.stop()

        st.badge(f"Connected · {len(all_models)} model(s)", icon=":material/check_circle:", color="green")

        # Filter down to text chat models only — hide embedding models (both
        # providers can serve them) and Gemini's non-text model variants.
        if provider_name.startswith("Gemini"):
            chat_models = sorted(m for m in all_models if "embed" not in m and not any(x in m for x in GEMINI_EXCLUDE))
        else:
            chat_models = [m for m in all_models if "embed" not in m.lower()] or all_models

        if not chat_models:
            st.error(f"{provider_name} has no usable chat models loaded/available.")
            st.stop()

        # Prefer each provider's configured default (see PROVIDERS above) if
        # it's actually available right now; otherwise just fall back to
        # whatever's first, so this never crashes if a model gets renamed.
        default_model = provider["default_model"]
        default_chat = default_model if default_model in chat_models else chat_models[0]
        model = st.selectbox(
            "Chat model", chat_models, index=chat_models.index(default_chat),
            help="Models available from the selected provider.",
        )

        with st.expander("Advanced", icon=":material/tune:"):
            temperature = st.slider("Temperature", 0.0, 1.5, 0.3, 0.1)
            max_tokens = st.slider("Max tokens", 50, 2000, 500, 50)

    # Extra keyword args merged into every chat.completions.create() call.
    # Only Gemini needs this (see GEMINI_REASONING_EFFORT above); LM Studio
    # gets an empty dict, i.e. no behavior change.
    extra_args = {"reasoning_effort": GEMINI_REASONING_EFFORT} if provider_name.startswith("Gemini") else {}

    # ── Mode: with tools, or without ────────────────────────────────────
    with st.container(border=True):
        st.markdown("**:material/route: Mode**")
        mode_choice = st.segmented_control(
            "Mode",
            [":material/build: Tools + Workflow", ":material/chat: Plain Chat"],
            default=":material/build: Tools + Workflow",
            label_visibility="collapsed",
        )
        use_tools = mode_choice is not None and "Tools" in mode_choice
        if use_tools:
            st.caption("The model can call the simulated tools below and you'll see every step.")
        else:
            st.caption("No tools available — a direct request/response, for comparison.")

    # ── Simulated tools reference ───────────────────────────────────────
    with st.container(border=True):
        st.markdown("**:material/build: Simulated tools**")
        st.caption("Local mock functions only — no internet access, no API keys.")
        tool_labels = {
            "get_weather": "Fake weather lookup for a handful of cities",
            "calculate": "Real arithmetic, evaluated locally and safely",
            "convert_currency": "Currency conversion using fixed demo rates",
            "get_current_time": "Local time using fixed simulated UTC offsets",
        }
        for name, desc in tool_labels.items():
            row = st.container(horizontal=True)
            row.caption(f"{TOOL_ICONS[name]} `{name}`")
            row.caption(desc)

    st.space("small")
    if st.button("Clear conversation", icon=":material/mop:", width="stretch"):
        st.session_state.messages = []
        st.rerun()


# ── Session state ────────────────────────────────────────────────────────
# st.session_state persists across reruns (Streamlit reruns the whole script
# top-to-bottom on every interaction). Each stored message also carries which
# mode/provider produced it and its own trace, so switching modes mid-chat
# doesn't lose the history of how earlier replies were generated.
if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Header ───────────────────────────────────────────────────────────────
st.title(":material/precision_manufacturing: Tools & Workflows — Live Demo")
st.caption(
    f"Watch a request travel from your message to the model's response, with or without tools. "
    f"Provider: {provider_name} · `{model}`"
)
render_pipeline(PIPELINE_TOOLS if use_tools else PIPELINE_PLAIN)
st.divider()


# ── Chat history ─────────────────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and message.get("mode_label"):
            st.caption(f":material/label: {message['mode_label']}")
        st.write(message["content"])
        if message.get("trace"):
            render_trace(message["trace"], message["mode_label"])


# ── Suggestion chips (only before the first message) ────────────────────
prompt = None
if not st.session_state.messages:
    selected = st.pills("Try asking:", list(SUGGESTIONS.keys()), label_visibility="collapsed")
    if selected:
        prompt = SUGGESTIONS[selected]

prompt = st.chat_input("Type a message", submit_mode="disable") or prompt


# ── Handle a new turn ─────────────────────────────────────────────────────
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Build the message list the API expects: system prompt (which differs by
    # mode, so the model knows whether it even has tools) + prior turns + the
    # new question.
    system_prompt = SYSTEM_PROMPT_TOOLS if use_tools else SYSTEM_PROMPT_PLAIN
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
        if m["role"] in ("user", "assistant")
    ]
    request_messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": prompt}]
    mode_label = "Tools + Workflow" if use_tools else "Plain Chat"

    with st.chat_message("assistant"):
        st.caption(f":material/label: {mode_label}")
        try:
            if use_tools:
                with st.status("Running the tool-augmented workflow…", type="step") as status:
                    text, trace = run_with_tools(client, model, request_messages, temperature, max_tokens, extra_args)
                    status.update(label="Workflow complete", state="complete")
                st.write(text)
            else:
                text, trace = run_plain(client, model, request_messages, temperature, max_tokens, extra_args)
        except Exception as e:
            st.error(
                f"Request failed: {e}\n\n"
                + ("This model may not support function calling — try a Llama 3.1+/Qwen/Gemma "
                   "instruct model in LM Studio, or switch to Plain Chat mode." if use_tools else
                   "Check that the selected provider is reachable (LM Studio running, or Gemini API key valid).")
            )
            st.stop()

        render_trace(trace, mode_label)

    # Save the reply (with its trace + which mode/provider made it) so chat
    # history survives the next rerun and the trace stays inspectable.
    st.session_state.messages.append(
        {"role": "assistant", "content": text, "trace": trace, "mode_label": mode_label}
    )
