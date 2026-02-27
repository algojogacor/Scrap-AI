from flask import Flask, request, jsonify
from g4f.client import Client
import os

app = Flask(__name__)
client = Client()

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    system = data.get('system', '')
    messages = data.get('messages', [])

    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    try:
        # Coba GPT-4o dulu
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=full_messages,
        )
        return jsonify({"reply": response.choices[0].message.content, "model": "gpt-4o"})
    except Exception as e1:
        try:
            # Fallback ke GPT-4
            response = client.chat.completions.create(
                model="gpt-4",
                messages=full_messages,
            )
            return jsonify({"reply": response.choices[0].message.content, "model": "gpt-4"})
        except Exception as e2:
            return jsonify({"error": f"GPT-4o: {str(e1)} | GPT-4: {str(e2)}"}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)