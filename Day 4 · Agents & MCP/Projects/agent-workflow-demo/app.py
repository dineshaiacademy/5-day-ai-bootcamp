"""
Agents & Workflows — Live Demo (Dinesh AI Academy, Day 4)

What this app teaches — the same three-way distinction as the Day 4 notebook,
now interactive and side by side:

    Tool      A single capability (a Python function). It does nothing on its
              own until something decides to call it.
    Workflow  A FIXED sequence of tool calls the developer wrote in code. The
              same steps run, in the same order, every single time — the
              model never gets a say in *which* tools run or *when*.
    Agent     A LOOP where the model itself decides the next action — call a
              tool, or answer — based on the goal and everything that has
              happened so far. Your code just keeps the loop running until
              the model says it's done (or a safety cap is hit).

Three modes, switchable live in the sidebar, all sharing the same three tools
(calculate, get_current_time, get_weather) so the *only* thing that changes
between them is who is making the decisions:

    1. Plain Chat        — one request, no tools at all. The baseline.
    2. Fixed Workflow     — a hardcoded "trip briefing" pipeline: weather
                            lookup, then time lookup, then an LLM writes a
                            short briefing from both. Same 2 tools, same
                            order, for any city you pick.
    3. Autonomous Agent   — the real agent loop from the notebook: the model
                            decides which tool(s) to call, in what order, how
                            many steps it needs, and when to stop.

Provider is a second, independent choice: LM Studio (100% local, free) or
Gemini (cloud, free tier). Both speak the same OpenAI-compatible wire format,
so the same code drives either one — only base_url/api_key differ.
"""

import json
import operator
import os
from datetime import datetime
from zoneinfo import ZoneInfo

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
# demo. LM Studio ignores this field entirely, so it's safe to always send it.
GEMINI_REASONING_EFFORT = "low"

# Gemini's model list includes image/audio/video/etc. models that can't hold a
# text conversation — filtered out of the dropdown so students don't pick one by
# accident and get a confusing error.
GEMINI_EXCLUDE = (
    "image", "audio", "tts", "live", "transcribe", "computer-use", "robotics",
    "veo", "lyria", "aqa", "deep-research", "antigravity", "nano-banana",
)

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

DEFAULT_MAX_STEPS = 5  # matches the notebook's run_agent() default

SYSTEM_PROMPT_PLAIN = (
    "You are a helpful, concise assistant. Answer from your own knowledge only — "
    "you have no tools available right now. If you don't know something, say so "
    "instead of guessing."
)
SYSTEM_PROMPT_AGENT = (
    "You are a helpful assistant with access to a small set of tools (calculator, "
    "current time, weather). Call a tool whenever it would give a more accurate or "
    "current answer than your own knowledge. If a question needs the result of one "
    "tool as input to another (for example, converting a temperature you just "
    "looked up), call the tools one after another rather than guessing the second "
    "value. If no tool is needed, answer directly. Never claim to have looked "
    "something up if you didn't actually call a tool."
)
SYSTEM_PROMPT_WORKFLOW = (
    "You are a concise, friendly travel assistant. Write only what is asked for, "
    "nothing extra."
)

MODE_PLAIN = ":material/chat: Plain chat"
MODE_WORKFLOW = ":material/schema: Fixed workflow"
MODE_AGENT = ":material/smart_toy: Autonomous agent"

SUGGESTIONS_PLAIN = {
    ":material/lightbulb: Definition": "In one sentence, what is an AI agent?",
    ":material/compare_arrows: Compare": "What's the difference between a workflow and an agent?",
}
SUGGESTIONS_AGENT = {
    ":material/thermostat: Chained (order matters)": "What's the current temperature in Tokyo in Celsius, and what is that in Fahrenheit?",
    ":material/travel_explore: Independent tools": "What's the weather in Paris, and what time is it there right now?",
    ":material/compare_arrows: Comparison": "Is it warmer in Mumbai or Paris right now?",
    ":material/public: Trick question": "What is the capital of France?",
}

st.set_page_config(page_title="Agents & Workflows", page_icon=":material/smart_toy:", layout="wide")


# ── Tools (shared by Fixed Workflow and Autonomous Agent) ──────────────────
# Plain local Python functions — no network calls, no extra API keys. Same
# three tools the Day 4 notebook builds by hand, so this app picks up right
# where the notebook leaves off.

