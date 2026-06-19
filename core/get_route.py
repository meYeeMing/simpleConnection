import subprocess
import sys
import ipaddress
from core.config import config
from core.utils import is_admin


class RouteService:
    def __init__(self):
        self.config = config()

    def get_route_list_subnets(self) -> list[str]:
        """Returns the current route-list from config (always fresh)."""
        profiles = self.config.get_all() or {}
        subnets = set()
        for prof in profiles.values():
            if isinstance(prof, dict) and "route-list" in prof:
                for r in prof["route-list"]:
                    subnets.add(r)
        return sorted(list(subnets))

    def get_route_list(self):
        if sys.platform == "win32":
            route_list = subprocess.run(
                ["route", "print", "-4"], capture_output=True, text=True, creationflags=0x08000000
            )
            return route_list.stdout
        else:
            route_list = subprocess.run(
                ["ip", "route", "show"], capture_output=True, text=True
            )
            return route_list.stdout

    def route_lists(self) -> list[dict]:
        raw_route_list = self.get_route_list()
        route_list_set = []
        
        if sys.platform == "win32":
            for line in raw_route_list.splitlines():
                parts = line.strip().split()
                if len(parts) >= 4:
                    try:
                        dest_ip = ipaddress.ip_address(parts[0])
                        netmask_ip = ipaddress.ip_address(parts[1])
                        r_net = ipaddress.ip_network(f"{parts[0]}/{parts[1]}", strict=False)
                        
                        if len(parts) == 5:
                            gateway = parts[2]
                            metric = int(parts[4])
                        else:
                            gateway = parts[2]
                            metric = int(parts[3])
                            
                        route_list_set.append({
                            "dest": str(dest_ip),
                            "netmask": str(netmask_ip),
                            "cidr": str(r_net),
                            "gateway": gateway,
                            "metric": metric
                        })
                    except (ValueError, IndexError):
                        pass
        else:
            for line in raw_route_list.splitlines():
                parts = line.strip().split()
                if not parts:
                    continue
                dest_str = parts[0]
                if dest_str == "default":
                    r_net = ipaddress.ip_network("0.0.0.0/0")
                else:
                    try:
                        r_net = ipaddress.ip_network(dest_str, strict=False)
                    except ValueError:
                        continue
                
                # Parse gateway (via)
                gateway = "On-link"
                if "via" in parts:
                    idx = parts.index("via")
                    if idx + 1 < len(parts):
                        gateway = parts[idx + 1]
                
                # Parse metric
                metric = 0
                if "metric" in parts:
                    idx = parts.index("metric")
                    if idx + 1 < len(parts):
                        try:
                            metric = int(parts[idx + 1])
                        except ValueError:
                            pass
                
                route_list_set.append({
                    "dest": str(r_net.network_address),
                    "netmask": str(r_net.netmask),
                    "cidr": str(r_net),
                    "gateway": gateway,
                    "metric": metric
                })
                
        return route_list_set


if __name__ == "__main__":
    route_service = RouteService()
    print(route_service.route_lists())
