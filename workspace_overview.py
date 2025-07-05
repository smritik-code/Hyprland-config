import gi
import subprocess
import json
import sys

# GTK setup
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, Gdk

class WorkspaceOverview:
    def __init__(self):
        self.current_workspace = self.get_current_workspace()
        if self.current_workspace is None:
            print("Error: Could not determine current workspace")
            sys.exit(1)

        self.keyboard_selected_workspace = self.current_workspace
        self.workspaces, self.clients = self.get_workspace_data()

        if not self.workspaces:
            print("Error: No workspaces found")
            sys.exit(1)

        self.workspace_apps = self.map_workspace_apps()
        self.cols = self.calculate_columns()
        self.frames = {}
        self.setup_window()
        self.populate_ui()

    def get_workspace_data(self):
        try:
            workspaces = json.loads(
                subprocess.check_output(["hyprctl", "workspaces", "-j"], stderr=subprocess.DEVNULL)
            )
            clients = json.loads(
                subprocess.check_output(["hyprctl", "clients", "-j"], stderr=subprocess.DEVNULL)
            )
            return workspaces, clients
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error getting workspace data: {e}")
            return [], []

    def get_current_workspace(self):
        try:
            output = subprocess.check_output(
                ["hyprctl", "activeworkspace", "-j"], stderr=subprocess.DEVNULL
            )
            data = json.loads(output)
            return data.get("id")
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            print(f"Error getting current workspace: {e}")
            return None

    def map_workspace_apps(self):
        apps = {ws["id"]: [] for ws in self.workspaces}
        for client in self.clients:
            wsid = client.get("workspace", {}).get("id")
            if wsid in apps:
                apps[wsid].append(client.get("class", ""))
        return apps

    def calculate_columns(self):
        count = len(self.workspaces)
        return min(max(2, int(count ** 0.5 + 0.5)), 4)

    def setup_window(self):
        self.window = Gtk.Window(title="Workspace Overview")
        self.window.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.window.set_keep_above(True)
        self.window.set_decorated(False)
        self.window.stick()
        self.window.fullscreen()

        screen = self.window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.window.set_visual(visual)

        css_provider = Gtk.CssProvider()
        css = """
            window {
                background: rgba(0, 0, 0, 0.7);
            }
            frame {
                border-radius: 10px;
                border: 1px solid alpha(@theme_fg_color, 0.3);
                background-color: alpha(@theme_bg_color, 0.5);
            }
            frame.current-workspace {
                border: 3px solid #87cefa;
                background-color: alpha(#87cefa, 0.1);
            }
            frame.keyboard-selected {
                border: 2px solid #729fcf;
            }
            label {
                color: #ffffff;
                font-weight: bold;
            }
            label.current-workspace-label {
                color: #87cefa;
            }
            label.keyboard-selected-label {
                color: #729fcf;
            }
        """
        css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.window.set_app_paintable(True)
        self.window.connect("destroy", Gtk.main_quit)
        self.window.connect("key-press-event", self.on_key_press)

    def populate_ui(self):
        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        outer_box.set_halign(Gtk.Align.CENTER)
        outer_box.set_valign(Gtk.Align.CENTER)

        grid = Gtk.Grid()
        grid.set_row_spacing(30)
        grid.set_column_spacing(30)
        grid.set_margin_top(50)
        grid.set_margin_bottom(50)
        grid.set_margin_start(50)
        grid.set_margin_end(50)

        for idx, ws in enumerate(sorted(self.workspaces, key=lambda x: x["id"])):
            frame = self.create_workspace_frame(ws)
            self.frames[ws["id"]] = frame
            grid.attach(frame, idx % self.cols, idx // self.cols, 1, 1)

        outer_box.pack_start(grid, False, False, 0)
        self.window.add(outer_box)
        self.update_highlighting()
        self.window.show_all()

    def create_workspace_frame(self, workspace):
        frame = Gtk.Frame()
        frame.set_size_request(300, 250)

        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.connect("clicked", self.on_workspace_click, workspace["id"])

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(15)
        box.set_margin_bottom(15)

        label = Gtk.Label(label=f"Workspace {workspace['id']}")
        box.pack_start(label, False, False, 0)

        apps_grid = Gtk.Grid()
        apps_grid.set_row_spacing(10)
        apps_grid.set_column_spacing(10)
        apps_grid.set_halign(Gtk.Align.CENTER)
        apps_grid.set_valign(Gtk.Align.CENTER)

        app_classes = self.workspace_apps.get(workspace["id"], [])
        for idx, app in enumerate(app_classes):
            icon = self.get_icon_pixbuf(app)
            if icon:
                img = Gtk.Image.new_from_pixbuf(icon)
                container = Gtk.Box()
                container.set_halign(Gtk.Align.CENTER)
                container.set_valign(Gtk.Align.CENTER)
                container.set_hexpand(True)
                container.set_vexpand(True)
                container.pack_start(img, True, True, 0)
                apps_grid.attach(container, idx % 3, idx // 3, 1, 1)
            else:
                lbl = Gtk.Label(label=app[:3] if app else "?")
                container = Gtk.Box()
                container.set_halign(Gtk.Align.CENTER)
                container.set_valign(Gtk.Align.CENTER)
                container.set_hexpand(True)
                container.set_vexpand(True)
                container.pack_start(lbl, True, True, 0)
                apps_grid.attach(container, idx % 3, idx // 3, 1, 1)



        box.pack_start(apps_grid, False, False, 0)
        btn.add(box)
        frame.add(btn)
        return frame

    def get_icon_pixbuf(self, app_name, size=64):
        try:
            icon_theme = Gtk.IconTheme.get_default()
            icon = icon_theme.lookup_icon(
                app_name.lower() if app_name else "application-x-executable",
                size,
                Gtk.IconLookupFlags.FORCE_SIZE,
            )
            return icon.load_icon()
        except Exception:
            return None

    def update_highlighting(self):
        for ws_id, frame in self.frames.items():
            btn = frame.get_child()
            box = btn.get_child()
            label = box.get_children()[0]

            ctx = frame.get_style_context()
            ctx.remove_class("current-workspace")
            ctx.remove_class("keyboard-selected")

            lbl_ctx = label.get_style_context()
            lbl_ctx.remove_class("current-workspace-label")
            lbl_ctx.remove_class("keyboard-selected-label")

            if ws_id == self.current_workspace:
                ctx.add_class("current-workspace")
                lbl_ctx.add_class("current-workspace-label")
            elif ws_id == self.keyboard_selected_workspace:
                ctx.add_class("keyboard-selected")
                lbl_ctx.add_class("keyboard-selected-label")

    def on_workspace_click(self, widget, ws_id):
        try:
            subprocess.run(
                ["hyprctl", "dispatch", "workspace", str(ws_id)], check=True, stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError as e:
            print(f"Failed to switch workspace: {e}")
        Gtk.main_quit()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
        elif event.keyval == Gdk.KEY_Return:
            self.switch_to_selected_workspace()
        elif event.keyval in (Gdk.KEY_Right, Gdk.KEY_Left, Gdk.KEY_Down, Gdk.KEY_Up):
            self.navigate_workspaces(event.keyval)

    def switch_to_selected_workspace(self):
        try:
            subprocess.run(
                ["hyprctl", "dispatch", "workspace", str(self.keyboard_selected_workspace)],
                check=True,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError as e:
            print(f"Failed to switch workspace: {e}")
        Gtk.main_quit()

    def navigate_workspaces(self, keyval):
        ids = sorted([ws["id"] for ws in self.workspaces])
        if not ids:
            return

        try:
            current_idx = ids.index(self.keyboard_selected_workspace)
        except ValueError:
            current_idx = 0

        if keyval == Gdk.KEY_Right:
            new_idx = (current_idx + 1) % len(ids)
        elif keyval == Gdk.KEY_Left:
            new_idx = (current_idx - 1) % len(ids)
        elif keyval == Gdk.KEY_Down:
            new_idx = min(current_idx + self.cols, len(ids) - 1)
        elif keyval == Gdk.KEY_Up:
            new_idx = max(current_idx - self.cols, 0)
        else:
            return

        self.keyboard_selected_workspace = ids[new_idx]
        self.update_highlighting()

if __name__ == "__main__":
    try:
        overview = WorkspaceOverview()
        Gtk.main()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