_SAFE_OPS = {
    "add": operator.add, "subtract": operator.sub,
    "multiply": operator.mul, "divide": operator.truediv,
}


def calculate(a: float, b: float, operation: str) -> dict:
    """Perform a basic arithmetic calculation: add, subtract, multiply, or divide."""
    func = _SAFE_OPS.get(operation)
    if func is None:
        return {"error": f"unsupported operation '{operation}' — use add, subtract, multiply, or divide"}
    if operation == "divide" and b == 0:
        return {"error": "cannot divide by zero"}
    return {"a": a, "b": b, "operation": operation, "result": func(a, b)}


def get_current_time(timezone: str) -> dict:
    """Get the current date and time for an IANA timezone, e.g. Asia/Tokyo."""
    try:
        now = datetime.now(ZoneInfo(timezone))
    except Exception:
        return {"timezone": timezone, "error": "unknown IANA timezone — try e.g. Asia/Tokyo, Europe/Paris, America/New_York"}
    return {
        "timezone": timezone,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "formatted": now.strftime("%A, %d %B %Y at %I:%M:%S %p"),
    }


WEATHER_DB = {  # simulated, fixed data — offline and reproducible for a classroom
    "tokyo": {"temp_c": 26, "condition": "sunny"},
    "paris": {"temp_c": 18, "condition": "cloudy"},
    "mumbai": {"temp_c": 31, "condition": "humid, partly cloudy"},
    "new york": {"temp_c": 21, "condition": "rainy"},
    "london": {"temp_c": 16, "condition": "overcast"},
}


def get_weather(city: str) -> dict:
    """Get the current simulated weather (temperature in Celsius, condition) for a city."""
    data = WEATHER_DB.get(city.strip().lower())
    if data is None:
        return {"city": city, "temp_c": 20, "condition": "unknown", "note": "city not in demo dataset"}
    return {"city": city, **data}


# Only used by Fixed Workflow, to turn the city picker into a timezone for
# get_current_time — Fixed Workflow always calls both tools, so it needs this
# mapping up front; the Agent instead asks Gemini/LM Studio for a timezone name.
CITY_TIMEZONE = {
    "tokyo": "Asia/Tokyo", "paris": "Europe/Paris", "mumbai": "Asia/Kolkata",
    "new york": "America/New_York", "london": "Europe/London",
}

TOOLBOX = {
    "calculate": calculate,
    "get_current_time": get_current_time,
    "get_weather": get_weather,
}

TOOL_ICONS = {
    "calculate": ":material/calculate:",
    "get_current_time": ":material/schedule:",
    "get_weather": ":material/partly_cloudy_day:",
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "calculate",
        "description": "Perform a basic arithmetic calculation.",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "The first number."},
                "b": {"type": "number", "description": "The second number."},
                "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
            },
            "required": ["a", "b", "operation"],
        },
    }},
    {"type": "function", "function": {
        "name": "get_current_time",
        "description": "Get the current date and time for an IANA timezone, e.g. Asia/Tokyo or Europe/Paris.",
        "parameters": {
            "type": "object",
            "properties": {"timezone": {"type": "string", "description": "IANA timezone name, e.g. Asia/Kolkata"}},
            "required": ["timezone"],
        },
    }},
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "Get the current simulated weather (temperature in Celsius, condition) for a city.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name, e.g. 'Tokyo'"}},
            "required": ["city"],
        },
    }},
]


# ── LLM client ───────────────────────────────────────────────────────────
# The `openai` SDK works with ANY server that speaks the OpenAI API shape, not
# just OpenAI's own cloud — that's the whole trick behind supporting two
# providers with almost no extra code. LM Studio and Gemini both implement that
# shape, so only base_url + api_key change between them.

@st.cache_resource
def get_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=base_url, api_key=api_key)


@st.cache_data(ttl=30)
def list_models(base_url: str, api_key: str) -> list[str]:
    client = get_client(base_url, api_key)
    return sorted(m.id.removeprefix("models/") for m in client.models.list().data)


def _plain(message) -> dict:
    """Turn an SDK message object (a Pydantic model) into a plain JSON-serializable dict, for the trace panel."""
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    return message


