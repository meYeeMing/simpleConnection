import json
import sys
import subprocess
import ipaddress
import time

class NetworkManager:
    def __init__(self):
        self.creationflags = 0
        if sys.platform == "win32":
            self.creationflags = 0x08000000

    def get_adapters(self) -> list[dict]:
        """
        Retrieves physical network adapters (excluding Wi-Fi and Bluetooth)
        along with their active IPv4 addresses and gateways.
        Uses fast, robust primitive cmdlets.
        """
        # 1. Get physical adapters
        adapters_cmd = [
            "powershell", "-Command",
            "Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, InterfaceIndex | ConvertTo-Json -Compress"
        ]
        
        # 2. Get IP addresses
        ips_cmd = [
            "powershell", "-Command",
            "Get-NetIPAddress -AddressFamily IPv4 | Select-Object InterfaceIndex, IPAddress | ConvertTo-Json -Compress"
        ]
        
        # 3. Get gateways
        routes_cmd = [
            "powershell", "-Command",
            "Get-NetRoute -DestinationPrefix 0.0.0.0/0 -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object InterfaceAlias, NextHop | ConvertTo-Json -Compress"
        ]

        adapters_list = []
        ips_map = {}
        routes_map = {}

        try:
            res_adapters = subprocess.run(adapters_cmd, capture_output=True, text=True, creationflags=self.creationflags)
            if res_adapters.returncode == 0 and res_adapters.stdout.strip():
                data = json.loads(res_adapters.stdout.strip())
                adapters_list = [data] if isinstance(data, dict) else data

            res_ips = subprocess.run(ips_cmd, capture_output=True, text=True, creationflags=self.creationflags)
            if res_ips.returncode == 0 and res_ips.stdout.strip():
                data = json.loads(res_ips.stdout.strip())
                ips = [data] if isinstance(data, dict) else data
                for ip_info in ips:
                    idx = ip_info.get("InterfaceIndex")
                    addr = ip_info.get("IPAddress")
                    if addr != "127.0.0.1":
                        ips_map[idx] = addr

            res_routes = subprocess.run(routes_cmd, capture_output=True, text=True, creationflags=self.creationflags)
            if res_routes.returncode == 0 and res_routes.stdout.strip():
                data = json.loads(res_routes.stdout.strip())
                routes = [data] if isinstance(data, dict) else data
                for r in routes:
                    alias = r.get("InterfaceAlias")
                    hop = r.get("NextHop")
                    routes_map[alias] = hop
        except Exception as e:
            print(f"Error executing adapter commands: {e}", file=sys.stderr)

        merged_adapters = []
        for a in adapters_list:
            name = a.get("Name")
            desc = a.get("InterfaceDescription", "")
            status = a.get("Status", "Disconnected")
            idx = a.get("InterfaceIndex")

            name_lower = name.lower() if name else ""
            desc_lower = desc.lower() if desc else ""
            if "wi-fi" in name_lower or "wifi" in name_lower or "wireless" in name_lower or "wi-fi" in desc_lower or "wifi" in desc_lower or "wireless" in desc_lower:
                continue
            if "bluetooth" in name_lower or "bluetooth" in desc_lower:
                continue

            ip = ips_map.get(idx)
            if not ip:
                ip = "No IP Address"

            gateway = routes_map.get(name)
            if not gateway or gateway == "0.0.0.0":
                gateway = "None"

            merged_adapters.append({
                "InterfaceAlias": name,
                "InterfaceIndex": idx,
                "InterfaceDescription": desc,
                "IPv4Address": ip,
                "IPv4DefaultGateway": gateway,
                "Status": status
            })

        return merged_adapters

    def set_dhcp(self, adapter_name: str) -> tuple[bool, str]:
        """
        Enables DHCP for both IP configuration and DNS on the specified adapter.
        """
        try:
            ps_cmd = [
                "powershell", "-Command",
                f"Remove-NetIPAddress -InterfaceAlias '{adapter_name}' -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue; "
                f"Remove-NetRoute -InterfaceAlias '{adapter_name}' -DestinationPrefix '0.0.0.0/0' -Confirm:$false -ErrorAction SilentlyContinue; "
                f"Remove-NetRoute -InterfaceAlias '{adapter_name}' -DestinationPrefix '0.0.0.0/0' -PolicyStore PersistentStore -Confirm:$false -ErrorAction SilentlyContinue; "
                f"Set-NetIPInterface -InterfaceAlias '{adapter_name}' -Dhcp Enabled -ErrorAction Stop; "
                f"Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -ResetServerAddresses -ErrorAction Stop"
            ]
            res = subprocess.run(ps_cmd, capture_output=True, text=True, creationflags=self.creationflags)
            if res.returncode != 0:
                return False, f"Failed to set DHCP: {res.stderr.strip()}"
            return True, "DHCP enabled successfully."
        except Exception as e:
            return False, f"Exception setting DHCP: {str(e)}"

    def set_static(self, adapter_name: str, ip: str, gateway: str, mask: str = "255.255.255.0") -> tuple[bool, str]:
        """
        Configures static IP, subnet mask, and gateway on the specified adapter using PowerShell.
        """
        try:
            # Convert subnet mask to prefix length
            prefix_len = ipaddress.IPv4Network(f"0.0.0.0/{mask}").prefixlen
        except Exception:
            prefix_len = 24

        try:
            # Validate gateway is a proper IP before injecting into PowerShell
            if gateway:
                ipaddress.ip_address(gateway)  # raises ValueError if invalid
            # Build PowerShell command — Remove existing IPs and default routes, then set the new static address
            gw_param = f"-DefaultGateway '{gateway}'" if gateway else ""
            ps_cmd = [
                "powershell", "-Command",
                f"Remove-NetIPAddress -InterfaceAlias '{adapter_name}' -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue; "
                f"Remove-NetRoute -InterfaceAlias '{adapter_name}' -DestinationPrefix '0.0.0.0/0' -Confirm:$false -ErrorAction SilentlyContinue; "
                f"Remove-NetRoute -InterfaceAlias '{adapter_name}' -DestinationPrefix '0.0.0.0/0' -PolicyStore PersistentStore -Confirm:$false -ErrorAction SilentlyContinue; "
                f"New-NetIPAddress -InterfaceAlias '{adapter_name}' -IPAddress '{ip}' -PrefixLength {prefix_len} {gw_param} -ErrorAction Stop"
            ]
            res = subprocess.run(ps_cmd, capture_output=True, text=True, creationflags=self.creationflags)
            if res.returncode != 0:
                return False, f"Failed to set static IP: {res.stderr.strip()}"
            return True, "Static IP configured successfully."
        except ValueError as e:
            return False, f"Invalid gateway IP address: {e}"
        except Exception as e:
            return False, f"Exception setting static IP: {str(e)}"

    def get_wifi_metric(self) -> int:
        """
        Returns the interface metric of the Wi-Fi interface, or 1000 if not found.
        """
        cmd = [
            "powershell",
            "-Command",
            "Get-NetIPInterface -InterfaceAlias *WiFi* -AddressFamily IPv4 | Select-Object -ExpandProperty InterfaceMetric"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=self.creationflags)
            if res.returncode == 0 and res.stdout.strip():
                return int(res.stdout.strip().splitlines()[0])
        except Exception:
            pass
        return 1000

    def apply_routing(self, selected_adapter: str, subnets: list[str], configured_gateway: str = None) -> tuple[bool, str]:
        """
        Clears existing static routes for the given subnets and re-adds them
        pointing to the selected adapter with a high priority (low metric, e.g. 5).
        """
        try:
            # 1. Discover the gateway for the selected adapter.
            # If DHCP is used, wait up to 10 seconds for the adapter to receive its IP and gateway.
            gateway = configured_gateway
            gateway_inferred = False
            if not gateway:
                for _ in range(10):
                    adapters = self.get_adapters()
                    for a in adapters:
                        if a["InterfaceAlias"] == selected_adapter:
                            ip = a["IPv4Address"]
                            g = a["IPv4DefaultGateway"]
                            # Only accept a gateway if we have a valid, non-APIPA IP and a default gateway
                            if ip and ip != "No IP Address" and not ip.startswith("169.254."):
                                if g and g != "0.0.0.0" and g != "None":
                                    gateway = g
                                    break
                    if gateway:
                        break
                    time.sleep(1)

                # Fallback: if we still don't have a gateway but have a valid IP, infer gateway as x.y.z.1
                if not gateway:
                    adapters = self.get_adapters()
                    for a in adapters:
                        if a["InterfaceAlias"] == selected_adapter:
                            ip = a["IPv4Address"]
                            if ip and ip != "No IP Address" and not ip.startswith("169.254."):
                                parts = ip.split('.')
                                if len(parts) == 4:
                                    gateway = f"{parts[0]}.{parts[1]}.{parts[2]}.1"
                                    gateway_inferred = True
                                    break

            # 2. Get all managed subnets across all configured profiles to clean up old routes
            all_managed_subnets = set()
            try:
                from core.config import config
                conf = config()
                profiles = conf.get_all() or {}
                for prof_data in profiles.values():
                    for s in (prof_data.get("route-list") or []):
                        if s:
                            all_managed_subnets.add(s.strip())
            except Exception as e:
                print(f"Error loading managed subnets for cleanup: {e}")

            # Also ensure all subnets currently being applied are in the managed set
            for s in subnets:
                all_managed_subnets.add(s.strip())

            # 3. Helper to compare gateways
            def gateways_equal(gw1, gw2):
                g1 = (gw1 or "").strip().lower()
                g2 = (gw2 or "").strip().lower()
                if g1 in ("", "0.0.0.0", "none", "on-link"):
                    g1 = ""
                if g2 in ("", "0.0.0.0", "none", "on-link"):
                    g2 = ""
                return g1 == g2

            # 4. Query global persistent routes to find mismatching gateways or obsolete subnets
            persistent_routes = []
            cmd_pers = [
                "powershell", "-Command",
                "Get-NetRoute -PolicyStore PersistentStore -ErrorAction SilentlyContinue | Select-Object DestinationPrefix, NextHop | ConvertTo-Json -Compress"
            ]
            res_pers = subprocess.run(cmd_pers, capture_output=True, text=True, creationflags=self.creationflags)
            if res_pers.returncode == 0 and res_pers.stdout.strip():
                try:
                    data = json.loads(res_pers.stdout.strip())
                    persistent_routes = [data] if isinstance(data, dict) else data
                except Exception:
                    pass

            # 5. Query active manual static routes
            active_routes = []
            cmd_act = [
                "powershell", "-Command",
                "Get-NetRoute -Protocol Netmgmt -ErrorAction SilentlyContinue | Select-Object DestinationPrefix, NextHop | ConvertTo-Json -Compress"
            ]
            res_act = subprocess.run(cmd_act, capture_output=True, text=True, creationflags=self.creationflags)
            if res_act.returncode == 0 and res_act.stdout.strip():
                try:
                    data = json.loads(res_act.stdout.strip())
                    active_routes = [data] if isinstance(data, dict) else data
                except Exception:
                    pass

            # 6. Build a list of specific routes we want to remove
            routes_to_remove = []  # list of tuples: (prefix, nexthop)
            
            # Check persistent routes
            for r in persistent_routes:
                prefix = r.get("DestinationPrefix")
                nh = r.get("NextHop")
                if not prefix or prefix == "0.0.0.0/0":
                    continue
                if prefix in all_managed_subnets:
                    if prefix not in subnets or not gateways_equal(nh, gateway):
                        routes_to_remove.append((prefix, nh))

            # Check active routes
            for r in active_routes:
                prefix = r.get("DestinationPrefix")
                nh = r.get("NextHop")
                if not prefix or prefix == "0.0.0.0/0":
                    continue
                if prefix in all_managed_subnets:
                    if prefix not in subnets or not gateways_equal(nh, gateway):
                        routes_to_remove.append((prefix, nh))

            # Deduplicate routes to remove
            routes_to_remove = list(set(routes_to_remove))

            # 7. Remove the identified mismatching/obsolete routes globally
            for prefix, nh in routes_to_remove:
                gw_param = f"-NextHop '{nh}'" if (nh and nh not in ("0.0.0.0", "none", "on-link")) else ""
                
                rm_active = [
                    "powershell", "-Command",
                    f"Remove-NetRoute -DestinationPrefix '{prefix}' {gw_param} -Confirm:$false -ErrorAction SilentlyContinue"
                ]
                subprocess.run(rm_active, capture_output=True, creationflags=self.creationflags)
                
                rm_pers = [
                    "powershell", "-Command",
                    f"Remove-NetRoute -DestinationPrefix '{prefix}' {gw_param} -PolicyStore PersistentStore -Confirm:$false -ErrorAction SilentlyContinue"
                ]
                subprocess.run(rm_pers, capture_output=True, creationflags=self.creationflags)

            # Remove default route (0.0.0.0/0) if not in the target subnets list,
            # to prevent overriding the main internet (Wi-Fi) default route.
            has_default = False
            for s in subnets:
                try:
                    net = ipaddress.ip_network(s, strict=False)
                    if net.prefixlen == 0:
                        has_default = True
                        break
                except ValueError:
                    if s == "default" or s == "0.0.0.0":
                        has_default = True
                        break
            
            if not has_default:
                # Remove active default route on this adapter
                rm_default_cmd = [
                    "powershell",
                    "-Command",
                    f"Remove-NetRoute -DestinationPrefix '0.0.0.0/0' -InterfaceAlias '{selected_adapter}' -Confirm:$false -ErrorAction SilentlyContinue"
                ]
                subprocess.run(rm_default_cmd, capture_output=True, creationflags=self.creationflags)
                
                # Remove persistent default route on this adapter if any
                rm_pers_cmd = [
                    "powershell",
                    "-Command",
                    f"Remove-NetRoute -DestinationPrefix '0.0.0.0/0' -InterfaceAlias '{selected_adapter}' -PolicyStore PersistentStore -Confirm:$false -ErrorAction SilentlyContinue"
                ]
                subprocess.run(rm_pers_cmd, capture_output=True, creationflags=self.creationflags)

            # Configure the interface metric dynamically based on whether it should host a default route.
            # If not (has_default is False), we set a high metric (1200) so that other active interfaces (like Wi-Fi)
            # are preferred for internet traffic, even if a default route is dynamically added later by DHCP.
            # If yes (has_default is True), we set a low metric (10) to prioritize this adapter.
            metric = 10 if has_default else 1200
            metric_cmd = [
                "powershell",
                "-Command",
                f"Set-NetIPInterface -InterfaceAlias '{selected_adapter}' -AddressFamily IPv4 -InterfaceMetric {metric} -Confirm:$false -ErrorAction SilentlyContinue"
            ]
            subprocess.run(metric_cmd, capture_output=True, creationflags=self.creationflags)

            # 2. Add static routes for each configured subnet (both active and persistently)
            for subnet in subnets:
                # Remove existing route first from active and persistent stores
                rm_cmd = [
                    "powershell",
                    "-Command",
                    f"Remove-NetRoute -DestinationPrefix '{subnet}' -InterfaceAlias '{selected_adapter}' -Confirm:$false -ErrorAction SilentlyContinue"
                ]
                subprocess.run(rm_cmd, capture_output=True, creationflags=self.creationflags)
                
                rm_pers_cmd = [
                    "powershell",
                    "-Command",
                    f"Remove-NetRoute -DestinationPrefix '{subnet}' -InterfaceAlias '{selected_adapter}' -PolicyStore PersistentStore -Confirm:$false -ErrorAction SilentlyContinue"
                ]
                subprocess.run(rm_pers_cmd, capture_output=True, creationflags=self.creationflags)

                # Add new route with low metric (5)
                # If gateway is known, use NextHop. Otherwise, route on-link.
                if gateway:
                    add_cmd = [
                        "powershell",
                        "-Command",
                        f"New-NetRoute -DestinationPrefix '{subnet}' -InterfaceAlias '{selected_adapter}' -NextHop '{gateway}' -RouteMetric 5 -Confirm:$false"
                    ]
                    add_pers_cmd = [
                        "powershell",
                        "-Command",
                        f"New-NetRoute -DestinationPrefix '{subnet}' -InterfaceAlias '{selected_adapter}' -NextHop '{gateway}' -RouteMetric 5 -PolicyStore PersistentStore -Confirm:$false"
                    ]
                else:
                    add_cmd = [
                        "powershell",
                        "-Command",
                        f"New-NetRoute -DestinationPrefix '{subnet}' -InterfaceAlias '{selected_adapter}' -RouteMetric 5 -Confirm:$false"
                    ]
                    add_pers_cmd = [
                        "powershell",
                        "-Command",
                        f"New-NetRoute -DestinationPrefix '{subnet}' -InterfaceAlias '{selected_adapter}' -RouteMetric 5 -PolicyStore PersistentStore -Confirm:$false"
                    ]
                
                res = subprocess.run(add_cmd, capture_output=True, text=True, creationflags=self.creationflags)
                if res.returncode != 0:
                    err_msg = res.stderr.strip()
                    if "already exists" in err_msg.lower() or "msft_netroute" in err_msg.lower():
                        pass
                    else:
                        return False, f"Failed to add active route for {subnet}: {err_msg}"
                
                res_pers = subprocess.run(add_pers_cmd, capture_output=True, text=True, creationflags=self.creationflags)
                if res_pers.returncode != 0:
                    err_msg = res_pers.stderr.strip()
                    if "already exists" in err_msg.lower() or "msft_netroute" in err_msg.lower():
                        pass
                    else:
                        return False, f"Failed to add persistent route for {subnet}: {err_msg}"

            inferred_note = f" (Warning: gateway {gateway} was inferred — verify this is correct)" if gateway_inferred else ""
            return True, f"Routing successfully updated via {selected_adapter} (Gateway: {gateway or 'On-link'}).{inferred_note}"
        except Exception as e:
            return False, f"Exception applying routing: {str(e)}"
