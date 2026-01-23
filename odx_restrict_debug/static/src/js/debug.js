/** @odoo-module **/
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { Transition } from "@web/core/transition";
import { Component, useState } from "@odoo/owl";
import { LoadingIndicator } from "@web/webclient/loading_indicator/loading_indicator";
import { rpc } from "@web/core/network/rpc";

export class LoadingIndicatorDebug extends LoadingIndicator {
    setup() {
        this.uiService = useService("ui");
        this.state = useState({
            count: 0,
            show: false,
        });
        this.rpcIds = new Set();
        this.shouldUnblock = false;
        this.startShowTimer = null;
        this.blockUITimer = null;
        useBus(this.env.bus, "RPC:REQUEST", this.requestCall);
        useBus(this.env.bus, "RPC:RESPONSE", this.responseCall);
        if (odoo.debug){
            var hasGroup = rpc("/web/dataset/call_kw/res.users/has_group", {
                model: "res.users",
                method: "has_debug_group",
                args: [{}],
                kwargs: {},
            });
            hasGroup.then(function(DebugAdmin) {
            if (!DebugAdmin) {
        var newDiv = document.createElement('div');
        newDiv.classList.add('fixed-top', 'd-flex', 'justify-content-center', 'align-items-center', 'flex-column', 'vh-100');
        document.addEventListener('keydown', function() {
          if (event.keyCode == 16) {
                alert("This Operation is not Allowed, Please Contact Administrator");
                return false;
              } else if (event.ctrlKey && event.shiftKey) {
                alert("This function has been disabled to prevent you from stealing my code!");
                return false;
              }
          }, false);

        if (document.addEventListener) {
          document.addEventListener('contextmenu', function(e) {
            alert("This Operation is not Allowed, Please Contact Administrator");
            e.preventDefault();
          }, false);
        } else {
          document.attachEvent('oncontextmenu', function() {
            alert("This Operation is not Allowed, Please Contact Administrator");
            window.event.returnValue = false;
          });
        }
        //Set content inside the new div
        newDiv.textContent = 'You Are Not Allowed To Continue With Debug Mode Please Contact Administrator or Turn Off Debug';
        var turnOffDebugButton = document.createElement('button');
        turnOffDebugButton.textContent = 'Turn Off Debug Mode';
        turnOffDebugButton.style.marginTop = '10px';
        turnOffDebugButton.style.marginTop = '10px';
        turnOffDebugButton.style.padding = '8px 12px';
        //turnOffDebugButton.style.backgroundColor = '#c9aa42';
        turnOffDebugButton.style.backgroundColor = '#c9aa42';
        turnOffDebugButton.style.color = 'white';
        turnOffDebugButton.style.fontSize = '16px';
        turnOffDebugButton.style.fontWeight = 'bold';
        turnOffDebugButton.style.width = '810px';
        turnOffDebugButton.style.borderColor = '#c9aa42';

        // Add the button to the new div
        newDiv.appendChild(turnOffDebugButton);
        // Add styles to the new div
        newDiv.style.position = 'fixed';
        newDiv.style.top = '0';
        newDiv.style.left = '0';
        newDiv.style.width = '100%';
        newDiv.style.height = '100%';
        newDiv.style.position = 'fixed';
        newDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        newDiv.style.padding = '20px';
        newDiv.style.fontWeight = 'bold';
        newDiv.style.fontSize = '18px';
        // Append the new div to the blockUIElement
        var blockUIElement = document.querySelector('.o_blockUI');
        document.body.appendChild(newDiv);
        turnOffDebugButton.onclick = function() {
            // Get the current URL
            // Replace 'debug=1' with 'debug=0' in the URL
            // Update the URL in the address bar
            // Reload the page
            var currentURL = window.location.href;
            var newURL = currentURL
            if (currentURL.includes('debug=assets%2Ctests')) {
            newURL = currentURL.replace(/(\?|&)debug=assets%2Ctests(&|#|$)/, '$1debug=0$2');
            }
            else if (currentURL.includes('debug=assets')) {
            newURL = currentURL.replace(/(\?|&)debug=assets(&|#|$)/, '$1debug=0$2');
            }
            else if (currentURL.includes('debug=1')) {
            newURL = currentURL.replace(/(\?|&)debug=1(&|#|$)/, '$1debug=0$2');
            }
            else{
            newURL = currentURL.replace('/web#', '/web?debug=0#');
            }
            window.history.replaceState({}, document.title, newURL);
            location.reload();
        };
        alert("You Are Not Allowed To Continue With Debug Mode Please Contact Administrator or Turn Off Debug");
        //Logout
        var LogoutUrl = window.location.origin + "/web/session/logout?debug=0"
        window.history.replaceState({}, document.title, LogoutUrl);
        location.reload();
        }
            });
        }
    }
}

registry.category("main_components").add("LoadingIndicatorDebug", {
    Component: LoadingIndicatorDebug,
});

