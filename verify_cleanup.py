# -*- coding: utf-8 -*-
"""清理结果全量验证。

检查: 推广程序空壳化与锁定 / 核心输入法文件完整性 / 输入法注册与加载 /
      hosts 拦截段 / 进程与服务 / 配置锁定状态。

用法: python verify_cleanup.py
自动复用 sogou_cleaner.py 的安装目录探测, 不依赖硬编码路径。
"""
import ctypes
import ctypes.wintypes as wt
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from sogou_cleaner import find_sogou, py_dir
except Exception as e:
    print("无法导入 sogou_cleaner.py: %s" % e)
    sys.exit(1)

STUBBED = ["SGTool.exe", "SogouCloud.exe", "SGSmartAssistant.exe", "SGIGuideHelper.exe",
           "sgfeedbackhelper.exe", "SGWangzai.exe", "SGBizLauncher.exe", "SGDownload.exe",
           "SGWizard.exe", "PinyinUp.exe", "crashrpt.exe"]

# 版本目录下必须保持原样的核心输入法文件
CORE_IN_VER = ["SogouTSF.dll", "ImeFunc.dll", "UIPlugin.dll"]

# 位于 system32 的输入法本体
CORE_IN_SYS32 = ["SogouTSF.ime", "SogouPY.ime"]

SOGOU_TSF_CLSID = "{E7EA138E-69F8-11D7-A6EA-00065B844310}"


def run(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, timeout=20)
    except Exception:
        return None


def read_locked(path):
    """读取被拒即视为已锁定；返回 (是否可读, 是否存在)"""
    if not os.path.exists(path):
        return None, False
    try:
        open(path, "rb").read(1)
        return True, True
    except Exception:
        return False, True


def dir_write_locked(path):
    """目录被锁时仍可列目录, 必须用写入探测判断"""
    probe = os.path.join(path, ".verify_probe")
    try:
        open(probe, "w").close()
    except OSError:
        return True
    try:
        os.remove(probe)
    except OSError:
        pass
    return False


R = find_sogou()
PY = py_dir()
print("=" * 68)
if R:
    print("安装目录: %s  (版本 %s)" % (R["root"], os.path.basename(R["ver"])))
else:
    print("未找到搜狗输入法安装目录")
VER = R["ver"] if R else ""

# ---------------------------------------------------------------- 1
print()
print("=" * 68)
print("[1] 推广程序空壳化 + 锁定状态")
print("=" * 68)
if VER:
    for n in STUBBED:
        p = os.path.join(VER, n)
        if not os.path.isfile(p):
            print("  %-26s 不存在" % n)
            continue
        size = os.path.getsize(p)
        readable, _ = read_locked(p)
        print("  %-26s %5d 字节  %-4s  %s"
              % (n, size, "空壳" if size <= 2048 else "原始(!)",
                 "已锁定" if readable is False else "可读(未锁定!)"))

# ---------------------------------------------------------------- 2
print()
print("=" * 68)
print("[2] 核心输入法文件完整性 (必须为原始大小)")
print("=" * 68)
sd = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "system32")
for n in CORE_IN_SYS32:
    p = os.path.join(sd, n)
    if os.path.isfile(p):
        sz = os.path.getsize(p)
        print("  system32\\%-20s %10d 字节  %s"
              % (n, sz, "OK" if sz > 1_000_000 else "!! 疑似被破坏"))
    else:
        print("  system32\\%-20s 不存在(!)" % n)
if VER:
    for n in CORE_IN_VER:
        p = os.path.join(VER, n)
        if os.path.isfile(p):
            sz = os.path.getsize(p)
            print("  %-28s %10d 字节  %s"
                  % (n, sz, "OK" if sz > 4096 else "!! 疑似被破坏"))
        else:
            print("  %-28s 不存在" % n)

# ---------------------------------------------------------------- 3
print()
print("=" * 68)
print("[3] 输入法注册与加载状态")
print("=" * 68)
import winreg
# 实现体在 Classes\CLSID 下, 注册与语言配置在 CTF\TIP 下, 两处都要在
try:
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Classes\CLSID" + "\\" + SOGOU_TSF_CLSID
                        + r"\InprocServer32") as k:
        dll = winreg.QueryValueEx(k, "")[0]
    print("  TSF 实现体: %s" % dll)
    print("    文件存在: %s  (%d 字节)"
          % (os.path.isfile(dll), os.path.getsize(dll) if os.path.isfile(dll) else 0))
except OSError:
    print("  TSF 实现体注册缺失(!)")
try:
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\Microsoft\CTF\TIP" + "\\" + SOGOU_TSF_CLSID
                        + r"\LanguageProfile\0x00000804") as k:
        profs = [winreg.EnumKey(k, i) for i in range(winreg.QueryInfoKey(k)[0])]
    print("  TSF 语言配置 (zh-CN): %d 项 %s" % (len(profs), "OK" if profs else "(!)"))
