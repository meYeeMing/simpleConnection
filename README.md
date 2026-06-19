# simple Connection

A Windows desktop tool for managing network adapter IP configuration and static routing profiles. Designed for environments where a single machine connects to multiple networks (e.g. a direct-wired router, a SIM card router, and a USB dongle) and needs to quickly switch between them with the correct IP settings and subnet routes.

---

## Purpose

When connecting to various network devices, it's common to need different adapter configurations:

- A **static IP** address to directly connect to a router's management interface
- **DHCP** assignment for plug-and-play devices like SIM card routers or USB dongles
- Specific **static routes** to ensure traffic for target subnets goes through the right adapter rather than the default internet gateway

SimpleConnection automates all of this with a single click.

---

## Features

- **Connection Profiles** — Switch between different profiles (e.g. Direct-wired, USB 4G modem, SIM card router)
- **Static IP Configuration** — Set IP address, subnet mask, and gateway for static profiles
- **DHCP Support** — Switch profiles to DHCP mode, disabling and greying out static fields automatically
- **Route Management** — Configure target subnets that route through the selected adapter at high priority, while preserving your main internet connection
- **Adapter Binding** — Map each profile to a specific physical network adapter and save the binding persistently
- **Live Adapter Status** — View all detected adapters with their current IP addresses and gateways in a live-refreshing table
- **Subnet CIDR Calculation** — Automatically derives the subnet CIDR from the IP and mask, and keeps the route-list in sync
---

## Project Structure

```
simpleConnection/
├── main.py                  # Entrypoint — requests admin privileges, launches App
├── get_route.py             # RouteService: reads system routing table
├── requirements.txt         # Python dependencies
├── build_win.py             # PyInstaller build script → dist_win/SimpleConnection/
├── config.yaml              # Persistent user configuration
├── README.md                # README
│
├── core/
│   ├── config.py            # Singleton config loader/saver 
│   ├── network_manager.py   # PowerShell-based adapter and route management
│   └── utils.py             # is_admin(), elevate_privileges() helpers
│
└── ui/
    ├── app.py               # Main App class — all views and UI logic
    ├── loading_dialog.py    # LoadingDialog — modal spinner shown during apply
    ├── styles.py            # TTK style configuration loader
    └── style_config.json    # Color and font tokens used by styles.py
```

---

## Configuration (`config.yaml`)

The configuration file (`config.yaml` located in the root folder or next to the executable) stores all connection profiles and is automatically updated on every change.

```yaml
192.168.1.1:direct-wired:
  AdapterName: Ethernet
  Ip: 192.168.1.99
  IpGateway: 192.168.1.1
  dhcp: false
  mask: 255.255.255.0
  route-list:
  - 192.168.0.0/24
  - 10.10.10.0/23

auto:
  AdapterName: Ethernet 2
  Ip: ''
  IpGateway: ''
  dhcp: true
  mask: ''
  route-list:

```

> **Note:** When you change the static IP or subnet mask in Settings, the corresponding subnet CIDR in `route-list` is automatically recalculated and updated.

---

## User Guide

Follow these steps to configure and connect profiles using the tool:

### 1. Launch the Application
* Run `RouteConfigurator.exe` or execute `python main.py` as Administrator.
* A User Account Control (UAC) prompt will appear requesting administrator privileges. Click **Yes** (required to modify system network configurations).

### 2. Configure Connection Profiles (Settings)
* Click **Settings** on the sidebar.
* **Select or Create a Profile:**
  * To edit an existing profile, select it from the dropdown.
  * To create a new profile, click the **New Profile** button, then enter a name in the **Profile Name** field (names cannot contain colons `:`).
* **Choose IP Assignment Mode:**
  * **Static IP:** Select "Static IP". The entry fields will enable. Enter your **Static IP Address**, **Subnet Mask**, and **Gateway**.
  * **DHCP:** Select "DHCP". The static fields will automatically disable and turn grey, indicating that the IP and gateway will be fetched dynamically from the router.
* **Map to a Physical Adapter:**
  * Select your target network adapter (e.g. `Ethernet` or `Ethernet 2`) from the **Mapped Adapter** dropdown list.
* **Manage Target Subnets (Route List):**
  * Enter subnets in CIDR format (e.g. `10.10.30.0/24` or `192.186.82.0/23`) into the entry field next to the **Add** button.
  * Click **Add** to include the subnet in the list.
  * To delete a subnet, select it from the listbox and click **Remove Selected Subnet**.
