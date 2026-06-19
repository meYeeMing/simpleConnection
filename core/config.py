import os
import yaml
import sys
import shutil


class config:
    _instance = None
    _config = {}

    # Calculate config path dynamically based on runtime environment (source vs compiled)

    if getattr(sys, "frozen", False):
        # User-modifiable config lives next to the executable
        _base_dir = os.path.dirname(sys.executable)
        _config_path = os.path.join(_base_dir, "config.yaml")

        # If user config does not exist, copy the bundled default config from PyInstaller assets
        if not os.path.exists(_config_path):
            _bundled_config = os.path.join(sys._MEIPASS, "config.yaml")
            if os.path.exists(_bundled_config):
                os.makedirs(os.path.dirname(_config_path), exist_ok=True)
                shutil.copy(_bundled_config, _config_path)
    else:
        # __file__ is core/config.py, go up one level for root
        _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _config_path = os.path.join(_base_dir, "config.yaml")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(config, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.load_config()

    def load_config(self):
        if not os.path.exists(self._config_path):
            self._config = {}
            raise FileNotFoundError(f"config file not found at {self._config_path}")
        with open(self._config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}
        self.migrate_old_config()

    def migrate_old_config(self):
        if not isinstance(self._config, dict):
            self._config = {}
            return
        
        # Check if old format keys are present
        has_old_keys = any(k in self._config for k in ["direct", "router", "dongle", "route-list", "adapter-bindings"])
        if has_old_keys:
            old_config = self._config
            new_config = {}
            
            # 1. Migrate Router (direct)
            direct = old_config.get("direct") or {}
            router_binding = (old_config.get("adapter-bindings") or {}).get("router", "")
            route_list = old_config.get("route-list") or []
            
            new_config["10.10.30.1:router"] = {
                "AdapterName": router_binding,
                "dhcp": direct.get("dhcp", False),
                "Ip": direct.get("ip", "10.10.30.170"),
                "mask": direct.get("mask", "255.255.255.0"),
                "IpGateway": direct.get("gateway", "10.10.30.1"),
                "route-list": route_list
            }
            
            # 2. Migrate Sim Card Router (sim-card-router)
            sim_binding = (old_config.get("adapter-bindings") or {}).get("sim-card-router", "")
            new_config["192.186.82.1:sim-card-router"] = {
                "AdapterName": sim_binding,
                "dhcp": True,
                "Ip": "",
                "mask": "",
                "IpGateway": "192.186.82.1",
                "route-list": ["192.186.82.0/24"]
            }
            
            # 3. Migrate Dongle (dongle)
            dongle_binding = (old_config.get("adapter-bindings") or {}).get("dongle", "")
            new_config["192.168.1.1:dongle"] = {
                "AdapterName": dongle_binding,
                "dhcp": True,
                "Ip": "",
                "mask": "",
                "IpGateway": "192.168.1.1",
                "route-list": []
            }
            
            self._config = new_config
            self.save_config()

    def save_config(self):
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, default_flow_style=False, encoding="utf-8")

    def get(self, key):
        return self._config.get(key)

    def set(self, key, value):
        self._config[key] = value
        self.save_config()

    def get_all(self):
        return self._config

    def delete(self, key):
        if key in self._config:
            del self._config[key]
            self.save_config()
