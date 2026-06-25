import datetime
import json
from pathlib import Path
from openai import OpenAI
import streamlit as st
import uuid

st.set_page_config(
    page_title="HackGPT",
    page_icon="🤖",
    layout="wide",
)

client = OpenAI(
    api_key=st.secrets["CLOD_API_KEY"],
    base_url="https://api.clod.io/v1",
)

CLOD_BASE_URL = "https://api.clod.io/v1"

def clear_chat_history():
    st.session_state["chat_messages"] = []

available_gpt_models = {
    "Trinity Mini": "Modèle léger et rapide",
    "Gemma 4 31B IT": "Modèle Google performant",
    "Llama 3.1 8B": "Modèle Meta optimisé",
    "GPT OSS 120B": "Modèle open source puissant",
    "Qwen 3.5 9B": "Modèle Alibaba",
}

# Ensure a default model is selected (first available) before the selectbox renders.
if "openai_model" not in st.session_state and available_gpt_models:
  st.session_state["openai_model"] = next(iter(available_gpt_models.keys()))

st.session_state["date"] = datetime.date.today().strftime("%B %d, %Y")

package_data = {
   "version": "1.0.0-alpha.1",
   "release_date": datetime.date(2023, 7, 8),
}

hackgpt_footer = f"""
HackGPT {package_data['version']}, released on {package_data['release_date'].strftime('%B %d, %Y')}. Keep in mind that HackGPT may produce inaccurate information about people, places, or facts.
"""

st.session_state["use_cutoff_date"] = False

def get_cutoff_string():
  if "date_cutoff" not in st.session_state:
    st.session_state["date_cutoff"] = datetime.date(2021, 9, 1)
  if "date_cutoff_today" not in st.session_state:
    st.session_state["date_cutoff_today"] = datetime.date.today()

  if st.session_state["use_cutoff_date"]:
    date_cutoff_fmt = st.session_state["date_cutoff"].strftime("%B %d, %Y")
    date_cutoff_today_fmt = st.session_state["date_cutoff_today"].strftime("%B %d, %Y")
    return f"Your knowledge cutoff date is based on your latest update which occurred on {date_cutoff_fmt}, so you have limited knowledge of events that occurred after that date. Today's date is {date_cutoff_today_fmt}."

  return ""

with st.sidebar:
    st.title("Preferences")

    with st.expander("Model"):
      st.session_state["openai_model"] = st.selectbox(
          "Select a model",
          available_gpt_models.keys(),
      )

      st.write(available_gpt_models[st.session_state["openai_model"]])
      st.write(f"Modèle utilisé : {st.session_state['openai_model']}")

      # Read the JSON file
      try:
          data_file = Path(__file__).parent / "data" / "setup_prompts.json"
          with open(data_file, "r", encoding="utf-8") as file:
              setup_prompts = json.load(file)
      except FileNotFoundError:
          setup_prompts = []
          st.warning("Fichier setup_prompts.json introuvable, utilisation des valeurs par défaut")

          # add option for Custom prompt
          setup_prompts["custom"] = {
              "label": "Custom",
              "options": {
                  "custom": {
                      "label": "Custom",
                      "value": "You are an AI assistant helping a user with a task. Your tone of voice is friendly and helpful."
                  }
              }
          }

      # First selectbox for choosing the category
      category = st.selectbox("Select a setup prompt category",
                              list(setup_prompts.keys()),
                              format_func=lambda x: setup_prompts[x]["label"])

      # Get the options dictionary for the selected category
      options = setup_prompts[category]["options"]

      # Second selectbox for choosing the specific choice within the category
      choice = st.selectbox("Select a setup prompt", list(options.keys()), format_func=lambda x: options[x]["label"])

      # if the category is custom, add a text input for the custom prompt
      if category == "custom":
          custom_prompt = st.text_input("Custom setup prompt", value=setup_prompts["custom"]["options"]["custom"]["value"])
          if custom_prompt:
              options = {
                  "custom": {
                      "label": "Custom",
                      "value": custom_prompt
                  }
              }

      # Get the label and value for the selected choice
      label = options[choice]["label"]
      value = options[choice]["value"]

      # Store the selected choice in a dictionary
      selected_setup_prompt = {
          "label": label,
          "value": value
      }

      st.session_state["setup_prompt"] = selected_setup_prompt["value"]

      st.write('Tip: You can change the setup prompt on the fly for generating more creative responses.')

      st.session_state["use_cutoff_date"] = st.checkbox("Include knowlegde cutoff", value=False, help="Include the cutoff date in the setup prompt. This is useful for limiting the AI's knowledge to a certain date.")
      if st.session_state["use_cutoff_date"]:
        max_cutoff_date = datetime.date(2021, 9, 1)
        st.session_state["date_cutoff"] = st.date_input("Cutoff date", value=max_cutoff_date, help="This is the date of the knowledge cutoff. The AI will not be able to provide detailed information about events that happened after this date.", max_value=max_cutoff_date)
        st.session_state["date_cutoff_today"]  = st.date_input("Today's date", value=datetime.date.today(), help="The date of today.", max_value=datetime.date.today())
        
        st.session_state["setup_prompt"] += f" {get_cutoff_string()}"

    with st.expander("Chat options"):
      st.session_state["streaming_output"] = st.checkbox("Streaming output", value=True,  help="Show the output as if the AI is typing it out, instead of all at once.")
      clear_chat = st.button("Clear chat", help="Clear the chat history", use_container_width=True, on_click=clear_chat_history)

    with st.expander("Fine-tuning"):
      st.session_state["max_tokens"] = st.slider(
                                        "Max tokens",
                                        min_value=512,
                                        max_value=8192,
                                        value=2048,
                                        step=16,
                                        help="The maximum number of [tokens](https://platform.openai.com/tokenizer) to generate in the chat completion."
                                      )
      
      st.session_state["temperature"] = st.slider(
                                          "Temperature",
                                          min_value=0.0,
                                          max_value=2.0,
                                          value=1.0,
                                          step=0.01,
                                          help="What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic."
                                        )
      
      st.session_state["top_p"] = st.slider(
                                    "Top P",
                                    min_value=0.0,
                                    max_value=1.0,
                                    value=1.0,
                                    step=0.01,
                                    help="An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass. So 0.1 means only the tokens comprising the top 10% probability mass are considered. It is recommend altering this or temperature, but not both."
                                  )
      
      st.session_state["presence_penalty"] = st.slider(
                                                "Presence penalty", 
                                                min_value=-2.0,
                                                max_value=2.0,
                                                value=0.0,
                                                step=0.01,
                                                help="Number between -2.0 and 2.0. Positive values penalize new tokens based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics."
                                              )
      
      st.session_state["frequency_penalty"] = st.slider(
                                                "Frequency penalty",
                                                min_value=-2.0,
                                                max_value=2.0,
                                                value=0.0,
                                                step=0.01,
                                                help="Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in the text so far, decreasing the model's likelihood to repeat the same line verbatim."
                                              )
      

    with st.expander("API Configuration"):
      st.text_input("API token", value=st.secrets["CLOD_API_KEY"], type="password", help="You can find your API token [here](https://beta.openai.com/account/api-keys).", disabled=True)
      st.session_state["session_identifier"] = st.text_input(
                                        "Session identifier",
                                        value=str(uuid.uuid4()),
                                        type="password",
                                        disabled=True,
                                        help="A unique identifier representing the end-user, which can help OpenAI to monitor and detect abuse. You can find more information about the session identifier [here](https://beta.openai.com/docs/developer-apis/requests)."
                                      )

      button_generate_new_session_identifier = st.button("Generate new session identifier")
      if button_generate_new_session_identifier:
        st.session_state["session_identifier"] = str(uuid.uuid4())


