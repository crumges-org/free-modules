/** @odoo-module **/

import { registry } from "@web/core/registry";
import { createFileViewer } from "@web/core/file_viewer/file_viewer_hook";

export const kxRecordingPlaybackService = {
    dependencies: ["orm", "mail.store"],
    start(env, { orm }) {
        const store = env.services["mail.store"];
        const fileViewer = createFileViewer();

        async function playByRecordingId(recordingId) {
            const data = await orm.call("kx.screen.recording", "get_playback_data", [[recordingId]]);
            if (!data?.attachment_id) {
                return;
            }
            const attachment = store.Attachment.insert({
                id: data.attachment_id,
                name: data.name,
                filename: data.name,
                mimetype: data.mimetype || "video/webm",
            });
            fileViewer.open(attachment);
        }

        return { playByRecordingId };
    },
};

registry.category("services").add("kx_recording_playback", kxRecordingPlaybackService);

export async function kxRecordingPlaybackAction(env, action) {
    const recordingId = action.params?.recording_id;
    if (recordingId) {
        await env.services.kx_recording_playback.playByRecordingId(recordingId);
    }
}

registry.category("actions").add("kx_recording_playback", kxRecordingPlaybackAction);
