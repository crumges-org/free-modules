/** @odoo-module **/

import { EventBus, reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";

const { DateTime } = luxon;
import {
    buildFallbackRecordStream,
    buildMixedRecordingStream,
    cloneMediaStream,
    resumeRecordingAudioContext,
    stopRecordStream,
    stopRecordingStreamSession,
    waitForLiveTracks,
} from "./recording_stream";

function getMimeTypeCandidates() {
    const candidates = [
        "video/webm;codecs=vp9,opus",
        "video/webm;codecs=vp8,opus",
        "video/webm;codecs=vp8",
        "video/webm",
    ];
    const supported = candidates.filter((mime) => MediaRecorder.isTypeSupported(mime));
    return supported.length ? supported : ["video/webm"];
}

export const kxVideoRecordingService = {
    dependencies: ["notification", "kx_recording_playback"],
    start(env, { notification, kx_recording_playback }) {
        const bus = new EventBus();

        /** @type {null | object} */
        let streamSession = null;
        /** @type {MediaRecorder | null} */
        let mediaRecorder = null;
        /** @type {MediaStream | null} */
        let recordStream = null;
        let recorderMimeType = "video/webm";
        let isStartingRecorder = false;
        /** @type {Blob[]} */
        let recordedChunks = [];
        /** @type {Blob | null} */
        let recordedBlob = null;
        /** @type {string | null} */
        let playbackObjectUrl = null;
        /** @type {number | null} */
        let durationTimer = null;
        /** @type {(() => void) | null} */
        let videoTrackEndedHandler = null;

        /** @type {{ resModel?: string, resId?: number, onSaved?: function }} */
        let linkContext = {};

        const state = reactive({
            /** idle | setup | picking | ready | recording | preview | saving | saved */
            phase: "idle",
            duration: 0,
            error: null,
            includeMic: true,
            includeSystemAudio: true,
            /** Bumped when preview blob URL changes so UI can re-bind video. */
            previewRevision: 0,
            /** Set after successful upload: { id, name, attachment_id, view_url } */
            lastSaved: null,
            isStarting: false,
            /** When set, systray recording can auto-link to the open form document. */
            formLink: null,
            linkToCurrentDocument: false,
            autoDelete: false,
            autoDeleteDays: 30,
            /** "current" = this tab only; "other" = Chrome screen/window/tab picker */
            shareMode: "current",
            /** Editable title before save (set when preview opens). */
            recordingName: "",
            isPaused: false,
        });

        function _localTimestamp() {
            return DateTime.local().toFormat("yyyy-MM-dd HH:mm");
        }

        function _defaultRecordingName() {
            const stamp = _localTimestamp();
            if (
                state.linkToCurrentDocument &&
                state.formLink?.displayName &&
                linkContext.resModel
            ) {
                return `${state.formLink.displayName} - Screen Recording - ${stamp}`;
            }
            return _t("Screen recording %s", stamp);
        }

        function supportsPauseResume() {
            return typeof MediaRecorder !== "undefined" && "pause" in MediaRecorder.prototype;
        }

        function isEnabled() {
            return (
                session.kx_video_recording_active !== false &&
                session.kx_video_recording_user !== false
            );
        }

        function isSupported() {
            return Boolean(
                typeof navigator !== "undefined" &&
                    navigator.mediaDevices?.getDisplayMedia &&
                    typeof MediaRecorder !== "undefined"
            );
        }

        function isActive() {
            return state.phase !== "idle";
        }

        function _clearDurationTimer() {
            if (durationTimer) {
                browser.clearInterval(durationTimer);
                durationTimer = null;
            }
        }

        function _startDurationTimer() {
            _clearDurationTimer();
            durationTimer = browser.setInterval(() => {
                if (state.phase === "recording" && !state.isPaused) {
                    state.duration += 1;
                    bus.trigger("KX_RECORDING_TICK");
                }
            }, 1000);
        }

        function _revokePlaybackUrl() {
            if (playbackObjectUrl) {
                URL.revokeObjectURL(playbackObjectUrl);
                playbackObjectUrl = null;
            }
        }

        function _unbindVideoTrackEnded() {
            const track = streamSession?.displayStream?.getVideoTracks()[0];
            if (track && videoTrackEndedHandler) {
                track.removeEventListener("ended", videoTrackEndedHandler);
            }
            videoTrackEndedHandler = null;
        }

        function _releaseRecordStream() {
            stopRecordStream(recordStream);
            recordStream = null;
        }

        function _releaseStreams() {
            _unbindVideoTrackEnded();
            _releaseRecordStream();
            stopRecordingStreamSession(streamSession);
            streamSession = null;
        }

        function _stopRecorderSilently() {
            _clearDurationTimer();
            const recorder = mediaRecorder;
            if (recorder) {
                recorder.onstop = null;
                if (recorder.state !== "inactive") {
                    try {
                        recorder.stop();
                    } catch {
                        /* noop */
                    }
                }
            }
            mediaRecorder = null;
            recordedChunks = [];
        }

        function _resetToIdle() {
            _stopRecorderSilently();
            _revokePlaybackUrl();
            recordedBlob = null;
            _releaseStreams();
            linkContext = {};
            state.phase = "idle";
            state.duration = 0;
            state.error = null;
            state.previewRevision = 0;
            state.lastSaved = null;
            state.recordingName = "";
            state.isPaused = false;
        }

        function requestOpenPanel() {
            bus.trigger("KX_RECORDING_OPEN_PANEL");
        }

        function _applyFormLinkToContext(ctx) {
            const out = { ...ctx };
            if (
                state.linkToCurrentDocument &&
                state.formLink?.resModel &&
                state.formLink?.resId
            ) {
                out.resModel = state.formLink.resModel;
                out.resId = state.formLink.resId;
            }
            return out;
        }

        /** Resolve document link at save time (respects “Link to record” checkbox). */
        function _getEffectiveLinkContext() {
            return _applyFormLinkToContext({
                resModel: linkContext.resModel,
                resId: linkContext.resId,
                onSaved: linkContext.onSaved,
            });
        }

        function setFormLink(link) {
            state.formLink = link;
        }

        function setLinkToCurrentDocument(enabled) {
            state.linkToCurrentDocument = Boolean(enabled);
            if (enabled && state.formLink?.resModel && state.formLink?.resId) {
                linkContext.resModel = state.formLink.resModel;
                linkContext.resId = state.formLink.resId;
            } else if (!linkContext.onSaved) {
                linkContext.resModel = undefined;
                linkContext.resId = undefined;
            }
        }

        function clearFormLink() {
            state.formLink = null;
        }

        /**
         * Start a recording workflow (systray only — no modal).
         * @param {Object} [options]
         * @param {string} [options.resModel]
         * @param {number} [options.resId]
         * @param {function} [options.onSaved]
         * @param {boolean} [options.openPanel]
         */
        function beginSession(options = {}) {
            if (!isEnabled()) {
                notification.add(_t("Screen recording is disabled."), { type: "warning" });
                return;
            }
            if (!isSupported()) {
                notification.add(
                    _t(
                        "Screen recording is not supported in this browser. Use Chrome or Edge on desktop."
                    ),
                    { type: "warning" }
                );
                return;
            }
            _stopRecorderSilently();
            _revokePlaybackUrl();
            recordedBlob = null;
            _releaseStreams();
            linkContext = _applyFormLinkToContext({
                resModel: options.resModel,
                resId: options.resId,
                onSaved: options.onSaved,
            });
            state.phase = "setup";
            state.duration = 0;
            state.error = null;
            state.lastSaved = null;
            state.recordingName = "";
            state.isPaused = false;
            if (options.openPanel !== false) {
                requestOpenPanel();
            }
            bus.trigger("KX_RECORDING_PREVIEW_SYNC");
        }

        function _bindVideoTrackEnded() {
            _unbindVideoTrackEnded();
            const track = streamSession?.displayStream?.getVideoTracks()[0];
            if (!track) {
                return;
            }
            videoTrackEndedHandler = () => {
                if (state.phase === "recording") {
                    stopRecording();
                } else if (state.phase === "ready") {
                    notification.add(
                        _t("Screen sharing ended. Choose another screen to continue."),
                        { type: "warning" }
                    );
                    _releaseStreams();
                    state.phase = "setup";
                }
            };
            track.addEventListener("ended", videoTrackEndedHandler);
        }

        async function pickScreen(shareMode) {
            if (shareMode) {
                state.shareMode = shareMode;
            }
            if (!isActive()) {
                beginSession({ openPanel: false });
            }
            state.error = null;
            state.phase = "picking";
            _stopRecorderSilently();
            _revokePlaybackUrl();
            recordedBlob = null;
            _releaseStreams();

            const currentTabOnly = state.shareMode === "current";
            try {
                streamSession = {
                    ...(await buildMixedRecordingStream({
                        includeMic: state.includeMic,
                        includeSystemAudio: state.includeSystemAudio,
                        currentTabOnly,
                        onMicDenied: () => {
                            notification.add(
                                _t(
                                    "Microphone access denied. Recording will continue without your voice."
                                ),
                                { type: "warning" }
                            );
                        },
                    })),
                };
                _bindVideoTrackEnded();
                await startRecording();
            } catch (err) {
                const msg = err?.message || String(err);
                if (!msg.includes("Permission denied") && err?.name !== "NotAllowedError") {
                    state.error = msg;
                    notification.add(_t("Could not access screen: %s", msg), { type: "danger" });
                }
                state.phase = "setup";
            }
        }

        function attachLivePreview(videoEl) {
            if (!videoEl || !streamSession?.mixedStream) {
                return;
            }
            if (state.phase !== "ready" && state.phase !== "recording") {
                return;
            }
            videoEl.srcObject = streamSession.mixedStream;
            videoEl.play().catch(() => {});
        }

        function attachPlaybackPreview(videoEl) {
            if (!videoEl || state.phase !== "preview" || !recordedBlob) {
                return;
            }
            if (!playbackObjectUrl) {
                playbackObjectUrl = URL.createObjectURL(recordedBlob);
                state.previewRevision += 1;
            }
            videoEl.src = playbackObjectUrl;
        }

        function clearVideoElement(videoEl) {
            if (!videoEl) {
                return;
            }
            videoEl.srcObject = null;
            videoEl.removeAttribute("src");
        }

        /**
         * Try MediaRecorder.start with mime and stream fallbacks (fixes intermittent browser errors).
         * @returns {Promise<{ recorder: MediaRecorder, mimeType: string }>}
         */
        async function _createAndStartRecorder(streamCandidates) {
            const mimeTypes = getMimeTypeCandidates();
            const sessionMixed = streamSession?.mixedStream;
            let lastError = null;
            for (const stream of streamCandidates) {
                await waitForLiveTracks(stream);
                for (const mimeType of mimeTypes) {
                    let recorder = null;
                    try {
                        recorder = new MediaRecorder(stream, { mimeType });
                        recorder.start(250);
                        return {
                            recorder,
                            mimeType: recorder.mimeType || mimeType,
                        };
                    } catch (err) {
                        lastError = err;
                        if (recorder && recorder.state !== "inactive") {
                            try {
                                recorder.stop();
                            } catch {
                                /* noop */
                            }
                        }
                    }
                }
                if (stream !== sessionMixed) {
                    stopRecordStream(stream);
                }
            }
            throw lastError || new Error("MediaRecorder could not start");
        }

        async function startRecording() {
            if (!["picking", "ready"].includes(state.phase) || isStartingRecorder) {
                return;
            }
            if (!streamSession?.mixedStream) {
                state.error = _t("Choose a screen to share first.");
                state.phase = "setup";
                return;
            }
            state.error = null;
            isStartingRecorder = true;
            state.isStarting = true;
            bus.trigger("KX_RECORDING_PREPARE_START");
            try {
                await resumeRecordingAudioContext(streamSession.audioContext);
                await waitForLiveTracks(streamSession.mixedStream);

                _releaseRecordStream();
                const streamCandidates = [];
                try {
                    streamCandidates.push(cloneMediaStream(streamSession.mixedStream));
                } catch {
                    /* use fallbacks below */
                }
                try {
                    streamCandidates.push(buildFallbackRecordStream(streamSession));
                } catch {
                    /* noop */
                }
                if (!streamCandidates.length) {
                    streamCandidates.push(streamSession.mixedStream);
                }

                const { recorder, mimeType } = await _createAndStartRecorder(streamCandidates);
                recordStream = recorder.stream || streamCandidates[0];
                recorderMimeType = mimeType;
                recordedChunks = [];
                mediaRecorder = recorder;
                recorder.ondataavailable = (ev) => {
                    if (ev.data?.size) {
                        recordedChunks.push(ev.data);
                    }
                };
                recorder.onstop = () => {
                    const blobType = recorderMimeType || "video/webm";
                    mediaRecorder = null;
                    recordedBlob = new Blob(recordedChunks, { type: blobType });
                    _releaseRecordStream();
                    _revokePlaybackUrl();
                    state.phase = "preview";
                    state.recordingName = _defaultRecordingName();
                    state.isPaused = false;
                    state.previewRevision += 1;
                    bus.trigger("KX_RECORDING_PREVIEW_SYNC");
                };
                state.phase = "recording";
                state.duration = 0;
                state.isPaused = false;
                _startDurationTimer();
                bus.trigger("KX_RECORDING_PREVIEW_SYNC");
            } catch (err) {
                _releaseRecordStream();
                state.error = err?.message || String(err);
                state.phase = streamSession ? "ready" : "setup";
                notification.add(_t("Could not start recording."), { type: "danger" });
            } finally {
                isStartingRecorder = false;
                state.isStarting = false;
            }
        }

        function pauseRecording() {
            const recorder = mediaRecorder;
            if (
                state.phase !== "recording" ||
                state.isPaused ||
                !recorder ||
                typeof recorder.pause !== "function"
            ) {
                return;
            }
            if (recorder.state === "recording") {
                recorder.pause();
                state.isPaused = true;
                bus.trigger("KX_RECORDING_TICK");
            }
        }

        function resumeRecording() {
            const recorder = mediaRecorder;
            if (
                state.phase !== "recording" ||
                !state.isPaused ||
                !recorder ||
                typeof recorder.resume !== "function"
            ) {
                return;
            }
            if (recorder.state === "paused") {
                recorder.resume();
                state.isPaused = false;
                bus.trigger("KX_RECORDING_TICK");
            }
        }

        function stopRecording() {
            _clearDurationTimer();
            state.isPaused = false;
            const recorder = mediaRecorder;
            if (recorder && recorder.state !== "inactive") {
                recorder.stop();
                return;
            }
            if (!recordedBlob && streamSession) {
                state.phase = "ready";
            }
        }

        async function discardPreview() {
            _revokePlaybackUrl();
            recordedBlob = null;
            _stopRecorderSilently();
            const mode = state.shareMode;
            _releaseStreams();
            await pickScreen(mode);
        }

        function changeScreen() {
            pickScreen();
        }

        function cancelSession() {
            _resetToIdle();
        }

        function setRecordingName(name) {
            state.recordingName = name;
        }

        async function saveRecording() {
            if (!recordedBlob || state.phase === "saving") {
                return;
            }
            const name = (state.recordingName || "").trim() || _defaultRecordingName();
            state.phase = "saving";
            try {
                const file = new File([recordedBlob], `${name}.webm`, {
                    type: recordedBlob.type || "video/webm",
                });
                const formData = new FormData();
                formData.append("ufile", file, file.name);
                formData.append("name", name);
                formData.append("duration", String(state.duration));
                const uploadLink = _getEffectiveLinkContext();
                if (uploadLink.resModel) {
                    formData.append("res_model", uploadLink.resModel);
                }
                if (uploadLink.resId) {
                    formData.append("res_id", String(uploadLink.resId));
                }
                formData.append("auto_delete", state.autoDelete ? "1" : "0");
                formData.append("auto_delete_days", String(state.autoDeleteDays || 30));
                if (odoo.csrf_token) {
                    formData.append("csrf_token", odoo.csrf_token);
                }
                const response = await browser.fetch("/kx_recording/upload", {
                    method: "POST",
                    body: formData,
                    credentials: "same-origin",
                });
                const payload = await response.json();
                if (!response.ok || payload.error) {
                    throw new Error(payload.error || _t("Upload failed"));
                }
                _stopRecorderSilently();
                _revokePlaybackUrl();
                recordedBlob = null;
                _releaseStreams();

                const viewUrl =
                    payload.view_url ||
                    (payload.id ? `/kx_recording/watch/${payload.id}` : null);
                state.lastSaved = {
                    id: payload.id,
                    name: payload.name,
                    attachment_id: payload.attachment_id,
                    view_url: viewUrl,
                };
                state.phase = "saved";
                bus.trigger("KX_RECORDING_PREVIEW_SYNC");
                notification.add(_t("Recording saved."), { type: "success" });
                const savedLink = _getEffectiveLinkContext();
                if (savedLink.onSaved) {
                    await savedLink.onSaved(payload);
                }
            } catch (err) {
                state.phase = "preview";
                notification.add(err?.message || _t("Could not save recording."), {
                    type: "danger",
                });
            }
        }

        function downloadLastSaved() {
            const attId = state.lastSaved?.attachment_id;
            if (!attId) {
                return;
            }
            browser.open(`/web/content/${attId}?download=true`, "_self");
        }

        function downloadRecordingAttachment(attachmentId) {
            if (attachmentId) {
                browser.open(`/web/content/${attachmentId}?download=true`, "_self");
            }
        }

        function viewLastSaved() {
            const id = state.lastSaved?.id;
            if (id) {
                kx_recording_playback.playByRecordingId(id);
            }
        }

        function dismissSaved() {
            _resetToIdle();
        }

        function startAnotherRecording() {
            const ctx = _getEffectiveLinkContext();
            beginSession({ ...ctx, openPanel: false });
            pickScreen();
        }

        function getDurationLabel() {
            const s = Math.floor(state.duration);
            const m = Math.floor(s / 60);
            const r = s % 60;
            return `${m}:${String(r).padStart(2, "0")}`;
        }

        return {
            bus,
            state,
            isEnabled,
            isSupported,
            isActive,
            beginSession,
            setFormLink,
            clearFormLink,
            setLinkToCurrentDocument,
            requestOpenPanel,
            pickScreen,
            startRecording,
            pauseRecording,
            resumeRecording,
            stopRecording,
            supportsPauseResume,
            discardPreview,
            changeScreen,
            cancelSession,
            setRecordingName,
            saveRecording,
            downloadLastSaved,
            downloadRecordingAttachment,
            viewLastSaved,
            dismissSaved,
            startAnotherRecording,
            attachLivePreview,
            attachPlaybackPreview,
            clearVideoElement,
            getDurationLabel,
        };
    },
};

registry.category("services").add("kx_video_recording", kxVideoRecordingService);
