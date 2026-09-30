import json
import re

import streamlit as st
from google import genai
from google.genai import types

from prompts import SYSTEM_PROMPT

from database import (
    create_database,
    get_today_protein,
    add_protein,
    get_protein_goal
)

from whatsapp import send_whatsapp_meal_summary


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="MacroSnap",
    page_icon="🥗",
    layout="centered"
)


# =========================================================
# GEMINI CLIENT
# =========================================================

client = genai.Client(
    api_key=st.secrets["GEMINI_API_KEY"]
)


# =========================================================
# CREATE DATABASE
# =========================================================

create_database()


# =========================================================
# NUTRITION RESPONSE SCHEMA
# =========================================================

nutrition_schema = {
    "type": "OBJECT",
    "properties": {

        "food_items": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            }
        },

        "calories": {
            "type": "NUMBER"
        },

        "protein": {
            "type": "NUMBER"
        },

        "carbohydrates": {
            "type": "NUMBER"
        },

        "fat": {
            "type": "NUMBER"
        },

        "notes": {
            "type": "STRING"
        },

        "tip": {
            "type": "STRING"
        }
    },

    "required": [
        "food_items",
        "calories",
        "protein",
        "carbohydrates",
        "fat",
        "notes",
        "tip"
    ]
}


# =========================================================
# SESSION STATE
# =========================================================

if "onboarding_complete" not in st.session_state:
    st.session_state.onboarding_complete = False

if "messages" not in st.session_state:
    st.session_state.messages = []

if "protein_goal" not in st.session_state:
    st.session_state.protein_goal = get_protein_goal()

if "today_protein" not in st.session_state:
    st.session_state.today_protein = get_today_protein()

if "latest_nutrition" not in st.session_state:
    st.session_state.latest_nutrition = None


# =========================================================
# TITLE
# =========================================================

st.title("🥗 MacroSnap")

st.caption(
    "Your AI nutrition buddy — analyze meals and track protein."
)


# =========================================================
# ONBOARDING
# =========================================================

if not st.session_state.onboarding_complete:

    st.subheader("👋 Welcome to MacroSnap")

    name = st.text_input(
        "What's your name?"
    )

    whatsapp_number = st.text_input(
        "WhatsApp number",
        placeholder="+919876543210"
    )

    if st.button("Continue"):

        if not name.strip():

            st.warning(
                "Please enter your name."
            )

        elif not whatsapp_number.strip():

            st.warning(
                "Please enter your WhatsApp number."
            )

        else:

            st.session_state.name = name.strip()

            st.session_state.whatsapp_number = (
                whatsapp_number.strip()
            )

            st.session_state.onboarding_complete = True

            st.rerun()

    st.stop()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header("📊 Daily Protein")

    protein_goal = st.number_input(
        "Protein goal (g)",
        min_value=1.0,
        value=float(
            st.session_state.protein_goal
        ),
        step=1.0
    )

    if protein_goal != st.session_state.protein_goal:

        st.session_state.protein_goal = protein_goal

        # Save to database
        from database import save_protein_goal

        save_protein_goal(
            protein_goal
        )

    st.session_state.today_protein = (
        get_today_protein()
    )

    today_protein = (
        st.session_state.today_protein
    )

    st.metric(
        "Today's Protein",
        f"{today_protein:.1f} g"
    )

    progress = (
        today_protein / protein_goal
        if protein_goal > 0
        else 0
    )

    progress = min(
        progress,
        1.0
    )

    st.progress(progress)

    st.caption(
        f"{today_protein:.1f} / "
        f"{protein_goal:.1f} g"
    )

    st.divider()

    st.write(
        f"👤 **{st.session_state.name}**"
    )

    st.write(
        f"📱 {st.session_state.whatsapp_number}"
    )


# =========================================================
# DISPLAY CHAT HISTORY
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# =========================================================
# CHAT INPUT
# =========================================================

prompt = st.chat_input(
    "Tell me what you ate...",
    accept_file=True,
    file_type=[
        "jpg",
        "jpeg",
        "png"
    ]
)


# =========================================================
# PROCESS USER MESSAGE
# =========================================================

