from flask import Flask, request, jsonify
import asyncio
import os
import logging
import sys

# Support nested event loops (Flask + asyncio)
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

app = Flask(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

CAI_TOKEN       = os.environ.get("CAI_TOKEN", "")
CAI_CHAR_ID     = os.environ.get("CAI_CHAR_ID", "")

# ── Cache client & chat_id supaya tidak buat session baru tiap request ──
_client   = None
_chat_id  = None

async def get_client():
    global _client
    if _client is None:
        from PyCharacterAI import get_client as cai_get_client
        _client = await cai_get_client(token=CAI_TOKEN)
        me = await _client.account.fetch_me()
        print(f"✅ C.AI login sebagai @{me.username}", flush=True)
    return _client

async def get_or_create_chat():
    global _chat_id
    client = await get_client()
    if _chat_id is None:
        chat, greeting = await client.chat.create_chat(CAI_CHAR_ID)
        _chat_id = chat.chat_id
        print(f"✅ Chat baru dibuat: {_chat_id}", flush=True)
        print(f"   Greeting: {greeting.get_primary_candidate().text[:60]}", flush=True)
    return _chat_id

async def send_message_async(user_message):
    client   = await get_client()
    chat_id  = await get_or_create_chat()
    answer   = await client.chat.send_message(CAI_CHAR_ID, chat_id, user_message)
    return answer.get_primary_candidate().text

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except Exception:
        return asyncio.run(coro)

def is_valid_reply(text):
    if not text or len(text.strip()) < 2:
        return False
    if text.strip().lower() in ["oke siap", "ok siap", "siap"]:
        return False
    return True

@app.route('/chat', methods=['POST'])
def chat():
    if not CAI_TOKEN or not CAI_CHAR_ID:
        return jsonify({"error": "CAI_TOKEN atau CAI_CHAR_ID belum diset"}), 500

    data     = request.json
    messages = data.get('messages', [])

    # Ambil pesan user terakhir saja — C.AI maintain history sendiri
    last_user_msg = ""
    for m in reversed(messages):
        if m.get('role') == 'user':
            last_user_msg = m.get('content', '')
            break

    if not last_user_msg:
        return jsonify({"error": "Tidak ada pesan user"}), 400

    try:
        reply = run_async(send_message_async(last_user_msg))
        if is_valid_reply(reply):
            print(f"✅ C.AI reply: {reply[:60]}", flush=True)
            return jsonify({"reply": reply, "provider": "CharacterAI"})
        return jsonify({"error": "Reply tidak valid"}), 500
    except Exception as e:
        print(f"❌ C.AI error: {e}", flush=True)
        # Reset chat kalau session expired
        global _client, _chat_id
        _client  = None
        _chat_id = None
        return jsonify({"error": str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset():
    global _client, _chat_id
    _client  = None
    _chat_id = None
    return jsonify({"status": "session reset"})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "mode": "CharacterAI",
        "char_id": CAI_CHAR_ID,
        "token_set": bool(CAI_TOKEN),
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
