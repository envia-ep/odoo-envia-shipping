/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { useEffect } from "@odoo/owl";

const ENVIA_POPUP_WINDOW_NAME = "envia_oauth_connect";
const POPUP_WIDTH = 320;
const POPUP_HEIGHT = 260;
const CALLBACK_POLL_INTERVAL_MS = 2000;

export class EnviaPluginConnectWizardController extends FormController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");
        this._callbackPollInterval = null;
        this._integrationUrlOpened = false;

        useEffect(
            () => {
                const record = this.model.root;
                if (record.data.state === "waiting_external") {
                    this._startWaitingExternalFlow(record);
                } else {
                    this._stopWaitingExternalFlow();
                }
                return () => this._stopWaitingExternalFlow();
            },
            () => [this.model.root.data.state, this.model.root.data.external_popup_url]
        );
    }

    async beforeExecuteActionButton(clickParams) {
        if (
            clickParams.name === "action_run_integration" ||
            clickParams.name === "action_open_envia_integration"
        ) {
            this._openEnviaIntegrationFromRecord();
        }
        return super.beforeExecuteActionButton(clickParams);
    }

    async onWillStart() {
        await super.onWillStart();
        const record = this.model.root;
        if (!record.resId || record.data.state !== "ready") {
            return;
        }
        const nextAction = await this.orm.call(
            "envia.plugin.connect.wizard",
            "action_redirect_if_configured",
            [[record.resId]]
        );
        if (nextAction && nextAction.type) {
            await this.actionService.doAction(nextAction);
        }
    }

    _startWaitingExternalFlow(record) {
        if (!this._integrationUrlOpened && record.data.external_popup_url) {
            this._openEnviaIntegrationFromRecord();
        }
        if (!this._integrationUrlOpened) {
            this._notifyEnviaNotOpened();
        }
        this._startCallbackPolling(record.resId);
    }

    _stopWaitingExternalFlow() {
        if (this._callbackPollInterval) {
            clearInterval(this._callbackPollInterval);
            this._callbackPollInterval = null;
        }
    }

    _buildPopupFeatures() {
        const left = Math.max(0, Math.round((window.screen.width - POPUP_WIDTH) / 2));
        const top = Math.max(0, Math.round((window.screen.height - POPUP_HEIGHT) / 2));
        return [
            `width=${POPUP_WIDTH}`,
            `height=${POPUP_HEIGHT}`,
            `left=${left}`,
            `top=${top}`,
            "resizable=yes",
            "scrollbars=yes",
            "toolbar=no",
            "menubar=no",
        ].join(",");
    }

    _notifyEnviaNotOpened() {
        const useSizedPopup = this.model.root.data.integration_use_sized_popup;
        this.notification.add(
            useSizedPopup
                ? _t(
                      "Envia.com did not open. Click Open Envia.com below or allow pop-ups for this site."
                  )
                : _t("Envia.com did not open. Click Open Envia.com below."),
            { type: "warning", sticky: true }
        );
    }

    _openEnviaIntegrationFromRecord() {
        const record = this.model.root;
        const url = record.data.external_popup_url;
        if (!url) {
            return;
        }
        if (record.data.integration_use_sized_popup) {
            this._openSizedPopup(url);
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_url",
            url,
            target: "new",
        });
        this._integrationUrlOpened = true;
    }

    _openSizedPopup(url) {
        const popup = window.open(url, ENVIA_POPUP_WINDOW_NAME, this._buildPopupFeatures());
        if (!popup) {
            this._notifyEnviaNotOpened();
            return;
        }
        this._integrationUrlOpened = true;
    }

    _startCallbackPolling(wizardId) {
        if (this._callbackPollInterval) {
            return;
        }
        this._callbackPollInterval = setInterval(async () => {
            const nextAction = await this.orm.call(
                "envia.plugin.connect.wizard",
                "action_poll_integration_status",
                [[wizardId]]
            );
            if (nextAction && nextAction.type) {
                this._stopWaitingExternalFlow();
                await this.actionService.doAction(nextAction);
            }
        }, CALLBACK_POLL_INTERVAL_MS);
    }
}

export const enviaPluginConnectWizardFormView = {
    ...formView,
    Controller: EnviaPluginConnectWizardController,
};

registry.category("views").add("envia_plugin_connect_wizard_form", enviaPluginConnectWizardFormView);
