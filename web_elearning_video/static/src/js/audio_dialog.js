/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component, onMounted, onWillUnmount} from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Mutex } from "@web/core/utils/concurrency";
import { rpc } from "@web/core/network/rpc";

export class AudioSelectorDialog extends Component {
    static template = "web_elearning_video.AudioDialog";
    static defaultProps = {
        useMediaLibrary: true,
    };
    static components = {
        Dialog,
    };
    static props = ["*"];

    /**
     * @override
     */
    setup () {
        super.setup();
        this.title = _t("Insert Audio");
        this.mutex = new Mutex();
        this.constraints = { audio: true, video: false };
        this.mediaRecorder = null;
        this.recordedBlobs = [];
        this.notificationService = useService("notification");
        onMounted(this._setupAudioElements.bind(this));
        onWillUnmount(() => {
            if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
            }
            if (this.stream) {
                this.stream.getTracks().forEach((track) => track.stop());
            }
            if (this.timerInterval) {
                clearInterval(this.timerInterval);
            }
            this.recordedBlobs = [];
        });
    }
    _setupAudioElements() {
        this.recordDot = document.querySelector('.record-dot');
        this.recordTimer = document.querySelector('.record-timer');
        this.startBtn = document.querySelector('button.note-record-btn');
        this.stopBtn = document.querySelector('button.note-record-stop-btn');
        this.playBtn = document.querySelector('button.note-audio-play');
        this.downloadBtn = document.querySelector('button.note-audio-download');
        this.recordedAudio = document.querySelector('audio.recorded');
        var self = this;
        navigator.mediaDevices.getUserMedia(this.constraints)
            .then(stream => {
                self.stream = stream;
                window.stream = stream;
                self._showControlButtons();
            })
            .catch(error => {
                self._showMicrophoneErrorMessage();
                self._hideControlButtons();
            });
    }

    _showMicrophoneErrorMessage() {
        var audioContainer = document.querySelector('div.audios');
        if (audioContainer.length === 0) {
            console.error("Error: Audio container not found.");
            return;
        }
        audioContainer.html(`
            <div class="microphone-error-message" style="
                width: 100%;
                text-align: center;
                color: red;
                padding: 10px;
                font-size: 16px;
                border-radius: 5px;
            ">
                ⚠️ Microphone not detected! Please enable your microphone.
            </div>
        `);
        if (this.recordDot) {
            this.recordDot.style.display = 'none';
        }
        if (this.recordTimer) {
            this.recordTimer.style.display = 'none';
        }
    }

    /**
     * Hide control buttons when the camera is not enabled.
     */
    _hideControlButtons() {
        this.startBtn.style.display = 'none';
        this.stopBtn.style.display = 'none';
        this.playBtn.style.display = 'none';
        this.downloadBtn.style.display = 'none';
    }

    /**
     * Show control buttons when the camera is enabled.
     */
    _showControlButtons() {
        this.startBtn.style.display = '';
        this.stopBtn.style.display = '';
        this.playBtn.style.display = '';
        this.downloadBtn.style.display = '';
    }

    async onStartRecording(ev) {
        try {
            this.mediaRecorder = new MediaRecorder(window.stream);
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.recordedBlobs.push(event.data);
                }
            };
        } catch (e0) {
            alert('MediaRecorder is not supported by this browser.');
            return;
        }
        this.mediaRecorder.start();
        this.startBtn.disabled = true;
        this.stopBtn.disabled = false;
        this.playBtn.disabled = true;
        this.downloadBtn.disabled = true; 
        this.recordDot.style.display = 'block';
        this.recordTimer.style.display = 'block';

        let seconds = 0;
        this.timerInterval = setInterval(() => {
            seconds++;
            const minutes = Math.floor(seconds / 60);
            const secs = seconds % 60;
            if (this.recordTimer) {
                this.recordTimer.textContent = `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }
    
    onStopRecording(ev) {
        this.mediaRecorder.stop();
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        this.recordDot.style.display = 'none';
        this.startBtn.disabled = false;
        this.stopBtn.disabled = true;
        this.playBtn.disabled = false;
        this.downloadBtn.disabled = false;
    }
    
    onPlayAudio(ev) {
        ev.preventDefault();
        var type = (this.recordedBlobs[0] || {}).type;
        var superBuffer = new Blob(this.recordedBlobs, { type });
        this.recordedAudio.src = window.URL.createObjectURL(superBuffer);
    }

    onDownloadAudio(ev) {
        ev.preventDefault();
        if (this.recordedBlobs.length === 0) {
            this.env.services.notification.add(
                "No recording available to download.",
                { type: "danger" }
            );
            return;
        }
        const blob = new Blob(this.recordedBlobs, { type: "audio/webm" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = 'none';
        a.href = url;
        a.download = "recording.webm";
        document.body.appendChild(a);
        a.click();
        setTimeout(function () {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 100);
    }
    
    async save() {
        if (!this.recordedBlobs || this.recordedBlobs.length === 0) {
            this.notificationService.add(_t("No audio recorded to save."), {
                type: 'danger',
            });
            return;
        }
    
        const saveRecordedAudio = this.recordedBlobs.length > 0;
        if (saveRecordedAudio) {
            const elements = await this.mutex.exec(async () => {
                const attachmentObj = await this.addAttachment(this.recordedBlobs);
                if (!attachmentObj || !attachmentObj.id) {
                    this.notificationService.add(_t("Failed to upload the recorded audio."), {
                        type: 'danger',
                    });
                    return [];
                }
    
                if (typeof window.stream === "object") {
                    window.stream.getTracks().forEach(track => track.stop());
                }
    
                if (this.recordedAudio && this.recordedAudio.length) {
                    this.recordedAudio.removeAttribute('src');
                    this.recordedAudio.load();
                }
    
                const src = `${window.location.origin}/web/content/${attachmentObj.id}?controls=1`;
                
                const wrapper = document.createElement('div');
                wrapper.innerHTML = `
                    <div class="media-audio" data-oe-expression="${src}">
                        <div class="css_editable_mode_display"></div>
                        <div class="media_iframe_video_size" contenteditable="false"></div>
                        <audio controls>
                            <source src="${src}" type="audio/mpeg" />
                        </audio>
                    </div>
                `;
                const audioElement = wrapper.firstElementChild;    
                return [audioElement];
            });
    
            if (elements && elements.length) {
                await this.props.save(elements[0]);
            }
        }
    
        this.props.close();
    }
    
    async blobToBase64(blob) {
        const reader = new FileReader();
        reader.readAsDataURL(blob);
        return new Promise(resolve => {
            reader.onloadend = () => {
                resolve(reader.result);
            };
        });
    }
    
    async addAttachment() {
        let audioAttachment;
        if (this.recordedBlobs) {
            let type = (this.recordedBlobs[0] || {}).type;
            let superBuffer = new Blob(this.recordedBlobs, { type });
            const bs64Audio = await this.blobToBase64(superBuffer);
            audioAttachment = await rpc('/web_editor/attachment/add_data', {
                'name': 'recording.webm',
                'data': bs64Audio.split(',')[1],
                'is_image': false,
            });
        }
        return audioAttachment;
    }
}
