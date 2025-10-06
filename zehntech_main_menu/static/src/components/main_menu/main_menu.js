//import { useState, onMounted } from "@odoo/owl"; // Add this import at the top
import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { WidgetHour } from "@zehntech_main_menu/components/widget_hour/widget_hour";
import { WidgetAnnouncement } from "@zehntech_main_menu/components/widget_announcement/widget_announcement";
import { user } from "@web/core/user";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

class MenuAction extends Component {
  static components = { WidgetHour, WidgetAnnouncement };
  static props = { ...standardActionServiceProps };
  static template = "zehntech_main_menu.MainMenu";

  setup() {
    this.orm = useService("orm");
    this.menuService = useService("menu");
    const companyService = useService("company");
    this.currentCompanyId = companyService.currentCompany.id;
    //this.search = useState({ value: "" }); // <-- Live search state
    //this.theme = useState({ dark: false });
    this.apps = this.menuService
      .getApps()
      .filter((app) => app.xmlid != "zehntech_main_menu.main_menu_root")
      .sort((a, b) => a.name.localeCompare(b.name));
      
    this.deg = `${
      90 + (180 * Math.atan(window.innerHeight / window.innerWidth)) / Math.PI
    }deg`;

    onWillStart(async () => {
      try {
        this.userIsAdmin = await user.hasGroup("base.group_system");
        const res = await this.orm.searchRead(
          "res.company",
          [["id", "=", this.currentCompanyId]],
          ["announcement", "show_widgets"]
        );
        this.announcement = res[0].announcement;
        this.showWidgets = res[0].show_widgets;
      } catch (error) {
        console.error("Error loading data:", error);
      }
    });
    // 🌗 Apply theme class on mount
    // onMounted(() => {
    //   this.updateThemeClass();
    // });
  }

  // 🌗 Method to toggle theme
// toggleTheme() {
//     this.theme.dark = !this.theme.dark;
//     this.updateThemeClass();
// }

// 🌗 Add/remove theme class on <body>
// updateThemeClass() {
//     const body = document.body;
//     if (this.theme.dark) {
//         body.classList.add("dark-theme");
//         body.classList.remove("light-theme");
//     } else {
//         body.classList.remove("dark-theme");
//         body.classList.add("light-theme");
//     }
// }

  // 🔍 Add this method just below setup()
  // get filteredApps() {
  //   const searchValue = this.search.value.toLowerCase();
  //   return this.apps.filter((app) =>
  //     app.name.toLowerCase().includes(searchValue)
  //   );
  // }

  onClickModule(menu) {
    menu && this.menuService.selectMenu(menu);
  }

  onChangeAnnouncement(value) {
    this.announcement = value;
  }

  async onSaveAnnouncement() {
    try {
      await this.orm.write("res.company", [this.currentCompanyId], {
        announcement: this.announcement,
      });
    } catch (error) {
      console.error("Error saving data:", error);
    }
  }
}

registry
  .category("actions")
  .add("zehntech_main_menu.action_open_main_menu", MenuAction);