with st.container():
  st.header(selected_setup_prompt["label"])
  st.write(hackgpt_footer)
  
  def messages():
     if 'chat_messages' not in st.session_state:
        st.session_state['chat_messages'] = []
     return [
      { "role": "system", "content": st.session_state["setup_prompt"] }
        ] + [
      {"role": message["role"], "content": message["content"]}
        for message in st.session_state["chat_messages"]
      ] # contains both the system message and the chat messages

  for message in messages():
      with st.chat_message(message["role"]):
          st.markdown(message["content"])

  if prompt := st.chat_input("What is up?"):
      st.session_state.chat_messages.append({ "role": "user", "content": prompt })
      with st.chat_message("user"):
          st.markdown(prompt)

      # Build messages once per user prompt
      _messages = [
        {"role": m["role"], "content": m["content"]}
        for m in messages()
      ]

      if st.session_state.streaming_output:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            try:
              for chunk in client.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=_messages,
                max_tokens=st.session_state["max_tokens"],
                temperature=st.session_state["temperature"],
                top_p=st.session_state["top_p"],
                presence_penalty=st.session_state["presence_penalty"],
                frequency_penalty=st.session_state["frequency_penalty"],
                user=st.session_state["session_identifier"],
                stream=True,
                stream_options={"include_usage": True},
                extra_body={},
              ):
                if getattr(chunk, "choices", None):
                  delta = chunk.choices[0].delta.content
                  if delta is not None:
                    full_response += delta
                    message_placeholder.markdown(full_response + "▌")
              message_placeholder.markdown(full_response)
            except Exception as e:
              st.error(
                f"CLōD API error (streaming). "
                f"base_url={CLOD_BASE_URL}, model={st.session_state['openai_model']}. "
                f"Last error: {type(e).__name__}: {e}"
              )

        if full_response != "":
          st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
      else:
        with st.chat_message("assistant"):
          message_placeholder = st.markdown("Thinking...")

          try:
            completion = client.chat.completions.create(
              model=st.session_state["openai_model"],
              messages=_messages,
              max_tokens=st.session_state["max_tokens"],
              temperature=st.session_state["temperature"],
              top_p=st.session_state["top_p"],
              presence_penalty=st.session_state["presence_penalty"],
              frequency_penalty=st.session_state["frequency_penalty"],
              user=st.session_state["session_identifier"],
              stream=False,
            )
            response_text = completion.choices[0].message.content
          except Exception as e:
            st.error(
              f"CLōD API error. "
              f"base_url={CLOD_BASE_URL}, model={st.session_state['openai_model']}. "
              f"Last error: {type(e).__name__}: {e}"
            )
            response_text = ""

          message_placeholder.markdown(response_text)
        st.session_state.chat_messages.append({"role": "assistant", "content": response_text})
