/** @odoo-module */

import { registry } from "@web/core/registry";
import {
    KanbanMany2ManyTagsAvatarUserField,
    kanbanMany2ManyTagsAvatarUserField,
    KanbanMany2ManyAvatarUserTagsList,
} from "@mail/views/web/fields/many2many_avatar_user_field/many2many_avatar_user_field";

export class ProjectKanbanProAvatarTagsList extends KanbanMany2ManyAvatarUserTagsList {
    static template = "project_kanban_pro.ProjectKanbanProAvatarTagsList";
}

export class ProjectKanbanProAvatarField extends KanbanMany2ManyTagsAvatarUserField {
    static template = "project_kanban_pro.ProjectKanbanProAvatarField";
    static components = {
        ...KanbanMany2ManyTagsAvatarUserField.components,
        TagsList: ProjectKanbanProAvatarTagsList,
    };

    getTagProps(record) {
        const props = super.getTagProps(...arguments);
        const workloadMap = this.props.record.data.user_workload_data || {};
        const workloadCount = workloadMap[String(record.resId)] || 0;
        props.workloadCount = workloadCount;
        props.workloadClass =
            workloadCount >= 8 ? "high" : workloadCount >= 4 ? "medium" : "low";
        props.onImageClicked = (ev) => {
            ev.stopPropagation();
            ev.preventDefault();
            this.env.searchModel.toggleAssigneeFilter(
                record.resId,
                record.data.display_name || record.data.name
            );
        };
        return props;
    }
}

export const projectKanbanProAvatarField = {
    ...kanbanMany2ManyTagsAvatarUserField,
    component: ProjectKanbanProAvatarField,
    additionalClasses: [
        "o_field_many2many_tags_avatar",
        "o_field_many2many_tags_avatar_kanban",
        "o_pkp_avatar_field",
    ],
};

registry.category("fields").add("project_kanban_pro_many2many_avatar_user", projectKanbanProAvatarField);