* **Save/Delete Changes:**
  * Click the **Save Profile** button at the bottom to save your settings to `config.yaml`.
  * Click **Delete Profile** to permanently remove the profile.

### 3. Connect and Apply Settings (Connection)
* Click **Connection** on the sidebar.
* Select your target connection profile from the **1. Select Connection Profile** table.
* **Review Profile Info:** The right-hand panel displays the profile configurations (Static IP, Subnet Mask, Gateway, CIDR, Mode; gateway is hidden in DHCP mode).
* **Confirm Adapter Mapping:**
  * If the profile has an adapter mapped, the dropdown in **2. Configure Adapter Mapping** will show the bound adapter.
  * If not, select a physical adapter from the dropdown list. Choosing an adapter saves the binding persistently.
* **Apply Settings:**
  * Click **Connect / Apply Settings**.
  * A loading dialog will appear while the configurations and routes are being updated (for DHCP mode, this includes waiting up to 10 seconds for address lease assignment).
  * A success or error notification will be shown upon completion.
* **Verify Adapter Status:**
  * Review the **Current Adapters IP Status** table at the bottom to confirm that your network interface alias, status, IPv4 address, and gateway are updated correctly. Click **Refresh Status** to refresh the list at any time.

---

## How Routing Works

When you click **Connect / Apply Settings**, the tool:

1. Configures the selected adapter with the right IP settings (static or DHCP).
2. For DHCP profiles, automatically waits (polls for up to 10 seconds) for the DHCP client to negotiate and receive its IP address and default gateway from the router.
3. Queries active and persistent routes globally and cleans up mismatching/obsolete static and persistent routes (e.g. routes pointing to an old gateway).
4. Adds target subnet routes to **both** the active routing table and the **persistent store** (`-PolicyStore PersistentStore`) via the adapter's gateway with metric 5.
5. Dynamically manages the **Interface Metric**:
   - If the profile's route list does **not** contain the default route (`0.0.0.0/0`), it sets the adapter's interface metric to **`1200`** and deletes its default gateway route. This ensures your primary internet connection (like Wi-Fi) is preferred and not disrupted.
   - If the profile explicitly contains `0.0.0.0/0`, the interface metric is set to a low value (**`10`**) to prioritize this adapter's default route.

---

## Prerequisites

- **Windows 10/11** (uses PowerShell `New-NetIPAddress`, `New-NetRoute`, etc.)
- **Python 3.10+** (for development/source use)
- **Administrator privileges** (the app auto-elevates via UAC on launch)

---

## Development Setup

```powershell
# Clone the repo
git clone https://github.com/h1234a/simpleConnection.git
cd simpleConnection

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run directly (will prompt for UAC elevation)
python main.py
```

---

## Building a Standalone Executable

The `build_win.py` script compiles the app to a self-contained `dist_win/SimpleConnection/` directory using PyInstaller:

```powershell
python build_win.py
```

The output directory `dist_win/SimpleConnection/` (or the standalone single-file `dist_win/SimpleConnection.exe` if built with `--onefile`) can be deployed as-is. The `config.yaml` file next to the executable is user-editable and persists settings across runs.

> **Important:** Close the application before running a new build, otherwise PyInstaller may fail with a permission error on the existing executable.

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `pyyaml` | 6.0.3 | Reading and writing `config.yaml` |
| `pyinstaller` | 6.21.0 | Building the standalone Windows executable |

The GUI is built with Python's built-in `tkinter` — no additional UI framework is needed.

---

## Technical Notes

- **PowerShell for configuration**: The app uses native PowerShell cmdlets (`Set-NetIPInterface`, `New-NetIPAddress`, `New-NetRoute`) to configure interfaces and routing, making it idempotent and locale-independent.
- **Persistent Routing**: Subnet routes are added to both the active routing table and the Windows registry's `PersistentStore`, meaning they persist across adapter disconnects, lease renewals, and reboots.
- **Dynamic Metrics**: The adapter's `InterfaceMetric` is dynamically configured to prevent secondary DHCP adapter default gateways from hijacking the primary internet connection.
- **Thread safety**: Adapter enumeration and profile apply operations run in background threads. All UI updates are dispatched back to the main thread via `root.after(0, ...)`.
- **Config persistence**: `core/config.py` is a singleton. Every `config.set()` call immediately writes the full config to `config.yaml` in the root/executable directory.
