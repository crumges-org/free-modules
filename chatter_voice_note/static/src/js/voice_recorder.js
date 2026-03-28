/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { Chatter } from "@mail/chatter/web_portal/chatter";

patch(Chatter.prototype, {

    setup() {
        super.setup();

        this._voiceState = useState({
            recording: false,
            seconds: 0,
        });

        this._interval = null;
        this._mediaRecorder = null;
        this._chunks = [];
    },

    get voiceState() {
        return this._voiceState || { recording: false, seconds: 0 };
    },

    async toggleVoiceRecording() {

        if (!this._voiceState.recording) {

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            let options = {};
            if (MediaRecorder.isTypeSupported("audio/mp4")) {
                options = { mimeType: "audio/mp4" };
            } else if (MediaRecorder.isTypeSupported("audio/webm")) {
                options = { mimeType: "audio/webm" };
            }

            this._mediaRecorder = new MediaRecorder(stream, options);
            this._chunks = [];

            this._mediaRecorder.ondataavailable = (e) => {
                this._chunks.push(e.data);
            };

            this._mediaRecorder.onstop = async () => {

                const mimeType = this._mediaRecorder.mimeType || "audio/webm";
                const blob = new Blob(this._chunks, { type: mimeType });

                const extension = mimeType.includes("mp3") ? "mp3" : "webm";

                const now = new Date();
                const timestamp = now.toISOString().replace(/[:.]/g, "-");
                const filename = `Voice_Note_${timestamp}.${extension}`;

                const base64 = await this._blobToBase64(blob);

                // ✅ Create attachment
                const attachmentId = await this.orm.create("ir.attachment", [{
                    name: filename,
                    datas: base64.split(",")[1],
                    res_model: this.env.model.config.resModel,
                    res_id: this.env.model.config.resId,
                    mimetype: "audio/mpeg",
                }]);


                await this.env.model.root.load();
            };

            this._mediaRecorder.start();
            this._voiceState.recording = true;
            this._voiceState.seconds = 0;

            this._interval = setInterval(() => {
                this._voiceState.seconds++;
            }, 1000);

        } else {

            this._mediaRecorder.stop();
            clearInterval(this._interval);
            this._voiceState.recording = false;
        }
    },

    _blobToBase64(blob) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.readAsDataURL(blob);
            reader.onloadend = () => resolve(reader.result);
        });
    },
});