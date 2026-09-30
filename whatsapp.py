import streamlit as st
from twilio.rest import Client


def send_whatsapp_meal_summary(
    to_number,
    name,
    food,
    calories,
    protein,
    carbohydrates,
    fat,
    today_protein,
    protein_goal,
    tip
):

    account_sid = st.secrets["TWILIO_ACCOUNT_SID"]
    auth_token = st.secrets["TWILIO_AUTH_TOKEN"]

    from_number = "whatsapp:+17372508034"
    content_sid = "HXac51c61af94371da7904a767b414c2fc"
    to_number = "whatsapp:+916381088479"

    print("========== TWILIO DEBUG ==========")
    print("Account SID:", account_sid)
    print("From:", from_number)
    print("To:", to_number)
    print("Content SID:", content_sid)
    print("==================================")

    client = Client(
        account_sid,
        auth_token
    )

    message = client.messages.create(
        to=to_number,
        from_=from_number,
        content_sid=content_sid
    )

    return message.sid