PLUGIN_NAME = "Gelişmiş Sistem Araçları"

ACTIONS = {
    "Aygıt Yöneticisi": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "devmgmt"},
    "Disk Yönetimi": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "diskmgmt"},
    "Kayıt Defteri (Regedit)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "regedit"},
    "Komut İstemi (CMD)": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "cmd"},
    "Hizmetler": {"type": "plugin", "plugin_name": PLUGIN_NAME, "function": "services"}
}

def execute(func):
    import subprocess
    if func == "devmgmt": subprocess.Popen("devmgmt.msc", shell=True)
    elif func == "diskmgmt": subprocess.Popen("diskmgmt.msc", shell=True)
    elif func == "regedit": subprocess.Popen("regedit.exe", shell=True)
    elif func == "cmd": subprocess.Popen("cmd.exe", shell=True)
    elif func == "services": subprocess.Popen("services.msc", shell=True)