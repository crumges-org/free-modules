/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component, useState, useRef, onMounted, xml, onRendered, onWillUnmount} from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Mutex } from "@web/core/utils/concurrency";
import { rpc } from "@web/core/network/rpc";

export class VideoSelectorDialog extends Component {
    static template = "web_elearning_video.VideoDialog";
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
        this.title = _t("Insert Video");
        this.mutex = new Mutex();
        this.constraints = { audio: true, video: true };
        this.mediaRecorder = null;
        this.recordedBlobs = [];
        this.notificationService = useService("notification");
        onMounted(this._setupVideoElements.bind(this));
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
            // this.recordedBlobs = [];
        });
    }
    _setupVideoElements() {
        this.gumVideo = document.querySelector('.gum');
        this.recordedVideo = document.querySelector('.note-video-input');
        this.recordDot = document.querySelector('.record-dot');
        this.recordTimer = document.querySelector('.record-timer');
        this.startBtn = document.querySelector('button.note-record-btn');
        this.stopBtn = document.querySelector('button.note-record-stop-btn');
        this.playBtn = document.querySelector('button.note-video-play');
        this.downloadBtn = document.querySelector('button.note-video-download');

        var self = this;
        navigator.mediaDevices.getUserMedia(this.constraints)
        .then(stream => {
            if(!stream || stream.getVideoTracks().length === 0) {
                self._showCameraErrorMessage();
                self._hideControlButtons();
                return;
            }
            self.stream = stream;
            self.gumVideo.srcObject = stream;
            window.stream = stream;
            self._showControlButtons();
        })
        .catch(error => {
            self._showCameraErrorMessage();
            self._hideControlButtons();
        });
    }

    _showCameraErrorMessage() {
        var videoContainer = document.querySelector('div.videos');
        if (videoContainer.length === 0) {
            console.error("Error: Video container not found.");
            return;
        }
        videoContainer.innerHTML = `
            <div class="camera-error-message" style="
                width: 100%;
                text-align: center;
                color: red;
                padding: 10px;
                font-size: 16px;
                border-radius: 5px;
            ">
                ⚠️ Camera not detected! Please enable your camera.
            </div>
        `;
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
    

    async onStartRecording() {
        this.recordedBlobs = [];
        try {
            this.mediaRecorder = new MediaRecorder(this.stream, { mimeType: 'video/webm' });
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    this.recordedBlobs.push(event.data);
                }
            };
            this.mediaRecorder.onstop = () => {
                const blob = new Blob(this.recordedBlobs, { type: 'video/webm' });
                if (this.recordedVideo) {
                    this.recordedVideo.src = window.URL.createObjectURL(blob);
                    this.recordedVideo.muted = false;
                }

                if (this.playBtn) this.playBtn.disabled = false;
                if (this.downloadBtn) this.downloadBtn.disabled = false;
            };

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
        } catch (err) {
            console.error('Error starting video recording:', err);
            this.notification.add('Failed to access camera/microphone. Please check permissions.', {
                title: 'Recording Error',
                type: 'danger',
            });
        }
    }
    
    onStopRecording() {
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
    
    onPlayVideo() {
        if (this.recordedVideo) {
            this.recordedVideo.play();
        }
    }

    onDownloadVideo() {
        const blob = new Blob(this.recordedBlobs, { type: 'video/webm' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `recording_${new Date().toISOString()}.webm`;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 100);
    }
    
    async save() {
        if (!this.recordedBlobs || this.recordedBlobs.length === 0) {
            this.notificationService.add("No Video recorded to save.", {
                type: 'danger',
            });
            return;
        }
    
        const saveRecordedVideo = this.recordedBlobs.length > 0;
        if (saveRecordedVideo) {
            const elements = await this.mutex.exec(async () => {
                const attachmentObj = await this.addAttachment(this.recordedBlobs);
                if (!attachmentObj || !attachmentObj.id) {
                    this.notificationService.add("Failed to upload the recorded video.", {
                        type: 'danger',
                    });
                    return [];
                }
    
                if (typeof window.stream === "object") {
                    window.stream.getTracks().forEach(track => track.stop());
                }
    
                const recordedVideo = document.querySelector('note-video-input');
                if (recordedVideo && recordedVideo.length) {
                    recordedVideo.get(0).removeAttribute('src');
                    recordedVideo.get(0).load();
                }
    
                const src = `${window.location.origin}/web/content/${attachmentObj.id}?controls=1`;
                const wrapper = document.createElement('div');
                wrapper.innerHTML = `
                    <div class="media-video" data-oe-expression="${src}">
                        <div class="css_editable_mode_display"/>
                        <div class="media_iframe_video_size" contenteditable="false"></div>
                        <video controls>
                            <source src="${src}" type="video/webm" />
                        </video>
                    </div>
                `;
                const videoElement = wrapper.firstElementChild;    
                return [videoElement];
            });
    
            if (elements && elements.length) {
                await this.props.save(elements[0]);
            }
        }
        this.props.close();
    }
    
    async blobToBase64(blob) {
        return new Promise(resolve => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result);
            reader.readAsDataURL(blob);
        });
    }
    
    async addAttachment(blobs) {
        if (!blobs.length) return null;
        const superBuffer = new Blob(blobs, { type: 'video/webm' });
        const bs64Video = await this.blobToBase64(superBuffer);
        const response = await rpc('/web_editor/attachment/add_data', {
            name: 'recording.webm',
            data: bs64Video.split(',')[1],
            is_image: false,
        });
        return response;
    }
}
