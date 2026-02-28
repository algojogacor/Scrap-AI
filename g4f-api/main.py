from flask import Flask, request, jsonify
import g4f
import os
import logging
import sys

app = Flask(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# Cek provider yang tersedia di versi ini
def get_providers():
    provider_names = [
        "Blackbox", "DeepInfra", "Airforce", "PollinationsAI",
        "Free2GPT", "DDG", "You", "Pizzagpt", "ChatGptEs",
        "PerplexityLabs", "TeachAnything", "ReplicateHome",
    ]
    available = []
    for name in provider_names:
        provider = getattr(g4f.Provider, name, None)
        if provider:
            available.append((provider, name))
    print(f"✅ Provider tersedia: {[n for _, n in available]}", flush=True)
    return available

PROVIDERS = get_providers()

def build_messages(system, messages):
    result = []
    if system:
        result.append({"role": "system", "content": system})
        result.append({
            "role": "user",
            "content": f"Untuk percakapan ini kamu berperan sebagai karakter ini dan WAJIB ikuti semua instruksinya:\n\n{system}\n\nBalas 'oke siap' kalau mengerti."
        })
        result.append({"role": "assistant", "content": "oke siap"})
    result.extend(messages)
    return result

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    system   = data.get('system', '')
    messages = data.get('messages', [])
    full_messages = build_messages(system, messages)

    last_error = None
    for provider, name in PROVIDERS:
        try:
            response = g4f.ChatCompletion.create(
                model=g4f.models.default,
                messages=full_messages,
                provider=provider,
            )
            reply = str(response).strip()
            if reply and len(reply) > 2 and reply != "oke siap":
                print(f"✅ {name} berhasil", flush=True)
                return jsonify({"reply": reply, "provider": name})
            print(f"⚠️  {name} return kosong/pendek", flush=True)
        except Exception as e:
            last_error = str(e)
            print(f"⚠️  {name} gagal: {e}", flush=True)
            continue

    return jsonify({"error": last_error or "semua provider gagal"}), 500

@app.route('/health', methods=['GET'])
def health():
    providers = [n for _, n in PROVIDERS]
    return jsonify({"status": "ok", "providers": providers})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
