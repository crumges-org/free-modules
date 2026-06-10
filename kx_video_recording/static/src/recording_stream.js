/** @odoo-module **/

async function getDisplayStream({ currentTabOnly, includeSystemAudio }) {
    if (currentTabOnly) {
        // Chromium: lock to this tab — small “Share this tab” prompt, not the full picker.
        const tabOnlyConstraints = {
            video: { frameRate: 30 },
            audio: includeSystemAudio,
            preferCurrentTab: true,
            selfBrowserSurface: "include",
            surfaceSwitching: "exclude",
        };
        try {
            return await navigator.mediaDevices.getDisplayMedia(tabOnlyConstraints);
        } catch (err) {
            try {
                return await navigator.mediaDevices.getDisplayMedia({
                    video: { frameRate: 30 },
                    audio: includeSystemAudio,
                    preferCurrentTab: true,
                    selfBrowserSurface: "include",
                });
            } catch {
                throw err;
            }
        }
    }
    return navigator.mediaDevices.getDisplayMedia({
        video: { frameRate: 30 },
        audio: includeSystemAudio,
    });
}

/**
 * Build display + optional mic/system audio stream for screen recording.
 * @param {{ includeMic: boolean, includeSystemAudio: boolean, currentTabOnly?: boolean, onMicDenied?: function }} options
 * @returns {Promise<{ mixedStream: MediaStream, displayStream: MediaStream, micStream: MediaStream|null, audioContext: AudioContext|null }>}
 */
export async function buildMixedRecordingStream(options) {
    const { includeMic, includeSystemAudio, currentTabOnly, onMicDenied } = options;

    const displayStream = await getDisplayStream({
        currentTabOnly: Boolean(currentTabOnly),
        includeSystemAudio,
    });
    const videoTracks = [...displayStream.getVideoTracks()];
    const systemAudioTracks = includeSystemAudio ? [...displayStream.getAudioTracks()] : [];

    if (!includeMic) {
        return {
            mixedStream: new MediaStream([...videoTracks, ...systemAudioTracks]),
            displayStream,
            micStream: null,
            audioContext: null,
        };
    }

    let micStream = null;
    try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
        onMicDenied?.();
        return {
            mixedStream: new MediaStream([...videoTracks, ...systemAudioTracks]),
            displayStream,
            micStream: null,
            audioContext: null,
        };
    }

    if (!systemAudioTracks.length) {
        return {
            mixedStream: new MediaStream([...videoTracks, ...micStream.getAudioTracks()]),
            displayStream,
            micStream,
            audioContext: null,
        };
    }

    const audioContext = new AudioContext();
    const destination = audioContext.createMediaStreamDestination();
    const systemSource = audioContext.createMediaStreamSource(new MediaStream(systemAudioTracks));
    systemSource.connect(destination);
    const micSource = audioContext.createMediaStreamSource(micStream);
    micSource.connect(destination);
    return {
        mixedStream: new MediaStream([...videoTracks, ...destination.stream.getAudioTracks()]),
        displayStream,
        micStream,
        audioContext,
    };
}

/** Resume Web Audio after a user gesture (required before MediaRecorder on mixed audio). */
export async function resumeRecordingAudioContext(audioContext) {
    if (!audioContext) {
        return;
    }
    if (audioContext.state === "suspended") {
        await audioContext.resume();
    }
}

/** Wait until capture tracks are live (avoids intermittent MediaRecorder.start failures). */
export async function waitForLiveTracks(stream, timeoutMs = 3000) {
    const tracks = stream.getTracks();
    if (!tracks.length) {
        throw new Error("No media tracks available for recording.");
    }
    const deadline = Date.now() + timeoutMs;
    for (const track of tracks) {
        if (track.readyState === "ended") {
            throw new Error("Screen sharing ended before recording could start.");
        }
        while (track.readyState !== "live" && track.readyState !== "ended") {
            if (Date.now() > deadline) {
                break;
            }
            await new Promise((resolve) => setTimeout(resolve, 50));
        }
        if (track.readyState === "ended") {
            throw new Error("Screen sharing ended before recording could start.");
        }
    }
}

/** Clone tracks so preview elements and MediaRecorder do not contend on the same track. */
export function cloneMediaStream(stream) {
    return new MediaStream(stream.getTracks().map((track) => track.clone()));
}

/**
 * Fallback when WebAudio-mixed stream cannot be recorded: display video + any audio from mixed.
 * @param {{ mixedStream: MediaStream, displayStream: MediaStream }} session
 */
export function buildFallbackRecordStream(session) {
    const videoTracks = session.displayStream.getVideoTracks();
    const audioTracks = session.mixedStream.getAudioTracks();
    return new MediaStream([...videoTracks, ...audioTracks]);
}

/** @param {{ mixedStream?: MediaStream, displayStream?: MediaStream, micStream?: MediaStream|null, audioContext?: AudioContext|null }} session */
export function stopRecordingStreamSession(session) {
    if (!session) {
        return;
    }
    for (const stream of [session.mixedStream, session.displayStream, session.micStream]) {
        stream?.getTracks().forEach((track) => track.stop());
    }
    session.audioContext?.close?.();
}

/** Stop tracks on a dedicated recording clone stream. */
export function stopRecordStream(recordStream) {
    recordStream?.getTracks().forEach((track) => track.stop());
}
