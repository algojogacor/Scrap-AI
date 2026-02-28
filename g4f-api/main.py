from flask import Flask, request, jsonify
import g4f
import os
import logging
import sys

app = Flask(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# Urutan dari yang terbaik untuk Bahasa Indonesia
PROVIDERS_CONFIG = [
    # (provider_name, model) — DeepInfra paling bagus, support system prompt
    ("DeepInfra",      "meta-llama/Meta-Llama-3.1-70B-Instruct"),
    ("You",            g4f.models.default),
    ("TeachAnything",  g4f.models.default),
    ("PollinationsAI", "openai"),  # last resort, sering ngelantur
]

def get_providers():
    available = []
    for name, model in PROVIDERS_CONFIG:
        provider = getattr(g4f.Provider, name, None)
        if provider:
            available.append((provider, name, model))
    print(f"✅ Provider siap: {[n for _, n, _ in available]}", flush=True)
    return available

PROVIDERS = get_providers()

def build_messages(system, messages):
    result = []
    if system:
        # Dual inject — system role + conversation history
        result.append({"role": "system", "content": system})
        result.append({
            "role": "user",
            "content": f"Kamu berperan sebagai karakter ini dan WAJIB ikuti semua instruksinya:\n\n{system}\n\nBalas 'oke siap'."
        })
        result.append({"role": "assistant", "content": "oke siap"})
    result.extend(messages)
    return result

def is_valid_reply(text, system):
    if not text or len(text.strip()) < 2:
        return False
    # Pastikan tidak balas ulang instruksi sistem
    if text.strip().lower() in ["oke siap", "ok siap", "siap"]:
        return False
    # Deteksi gibberish Indo
    gibberish = ["lauk", "nampol", "nyamu", "tetap lauk"]
    if any(w in text.lower() for w in gibberish):
        return False
    return True

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    system   = data.get('system', '')
    messages = data.get('messages', [])
    full_messages = build_messages(system, messages)

    last_error = None
    for provider, name, model in PROVIDERS:
        try:
            response = g4f.ChatCompletion.create(
                model=model,
                messages=full_messages,
                provider=provider,
            )
            reply = str(response).strip()
            if is_valid_reply(reply, system):
                print(f"✅ {name} berhasil: {reply[:60]}...", flush=True)
                return jsonify({"reply": reply, "provider": name})
            print(f"⚠️  {name} tidak valid: '{reply[:40]}'", flush=True)
        except Exception as e:
            last_error = str(e)
            print(f"⚠️  {name} gagal: {e}", flush=True)
            continue

    return jsonify({"error": last_error or "semua provider gagal"}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "providers": [n for _, n, _ in PROVIDERS]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