if prompt:

    user_text = prompt.text

    uploaded_file = None

    if prompt.files:

        uploaded_file = prompt.files[0]


    # -----------------------------------------------------
    # SHOW USER MESSAGE
    # -----------------------------------------------------

    with st.chat_message("user"):

        if user_text:

            st.markdown(
                user_text
            )

        if uploaded_file:

            st.image(
                uploaded_file,
                caption="Uploaded meal"
            )


    # -----------------------------------------------------
    # SAVE USER MESSAGE
    # -----------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_text
        }
    )


    # -----------------------------------------------------
    # BUILD GEMINI CONTENT
    # -----------------------------------------------------

    contents = []


    # Add previous conversation
    for message in st.session_state.messages:

        if message["role"] == "user":

            contents.append(
                message["content"]
            )

        elif message["role"] == "assistant":

            contents.append(
                message["content"]
            )


    # Add current image if available
    if uploaded_file:

        image_bytes = uploaded_file.getvalue()

        contents.append(
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=uploaded_file.type
            )
        )


    # -----------------------------------------------------
    # GEMINI RESPONSE
    # -----------------------------------------------------

    with st.chat_message("assistant"):

        with st.spinner(
            "🔍 Analyzing your meal..."
        ):

            try:

                response = client.models.generate_content(

                    model="gemini-3.5-flash-lite",

                    contents=contents,

                    config=types.GenerateContentConfig(

                        system_instruction=SYSTEM_PROMPT,

                        response_mime_type="application/json",

                        response_schema=nutrition_schema
                    )
                )


                # -------------------------------------------------
                # PARSE GEMINI RESPONSE
                # -------------------------------------------------

                nutrition_data = json.loads(
                    response.text
                )


                # Save latest nutrition result
                # so we can use it for WhatsApp
                st.session_state.latest_nutrition = (
                    nutrition_data
                )


                # -------------------------------------------------
                # EXTRACT VALUES
                # -------------------------------------------------

                food_items = nutrition_data.get(
                    "food_items",
                    []
                )

                calories = nutrition_data.get(
                    "calories",
                    0
                )

                protein = nutrition_data.get(
                    "protein",
                    0
                )

                carbohydrates = nutrition_data.get(
                    "carbohydrates",
                    0
                )

                fat = nutrition_data.get(
                    "fat",
                    0
                )

                notes = nutrition_data.get(
                    "notes",
                    ""
                )

                tip = nutrition_data.get(
                    "tip",
                    ""
                )


                # -------------------------------------------------
                # PROTEIN CLEANING
                # -------------------------------------------------

                protein_text = str(
                    protein
                )

                protein_text = re.sub(
                    r"[^0-9.]",
                    "",
                    protein_text
                )

                if protein_text:

                    protein_value = float(
                        protein_text
                    )

                else:

                    protein_value = 0.0


                # -------------------------------------------------
                # ADD PROTEIN TO DATABASE
                # -------------------------------------------------

                add_protein(
                    protein_value
                )


                # Refresh today's protein
                st.session_state.today_protein = (
                    get_today_protein()
                )


                # -------------------------------------------------
                # DISPLAY RESULT
                # -------------------------------------------------

                st.markdown(
                    "### 🍽️ Meal Analysis"
                )

                st.write(
                    "**Food:** "
                    + ", ".join(food_items)
                )

                st.write(
                    f"🔥 **Calories:** "
                    f"{calories} kcal"
                )

                st.write(
                    f"💪 **Protein:** "
                    f"{protein_value} g"
                )

                st.write(
                    f"🍞 **Carbohydrates:** "
                    f"{carbohydrates} g"
                )

                st.write(
                    f"🥑 **Fat:** "
                    f"{fat} g"
                )

                st.write(
                    f"📝 **Notes:** "
                    f"{notes}"
                )

                st.write(
                    f"💡 **Tip:** "
                    f"{tip}"
                )


                # -------------------------------------------------
                # PROTEIN PROGRESS
                # -------------------------------------------------

                st.divider()

                st.write(
                    "📊 **Today's Protein Progress**"
                )

                st.write(
                    f"{st.session_state.today_protein:.1f} "
                    f"/ "
                    f"{st.session_state.protein_goal:.1f} g"
                )


                # -------------------------------------------------
                # SAVE ASSISTANT MESSAGE
                # -------------------------------------------------

                assistant_message = (
                    f"🍽️ Food: "
                    f"{', '.join(food_items)}\n\n"
                    f"🔥 Calories: "
                    f"{calories} kcal\n\n"
                    f"💪 Protein: "
                    f"{protein_value} g\n\n"
                    f"🍞 Carbohydrates: "
                    f"{carbohydrates} g\n\n"
                    f"🥑 Fat: "
                    f"{fat} g\n\n"
                    f"📝 Notes: "
                    f"{notes}\n\n"
                    f"💡 Tip: "
                    f"{tip}"
                )


                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_message
                    }
                )


            except Exception as error:

                st.error(
                    "❌ Something went wrong."
                )

                st.exception(
                    error
                )


# =========================================================
# WHATSAPP BUTTON
# =========================================================

if st.session_state.latest_nutrition:

    st.divider()

    st.subheader(
        "📱 WhatsApp Meal Summary"
    )

    st.caption(
        "Send your latest meal analysis to your WhatsApp."
    )


    if st.button(
        "📱 Send Meal Summary to WhatsApp"
    ):

        # IMPORTANT TEST
        st.write(
            "BUTTON CLICKED"
        )

        try:

            nutrition = (
                st.session_state.latest_nutrition
            )


            food_items = nutrition.get(
                "food_items",
                []
            )

            calories = nutrition.get(
                "calories",
                0
            )

            protein = nutrition.get(
                "protein",
                0
            )

            carbohydrates = nutrition.get(
                "carbohydrates",
                0
            )

            fat = nutrition.get(
                "fat",
                0
            )

            tip = nutrition.get(
                "tip",
                ""
            )


            # Clean protein
            protein_text = str(
                protein
            )

            protein_text = re.sub(
                r"[^0-9.]",
                "",
                protein_text
            )

            if protein_text:

                protein_value = float(
                    protein_text
                )

            else:

                protein_value = 0.0


            # Refresh today's protein
            st.session_state.today_protein = (
                get_today_protein()
            )


            # -------------------------------------------------
            # SEND TO TWILIO
            # -------------------------------------------------

            whatsapp_sid = (
                send_whatsapp_meal_summary(

                    to_number=(
                        st.session_state.whatsapp_number
                    ),

                    name=(
                        st.session_state.name
                    ),

                    food=", ".join(
                        food_items
                    ),

                    calories=calories,

                    protein=protein_value,

                    carbohydrates=carbohydrates,

                    fat=fat,

                    today_protein=(
                        st.session_state.today_protein
                    ),

                    protein_goal=(
                        st.session_state.protein_goal
                    ),

                    tip=tip
                )
            )


            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            st.success(
                "✅ WhatsApp message sent!"
            )

            st.write(
                f"Message SID: {whatsapp_sid}"
            )


        except Exception as error:

            st.error(
                "❌ WhatsApp sending failed."
            )

            st.exception(
                error
            )