except OSError:
    print("  TSF 语言配置缺失(!)")

user32 = ctypes.WinDLL("user32", use_last_error=True)
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
TH32CS_SNAPMODULE = 0x00000008


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD),
                ("th32ProcessID", wt.DWORD), ("GlblcntUsage", wt.DWORD),
                ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
                ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE),
                ("szModule", ctypes.c_char * 256), ("szExePath", ctypes.c_char * 260)]


# 找一个已加载搜狗 IME 的进程, 证明输入法确实在跑
found_proc = None
snap = k32.CreateToolhelp32Snapshot(0x2, 0)
if snap not in (0, -1):
    TH32CS_SNAPPROCESS_ENTRY = ctypes.c_char * 260

    class PE32(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)), ("th32ModuleID", wt.DWORD),
                    ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                    ("szExeFile", TH32CS_SNAPPROCESS_ENTRY)]
    pe = PE32()
    pe.dwSize = ctypes.sizeof(PE32)
    ok = k32.Process32First(snap, ctypes.byref(pe))
    while ok:
        pid = pe.th32ProcessID
        ms = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid)
        if ms not in (0, -1):
            me = MODULEENTRY32()
            me.dwSize = ctypes.sizeof(MODULEENTRY32)
            if k32.Module32First(ms, ctypes.byref(me)):
                while True:
                    path = me.szExePath.decode("mbcs", errors="ignore")
                    if "sogou" in path.lower() and path.lower().endswith(".ime"):
                        found_proc = (pid, pe.szExeFile.decode("mbcs", errors="ignore"), path)
                        break
                    if not k32.Module32Next(ms, ctypes.byref(me)):
                        break
            k32.CloseHandle(ms)
        if found_proc:
            break
        ok = k32.Process32Next(snap, ctypes.byref(pe))
    k32.CloseHandle(snap)

if found_proc:
    print("  输入法已加载: 进程 %s (pid %d) 载入 %s"
          % (found_proc[1], found_proc[0], os.path.basename(found_proc[2])))
else:
    print("  当前没有进程加载搜狗 IME (未使用输入法时会这样, 不一定是故障)")

# ---------------------------------------------------------------- 4
print()
print("=" * 68)
print("[4] hosts 拦截段")
print("=" * 68)
hosts = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                     "System32", "drivers", "etc", "hosts")
try:
    txt = open(hosts, encoding="utf-8", errors="ignore").read()
    m = re.search(r"(?ms)# sogou-debloat-start(.*?)# sogou-debloat-end", txt)
    if m:
        doms = re.findall(r"0\.0\.0\.0\s+(\S+)", m.group(1))
        print("  已拦截 %d 个域名" % len(doms))
        print("  词库更新域名是否被误拦: %s"
              % ("是(!)" if any("dict" in d or "pinyin" in d for d in doms) else "否"))
    else:
        print("  未找到拦截段")
except Exception as e:
    print("  读取 hosts 失败: %s" % e)

# ---------------------------------------------------------------- 5
print()
print("=" * 68)
print("[5] 进程 / 服务")
print("=" * 68)
r = run('tasklist /fo csv')
running = []
if r and r.stdout:
    t = r.stdout.decode("gbk", errors="ignore").lower()
    for n in STUBBED + ["SGWebRender.exe", "SGMiniBrowserHelperHost.exe"]:
        if n.lower() in t:
            running.append(n)
print("  推广进程仍在运行: %s" % (running if running else "无"))
r = run('sc qc SogouSvc')
if r and r.stdout:
    mm = re.search(rb"START_TYPE\s*:\s*\d+\s+(\w+)", r.stdout)
    print("  SogouSvc 启动类型: %s" % (mm.group(1).decode() if mm else "?"))
else:
    print("  SogouSvc: 不存在")

# ---------------------------------------------------------------- 6
print()
print("=" * 68)
print("[6] 配置与痕迹锁定状态")
print("=" * 68)
targets = [os.path.join(PY, "Components", "ComponentConfig.ini"),
           os.path.join(PY, "FastPassport.ini"),
           os.path.join(PY, "ThirdPassport.ini"),
           os.path.join(PY, "Popup"),
           os.path.join(PY, "Components", "SmartInfo")]
for p in targets:
    if not os.path.exists(p):
        print("  %-52s 不存在" % p.replace(PY, "...SogouPY"))
    elif os.path.isdir(p):
        print("  %-52s %s" % (p.replace(PY, "...SogouPY"),
                              "已锁定(禁止新建)" if dir_write_locked(p) else "可写(未锁定)"))
    else:
        readable, _ = read_locked(p)
        print("  %-52s %s" % (p.replace(PY, "...SogouPY"),
                              "已锁定" if readable is False else "可读(未锁定)"))
