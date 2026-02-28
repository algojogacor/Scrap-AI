from flask import Flask, request, jsonify
import g4f
import os
import logging
import sys

app = Flask(__name__)

# Redirect access log ke stdout biar Railway tidak salah baca sebagai error
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

PROVIDERS_TO_TRY = [
    (g4f.Provider.Liaobots,    "gpt-4o"),
    (g4f.Provider.Blackbox,    "blackbox"),
    (g4f.Provider.DeepInfra,   "meta-llama/Meta-Llama-3.1-70B-Instruct"),
    (g4f.Provider.Airforce,    "gpt-4o-mini"),
]

def build_messages(system, messages):
    """
    Inject persona sebagai pseudo-conversation di awal
    supaya provider yang tidak support system role tetap baca persona.
    """
    result = []

    if system:
        # Cara 1: system role (untuk provider yang support)
        result.append({"role": "system", "content": system})
        # Cara 2: inject ulang sebagai user+assistant exchange (fallback)
        result.append({
            "role": "user",
            "content": f"Untuk percakapan ini, kamu berperan sebagai karakter berikut dan WAJIB mengikuti semua instruksinya:\n\n{system}\n\nBalas 'oke siap' kalau kamu mengerti."
        })
        result.append({
            "role": "assistant",
            "content": "oke siap"
        })

    result.extend(messages)
    return result

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    system  = data.get('system', '')
    messages = data.get('messages', [])

    full_messages = build_messages(system, messages)

    last_error = None
    for provider, model in PROVIDERS_TO_TRY:
        try:
            response = g4f.ChatCompletion.create(
                model=model,
                messages=full_messages,
                provider=provider,
            )
            if response and len(str(response).strip()) > 1:
                print(f"✅ Provider berhasil: {provider.__name__}", flush=True)
                return jsonify({"reply": str(response), "model": model, "provider": provider.__name__})
        except Exception as e:
            last_error = str(e)
            print(f"⚠️  {provider.__name__} gagal: {e}", flush=True)
            continue

    return jsonify({"error": last_error or "semua provider gagal"}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
