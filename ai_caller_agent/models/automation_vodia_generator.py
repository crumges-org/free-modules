from odoo import models, fields, api

class automationCampaign(models.Model):
    _inherit = "automation.campaign"

    # ---------------------------------------------------
    # VODIA SCRIPT GENERATOR FIELDS
    # ---------------------------------------------------
    vodia_openai_api_key = fields.Char(string="OpenAI API Key")
    
    vodia_model = fields.Selection(
        [("gpt-realtime", "gpt-realtime")],
        string="Model",
        default="gpt-realtime",
        required=True
    )
    
    # Codec is removed from UI, hardcoded in script
    
    vodia_webhook_url = fields.Char(string="Webhook URL")
    vodia_webhook_secret = fields.Char(string="Webhook Secret")
    vodia_webhook_url_endcall = fields.Char(string="Webhook URL EndCall")
    vodia_instructions = fields.Text(string="Instructions")
    
    vodia_generated_script = fields.Text(string="Generated Script", readonly=True)

    def action_clear_vodia_script(self):
        """Clear the generated script."""
        self.ensure_one()
        self.vodia_generated_script = ""

    def action_generate_vodia_script(self):
        """
        Generate the Vodia JS script based on the fields provided.
        """
        self.ensure_one()
        
        # Helper to safely get string values
        api_key = self.vodia_openai_api_key or ""
        model = self.vodia_model or "gpt-realtime"
        codec = "g711_ulaw"  # Hardcoded as requested
        webhook_url = self.vodia_webhook_url or ""
        webhook_secret = self.vodia_webhook_secret or ""
        webhook_end = self.vodia_webhook_url_endcall or ""
        
        # Format instructions: Use raw input as JS array content (user provides quotes/commas)
        raw_instr = self.vodia_instructions or ""
        lines = raw_instr.split('\n')
        
        # Just indent the lines, don't escape or quote them
        js_lines = []
        for line in lines:
            # We still strip whitespace to avoid double indentation if user pasted with indent
            # But we trust the user's content (comments, quotes, commas)
            js_lines.append(f'    {line}')
        
        # Join with newline (commas are expected to be in the input lines)
        instructions_js_body = "\n".join(js_lines)
        
        # Construct the full JS variable declaration
        instructions_block = f"var instructions = [\n{instructions_js_body}\n].join(' ');"

        script_template = f"""'use strict';

/* =======================
   CONFIG
   ======================= */
var OPENAI_API_KEY = "{api_key}";
var MODEL = "{model}";
var CODEC = "{codec}";

var WEBHOOK_URL = "{webhook_url}";
var WEBHOOK_SECRET = "{webhook_secret}";

var WEBHOOK_URL_ENDCALL = "{webhook_end}";

/* =======================
   HELPERS
   ======================= */
function now() {{ return new Date().toISOString(); }}
function rand(n) {{ return Math.random().toString(36).slice(2, 2 + n); }}
function fallbackId() {{ return now() + "-" + rand(6); }}
function getHeader(n) {{ try {{ return call.getHeader(n) || call.getHeader(String(n).toLowerCase()) || ""; }} catch (_) {{ return ""; }} }}
function onlyDigits(s) {{ return (s || "").replace(/[^\\d]/g, ""); }}
function stripPlus1(num) {{ num = onlyDigits(num); return (num.length === 11 && num[0] === '1') ? num.slice(1) : num; }}

/* Track ID — keep v10 behavior */
var TRACK_ID = fallbackId();

/* =======================
   ANI (x-ani)
   ======================= */
function detectANI() {{
    // 0) X-ANI header if upstream injected it
    var xani = getHeader("X-ANI") || getHeader("x-ani");
    if (xani) return stripPlus1(xani);

    // 1) Vodia tables: cobjs.from
    try {{
        if (typeof tables !== "undefined" && tables['cobjs']) {{
            var fromRaw = tables['cobjs'].get(call.callid, 'from') || "";
            var mFrom = String(fromRaw).match(/sip:(\\+?\\d+)[@;>]/i);
            if (mFrom && mFrom[1]) return stripPlus1(mFrom[1]);
        }}
    }} catch (_) {{ }}

    // 2) SIP headers: P-Asserted-Identity, From
    var pai = getHeader("P-Asserted-Identity");
    var frm = getHeader("From") || getHeader("f");
    var hdr = pai || frm || "";
    var mHdr = String(hdr).match(/(\\+?\\d{{7,}})/);
    if (mHdr) return stripPlus1(mHdr[1]);

    // 3) Call object (may be empty at start for /dial/)
    if (call && call.caller) return stripPlus1(call.caller);

    return "";
}}

/* =======================
   WEBHOOKS (only start + end)
   ======================= */
function webhook(event, extra) {{
    // **Use fresh ANI at send time**
    var aniNow = detectANI();

    var body = Object.assign({{
        event: event,
        trackid: TRACK_ID,
        token: TRACK_ID,
        ts: now(),
        call_id: (call && call.id) || "",
        caller: (call && call.caller) || "",
        callee: (call && call.called) || "",
        ani: aniNow || ""
    }}, extra || {{}});

    try {{
        system.http({{
            url: WEBHOOK_URL,
            method: "POST",
            verify: true,
            header: [
                {{ name: "Content-Type", value: "application/json" }},
                {{ name: "X-Secret", value: WEBHOOK_SECRET, secret: true }},
                {{ name: "X-TrackID", value: TRACK_ID }},
                {{ name: "X-Token", value: TRACK_ID }},
                {{ name: "X-ANI", value: aniNow || "" }}
            ],
            body: JSON.stringify(body),
            callback: function (c) {{ try {{ call.log("WEBHOOK " + event + " => " + c + " ani=" + (aniNow || "")); }} catch (_) {{ }} }}
        }});
    }} catch (e) {{ try {{ call.log("webhook error " + e); }} catch (_) {{ }} }}
}}

/* =======================
   TRANSCRIPT (compact)
   ======================= */
var sentEnd = false;
var userTurns = [];   // {{ ts, text }}
var agentTurns = [];   // {{ ts, text }}
var agentBuf = "";   // accumulates assistant transcript between .delta and .done
var goodbyeSent = false;

function pushAgentIfAny() {{
    var t = agentBuf.trim();
    if (t) agentTurns.push({{ ts: now(), text: t }});
    agentBuf = "";
}}

function finalizeAndSend(reason) {{
    if (sentEnd) return;
    sentEnd = true;

    // Flush any pending assistant buffer
    pushAgentIfAny();

    webhook("call_end", {{
        reason: reason || "unknown",
        transcript: {{ user: userTurns, agent: agentTurns }}
    }});
}}

function safeHang(reason) {{
    // send end first so you always get it
    finalizeAndSend(reason || "hangup");

    // stop any streaming/playback and hang up
    try {{ call.stream(); }} catch (_) {{ }}
    try {{ call.hangup(); }} catch (_) {{ }}

    // watchdog in case PBX refuses immediately
    try {{
        setTimeout(function () {{
            try {{ call.stream(); }} catch (_) {{ }}
            try {{ call.hangup(); }} catch (_) {{ }}
        }}, 1200);
    }} catch (_) {{ }}
}}

/* =======================
   START CALL
   ======================= */
try {{ if (!call.answered) call.answer(); }} catch (_) {{ }}
try {{ call.unmute(); }} catch (_) {{ }}
// Ensure start payload also carries the freshest ANI
webhook("call_start", {{ ani: detectANI() }});

/* Also emit end if remote hangs up */
try {{
    if (typeof call.on === 'function') {{
        call.on('hangup', function () {{ safeHang("remote_hangup"); }});
    }}
}} catch (_) {{ }}

/* =======================
   PROMPT
   ======================= */
{instructions_block}


/* =======================
   REALTIME WS
   ======================= */
var ws = new Websocket("wss://api.openai.com/v1/realtime?model=" + MODEL);
ws.header([
    {{ name: "Authorization", value: "Bearer " + OPENAI_API_KEY, secret: true }},
    {{ name: "OpenAI-Beta", value: "realtime=v1" }},
    {{ name: "Sec-WebSocket-Protocol", value: "realtime" }}
]);

ws.on('open', function () {{ /* keep noise low */ }});

ws.on('close', function () {{
    // Ensure end gets sent even if nothing else fired
    safeHang("socket_closed");
    try {{ call.stream(); }} catch (_) {{ }}
}});

ws.on('error', function (e) {{
    try {{ call.log("WS error: " + e); }} catch (_) {{ }}
    // end will be sent by on('close') or PBX hangup
}});

ws.on('message', function (m) {{
    var msg = {{}}; try {{ msg = JSON.parse(m); }} catch (_) {{ return; }}

    if (msg.type === "session.created") {{
        ws.send(JSON.stringify({{
            type: "session.update", session: {{
                instructions: instructions,
                voice: "coral",
                turn_detection: {{ type: "server_vad", threshold: 0.5, prefix_padding_ms: 300, silence_duration_ms: 500 }},
                input_audio_format: CODEC,
                output_audio_format: CODEC,
                input_audio_transcription: {{ model: "whisper-1" }}
            }}
        }}));
    }}
    else if (msg.type === "session.updated") {{
        try {{ call.stream({{ codec: CODEC, interval: 0.5, callback: stream }}); }}
        catch (e) {{ try {{ call.log("stream error: " + e); }} catch (_) {{ }} }}
    }}
    else if (msg.type === "response.audio.delta" && msg.delta) {{
        try {{
            var audio = fromBase64String(msg.delta);
            call.play({{ direction: "out", codec: CODEC, audio: audio }});
        }} catch (_) {{ }}
    }}

    /* --------- CAPTURE ASSISTANT TRANSCRIPT RELIABLY --------- */
    else if (msg.type === "response.audio_transcript.delta" && msg.delta) {{
        agentBuf += String(msg.delta);
    }}
    else if (msg.type === "response.audio_transcript.done") {{
        // assistant turn done
        pushAgentIfAny();

        // If assistant just said goodbye, hang up
        // (check last turn text)
        var last = agentTurns.length ? agentTurns[agentTurns.length - 1].text : "";
        if (!goodbyeSent && /\\b(bye|goodbye|take care|talk to you later|have a good (day|one))\\b/i.test(last)) {{
            goodbyeSent = true;
            // small delay to let last audio finish at callee
            setTimeout(function () {{ safeHang("agent_goodbye"); }}, 600);
        }}
    }}

    /* --------- CAPTURE USER TRANSCRIPT --------- */
    else if ((msg.type === "conversation.item.input_audio_transcription.delta" && msg.delta)
        || (msg.type === "input_audio_transcription.delta" && msg.delta)) {{
        // we only save on completed to avoid fragments
    }}
    else if ((msg.type === "conversation.item.input_audio_transcription.completed" && msg.transcript)
        || (msg.type === "input_audio_transcription.completed" && (msg.text || msg.transcript))) {{
        var userText = String(msg.transcript || msg.text || "").trim();
        if (userText) {{
            userTurns.push({{ ts: now(), text: userText }});

            // User ends → hang up quickly
            if (/\\b(no|not interested|stop|bye|goodbye|hang up|do not call)\\b/i.test(userText)) {{
                setTimeout(function () {{ safeHang("user_ended"); }}, 300);
            }}
        }}
    }}
}});

/* stream mic → OpenAI */
function stream(a) {{
    try {{
        ws.send(JSON.stringify({{ type: "input_audio_buffer.append", audio: toBase64String(a) }}));
    }} catch (_) {{ }}
}}

try {{ ws.connect(); }} catch (e) {{ try {{ call.log("ws connect err " + e); }} catch (_) {{ }} }}
"""
        self.vodia_generated_script = script_template