# ── Mode 1: Plain Chat ──────────────────────────────────────────────────
def run_plain(client, model, messages, temperature, max_tokens, extra_args):
    """One request, no `tools` argument at all — the model answers from what it already knows."""
    request = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, **extra_args}
    stream = client.chat.completions.create(
        model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, stream=True, **extra_args,
    )
    text = st.write_stream(chunk.choices[0].delta.content or "" for chunk in stream if chunk.choices)
    trace = [{"kind": "llm_call", "request": request, "response": {"role": "assistant", "content": text}}]
    return text, trace


# ── Mode 2: Fixed Workflow ──────────────────────────────────────────────
def run_fixed_workflow(client, model, city, temperature, max_tokens, extra_args):
    """
    A hardcoded pipeline: get_weather(city) -> get_current_time(timezone) ->
    one LLM call that turns both results into a short briefing. These three
    steps run in this exact order for EVERY city, no exceptions — the
    developer decided the plan in code, not the model. Compare to
    run_agent() below, where nothing about the plan is fixed in advance.
    """
    trace = []

    weather = get_weather(city)
    trace.append({"kind": "tool_call", "tool_name": "get_weather", "arguments": {"city": city}, "result": weather})

    timezone = CITY_TIMEZONE.get(city.strip().lower(), "UTC")
    time_info = get_current_time(timezone)
    trace.append({"kind": "tool_call", "tool_name": "get_current_time", "arguments": {"timezone": timezone}, "result": time_info})

    synthesis_prompt = (
        f"Write a short, friendly one-paragraph trip briefing (under 60 words) for someone "
        f"about to call or visit {city}. Current weather: {json.dumps(weather)}. Current local "
        f"time: {json.dumps(time_info)}. Mention the weather, one quick packing tip, and the local time."
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_WORKFLOW},
        {"role": "user", "content": synthesis_prompt},
    ]
    request = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, **extra_args}
    response = client.chat.completions.create(
        model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, **extra_args,
    )
    text = response.choices[0].message.content or ""
    trace.append({"kind": "llm_call", "request": request, "response": _plain(response.choices[0].message)})

    return weather, time_info, text, trace


# ── Mode 3: Autonomous Agent ─────────────────────────────────────────────
def run_agent(client, model, messages, temperature, max_tokens, extra_args, max_steps):
    """
    The agent loop. Each pass through the `for` loop:
      1. Send the conversation so far PLUS the tool menu (TOOL_SCHEMAS).
      2. The model replies with either plain text (done) or a `tool_calls`
         list — it is *asking* us to run one or more tools; it can never run
         them itself.
      3. For each requested tool call: look up the real Python function in
         TOOLBOX, run it with the model-supplied arguments, and append the
         JSON result back into the conversation as a `role: "tool"` message.
      4. Loop again — the model now sees the result and decides the next
         action, or stops.

    max_steps is a safety cap: a confused model could otherwise keep
    requesting tools forever, burning API quota with no final answer.
    """
    trace = []
    working = list(messages)  # local copy — grows with tool_calls/results as we go

    for _ in range(max_steps):
        request = {
            "model": model,
            "messages": [_plain(m) for m in working],
            "tools": [t["function"]["name"] for t in TOOL_SCHEMAS],  # names only, for a readable trace
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
            return message.content or "", trace

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}  # a weak model occasionally sends malformed JSON arguments
            func = TOOLBOX.get(name)
            result = func(**args) if func else {"error": f"unknown tool '{name}'"}
            trace.append({"kind": "tool_call", "tool_name": name, "arguments": args, "result": result})
            working.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})

    return f"Hit the {max_steps}-step safety cap for this demo — try rephrasing your question.", trace


# ── Pipeline diagrams (static legend above the interaction area) ────────
PIPELINE_PLAIN = [
    (":material/chat_bubble: Request", "Your message sent to the model"),
    (":material/psychology: Model", "Model answers from its own knowledge only"),
    (":material/auto_awesome: Response", "Streamed back to you"),
]
PIPELINE_WORKFLOW = [
    (":material/partly_cloudy_day: Step 1 · fixed", "Code calls get_weather(city) — always, no choice"),
    (":material/schedule: Step 2 · fixed", "Code calls get_current_time(timezone) — always, no choice"),
    (":material/auto_awesome: Step 3 · fixed", "One LLM call turns both results into a briefing"),
]
PIPELINE_AGENT = [
    (":material/flag: Goal", "Your message becomes the agent's goal"),
    (":material/psychology: Model decides", "Tool call, or final answer? The model chooses"),
    (":material/build: Tool (if requested)", "App runs the real function, feeds the result back"),
    (":material/all_inclusive: Repeat until done", f"Loop continues — up to N steps — until the model answers"),
]


