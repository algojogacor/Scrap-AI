from flask import Flask, request, jsonify
import g4f
import os

app = Flask(__name__)

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
        # Coba GPT-4o dulu, fallback ke Gemini
        response = g4f.ChatCompletion.create(
            model=g4f.models.gpt_4o,
            messages=full_messages,
            provider=g4f.Provider.PollinationsAI,
        )
        return jsonify({"reply": response, "model": "gpt-4o"})
    except Exception as e1:
        try:
            response = g4f.ChatCompletion.create(
                model="gemini-1.5-pro",
                messages=full_messages,
                provider=g4f.Provider.Gemini,
            )
            return jsonify({"reply": response, "model": "gemini-pro"})
        except Exception as e2:
            return jsonify({"error": str(e2)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)