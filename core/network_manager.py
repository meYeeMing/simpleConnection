import json
import os
import sys
import subprocess
import ipaddress
import tempfile
import time

if sys.platform == "win32":
    import winreg

class NetworkManager:
    def __init__(self):
        self.creationflags = 0
        if sys.platform == "win32":
            self.creationflags = 0x08000000

    def get_adapters(self) -> list[dict]:
        """
        Retrieves physical network adapters (excluding Wi-Fi and Bluetooth)
        along with their active IPv4 addresses and gateways.
        Uses a batched WMI/CIM query for maximum speed and robustness.
        """
        script = (
            "$adapters = Get-CimInstance Win32_NetworkAdapter | Where-Object { $_.NetConnectionID -ne $null } | Select-Object NetConnectionID, Name, InterfaceIndex, NetConnectionStatus | ConvertTo-Json -Compress; "
            "$config = Get-CimInstance Win32_NetworkAdapterConfiguration | Select-Object InterfaceIndex, IPAddress, DefaultIPGateway, SettingID | ConvertTo-Json -Compress; "
            "Write-Output '===ADAPTERS==='; Write-Output $adapters; "
            "Write-Output '===CONFIG==='; Write-Output $config;"
        )
        cmd = ["powershell", "-Command", script]

        adapters_list = []
        config_list = []

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=self.creationflags)
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.split("===")
                sections = {}
                current_key = None
                for part in parts:
                    part_str = part.strip()
                    if part_str in ("ADAPTERS", "CONFIG"):
                        current_key = part_str
                    elif current_key and part_str:
                        sections[current_key] = part_str
                        current_key = None

                if "ADAPTERS" in sections:
                    try:
                        data = json.loads(sections["ADAPTERS"])
                        adapters_list = [data] if isinstance(data, dict) else data
                    except Exception:
                        pass

                if "CONFIG" in sections:
                    try:
                        data = json.loads(sections["CONFIG"])
                        config_list = [data] if isinstance(data, dict) else data
                    except Exception:
                        pass
        except Exception as e:
            print(f"Error executing adapter commands: {e}", file=sys.stderr)

        # Map CONFIG by InterfaceIndex
        config_map = {}
        for c in config_list:
            idx = c.get("InterfaceIndex")
            if idx is not None:
                config_map[idx] = c

        merged_adapters = []
        for a in adapters_list:
            name = a.get("NetConnectionID")
            desc = a.get("Name", "")
            status_code = a.get("NetConnectionStatus")
            idx = a.get("InterfaceIndex")

            name_lower = name.lower() if name else ""
            desc_lower = desc.lower() if desc else ""
            if "wi-fi" in name_lower or "wifi" in name_lower or "wireless" in name_lower or "wi-fi" in desc_lower or "wifi" in desc_lower or "wireless" in desc_lower:
                continue
            if "bluetooth" in name_lower or "bluetooth" in desc_lower:
                continue

            status = "Disconnected"
            if status_code == 2:
                status = "Up"

            # Get IP and Gateway from configuration/registry
            ip = "No IP Address"
            gateway = "None"
            conf = config_map.get(idx)
            if conf:
                ips = conf.get("IPAddress")
                if ips:
                    if isinstance(ips, list):
                        for ip_addr in ips:
                            if ":" not in ip_addr and ip_addr != "127.0.0.1":
                                ip = ip_addr
                                break
                    elif isinstance(ips, str):
                        if ":" not in ips and ips != "127.0.0.1":
                            ip = ips

                # 1. Check WMI DefaultIPGateway
                gws = conf.get("DefaultIPGateway")
                if gws:
                    if isinstance(gws, list):
                        for gw in gws:
                            if gw and gw != "0.0.0.0":
                                gateway = gw
                                break
                    elif isinstance(gws, str):
                        if gws and gws != "0.0.0.0":
                            gateway = gws

                # 2. Check Registry fallback if WMI gateway is empty
                if gateway == "None" or gateway == "0.0.0.0":
                    guid = conf.get("SettingID")
                    if guid:
                        try:
                            reg_path = rf"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{guid}"
                            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                            
                            # Try DhcpDefaultGateway
                            try:
                                reg_gws, _ = winreg.QueryValueEx(key, "DhcpDefaultGateway")
                                if reg_gws:
                                    if isinstance(reg_gws, list):
                                        for gw in reg_gws:
                                            if gw and gw != "0.0.0.0":
                                                gateway = gw
                                                break
                                    elif isinstance(reg_gws, str):
                                        if reg_gws and reg_gws != "0.0.0.0":
                                            gateway = reg_gws
                            except FileNotFoundError:
                                pass
                            
                            # Try DefaultGateway (static)
                            if gateway == "None" or gateway == "0.0.0.0":
                                try:
                                    reg_gws, _ = winreg.QueryValueEx(key, "DefaultGateway")
                                    if reg_gws:
                                        if isinstance(reg_gws, list):
                                            for gw in reg_gws:
                                                if gw and gw != "0.0.0.0":
                                                    gateway = gw
                                                    break
                                        elif isinstance(reg_gws, str):
                                            if reg_gws and reg_gws != "0.0.0.0":
                                                gateway = reg_gws
                                except FileNotFoundError:
                                    pass
                            
                            # Try DhcpServer as last resort gateway fallback
                            if gateway == "None" or gateway == "0.0.0.0":
                                try:
                                    reg_srv, _ = winreg.QueryValueEx(key, "DhcpServer")
                                    if reg_srv and reg_srv != "0.0.0.0" and reg_srv != "255.255.255.255":
                                        gateway = reg_srv
                                except FileNotFoundError:
                                    pass

                            winreg.CloseKey(key)
                        except Exception:
                            pass

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
        Uses a batched single-process PowerShell script to avoid process spawn overhead.
        """
        try:
            # 1. Discover the gateway for the selected adapter.
            # If DHCP is used, wait up to 10 seconds for the adapter to receive its IP and gateway.
            gateway = configured_gateway
            gateway_inferred = False
            if not gateway:
                fallback_gw = None
                # Poll every 0.5 seconds for up to 60 times (30 seconds total)
                for _ in range(60):
                    adapters = self.get_adapters()
                    for a in adapters:
                        if a["InterfaceAlias"] == selected_adapter:
                            ip = a["IPv4Address"]
                            g = a["IPv4DefaultGateway"]
                            
                            # Keep track of any non-empty gateway we see, even if IP is not fully ready
                            if g and g != "0.0.0.0" and g != "None":
                                fallback_gw = g

                            # Only accept a gateway if we have a valid, non-APIPA IP and a default gateway
                            if ip and ip != "No IP Address" and not ip.startswith("169.254."):
                                if g and g != "0.0.0.0" and g != "None":
                                    gateway = g
                                    break
                    if gateway:
                        break
                    time.sleep(0.5)

                # Fallback 1: use the fallback gateway we found during polling (even if IP was slow/not ready)
                if not gateway and fallback_gw:
                    gateway = fallback_gw

                # Fallback 2: if we still don't have a gateway but have a valid IP, infer gateway as x.y.z.1
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
                if s and s.strip():
                    all_managed_subnets.add(s.strip())

            # 3. Determine if default route is requested
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

            # Configure the interface metric dynamically based on whether it should host a default route.
            metric = 10 if has_default else 1200

            # 4. Build single batched PowerShell script to execute all route updates
            subnets_ps = ", ".join(f"'{s.strip()}'" for s in subnets if s.strip())
            all_managed_ps = ", ".join(f"'{s}'" for s in all_managed_subnets)
            has_default_val = "true" if has_default else "false"
            
            ps_script = (
                f"$adapter = '{selected_adapter}'\n"
                f"$gateway = '{gateway or ''}'\n"
                f"$metric = {metric}\n"
                f"$subnets = @({subnets_ps})\n"
                f"$all_managed = @({all_managed_ps})\n"
                f"$has_default = ${has_default_val}\n"
                
                # 1. Remove default route if not requested
                "if (-not $has_default) {\n"
                "  Remove-NetRoute -DestinationPrefix '0.0.0.0/0' -InterfaceAlias $adapter -Confirm:$false -ErrorAction SilentlyContinue\n"
                "  Remove-NetRoute -DestinationPrefix '0.0.0.0/0' -InterfaceAlias $adapter -PolicyStore PersistentStore -Confirm:$false -ErrorAction SilentlyContinue\n"
                "}\n"
                
                # 2. Set interface metric
                "Set-NetIPInterface -InterfaceAlias $adapter -AddressFamily IPv4 -InterfaceMetric $metric -Confirm:$false -ErrorAction SilentlyContinue\n"
                
                # 3. Clean up mismatching/obsolete routes from persistent store
                "$pers = Get-NetRoute -PolicyStore PersistentStore -ErrorAction SilentlyContinue\n"
                "foreach ($r in $pers) {\n"
                "  $prefix = $r.DestinationPrefix; $nh = $r.NextHop\n"
                "  if ($prefix -eq '0.0.0.0/0' -or -not $prefix) { continue }\n"
                "  if ($prefix -in $all_managed) {\n"
                "    $gw_equal = ($nh -eq $gateway) -or (($nh -in @('0.0.0.0', 'none', 'on-link', $null)) -and ($gateway -in @('0.0.0.0', 'none', 'on-link', '', $null)))\n"
                "    if ($prefix -notin $subnets -or -not $gw_equal) {\n"
                "      if ($nh -and $nh -notin @('0.0.0.0', 'none', 'on-link')) {\n"
                "        Remove-NetRoute -DestinationPrefix $prefix -NextHop $nh -PolicyStore PersistentStore -Confirm:$false -ErrorAction SilentlyContinue\n"
                "      } else {\n"
                "        Remove-NetRoute -DestinationPrefix $prefix -PolicyStore PersistentStore -Confirm:$false -ErrorAction SilentlyContinue\n"
                "      }\n"
                "    }\n"
                "  }\n"
                "}\n"
                
                # 4. Clean up mismatching/obsolete routes from active store
                "$act = Get-NetRoute -Protocol Netmgmt -ErrorAction SilentlyContinue\n"
                "foreach ($r in $act) {\n"
                "  $prefix = $r.DestinationPrefix; $nh = $r.NextHop\n"
                "  if ($prefix -eq '0.0.0.0/0' -or -not $prefix) { continue }\n"
                "  if ($prefix -in $all_managed) {\n"
                "    $gw_equal = ($nh -eq $gateway) -or (($nh -in @('0.0.0.0', 'none', 'on-link', $null)) -and ($gateway -in @('0.0.0.0', 'none', 'on-link', '', $null)))\n"
                "    if ($prefix -notin $subnets -or -not $gw_equal) {\n"
                "      if ($nh -and $nh -notin @('0.0.0.0', 'none', 'on-link')) {\n"
                "        Remove-NetRoute -DestinationPrefix $prefix -NextHop $nh -Confirm:$false -ErrorAction SilentlyContinue\n"
                "      } else {\n"
                "        Remove-NetRoute -DestinationPrefix $prefix -Confirm:$false -ErrorAction SilentlyContinue\n"
                "      }\n"
                "    }\n"
                "  }\n"
                "}\n"
                
                # 5. Add static routes for each requested subnet (both active and persistently) if not already correct
                "foreach ($subnet in $subnets) {\n"
                "  $has_active = Get-NetRoute -DestinationPrefix $subnet -InterfaceAlias $adapter -ErrorAction SilentlyContinue | Where-Object {\n"
                "    if ($gateway) { $_.NextHop -eq $gateway } else { $_.NextHop -in @('0.0.0.0', 'none', 'on-link', '', $null) }\n"
                "  }\n"
                "  if (@($has_active).Count -ne 1) {\n"
                "    Remove-NetRoute -DestinationPrefix $subnet -InterfaceAlias $adapter -Confirm:$false -ErrorAction SilentlyContinue\n"
                "    if ($gateway) {\n"
                "      New-NetRoute -DestinationPrefix $subnet -InterfaceAlias $adapter -NextHop $gateway -RouteMetric 5 -Confirm:$false -ErrorAction SilentlyContinue\n"
                "    } else {\n"
                "      New-NetRoute -DestinationPrefix $subnet -InterfaceAlias $adapter -RouteMetric 5 -Confirm:$false -ErrorAction SilentlyContinue\n"
                "    }\n"
                "  }\n"
                "  $has_pers = Get-NetRoute -DestinationPrefix $subnet -PolicyStore PersistentStore -ErrorAction SilentlyContinue | Where-Object {\n"
                "    if ($gateway) { $_.NextHop -eq $gateway } else { $_.NextHop -in @('0.0.0.0', 'none', 'on-link', '', $null) }\n"
                "  }\n"
                "  if (@($has_pers).Count -ne 1) {\n"
                "    Remove-NetRoute -DestinationPrefix $subnet -PolicyStore PersistentStore -Confirm:$false -ErrorAction SilentlyContinue\n"
                "    if ($gateway) {\n"
                "      New-NetRoute -DestinationPrefix $subnet -InterfaceAlias $adapter -NextHop $gateway -RouteMetric 5 -PolicyStore PersistentStore -Confirm:$false -ErrorAction SilentlyContinue\n"
                "    } else {\n"
                "      New-NetRoute -DestinationPrefix $subnet -InterfaceAlias $adapter -RouteMetric 5 -PolicyStore PersistentStore -Confirm:$false -ErrorAction SilentlyContinue\n"
                "    }\n"
                "  }\n"
                "}\n"
            )

            # Write script to a system temp file and run it; always delete after execution.
            # powershell -Command fails on long/complex scripts due to command-line parsing limits.
            fd, temp_file = tempfile.mkstemp(suffix=".ps1")
            try:
                with os.fdopen(fd, "w") as f_out:
                    f_out.write(ps_script)
                
                cmd_run = ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_file]
                res_run = subprocess.run(cmd_run, capture_output=True, text=True, creationflags=self.creationflags)
                
                if res_run.returncode != 0:
                    return False, f"Failed to apply routing: {res_run.stderr.strip()}"
            finally:
                # Always delete the temp file, success or failure
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

            inferred_note = f" (Warning: gateway {gateway} was inferred — verify this is correct)" if gateway_inferred else ""
            return True, f"Routing successfully updated via {selected_adapter} (Gateway: {gateway or 'On-link'}).{inferred_note}"
        except Exception as e:
            return False, f"Exception applying routing: {str(e)}"
