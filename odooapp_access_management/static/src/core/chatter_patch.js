import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/chatter/web_portal/chatter";

/**
 * Per-part chatter restrictions (features G2-G6).
 *
 * Hiding the *whole* chatter (G1) happens on the server by dropping the
 * `<chatter/>` node from the arch, so it never reaches here. What is left are
 * the individual controls, which have no arch of their own.
 *
 * The template extension in chatter_patch.xml reads these getters. Posting is
 * blocked independently in `mail.thread.message_post`, so a user who re-enables
 * the button in devtools still cannot post.
 */
patch(Chatter.prototype, {
    get aamFlags() {
        const aam = this.env.services.aam_policy;
        if (!aam || aam.isUnrestricted) {
            return {};
        }
        const model = aam.chatterFor(this.props.threadModel);
        const flag = (name) => Boolean(aam.isGlobal(name) || model[name]);
        return {
            sendMessage: flag("hide_send_message"),
            logNote: flag("hide_log_note"),
            activity: flag("hide_activity"),
            followers: flag("hide_followers"),
            attachments: flag("hide_attachments"),
        };
    },
});
