/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { markEventHandled } from "@web/core/utils/misc";

import {
    deserializeDate,
    deserializeDateTime,
    formatDate,
} from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import {
    formatChar,
    formatFloat,
    formatInteger,
    formatMonetary,
    formatText,
} from "@web/views/fields/formatters";
import {localization} from "@web/core/l10n/localization";
import { patch } from "@web/core/utils/patch";
import * as DatesUtils from "@web/core/l10n/dates";
let {formatDateTime} = DatesUtils;
const {DateTime} = luxon;
const _formatDateTime = formatDateTime;
formatDateTime = (value, options = {}) => {
    if (options.isUTC) {
        if (!value) {
            return "";
        }
        value = value.toUTC();
        let convertedValue = DateTime.fromObject(value.toObject(), {
            setZone: true,
            zone: "utc",
        });
        const format = options.format || localization.dateTimeFormat;
        return convertedValue.setZone('utc').toFormat(format);
    }
    return _formatDateTime(value, options);
};


patch(Message.prototype, {
    formatTracking(trackingType, trackingValue) {
        switch (trackingType) {
            case "boolean":
                return trackingValue.value ? _t("Yes") : _t("No");
            /**
             * many2one formatter exists but is expecting id/display_name or data
             * object but only the target record name is known in this context.
             *
             * Selection formatter exists but requires knowing all
             * possibilities and they are not given in this context.
             */
            case "char":
            case "many2one":
            case "selection":
                return formatChar(trackingValue.value);
            case "date": {
                const value = trackingValue.value
                    ? deserializeDate(trackingValue.value)
                    : trackingValue.value;
                return formatDate(value);
            }
            case "datetime": {
                const value = trackingValue.value
                    ? deserializeDateTime(trackingValue.value)
                    : trackingValue.value;
                return formatDateTime(value, {'isUTC': trackingValue.isUtc || false});
            }
            case "float":
                return formatFloat(trackingValue.value);
            case "integer":
                return formatInteger(trackingValue.value);
            case "text":
                return formatText(trackingValue.value);
            case "monetary":
                return formatMonetary(trackingValue.value, {
                    currencyId: trackingValue.currencyId,
                });
            default:
                return trackingValue.value;
        }
    },
});
