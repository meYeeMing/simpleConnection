import tkinter as tk
from tkinter import ttk, messagebox
import ipaddress
import threading
import time

from core.config import config
from core.network_manager import NetworkManager
from ui.styles import configure_styles
from ui.loading_dialog import LoadingDialog

# Constant: display names for each connection profile key
PROFILE_DISPLAY_NAMES = {
    "router": "Router",
    "sim-card-router": "Sim Card Router",
    "dongle": "Dongle",
}


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Network Route & IP Configurator")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # Initialize configurations and managers
        self.config = config()
        self.net_mgr = NetworkManager()

        # Modern visual styling
        self.style = ttk.Style()
        self.style.theme_use("clam")
        configure_styles(self.root, self.style)

        # Main Layout: Sidebar & Content Area
        self.main_container = tk.Frame(self.root, bg="#f8f9fa")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.sidebar = tk.Frame(self.main_container, width=120, bg="#e9ecef")
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.content_area = tk.Frame(self.main_container, bg="#f8f9fa")
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Active view tracking
        self.current_frame = None

        # Draw sidebar navigation buttons
        self.build_sidebar()

        # Default to Main view
        self.show_main()

    def build_sidebar(self):
        # Sidebar Title
        title_label = tk.Label(
            self.sidebar,
            text=f"Router \n Configurator",
            fg="#0066cc",
            bg="#e9ecef",
            font=("Segoe UI", 12, "bold"),
        )
        title_label.pack(pady=20)

        # Buttons
        btn_main = ttk.Button(
            self.sidebar,
            text="Connection",
            style="Sidebar.TButton",
            command=self.show_main,
        )
        btn_main.pack(fill=tk.X, padx=10, pady=8)

        btn_settings = ttk.Button(
            self.sidebar,
            text="Settings",
            style="Sidebar.TButton",
            command=self.show_settings,
        )
        btn_settings.pack(fill=tk.X, padx=10, pady=8)
        creator_lbl = tk.Label(
            self.sidebar,
            text="Created by Simply",
            fg="#0e41b0",
            bg="#e9ecef",
            font=("Segoe UI", 8, "bold"),
        )
        creator_lbl.pack(side=tk.BOTTOM, pady=10)
        admin_lbl = tk.Label(
            self.sidebar,
            text="ADMIN PRIVILEGES",
            fg="#2b8a3e",
            bg="#e9ecef",
            font=("Segoe UI", 8, "bold"),
        )
        admin_lbl.pack(side=tk.BOTTOM, pady=10)

    def clear_content_area(self):
        if hasattr(self, "tree_adapters"):
            self.tree_adapters = None
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = ttk.Frame(self.content_area)
        self.current_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=25)

    # ==================== VIEW 1: MAIN (CONNECTION & MAPPINGS) ====================
    def show_main(self):
        self.clear_content_area()

        # Title
        header = ttk.Label(
            self.current_frame,
            text="Main: Connection Profiles & Mappings",
            style="Heading.TLabel",
        )
        header.pack(anchor=tk.W, pady=(0, 15))

        # Horizontal Row Container for Profile Selection and Details Panel
        profile_row = ttk.Frame(self.current_frame)
        profile_row.pack(fill=tk.X, pady=(0, 10))

        # 1. Select Connection Profile Frame (Left)
        profile_frame = ttk.LabelFrame(
            profile_row, text="1. Select Connection Profile", padding=15
        )
        profile_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Selection tracker for active profile (initially empty)
        self.selected_profile = tk.StringVar(value="")

        # Treeview to display connection profiles
        columns_prof = ("name", "gateway")
        self.tree_profiles = ttk.Treeview(
            profile_frame, columns=columns_prof, show="headings", height=4
        )
        self.tree_profiles.heading("name", text="Profile Name")
        self.tree_profiles.heading("gateway", text="Gateway IP")
        
        self.tree_profiles.column("name", width=200, anchor=tk.W, stretch=tk.NO)
        self.tree_profiles.column("gateway", width=120, anchor=tk.CENTER, stretch=tk.NO)
        
        # Scrollbar for profile list
        sb_profiles = ttk.Scrollbar(profile_frame, orient=tk.VERTICAL, command=self.tree_profiles.yview)
        self.tree_profiles.configure(yscrollcommand=sb_profiles.set)
        
        self.tree_profiles.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_profiles.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree_profiles.bind("<<TreeviewSelect>>", self.on_profile_select_tree)

        # Populating profiles treeview dynamically from config
        profiles = self.config.get_all() or {}
        if not profiles:
            self.tree_profiles.insert(
                "",
                tk.END,
                values=("No profiles found. Go to Settings to create one.", "")
            )
        else:
            for key, prof in profiles.items():
                if ":" in key:
                    gw, name = key.split(":", 1)
                else:
                    name = key
                    gw = prof.get("IpGateway", "")
                
                gw_display = gw if gw else "Auto (DHCP)"
                self.tree_profiles.insert(
                    "",
                    tk.END,
                    iid=key,
                    values=(name, gw_display)
                )

        # Connection Profile Info Panel (Right)
        self.info_frame = ttk.LabelFrame(
            profile_row, text="Connection Profile Info", padding=15
        )
        self.info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.lbl_info_title = ttk.Label(
            self.info_frame, text="Select a profile to view details...", font=("Segoe UI", 10, "italic")
        )
        self.lbl_info_title.pack(anchor=tk.W, pady=(0, 5))

        self.lbl_info_mode = ttk.Label(self.info_frame, text="")
        self.lbl_info_mode.pack(anchor=tk.W, pady=2)

        self.lbl_info_ip = ttk.Label(self.info_frame, text="")
        self.lbl_info_ip.pack(anchor=tk.W, pady=2)

        self.lbl_info_mask = ttk.Label(self.info_frame, text="")
        self.lbl_info_mask.pack(anchor=tk.W, pady=2)

        self.lbl_info_gateway = ttk.Label(self.info_frame, text="")
        self.lbl_info_gateway.pack(anchor=tk.W, pady=2)

        self.lbl_info_cidr = ttk.Label(self.info_frame, text="")
        self.lbl_info_cidr.pack(anchor=tk.W, pady=2)

        # 2. Adapter Mapping & Connection Section (dynamically shown/hidden)
        self.mapping_container_frame = ttk.Frame(self.current_frame)
        self.mapping_container_frame.pack(fill=tk.X, pady=5)

        self.mapping_placeholder = ttk.Label(
            self.mapping_container_frame,
            text="Select a profile above to configure its adapter mapping...",
            font=("Segoe UI", 10, "italic"),
            foreground="#868e96",
        )
        self.mapping_placeholder.pack(fill=tk.BOTH, expand=True, pady=10)

        # Create mapping_frame inside mapping_container_frame but don't pack it yet
        self.mapping_frame = ttk.LabelFrame(
            self.mapping_container_frame,
            text="2. Configure Adapter Mapping",
            padding=15,
        )

        self.lbl_selected_profile_name = ttk.Label(
            self.mapping_frame,
            text="Selected Profile: None",
            font=("Segoe UI", 11, "bold"),
            foreground="#0066cc",
        )
        self.lbl_selected_profile_name.pack(anchor=tk.W, pady=(0, 10))

        cbo_container = ttk.Frame(self.mapping_frame)
        cbo_container.pack(fill=tk.X, pady=5)

        ttk.Label(
            cbo_container, text="Map to Adapter:", font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.sys_adapters = []
        self.sys_adapters_names = [""]

        self.cbo_mapping = ttk.Combobox(
            cbo_container, values=self.sys_adapters_names, state="disabled", width=35
        )
        self.cbo_mapping.pack(side=tk.LEFT, padx=(0, 15))
        self.cbo_mapping.bind("<<ComboboxSelected>>", self.on_adapter_select)

        self.btn_apply = ttk.Button(
            cbo_container,
            text="Connect / Apply Settings",
            style="Action.TButton",
            command=self.apply_profile,
        )
        self.btn_apply.pack(side=tk.LEFT)

        # 3. Adapter Status Grid
        status_frame = ttk.LabelFrame(
            self.current_frame, text="Current Adapters IP Status", padding=15
        )
        status_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        columns = ("alias", "status", "ip", "gateway", "description")

        table_container = ttk.Frame(status_frame)
        table_container.pack(fill=tk.BOTH, expand=True)

        self.tree_adapters = ttk.Treeview(
            table_container, columns=columns, show="headings", height=5
        )
        self.tree_adapters.heading("alias", text="Adapter Name")
        self.tree_adapters.heading("status", text="Status")
        self.tree_adapters.heading("ip", text="IP Address")
        self.tree_adapters.heading("gateway", text="Gateway")
        self.tree_adapters.heading("description", text="Interface Description")

        self.tree_adapters.column("alias", width=120, anchor=tk.W)
        self.tree_adapters.column("status", width=90, anchor=tk.CENTER)
        self.tree_adapters.column("ip", width=120, anchor=tk.CENTER)
        self.tree_adapters.column("gateway", width=85, anchor=tk.CENTER)
        self.tree_adapters.column("description", width=250, anchor=tk.W)
        
        # Scrollbar for adapter table
        sb_adapters = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree_adapters.yview)
        self.tree_adapters.configure(yscrollcommand=sb_adapters.set)
        
        self.tree_adapters.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_adapters.pack(side=tk.RIGHT, fill=tk.Y)

        btn_refresh = ttk.Button(
            status_frame, text="Refresh Status", command=self.refresh_adapter_table
        )
        btn_refresh.pack(anchor=tk.E, pady=(10, 0))

        # Start loading data in the background
        self.refresh_adapter_table()

    def refresh_adapter_table(self):
        if not hasattr(self, "tree_adapters") or not self.tree_adapters or not self.tree_adapters.winfo_exists():
            return
        # Clear table and insert loading message
        for item in self.tree_adapters.get_children():
            self.tree_adapters.delete(item)
        self.tree_adapters.insert(
            "", tk.END, values=("Loading active adapters...", "", "", "", "")
        )

        def worker():
            adapters = self.net_mgr.get_adapters()
            self.root.after(0, lambda: self.populate_adapter_table(adapters))

        threading.Thread(target=worker, daemon=True).start()

    def populate_adapter_table(self, adapters):
        if not hasattr(self, "tree_adapters") or not self.tree_adapters or not self.tree_adapters.winfo_exists():
            return
        for item in self.tree_adapters.get_children():
            self.tree_adapters.delete(item)

        self.sys_adapters = adapters
        self.sys_adapters_names = [
            a.get("InterfaceAlias") for a in adapters if a.get("InterfaceAlias")
        ]
        self.sys_adapters_names.insert(0, "")

        # Enable and configure mapping combobox
        if hasattr(self, "cbo_mapping") and self.cbo_mapping and self.cbo_mapping.winfo_exists():
            self.cbo_mapping.config(state="readonly", values=self.sys_adapters_names)

        # Trigger profile refresh to load bindings
        self.on_profile_change()

        if not hasattr(self, "tree_adapters") or not self.tree_adapters or not self.tree_adapters.winfo_exists():
            return

        if not adapters:
            self.tree_adapters.insert(
                "", tk.END, values=("No adapters found on the system", "", "", "", "")
            )
            return

        for a in adapters:
            if not hasattr(self, "tree_adapters") or not self.tree_adapters or not self.tree_adapters.winfo_exists():
                return
            self.tree_adapters.insert(
                "",
                tk.END,
                values=(
                    a.get("InterfaceAlias") or "Unknown",
                    a.get("Status") or "Unknown",
                    a.get("IPv4Address") or "No IP Address",
                    a.get("IPv4DefaultGateway") or "None",
                    a.get("InterfaceDescription") or "",
                ),
            )

    def on_profile_select_tree(self, event=None):
        if not hasattr(self, "tree_profiles") or not self.tree_profiles or not self.tree_profiles.winfo_exists():
            return
        selected = self.tree_profiles.selection()
        if not selected:
            self.selected_profile.set("")
        else:
            self.selected_profile.set(selected[0])
        self.on_profile_change()

    def on_profile_change(self):
        if not hasattr(self, "lbl_info_title") or not self.lbl_info_title or not self.lbl_info_title.winfo_exists():
            return

        profile_key = self.selected_profile.get()
        if not profile_key:
            if hasattr(self, "mapping_frame") and self.mapping_frame.winfo_exists():
                self.mapping_frame.pack_forget()
            if hasattr(self, "mapping_placeholder") and self.mapping_placeholder.winfo_exists():
                self.mapping_placeholder.pack(fill=tk.BOTH, expand=True, pady=10)
            self.lbl_info_title.config(text="Select a profile to view details...", font=("Segoe UI", 10, "italic"))
            self.lbl_info_mode.config(text="")
            self.lbl_info_ip.config(text="")
            self.lbl_info_mask.config(text="")
            self.lbl_info_gateway.config(text="")
            self.lbl_info_cidr.config(text="")
            return

        # Hide placeholder
        if hasattr(self, "mapping_placeholder") and self.mapping_placeholder.winfo_exists():
            self.mapping_placeholder.pack_forget()

        # Get profile data
        profiles = self.config.get_all() or {}
        prof_data = profiles.get(profile_key)
        if not prof_data:
            return

        if ":" in profile_key:
            gw, name = profile_key.split(":", 1)
        else:
            name = profile_key
            gw = prof_data.get("IpGateway", "")

        # Update profile details on the right panel
        self.lbl_info_title.config(text=f"Profile: {name}", font=("Segoe UI", 11, "bold"))
        
        is_dhcp = prof_data.get("dhcp", False)
        if is_dhcp:
            self.lbl_info_mode.config(text="Mode: DHCP")
            self.lbl_info_ip.config(text="")
            self.lbl_info_mask.config(text="")
            self.lbl_info_gateway.config(text="")
            self.lbl_info_cidr.config(text="")
        else:
            self.lbl_info_mode.config(text="Mode: Static IP")
            ip = prof_data.get("Ip", "")
            mask = prof_data.get("mask", "")
            
            # Calculate CIDR
            try:
                interface = ipaddress.IPv4Interface(f"{ip}/{mask}")
                cidr = str(interface.network)
            except Exception:
                cidr = "Invalid IP/Mask"
            
            self.lbl_info_ip.config(text=f"IP Address: {ip}")
            self.lbl_info_mask.config(text=f"Subnet Mask: {mask}")
            self.lbl_info_gateway.config(text=f"Gateway: {gw}")
            self.lbl_info_cidr.config(text=f"Subnet CIDR: {cidr}")

        self.lbl_selected_profile_name.config(text=f"Selected Profile: {name}")

        # Set combobox value to currently saved binding
        bound_adapter = prof_data.get("AdapterName", "")
        if hasattr(self, "cbo_mapping") and self.cbo_mapping.winfo_exists():
            if bound_adapter in self.sys_adapters_names:
                self.cbo_mapping.set(bound_adapter)
            else:
                self.cbo_mapping.set("")

        # Pack the mapping frame
        if hasattr(self, "mapping_frame") and self.mapping_frame.winfo_exists():
            self.mapping_frame.pack(fill=tk.X, expand=True)

    def on_adapter_select(self, event=None):
        profile_key = self.selected_profile.get()
        if not profile_key:
            return
        selected_adapter = self.cbo_mapping.get()
        
        profiles = self.config.get_all() or {}
        if profile_key in profiles:
            profiles[profile_key]["AdapterName"] = selected_adapter
            self.config.save_config()

    def apply_profile(self):
        profile_key = self.selected_profile.get()
        if not profile_key:
            return

        profiles = self.config.get_all() or {}
        prof_data = profiles.get(profile_key)
        if not prof_data:
            return

        adapter_name = prof_data.get("AdapterName", "")
        if ":" in profile_key:
            _, profile_name = profile_key.split(":", 1)
        else:
            profile_name = profile_key

        if not adapter_name:
            messagebox.showerror(
                "Configuration Error",
                f"No network adapter is mapped to '{profile_name}'. Please select an adapter mapping from the dropdown.",
            )
            return

        subnets = prof_data.get("route-list") or []

        # Open loading modal
        loading = LoadingDialog(
            self.root,
            "Applying Settings",
            f"Applying profile '{profile_name}' on adapter '{adapter_name}'...\nThis may take a few seconds.",
        )

        def worker():
            success = False
            message = ""
            try:
                is_dhcp = prof_data.get("dhcp", False)
                if is_dhcp:
                    success, message = self.net_mgr.set_dhcp(adapter_name)
                    if success:
                        time.sleep(2)
                        success_route, msg_route = self.net_mgr.apply_routing(
                            adapter_name, subnets, None
                        )
                        message += f"\n{msg_route}"
                        if not success_route:
                            success = False
                else:
                    ip = prof_data.get("Ip", "")
                    gateway = prof_data.get("IpGateway", "")
                    mask = prof_data.get("mask", "")

                    success, message = self.net_mgr.set_static(
                        adapter_name, ip, gateway, mask
                    )
                    if success:
                        success_route, msg_route = self.net_mgr.apply_routing(
                            adapter_name, subnets, gateway
                        )
                        message += f"\n{msg_route}"
                        if not success_route:
                            success = False
            except Exception as e:
                success = False
                message = f"An exception occurred during apply: {str(e)}"

            # Post results back to the main thread
            self.root.after(
                0,
                lambda: self.on_apply_complete(
                    loading, profile_name, adapter_name, success, message
                ),
            )

        threading.Thread(target=worker, daemon=True).start()

    def on_apply_complete(
        self, loading_dialog, profile, adapter_name, success, message
    ):
        try:
            loading_dialog.grab_release()
            loading_dialog.destroy()
        except Exception:
            pass

        if success:
            messagebox.showinfo(
                "Success",
                f"Profile '{profile}' successfully applied on adapter '{adapter_name}'.\n{message}",
            )
        else:
            messagebox.showerror(
                "Error", f"Failed to apply profile '{profile}':\n{message}"
            )

        self.refresh_adapter_table()

    # ==================== VIEW 2: SETTINGS & ROUTE LIST ====================
    def show_settings(self):
        self.clear_content_area()

        # Header Profile Selector Frame
        selector_frame = ttk.Frame(self.current_frame)
        selector_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            selector_frame,
            text="Select Profile to Edit/Delete:",
            font=("Segoe UI", 10, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.cbo_profile_select = ttk.Combobox(
            selector_frame, state="readonly", width=35
        )
        self.cbo_profile_select.pack(side=tk.LEFT, padx=(0, 15))
        self.cbo_profile_select.bind("<<ComboboxSelected>>", self.on_profile_select_changed)

        btn_new = ttk.Button(
            selector_frame,
            text="New Profile",
            command=self.start_new_profile,
        )
        btn_new.pack(side=tk.LEFT)

        # Settings Container
        settings_container = ttk.Frame(self.current_frame)
        settings_container.pack(fill=tk.BOTH, expand=True)

        # Left Column: Profile Configuration
        self.left_editor_frame = ttk.LabelFrame(
            settings_container, text="Profile Configuration", padding=15
        )
        self.left_editor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Profile Name
        ttk.Label(self.left_editor_frame, text="Profile Name:").pack(anchor=tk.W, pady=(5, 2))
        self.ent_profile_name = ttk.Entry(self.left_editor_frame, font=("Segoe UI", 10))
        self.ent_profile_name.pack(fill=tk.X, pady=(0, 10))

        # Mode Selection
        mode_frame = ttk.Frame(self.left_editor_frame)
        mode_frame.pack(fill=tk.X, pady=(5, 10))

        self.router_mode = tk.StringVar(value="dhcp")

        ttk.Label(mode_frame, text="IP Assignment Mode:").pack(anchor=tk.W, pady=(0, 5))
        
        self.rad_static = ttk.Radiobutton(
            mode_frame,
            text="Static IP",
            variable=self.router_mode,
            value="static",
            command=self.on_router_mode_change,
        )
        self.rad_static.pack(side=tk.LEFT, padx=(0, 15))

        self.rad_dhcp = ttk.Radiobutton(
            mode_frame,
            text="DHCP",
            variable=self.router_mode,
            value="dhcp",
            command=self.on_router_mode_change,
        )
        self.rad_dhcp.pack(side=tk.LEFT)

        # IP Input fields
        self.lbl_ip = ttk.Label(self.left_editor_frame, text="Static IP Address:")
        self.lbl_ip.pack(anchor=tk.W, pady=(5, 2))
        self.ent_ip = ttk.Entry(self.left_editor_frame, font=("Segoe UI", 10))
        self.ent_ip.pack(fill=tk.X, pady=(0, 10))

        self.lbl_mask = ttk.Label(self.left_editor_frame, text="Subnet Mask:")
        self.lbl_mask.pack(anchor=tk.W, pady=(5, 2))
        self.ent_mask = ttk.Entry(self.left_editor_frame, font=("Segoe UI", 10))
        self.ent_mask.pack(fill=tk.X, pady=(0, 10))

        self.lbl_gateway = ttk.Label(self.left_editor_frame, text="Gateway:")
        self.lbl_gateway.pack(anchor=tk.W, pady=(5, 2))
        self.ent_gateway = ttk.Entry(self.left_editor_frame, font=("Segoe UI", 10))
        self.ent_gateway.pack(fill=tk.X, pady=(0, 10))

        # Mapped Adapter Selection
        ttk.Label(self.left_editor_frame, text="Mapped Adapter:").pack(anchor=tk.W, pady=(5, 2))
        adapters = getattr(self, "sys_adapters_names", [""])
        self.cbo_profile_adapter = ttk.Combobox(
            self.left_editor_frame, values=adapters, state="readonly", font=("Segoe UI", 10)
        )
        self.cbo_profile_adapter.pack(fill=tk.X, pady=(0, 15))

        # Right Column: Subnet list configuration
        route_frame = ttk.LabelFrame(
            settings_container, text="Target Subnets (Route List)", padding=15
        )
        route_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # Listbox
        list_container = ttk.Frame(route_frame)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.list_subnets = tk.Listbox(
            list_container,
            bg="#ffffff",
            fg="#212529",
            font=("Segoe UI", 10),
            selectbackground="#0066cc",
            selectforeground="#ffffff",
            borderwidth=1,
            highlightthickness=0,
        )
        # Scrollbar for subnet listbox
        sb_subnets = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.list_subnets.yview)
        self.list_subnets.configure(yscrollcommand=sb_subnets.set)
        
        self.list_subnets.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb_subnets.pack(side=tk.RIGHT, fill=tk.Y)

        # Input to add subnet
        add_sub_frame = ttk.Frame(route_frame)
        add_sub_frame.pack(fill=tk.X)

        self.ent_subnet = ttk.Entry(add_sub_frame, font=("Segoe UI", 10))
        self.ent_subnet.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        btn_add = ttk.Button(
            add_sub_frame,
            text="Add",
            style="Action.TButton",
            width=8,
            command=self.add_subnet,
        )
        btn_add.pack(side=tk.LEFT)

        btn_delete = ttk.Button(
            route_frame, text="Remove Selected Subnet", command=self.remove_subnet
        )
        btn_delete.pack(anchor=tk.W, pady=(10, 0))

        # Button row outside (below the two columns)
        btn_frame = ttk.Frame(self.current_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        self.btn_save_profile = ttk.Button(
            btn_frame,
            text="Save Profile",
            style="Action.TButton",
            command=self.save_profile_config,
        )
        self.btn_save_profile.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_delete_profile = ttk.Button(
            btn_frame,
            text="Delete Profile",
            command=self.delete_profile,
        )
        self.btn_delete_profile.pack(side=tk.LEFT)

        # Initialise Profile combobox and select first profile
        self.refresh_profile_combobox()

    def on_router_mode_change(self):
        mode = self.router_mode.get()
        if mode == "dhcp":
            self.ent_ip.config(state="disabled")
            self.ent_mask.config(state="disabled")
            self.ent_gateway.config(state="disabled")
        else:
            self.ent_ip.config(state="normal")
            self.ent_mask.config(state="normal")
            self.ent_gateway.config(state="normal")

    def on_profile_select_changed(self, event=None):
        selected_key = self.cbo_profile_select.get()
        self.load_profile_into_editor(selected_key)

    def start_new_profile(self):
        self.cbo_profile_select.set("")
        self.load_profile_into_editor(None)

    def refresh_profile_combobox(self, select_key=None):
        profiles = self.config.get_all() or {}
        profile_keys = list(profiles.keys())
        
        self.cbo_profile_select.config(values=profile_keys)
        
        if select_key and select_key in profile_keys:
            self.cbo_profile_select.set(select_key)
            self.load_profile_into_editor(select_key)
        elif profile_keys:
            self.cbo_profile_select.set(profile_keys[0])
            self.load_profile_into_editor(profile_keys[0])
        else:
            self.cbo_profile_select.set("")
            self.load_profile_into_editor(None)

    def load_profile_into_editor(self, profile_key):
        profiles = self.config.get_all() or {}
        prof_data = profiles.get(profile_key)
        
        self.ent_profile_name.config(state="normal")
        self.ent_profile_name.delete(0, tk.END)
        self.ent_gateway.config(state="normal")
        self.ent_gateway.delete(0, tk.END)
        self.ent_ip.config(state="normal")
        self.ent_ip.delete(0, tk.END)
        self.ent_mask.config(state="normal")
        self.ent_mask.delete(0, tk.END)
        
        if not prof_data:
            self.is_new_profile = True
            self.editing_profile_key = None
            self.ent_profile_name.insert(0, "")
            self.router_mode.set("dhcp")
            self.ent_gateway.insert(0, "")
            self.ent_ip.insert(0, "")
            self.ent_mask.insert(0, "255.255.255.0")
            self.cbo_profile_adapter.set("")
            self.btn_delete_profile.config(state="disabled")
            self.refresh_editor_subnet_list([])
            self.on_router_mode_change()
            return

        self.is_new_profile = False
        self.editing_profile_key = profile_key
        self.btn_delete_profile.config(state="normal")
        
        if ":" in profile_key:
            gw, name = profile_key.split(":", 1)
        else:
            name = profile_key
            gw = prof_data.get("IpGateway", "")

        self.ent_profile_name.insert(0, name)
        self.router_mode.set("dhcp" if prof_data.get("dhcp", False) else "static")
        self.ent_gateway.insert(0, gw)
        self.ent_ip.insert(0, prof_data.get("Ip", ""))
        self.ent_mask.insert(0, prof_data.get("mask", "255.255.255.0"))
        
        bound_adapter = prof_data.get("AdapterName", "")
        self.cbo_profile_adapter.set(bound_adapter)
        
        self.refresh_editor_subnet_list(prof_data.get("route-list") or [])
        self.on_router_mode_change()

    def refresh_editor_subnet_list(self, subnets):
        self.list_subnets.delete(0, tk.END)
        for s in subnets:
            self.list_subnets.insert(tk.END, s)

    def save_profile_config(self):
        name = self.ent_profile_name.get().strip()
        mode = self.router_mode.get()
        adapter = self.cbo_profile_adapter.get()
        
        if not name:
            messagebox.showerror("Validation Error", "Profile Name cannot be empty.")
            return
            
        if ":" in name:
            messagebox.showerror("Validation Error", "Profile Name cannot contain a colon (:).")
            return

        is_dhcp = (mode == "dhcp")
        ip = ""
        mask = ""
        gateway = ""

        if not is_dhcp:
            gateway = self.ent_gateway.get().strip()
            if not gateway:
                messagebox.showerror("Validation Error", "Gateway IP address is required for Static IP mode.")
                return

            try:
                ipaddress.ip_address(gateway)
            except ValueError:
                messagebox.showerror("Validation Error", "Invalid Gateway IP Address format.")
                return

            ip = self.ent_ip.get().strip()
            mask = self.ent_mask.get().strip()
            try:
                ipaddress.ip_address(ip)
                ipaddress.IPv4Interface(f"{ip}/{mask}")
            except ValueError:
                messagebox.showerror(
                    "Validation Error", "Invalid Static IP Address or Subnet Mask format."
                )
                return

        subnets = list(self.list_subnets.get(0, tk.END))

        if not is_dhcp:
            try:
                new_interface = ipaddress.IPv4Interface(f"{ip}/{mask}")
                new_cidr = str(new_interface.network)
                if new_cidr not in subnets:
                    subnets.append(new_cidr)
            except Exception:
                pass

        new_key = f"{gateway}:{name}" if gateway else name
        profiles = self.config.get_all()

        if self.is_new_profile and new_key in profiles:
            messagebox.showerror(
                "Validation Error", f"A profile with key '{new_key}' already exists."
            )
            return

        if not self.is_new_profile and self.editing_profile_key and self.editing_profile_key != new_key:
            self.config.delete(self.editing_profile_key)

        profiles[new_key] = {
            "AdapterName": adapter,
            "dhcp": is_dhcp,
            "Ip": ip,
            "mask": mask,
            "IpGateway": gateway,
            "route-list": subnets
        }
        self.config.save_config()

        messagebox.showinfo("Success", f"Profile '{name}' saved successfully!")
        self.refresh_profile_combobox(select_key=new_key)

    def delete_profile(self):
        if self.is_new_profile or not self.editing_profile_key:
            return

        profile_key = self.editing_profile_key
        if ":" in profile_key:
            _, name = profile_key.split(":", 1)
        else:
            name = profile_key

        confirm = messagebox.askyesno(
            "Confirm Delete", f"Are you sure you want to delete profile '{name}'?"
        )
        if not confirm:
            return

        self.config.delete(profile_key)
        messagebox.showinfo("Success", f"Profile '{name}' deleted.")
        self.refresh_profile_combobox()

    def add_subnet(self):
        new_sub = self.ent_subnet.get().strip()
        try:
            ipaddress.ip_network(new_sub, strict=False)
        except ValueError:
            messagebox.showerror(
                "Validation Error", "Invalid subnet CIDR format (e.g. 192.168.1.0/24)."
            )
            return

        existing = list(self.list_subnets.get(0, tk.END))
        if new_sub not in existing:
            self.list_subnets.insert(tk.END, new_sub)
            self.ent_subnet.delete(0, tk.END)
        else:
            messagebox.showwarning("Warning", "Subnet already exists in route-list.")

    def remove_subnet(self):
        selected = self.list_subnets.curselection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a subnet to remove.")
            return

        self.list_subnets.delete(selected[0])
