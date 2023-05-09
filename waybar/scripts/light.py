import subprocess

cur_val: float = round(float(subprocess.check_output(["light", "-G"])))
min_val = 15

with open("/etc/light/targets/sysfs/backlight/intel_backlight/save", "r") as f:
    raw_val = int(f.readline())
    restr_val = round(raw_val/8.92)

if cur_val > 25:
    subprocess.run(["light", "-O"])
    subprocess.run(["light", "-S", str(min_val)])
elif cur_val <= 25:
        if restr_val >= cur_val+10:
            subprocess.run(["light", "-I"])

        subprocess.run(["light", "-S", "100"])
