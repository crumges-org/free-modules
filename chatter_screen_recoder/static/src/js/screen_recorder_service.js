/** @odoo-module */

import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export const screenRecorderService = {
    dependencies: ["notification", "http"],

    start(env, { notification, http }) {
        let _mediaRecorder = null;
        let _screenStream = null;
        let _micStream = null;
        let _combinedStream = null;
        let _recordedChunks = [];
        let _timerInterval = null;
        let _startTime = null;
        let _pausedElapsed = 0;
        let _pauseStartTime = null;
        let _audioContext = null;

        const state = reactive({
            isRecording: false,
            isPaused: false,
            isUploading: false,
            timerDisplay: "00:00",
            sourceModel: null,
            sourceId: null,
            sourceName: null,

            startRecording,
            stopAndSave,
            pauseRecording,
            resumeRecording,
            discardRecording,
        });

        function _getRecorderMimeType() {
            const types = [
                "video/webm;codecs=vp9,opus",
                "video/webm;codecs=vp8,opus",
                "video/webm;codecs=vp9",
                "video/webm;codecs=vp8",
                "video/webm",
            ];
            for (const type of types) {
                if (MediaRecorder.isTypeSupported(type)) {
                    return type;
                }
            }
            return null;
        }

        function _updateTimer() {
            if (!_startTime) return;
            let elapsed;
            if (state.isPaused) {
                elapsed = Math.floor(_pausedElapsed / 1000);
            } else {
                elapsed = Math.floor((Date.now() - _startTime - _pausedElapsed) / 1000);
            }
            const minutes = String(Math.floor(elapsed / 60)).padStart(2, "0");
            const seconds = String(elapsed % 60).padStart(2, "0");
            state.timerDisplay = `${minutes}:${seconds}`;
        }

        function _stopAllStreams() {
            if (_screenStream) {
                _screenStream.getTracks().forEach((track) => track.stop());
                _screenStream = null;
            }
            if (_micStream) {
                _micStream.getTracks().forEach((track) => track.stop());
                _micStream = null;
            }
            if (_combinedStream) {
                _combinedStream.getTracks().forEach((track) => track.stop());
                _combinedStream = null;
            }
            if (_audioContext) {
                _audioContext.close();
                _audioContext = null;
            }
            if (_timerInterval) {
                clearInterval(_timerInterval);
                _timerInterval = null;
            }
        }

        function _resetState() {
            state.isRecording = false;
            state.isPaused = false;
            state.timerDisplay = "00:00";
            _mediaRecorder = null;
            _recordedChunks = [];
            _startTime = null;
            _pausedElapsed = 0;
            _pauseStartTime = null;
        }

        async function startRecording(model, id, name) {
            if (state.isRecording || state.isUploading) {
                return;
            }

            try {
                _screenStream = await navigator.mediaDevices.getDisplayMedia({
                    video: { mediaSource: "screen" },
                    audio: true,
                });
            } catch (err) {
                notification.add(
                    _t("Screen recording was cancelled or denied."),
                    { type: "warning" }
                );
                return;
            }

            // Capture microphone audio separately
            try {
                _micStream = await navigator.mediaDevices.getUserMedia({
                    audio: true,
                    video: false,
                });
            } catch (err) {
                _micStream = null;
            }

            const tracks = [..._screenStream.getVideoTracks()];

            if (_micStream || _screenStream.getAudioTracks().length > 0) {
                const audioContext = new AudioContext();
                const destination = audioContext.createMediaStreamDestination();

                if (_screenStream.getAudioTracks().length > 0) {
                    const screenAudioSource = audioContext.createMediaStreamSource(
                        new MediaStream(_screenStream.getAudioTracks())
                    );
                    screenAudioSource.connect(destination);
                }

                if (_micStream && _micStream.getAudioTracks().length > 0) {
                    const micAudioSource = audioContext.createMediaStreamSource(_micStream);
                    micAudioSource.connect(destination);
                }

                tracks.push(...destination.stream.getAudioTracks());
                _audioContext = audioContext;
            }

            _combinedStream = new MediaStream(tracks);
            _recordedChunks = [];

            const mimeType = _getRecorderMimeType();
            const options = {};
            if (mimeType) {
                options.mimeType = mimeType;
            }

            _mediaRecorder = new MediaRecorder(_combinedStream, options);

            _mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    _recordedChunks.push(event.data);
                }
            };

            _mediaRecorder.onstop = () => {
                _onRecordingStopped();
            };

            const videoTrack = _screenStream.getVideoTracks()[0];
            if (videoTrack) {
                videoTrack.onended = () => {
                    if (state.isRecording) {
                        stopAndSave();
                    }
                };
            }

            state.sourceModel = model;
            state.sourceId = id;
            state.sourceName = name;

            _mediaRecorder.start(1000);
            state.isRecording = true;
            state.isPaused = false;

            _startTime = Date.now();
            _pausedElapsed = 0;
            _timerInterval = setInterval(() => {
                _updateTimer();
            }, 1000);
        }

        function stopAndSave() {
            if (!_mediaRecorder || _mediaRecorder.state === "inactive") {
                return;
            }
            if (state.isPaused) {
                _mediaRecorder.resume();
            }
            _mediaRecorder.stop();
            _stopAllStreams();
            state.isRecording = false;
            state.isPaused = false;
        }

        function pauseRecording() {
            if (!_mediaRecorder || _mediaRecorder.state !== "recording") {
                return;
            }
            _mediaRecorder.pause();
            state.isPaused = true;
            _pauseStartTime = Date.now();
            if (_timerInterval) {
                clearInterval(_timerInterval);
                _timerInterval = null;
            }
        }

        function resumeRecording() {
            if (!_mediaRecorder || _mediaRecorder.state !== "paused") {
                return;
            }
            _mediaRecorder.resume();
            if (_pauseStartTime) {
                _pausedElapsed += Date.now() - _pauseStartTime;
                _pauseStartTime = null;
            }
            state.isPaused = false;
            _timerInterval = setInterval(() => {
                _updateTimer();
            }, 1000);
        }

        function discardRecording() {
            if (_mediaRecorder && _mediaRecorder.state !== "inactive") {
                // Detach onstop handler to prevent upload
                _mediaRecorder.onstop = null;
                if (state.isPaused) {
                    _mediaRecorder.resume();
                }
                _mediaRecorder.stop();
            }
            _stopAllStreams();
            _resetState();
            notification.add(
                _t("Recording discarded."),
                { type: "info" }
            );
        }

        async function _onRecordingStopped() {
            if (_recordedChunks.length === 0) {
                notification.add(
                    _t("No recording data captured."),
                    { type: "warning" }
                );
                _resetState();
                return;
            }

            const mimeType = _recordedChunks[0].type || "video/webm";
            const blob = new Blob(_recordedChunks, { type: mimeType });
            _recordedChunks = [];

            const now = new Date();
            const timestamp = now.toISOString().replace(/[:.]/g, "-").slice(0, 19);
            const filename = `screen_recording_${timestamp}.webm`;
            const file = new File([blob], filename, { type: mimeType });

            await _uploadRecording(file);
        }

        async function _uploadRecording(file) {
            state.isUploading = true;

            try {
                const resModel = state.sourceModel;
                const resId = state.sourceId;

                const fileData = await http.post(
                    "/web/binary/upload_attachment",
                    {
                        csrf_token: odoo.csrf_token,
                        ufile: [file],
                        model: resModel,
                        id: resId,
                    },
                    "text"
                );

                const parsedData = JSON.parse(fileData);
                if (parsedData.error) {
                    throw new Error(parsedData.error);
                }

                notification.add(
                    _t("Screen recording saved successfully."),
                    { type: "success" }
                );
            } catch (err) {
                notification.add(
                    _t("Failed to upload recording: ") + (err.message || err),
                    { type: "danger" }
                );
            } finally {
                state.isUploading = false;
                state.sourceModel = null;
                state.sourceId = null;
                state.sourceName = null;
            }
        }

        return state;
    },
};

registry.category("services").add("screen_recorder", screenRecorderService);