def render_pipeline(stages):
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


# ── Trace renderer (the literal request/response JSON, per step) ────────
def render_trace(trace, mode_label):
    with st.expander(f":material/route: How this was generated  ·  {mode_label}"):
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
                st.markdown(f"**Step {i + 1} · {icon} Tool call: `{step['tool_name']}`**")
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
    st.caption("Day 4 · Agents & MCP — live demo")
    st.space("small")

    # ── Provider & model ─────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**:material/cloud: Provider & model**")

        provider_name = st.segmented_control(
            "Provider", list(PROVIDERS), default="LM Studio (local)", required=True, label_visibility="collapsed"
        )
        provider = PROVIDERS[provider_name]

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

        if provider_name.startswith("Gemini"):
            chat_models = sorted(m for m in all_models if "embed" not in m and not any(x in m for x in GEMINI_EXCLUDE))
        else:
            chat_models = [m for m in all_models if "embed" not in m.lower()] or all_models

        if not chat_models:
            st.error(f"{provider_name} has no usable chat models loaded/available.")
            st.stop()

        default_model = provider["default_model"]
        default_chat = default_model if default_model in chat_models else chat_models[0]
        model = st.selectbox(
            "Chat model", chat_models, index=chat_models.index(default_chat),
            help="Models available from the selected provider.",
        )

        with st.expander("Advanced", icon=":material/tune:"):
            temperature = st.slider("Temperature", 0.0, 1.5, 0.3, 0.1)
            max_tokens = st.slider("Max tokens", 50, 2000, 500, 50)

    extra_args = {"reasoning_effort": GEMINI_REASONING_EFFORT} if provider_name.startswith("Gemini") else {}

    # ── Mode ─────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**:material/route: Mode**")
        mode = st.segmented_control(
            "Mode", [MODE_PLAIN, MODE_WORKFLOW, MODE_AGENT], default=MODE_AGENT, label_visibility="collapsed", required=True,
        )
        if mode == MODE_PLAIN:
            st.caption("No tools — a direct request/response, the baseline to compare against.")
            max_steps = DEFAULT_MAX_STEPS
        elif mode == MODE_WORKFLOW:
            st.caption("Same 2 tools, same fixed order, every run — the plan is written in code.")
            max_steps = DEFAULT_MAX_STEPS
        else:
            st.caption("The model decides which tools to call, in what order, and when to stop.")
            max_steps = st.slider(
                "Max steps (safety cap)", 2, 8, DEFAULT_MAX_STEPS, 1,
                help="Stops the loop if the model keeps requesting tools without ever answering.",
            )

    # ── Tools reference ──────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**:material/build: Available tools**")
        st.caption("Local mock functions only — no internet access, no extra API keys.")
        tool_labels = {
            "get_weather": "Simulated weather lookup for 5 demo cities",
            "get_current_time": "Real current time for any IANA timezone",
            "calculate": "Real arithmetic (add / subtract / multiply / divide)",
        }
        for name, desc in tool_labels.items():
            row = st.container(horizontal=True)
            row.caption(f"{TOOL_ICONS[name]} `{name}`")
            row.caption(desc)

    st.space("small")
    clear_label = "Clear workflow runs" if mode == MODE_WORKFLOW else "Clear conversation"
    if st.button(clear_label, icon=":material/mop:", width="stretch"):
        st.session_state.messages = []
        st.session_state.workflow_runs = []
        st.rerun()


# ── Session state ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "workflow_runs" not in st.session_state:
    st.session_state.workflow_runs = []


# ── Header ───────────────────────────────────────────────────────────────
st.title(":material/smart_toy: Agents & Workflows — Live Demo")
st.caption(f"Watch who decides the next step — code, or the model. Provider: {provider_name} · `{model}`")

with st.expander(":material/menu_book: Tool vs. Workflow vs. Agent — what's the difference?"):
    st.markdown(
        "| | Who picks the next step? | Can it skip a step it doesn't need? | Predictability |\n"
        "|---|---|---|---|\n"
        "| **Tool** | — (it's just a function) | — | — |\n"
        "| **Workflow** | The developer, hardcoded in advance | No — the code always runs it | High |\n"
        "| **Agent** | The model, at runtime | Yes — it just won't call that tool | Lower — needs guardrails |\n\n"
        "**One sentence to remember:** *Tool = capability. Workflow = a script. "
        "Agent = a script that lets the model choose its own next line.*"
    )

