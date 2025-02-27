import openai

# Ustawienie klucza API
client = openai.OpenAI(api_key="sk-svcacct-CEMIAp7F4yVsLM5rWt2dahRhykMsK01WHTIvZaeRASCOkUKpKVLI2zuASXUOgeNT3BlbkFJMctZoML9kuotw5mxoYmCk4XMCXXjwqEcvocjmBkHa3bSJSKewDHacv20BtKps9wA")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Jesteś ekspertem od analiz sportowych."},
        {"role": "user", "content": "Kto wygra mecz Real Madryt vs FC Barcelona?"}
    ]
)

print(response.choices[0].message.content)
