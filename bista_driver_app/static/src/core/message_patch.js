/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Message } from "@mail/core/common/message";


patch(Message.prototype, {
    setup() {
        super.setup();
        this.user = useService("user");

        onMounted(async () => {
            const hasSystemGroup = await this.user.hasGroup("base.group_system");

            if (!hasSystemGroup && this.props.message.model === "fleet.driver") {
                setTimeout(() => {
                    let root = this.el;

                    if (!root) {
                        const allMessages = document.querySelectorAll(".o-mail-Message-body ");
                        for (const msgEl of allMessages) {
                            const bodyHtml = msgEl.innerHTML;
                            if (bodyHtml.includes(`sms_link`) && bodyHtml.includes(this.props.message.body)) {
                                root = msgEl;
                                break;
                            }
                        }
                    }

                    if (root) {
                        const links = root.querySelectorAll("a.sms_link");
                        links.forEach((link) => {
                            link.addEventListener("click", (event) => {
                                event.preventDefault();
                                event.stopPropagation();
                            });
                            link.removeAttribute("href");
                            link.style.pointerEvents = "none";
                            link.style.textDecoration = "none";
                            link.style.cursor = "not-allowed";
                        });
                    }
                }, 50);
            }
        });
    }
});