render_pipeline({MODE_PLAIN: PIPELINE_PLAIN, MODE_WORKFLOW: PIPELINE_WORKFLOW, MODE_AGENT: PIPELINE_AGENT}[mode])
st.divider()


# ── Mode: Fixed Workflow (not a chat — one form, one deterministic pipeline) ─
if mode == MODE_WORKFLOW:
    st.markdown("**:material/travel_explore: Trip briefing workflow**")
    st.caption(
        "Pick any city — the SAME two tools run in the SAME order every time. "
        "Only the *arguments* change; the plan never does."
    )

    row = st.container(horizontal=True, vertical_alignment="bottom")
    city = row.selectbox("City", sorted(c.title() for c in WEATHER_DB), label_visibility="collapsed")
    run_clicked = row.button("Run workflow", icon=":material/play_arrow:", type="primary")

    if run_clicked:
        with st.status(f"Running the fixed workflow for {city}…", type="step") as status:
            weather, time_info, text, trace = run_fixed_workflow(
                client, model, city, temperature, max_tokens, extra_args
            )
            status.update(label="Workflow complete", state="complete")
        st.session_state.workflow_runs.append(
            {"city": city, "weather": weather, "time_info": time_info, "text": text, "trace": trace}
        )

    if not st.session_state.workflow_runs:
        st.info("No runs yet — pick a city above and click **Run workflow**.", icon=":material/info:")

    for run in reversed(st.session_state.workflow_runs):
        with st.container(border=True):
            st.markdown(f"**:material/location_on: {run['city']}**")
            cols = st.columns(2)
            with cols[0]:
                st.metric("Weather", f"{run['weather'].get('temp_c', '?')}°C")
                st.caption(run["weather"].get("condition", "unknown"))
            with cols[1]:
                st.metric("Local time", run["time_info"].get("time", "?"))
                st.caption(run["time_info"].get("date", ""))
            st.write(run["text"])
            render_trace(run["trace"], "Fixed Workflow")


# ── Mode: Plain Chat / Autonomous Agent (chat interface) ────────────────
else:
    mode_label = "Plain Chat" if mode == MODE_PLAIN else "Autonomous Agent"

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and message.get("mode_label"):
                st.caption(f":material/label: {message['mode_label']}")
            st.write(message["content"])
            if message.get("trace"):
                render_trace(message["trace"], message["mode_label"])

    prompt = None
    if not st.session_state.messages:
        suggestions = SUGGESTIONS_PLAIN if mode == MODE_PLAIN else SUGGESTIONS_AGENT
        selected = st.pills("Try asking:", list(suggestions.keys()), label_visibility="collapsed")
        if selected:
            prompt = suggestions[selected]

    prompt = st.chat_input("Type a message", submit_mode="disable") or prompt

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        system_prompt = SYSTEM_PROMPT_AGENT if mode == MODE_AGENT else SYSTEM_PROMPT_PLAIN
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
            if m["role"] in ("user", "assistant")
        ]
        request_messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": prompt}]

        with st.chat_message("assistant"):
            st.caption(f":material/label: {mode_label}")
            try:
                if mode == MODE_AGENT:
                    with st.status("Running the agent loop…", type="step") as status:
                        text, trace = run_agent(
                            client, model, request_messages, temperature, max_tokens, extra_args, max_steps
                        )
                        status.update(label="Agent finished", state="complete")
                    st.write(text)
                else:
                    text, trace = run_plain(client, model, request_messages, temperature, max_tokens, extra_args)
            except Exception as e:
                st.error(
                    f"Request failed: {e}\n\n"
                    + ("This model may not support function calling — try a Llama 3.1+/Qwen/Gemma "
                       "instruct model in LM Studio, or switch to Plain Chat mode." if mode == MODE_AGENT else
                       "Check that the selected provider is reachable (LM Studio running, or Gemini API key valid).")
                )
                st.stop()

            render_trace(trace, mode_label)

        st.session_state.messages.append(
            {"role": "assistant", "content": text, "trace": trace, "mode_label": mode_label}
        )
