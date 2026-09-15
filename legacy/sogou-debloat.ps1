<#
=============================================================================
 sogou-debloat.ps1  —  搜狗输入法 去广告/去推广/去遥测/去AI 通用脚本 v1.0
=============================================================================
 特性: 免编译(内嵌空壳程序)、可选项目、全程备份、一键还原、幂等可重跑

 用法:
   交互菜单:     powershell -ExecutionPolicy Bypass -File sogou-debloat.ps1
   执行全部:     powershell -ExecutionPolicy Bypass -File sogou-debloat.ps1 -All
   指定项目:     powershell ... -Remove ads,update,ai,telemetry,components,login,hosts,track,logs,startup
   预演(不修改): powershell ... -DryRun -All
   还原:         powershell ... -Restore
   可选开关:     -InstallDir <安装目录>         手动指定安装位置
                 -BackupRoot <目录>            指定备份位置(默认 系统盘\SogouDebloatBackup)
                 -DeleteAIBrowser              删除AI浏览器时不备份(省116MB备份)
                 -BlockDictDomains             hosts同时拦截词库更新域名(会失去词库更新)

 可选项目:
   ads        广告/推广弹窗进程 (SGTool/SogouCloud/旺仔/引导/反馈等)
   update     升级程序 + 升级服务 (词库更新默认保留, 见 hosts)
   crash      崩溃上报程序
   ai         AI助手浏览器 (CEF, 约116MB) + 网页渲染器
   telemetry  遥测/上报 DLL (shiply/beacon/qimei/Sogoulog)
   components 营销组件目录 (游戏中心/宠物/IChat/系统美化等) + 组件开关
   login      登录/账户痕迹 (图标/凭证文件/注册表登录态)
   mall       商城及无用设置页入口 (资源级修改, 实验性/版本相关)
   hosts      广告/遥测/账户域名拦截 (默认保留词库更新域名)
   track      追踪/状态注册表键
   logs       日志/缓存/弹窗数据清理
   startup    自启动面审计清理 (Run键/计划任务)

 说明:
   * 需要管理员权限; 所有修改前都会备份到 -BackupRoot 并可 -Restore 还原
   * 空壳化 = 把程序替换为 1KB 的"启动即退出"空壳并锁写保护,
     旧版不可用时也不会弹"找不到文件", 推广行为彻底消失
=============================================================================
#>
param(
    [string[]]$Remove = @(),
    [switch]$All,
    [switch]$DryRun,
    [switch]$Restore,
    [string]$InstallDir = '',
    [string]$BackupRoot = '',
    [switch]$DeleteAIBrowser,
    [switch]$BlockDictDomains
)

$ErrorActionPreference = 'Continue'

# ============ 内嵌空壳 (1024字节原生PE, 无依赖, 启动即退出) ============
$Script:StubX64B64 = 'TVoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQRQAAZIYBAAAAAAAAAAAAAAAAAPAAIgALAgAAAAIAAAACAAAAAAAAABAAAAAQAAAAAABAAQAAAAAQAAAAAgAABgAAAAAAAAAGAAAAAAAAAAAgAAAAAgAAAAAAAAIAAAAAABAAAAAAAAAQAAAAAAAAAAAQAAAAAAAAEAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAudGV4dAAAAAABAAAAEAAAAAIAAAACAAAAAAAAAAAAAAAAAAAgAABgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAzwMMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=='
$Script:StubX32B64 = 'TVoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQRQAATAEBAAAAAAAAAAAAAAAAAOAAAgELAQAAAAIAAAACAAAAAAAAABAAAAAQAAAAEAAAAABAAAAQAAAAAgAABgAAAAAAAAAGAAAAAAAAAAAgAAAAAgAAAAAAAAIAAAAAABAAABAAAAAAEAAAEAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAC50ZXh0AAAAAAEAAAAQAAAAAgAAAAIAAAAAAAAAAAAAAAAAACAAAGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAzwMMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=='

# ============ 状态 ============
$Script:BackupDir = ''
$Script:Manifest = ''
$Script:Results = @{}

# ============ 输出辅助 ============
function Say($t,$c='Gray'){ Write-Host $t -ForegroundColor $c }
function Ok($t){ Say ('    [完成] ' + $t) 'Green' }
function Sk($t){ Say ('    [跳过] ' + $t) 'DarkGray' }
function Pl($t){ Say ('    [计划] ' + $t) 'Yellow' }
function Wr($t){ Say ('    [注意] ' + $t) 'Magenta' }
function Hdr($t){ Say ''; Say ('== ' + $t) 'Cyan' }

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# ============ 清单与备份 ============
function Save-Record($action,$target,$backup){
    if(-not $Script:Manifest){ return }
    $obj = [ordered]@{ t=(Get-Date).ToString('yyyy-MM-dd HH:mm:ss'); action=$action; target=$target; backup=$backup }
    Add-Content -LiteralPath $Script:Manifest -Value ($obj | ConvertTo-Json -Compress) -Encoding UTF8
}

function Backup-ItemPath($path){
    $isDir = Test-Path -LiteralPath $path -PathType Container
    $sub = 'files'
    if($isDir){ $sub = 'dirs' }
    $destDir = Join-Path $Script:BackupDir $sub
    if(-not (Test-Path -LiteralPath $destDir)){ New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
    $name = Split-Path -Leaf $path
    $dest = Join-Path $destDir $name
    $i = 1
    while(Test-Path -LiteralPath $dest){ $dest = Join-Path $destDir ($name + '.' + $i); $i++ }
    if($isDir){ Move-Item -LiteralPath $path -Destination $dest -Force -ErrorAction SilentlyContinue }
    else { Move-Item -LiteralPath $path -Destination $dest -Force -ErrorAction SilentlyContinue }
    return $dest
}

function Remove-Deny($path){ & icacls.exe $path /remove:d '*S-1-1-0' 2>$null | Out-Null }
function Add-DenyFile($path){ & icacls.exe $path /deny '*S-1-1-0:(D,W)' 2>$null | Out-Null }
function Add-DenyDir($path){ & icacls.exe $path /deny '*S-1-1-0:(DE,WD,AD,DC)' 2>$null | Out-Null }

function Get-StubPath {
    $os64 = [Environment]::Is64BitOperatingSystem
    $tmp = Join-Path $env:TEMP ('sgd_stub_' + $(if($os64){'x64'}else{'x86'}) + '.exe')
    if(-not (Test-Path -LiteralPath $tmp)){
        $b64 = $Script:StubX64B64
        if(-not $os64){ $b64 = $Script:StubX32B64 }
        [IO.File]::WriteAllBytes($tmp, [Convert]::FromBase64String($b64))
    }
    return $tmp
}

function Kill-Exe($exeName){
    $n = [IO.Path]::GetFileNameWithoutExtension($exeName)
    Get-Process -Name $n -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}

function Is-Stub($path){
    try { return ((Get-Item -LiteralPath $path).Length -le 2048) } catch { return $false }
}

# ============ 核心操作 ============
function Set-StubFile($path){
    if(-not (Test-Path -LiteralPath $path -PathType Leaf)){ Sk ('不存在: ' + (Split-Path -Leaf $path)); return }
    if(Is-Stub $path){ Sk ('已是空壳: ' + (Split-Path -Leaf $path)); return }
    if($DryRun){ Pl ('将空壳化+锁定: ' + $path); return }
    Kill-Exe (Split-Path -Leaf $path)
    Remove-Deny $path
    $bk = Backup-ItemPath $path
    Copy-Item -LiteralPath (Get-StubPath) -Destination $path -Force
    Add-DenyFile $path
    Save-Record 'stub' $path $bk
    Ok ('已空壳化+锁定: ' + (Split-Path -Leaf $path))
}

function Move-OutFile($path){
    if(-not (Test-Path -LiteralPath $path -PathType Leaf)){ Sk ('不存在: ' + (Split-Path -Leaf $path)); return }
    if($DryRun){ Pl ('将移出(备份): ' + $path); return }
    Remove-Deny $path
    $bk = Backup-ItemPath $path
    Save-Record 'move' $path $bk
    Ok ('已移出: ' + (Split-Path -Leaf $path))
}

function Clear-AndLock($path){
    if(-not (Test-Path -LiteralPath $path)){ Sk ('不存在: ' + (Split-Path -Leaf $path)); return }
    if($DryRun){ Pl ('将清空+锁定: ' + $path); return }
    Remove-Deny $path
    $bk = $null
    $items = @(Get-ChildItem -LiteralPath $path -Force -ErrorAction SilentlyContinue)
    if($items.Count -gt 0){
        $bk = Backup-ItemPath $path
        if(-not (Test-Path -LiteralPath $path)){ New-Item -ItemType Directory -Path $path -Force | Out-Null }
    }
    if(-not (Test-Path -LiteralPath $path)){ New-Item -ItemType Directory -Path $path -Force | Out-Null }
    Add-DenyDir $path
    Save-Record 'clear' $path $bk
    Ok ('已清空+锁定: ' + (Split-Path -Leaf $path))
}

function Clear-Only($path){
    if(-not (Test-Path -LiteralPath $path)){ Sk ('不存在: ' + (Split-Path -Leaf $path)); return }
    if($DryRun){ Pl ('将清空: ' + $path); return }
    Get-ChildItem -LiteralPath $path -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Save-Record 'clearonly' $path $null
    Ok ('已清空: ' + (Split-Path -Leaf $path))
}

function Truncate-AndLock($path){
    if(-not (Test-Path -LiteralPath $path -PathType Leaf)){ Sk ('不存在: ' + (Split-Path -Leaf $path)); return }
    if($DryRun){ Pl ('将清空+锁定: ' + $path); return }
    Remove-Deny $path
    $bk = Backup-ItemPath $path
    New-Item -ItemType File -Path $path -Force | Out-Null
    Add-DenyFile $path
    Save-Record 'stub' $path $bk
    Ok ('已清空+锁定: ' + (Split-Path -Leaf $path))
}

function Reg-Del($key){
    if(-not (Test-Path $key)){ Sk ('注册表键不存在: ' + $key); return }
    if($DryRun){ Pl ('将导出并删除: ' + $key); return }
    $safe = ($key -replace '[:\\]','_')
    $bak = Join-Path $Script:BackupDir ('reg\' + $safe + '.reg')
    New-Item -ItemType Directory -Path (Split-Path $bak) -Force | Out-Null
    & reg.exe export $key $bak /y 2>$null | Out-Null
    Remove-Item -Path $key -Recurse -Force -ErrorAction SilentlyContinue
    Save-Record 'regdel' $key $bak
    Ok ('已删除(已导出备份): ' + $key)
}

# ============ 安装定位 ============
function Find-Sogou {
    $cands = @()
    if($InstallDir){ $cands += $InstallDir }
    $cands += @("$env:SystemDrive\搜狗输入法\SogouInput","$env:SystemDrive\搜狗输入法\SogouInput",
                "$env:ProgramFiles\SogouInput","${env:ProgramFiles(x86)}\SogouInput")
    foreach($k in @('HKLM:\SOFTWARE\WOW6432Node\SogouInput','HKLM:\SOFTWARE\SogouInput')){
        $v = Get-ItemProperty -Path $k -ErrorAction SilentlyContinue
        if($v){
            foreach($n in 'InstallDir','Path','InstallPath'){
                if($v.$n){ $cands += [string]$v.$n }
            }
        }
    }
    foreach($k in @('HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*')){
        Get-ItemProperty -Path $k -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -match '搜狗|Sogou' -and $_.InstallLocation } |
            ForEach-Object { $cands += $_.InstallLocation }
    }
    foreach($c in ($cands | Select-Object -Unique)){
        if(-not $c){ continue }
        $c = $c.TrimEnd('\')
        if(-not (Test-Path -LiteralPath $c)){ continue }
        $vd = Get-ChildItem -LiteralPath $c -Directory -ErrorAction SilentlyContinue |
              Where-Object { $_.Name -match '^\d+\.\d+' } | Sort-Object Name -Descending | Select-Object -First 1
        if($vd){ return @{ Root=$c; Ver=$vd.FullName } }
    }
    return $null
}

function Get-PyDir { return (Join-Path $env:USERPROFILE 'AppData\LocalLow\SogouPY') }

# ============ 各项目实现 ============
function Do-Ads($R){
    $names = 'SGTool.exe','SogouCloud.exe','SGSmartAssistant.exe','SGIGuideHelper.exe','sgfeedbackhelper.exe','SGWangzai.exe','SGBizLauncher.exe','SGDownload.exe','SGWizard.exe'
    foreach($n in $names){ Set-StubFile (Join-Path $R.Ver $n) }
}

function Do-Update($R){
    Set-StubFile (Join-Path $R.Ver 'PinyinUp.exe')
    $svc = Get-Service -Name 'SogouSvc' -ErrorAction SilentlyContinue
    if($svc){
        if($DryRun){ Pl '将禁用服务 SogouSvc' }
        else {
            $old = (Get-CimInstance Win32_Service -Filter "Name='SogouSvc'" -ErrorAction SilentlyContinue).StartMode
            & sc.exe config SogouSvc start= disabled 2>$null | Out-Null
            Save-Record 'svc' 'SogouSvc' $old
            Ok ('已禁用服务 SogouSvc (原类型: ' + $old + ')')
        }
    } else { Sk '服务 SogouSvc 不存在' }
    Say '    提示: 词库更新位于 hosts 白名单, 不受升级清理影响' 'DarkGray'
}

function Do-Crash($R){
    Set-StubFile (Join-Path $R.Ver 'crashrpt.exe')
    Set-StubFile (Join-Path $R.Root 'Components\crashrpt.exe')
}

function Do-AI($R){
    $browser = Join-Path $env:ProgramData 'SGAIAssistant\Browser'
    $marker = Join-Path $browser 'libcef.dll'
    if(Test-Path -LiteralPath $marker){
        if($DryRun){ Pl ('将移除 AI 浏览器组件: ' + $browser + ' (约116MB)') }
        elseif($DeleteAIBrowser){
            Remove-Deny $browser
            Remove-Item -LiteralPath $browser -Recurse -Force -ErrorAction SilentlyContinue
            Save-Record 'clear' $browser $null
            Ok '已删除 AI 浏览器组件(未备份)'
        } else {
            Remove-Deny $browser
            $bk = Backup-ItemPath $browser
            if(-not (Test-Path -LiteralPath $browser)){ New-Item -ItemType Directory -Path $browser -Force | Out-Null }
            Add-DenyDir $browser
            Save-Record 'clear' $browser $bk
            Ok ('已移除AI浏览器(已备份): ' + $browser)
        }
    } else { Sk 'AI 浏览器组件不存在' }
    Move-OutFile (Join-Path $R.Ver 'SGWebRender.exe')
}

function Do-Telemetry($R){
    $dlls = 'shiply.dll','beacon_sdk.dll','beacon_sdk64.dll','qimei.dll','qimei64.dll','Sogoulog.dll','Sogoulog64.dll'
    foreach($d in $dlls){ Move-OutFile (Join-Path $R.Ver $d) }
}

function Do-Components($R){
    $dirs = 'biz_center','game_center','AppBox','isgpet','SogouFlash','biz_pdf','IChat','systembeautify'
    foreach($d in $dirs){ Clear-AndLock (Join-Path $R.Root ('Components\' + $d)) }
    # 组件显示开关
    $cfg = Join-Path (Get-PyDir) 'Components\ComponentConfig.ini'
    if(Test-Path -LiteralPath $cfg){
        if($DryRun){ Pl ('将关闭组件开关: ' + $cfg) }
        else {
            $txt = Get-Content -LiteralPath $cfg -Encoding Unicode -Raw
            if($txt -match 'IChatCom\s*=\s*0' -and $txt -match 'ISGPetCom\s*=\s*0'){
                Sk '组件开关已是关闭状态'
            } else {
                $bk = Backup-ItemPath $cfg
                $new = "[Active]`r`nIChatCom=0`r`nISGPetCom=0`r`nPicFaceCom=1`r`nSystemBeautifyCom=0`r`n"
                [IO.File]::WriteAllText($cfg, $new, [Text.Encoding]::Unicode)
                Add-DenyFile $cfg
                Save-Record 'stub' $cfg $bk
                Ok '已关闭 IChat/旺仔/系统美化 组件开关并锁定'
            }
        }
    } else { Sk 'ComponentConfig.ini 不存在' }
}

function Do-Login($R){
    $py = Get-PyDir
    Clear-AndLock (Join-Path $R.Ver 'ThirdPassportIcon')
    Clear-AndLock (Join-Path $py 'ThirdPassportIcon')
    Truncate-AndLock (Join-Path $py 'FastPassport.ini')
    Truncate-AndLock (Join-Path $py 'ThirdPassport.ini')
    Reg-Del 'HKCU:\Software\SogouInput.user'
    Reg-Del 'HKCU:\Software\SogouInput.store.user'
}

function Do-Hosts($R){
    $hosts = Join-Path $env:SystemRoot 'System32\drivers\etc\hosts'
    $domains = @(
        'account.sogou.com','ie.sogou.com','wan.sogou.com','api.zhiyin.sogou.com',
        'master-proxy.shouji.sogou.com','srv.android.shouji.sogou.com','torrent.ie.sogou.com',
        'pro.cdn.ime.sogou.com','ime.gtimg.com','h5api.sginput.qq.com','push-service-pc.sginput.qq.com',
        'sec.sginput.qq.com','sj.qq.com','snowflake.qq.com','rdelivery.qq.com','6ts.qq.com','ts.qq.com',
        'oth.eve.mdt.qq.com','trace.inlong.qq.com','qqdata.ab.qq.com','tqqdata.ab.qq.com',
        'beacon.qq.com','report.beacon.qq.com','galileotelemetry.tencent.com'
    )
    if($BlockDictDomains){ $domains += @('pinyin.sogou.com','get.sogou.com','download.ime.sogou.com') }
    $content = Get-Content -LiteralPath $hosts -Raw -ErrorAction SilentlyContinue
    if($content -match 'sogou-debloat-start'){
        Sk 'hosts 拦截已存在'
    } else {
        if($DryRun){ Pl ('将写入 ' + $domains.Count + ' 个域名拦截到 hosts') }
        else {
            Copy-Item -LiteralPath $hosts -Destination (Join-Path $Script:BackupDir 'hosts.bak') -Force
            $block = "`r`n# sogou-debloat-start`r`n"
            foreach($d in $domains){ $block += ('0.0.0.0 ' + $d + "`r`n") }
            $block += '# sogou-debloat-end' + "`r`n"
            Add-Content -LiteralPath $hosts -Value $block -Encoding ASCII
            Save-Record 'hosts' $hosts (Join-Path $Script:BackupDir 'hosts.bak')
            Ok ('已写入 hosts 拦截 (' + $domains.Count + ' 个域名)')
        }
    }
    if(-not $DryRun){ & ipconfig.exe /flushdns 2>$null | Out-Null }
}

function Do-Track($R){
    Reg-Del 'HKCU:\Software\SogouInput.ppup'
    Reg-Del 'HKCU:\Software\SogouInput.tc'
    Reg-Del 'HKCU:\Software\SogouInput\KernelReport'
    Reg-Del 'HKCU:\Software\SogouInput\LongConn'
    Reg-Del 'HKCU:\Software\kdiskmgr_sogou'
    Reg-Del 'HKCU:\Software\kwallpaper_sogou'
    Reg-Del 'HKCU:\Software\kzip_sogou'
}

function Do-Logs($R){
    $py = Get-PyDir
    Clear-Only (Join-Path $py 'LOG')
    Clear-Only (Join-Path $py 'logs')
    Clear-Only (Join-Path $py 'Temp')
    Clear-Only (Join-Path $py 'SGCefCache')
    Clear-AndLock (Join-Path $py 'Popup')
    Clear-AndLock (Join-Path $py 'Components\SmartInfo')
    Truncate-AndLock (Join-Path $py 'Components\SuggList.ini')
    Clear-Only (Join-Path $env:ProgramData 'SogouInput\SGSysToast')
    Clear-Only (Join-Path $env:ProgramData 'SogouInput\SGBizConfig')
    Clear-Only (Join-Path $env:ProgramData 'SogouInput\ShiplyUpdate')
}

function Do-Startup($R){
    foreach($hive in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Run','HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run')){
        $props = Get-ItemProperty -Path $hive -ErrorAction SilentlyContinue
        if(-not $props){ continue }
        foreach($p in $props.PSObject.Properties){
            if($p.Name -like 'PS*'){ continue }
            $val = [string]$p.Value
            if($val -match 'Sogou|sogou|SGAI|SGMyInput'){
                if($DryRun){ Pl ('将移除自启动: ' + $hive + ' -> ' + $p.Name) }
                else {
                    $bak = Join-Path $Script:BackupDir ('reg\run_' + $p.Name + '.reg')
                    New-Item -ItemType Directory -Path (Split-Path $bak) -Force | Out-Null
                    & reg.exe export $hive $bak /y 2>$null | Out-Null
                    Remove-ItemProperty -Path $hive -Name $p.Name -Force -ErrorAction SilentlyContinue
                    Save-Record 'regdel' ($hive + '\' + $p.Name) $bak
                    Ok ('已移除自启动: ' + $p.Name)
                }
            }
        }
    }
    $tasks = & schtasks.exe /query /fo csv 2>$null | Select-String -Pattern 'sogou','SGAI'
    if($tasks){
        foreach($t in $tasks){
            $name = ($t.Line -split ',')[0].Trim('"')
            if($DryRun){ Pl ('将删除计划任务: ' + $name) }
            elseif($name){
                & schtasks.exe /delete /tn $name /f 2>$null | Out-Null
                Save-Record 'task' $name $null
                Ok ('已删除计划任务: ' + $name)
            }
        }
    } else { Sk '无搜狗相关计划任务' }
}

# ============ 商城/设置页资源补丁 (实验性) ============
function Find-Bytes([byte[]]$hay, [int]$start, [string]$needle){
    $enc = [Text.Encoding]::GetEncoding(28591)
    $hs = $enc.GetString($hay)
    return $hs.IndexOf($needle, $start)
}
function Patch-Nav([string]$t){
    # 只给目标 Option 自身加 visible="false" (duilib Option 支持隐藏, 不动父级避免错位)
    $targets = @('cmpx_nav_person','cmpx_nav_skincenter','cmpx_nav_crossdevice','cmpx_nav_custom','cmpx_nav_recommend')
    foreach($n in $targets){
        $pat = '(<Option(?![^>]*visible=)[^>]*name="' + $n + '")'
        $t = [regex]::Replace($t, $pat, '$1 visible="false"', 1)
    }
    # 智能服务: 同时隐藏包装层(带 name 的 VBoxOption)
    $t = [regex]::Replace($t, '(<VBoxOption(?![^>]*visible=)[^>]*name="cmpx_nav_smart_layout")', '$1 visible="false"', 1)
    return $t
}
function Patch-Page([string]$t){
    $re = New-Object regex '(?s)<VerticalLayout(?![^>]*visible=)'
    $out = $re.Replace($t, '<VerticalLayout visible="false"', 1)
    return $out
}
function Do-Mall($R){
    $exe = Join-Path $R.Ver 'SGMyInput.exe'
    if(-not (Test-Path -LiteralPath $exe)){ Sk 'SGMyInput.exe 不存在'; return }
    if($DryRun){ Pl '将尝试隐藏商城/无用设置页入口 (资源级, 实验性)'; return }
    $bk = Join-Path $Script:BackupDir 'files\SGMyInput.exe.before-mallpatch'
    New-Item -ItemType Directory -Path (Split-Path $bk) -Force | Out-Null
    Copy-Item -LiteralPath $exe -Destination $bk -Force
    $bytes = [IO.File]::ReadAllBytes($exe)
    $pages = @('personpage.xml','customServicePage.xml','smartServicePage.xml','crossDevicePage.xml','set/setrecommend.xml','set/setaccountpage.xml','set/setAccountPage.xml')
    $patched = 0
    $offset = 0
    $pkLocal = [string][char]0x50 + [char]0x4B + [char]0x03 + [char]0x04
    $pkEocd  = [string][char]0x50 + [char]0x4B + [char]0x05 + [char]0x06
    # 遍历所有 EOCD 候选, 用 ZipArchive 试读校验(真包才能解析出目录)
    $pkEocd  = [string][char]0x50 + [char]0x4B + [char]0x05 + [char]0x06
    $eocdList = @()
    $p = 0
    while($true){
        $p = Find-Bytes $bytes $p $pkEocd
        if($p -lt 0){ break }
        if(($p + 22) -le $bytes.Length){
            $cdSize = [BitConverter]::ToUInt32($bytes, $p + 12)
            $cdOff  = [BitConverter]::ToUInt32($bytes, $p + 16)
            $cmtLen = [BitConverter]::ToUInt16($bytes, $p + 20)
            if($cmtLen -le 512){
                $start = [long]$p - [long]$cdSize - [long]$cdOff
                if($start -ge 0 -and $start -lt $p){
                    $eocdList += @{ Start=[int]$start; End=[int]$p }
                }
            }
        }
        $p = $p + 1
    }
    Say ('    扫描到 ' + $eocdList.Count + ' 个 EOCD 候选, 逐个校验...') 'DarkGray'
    $offset = 0
    foreach($cand in $eocdList){
        $idx = [int]$cand.Start
        if($idx -lt $offset){ continue }
        $eocd = [int]$cand.End
        $commentLen = [BitConverter]::ToUInt16($bytes, $eocd + 20)
        $zipLen = $eocd + 22 + $commentLen - $idx
        if($zipLen -le 0 -or ($idx + $zipLen) -gt $bytes.Length){ continue }
        $sliceMagic = [string][char]$bytes[$idx] + [char]$bytes[$idx+1] + [char]$bytes[$idx+2] + [char]$bytes[$idx+3]
        if($sliceMagic -ne $pkLocal){ continue }
        $slice = New-Object byte[] $zipLen
        [Array]::Copy($bytes, $idx, $slice, 0, $zipLen)
        $ms = New-Object IO.MemoryStream(,$slice)
        $zip = $null
        try { $zip = New-Object IO.Compression.ZipArchive($ms, [IO.Compression.ZipArchiveMode]::Read) } catch { $ms.Dispose(); continue }
        $nav = $zip.GetEntry('cmxp_nav_menu.xml')
        $already = $false
        if($nav){
            $sr = New-Object IO.StreamReader($nav.Open())
            $navText = $sr.ReadToEnd(); $sr.Close()
            if($navText -match 'visible="false"'){ $already = $true }
        }
        if(-not $nav -or $already){
            $zip.Dispose(); $ms.Dispose()
            if($already){ Sk '商城入口已是隐藏状态' }
            continue
        }
        Say ('    发现布局资源包 @0x' + $idx.ToString('X') + ' (' + $zipLen + ' 字节), 开始隐藏商城/无用入口...') 'DarkGray'
        # 收集原始条目顺序
        $entryNames = @()
        foreach($e in $zip.Entries){ $entryNames += $e.FullName }
        # 读出全部条目数据(先在内存缓存, 供迭代重建复用)
        $entryData = @{}
        foreach($e in $zip.Entries){
            if($e.FullName.EndsWith('/')){ $entryData[$e.FullName] = $null; continue }
            $es = $e.Open(); $mem = New-Object IO.MemoryStream; $es.CopyTo($mem); $es.Close()
            $d = $mem.ToArray(); $mem.Dispose()
            if($e.FullName -eq 'cmxp_nav_menu.xml'){
                $d = [Text.Encoding]::UTF8.GetBytes((Patch-Nav ([Text.Encoding]::UTF8.GetString($d))))
            } elseif($pages -contains $e.FullName){
                $d = [Text.Encoding]::UTF8.GetBytes((Patch-Page ([Text.Encoding]::UTF8.GetString($d))))
            }
            $entryData[$e.FullName] = $d
        }
        $zip.Dispose(); $ms.Dispose()
        # 迭代重建直到正好等于原始长度(填充条目调整)
        $padSize = 0
        $newZip = $null
        $okBuild = $false
        for($iter = 1; $iter -le 6; $iter++){
            $oMs = New-Object IO.MemoryStream
            $oZip = New-Object IO.Compression.ZipArchive($oMs, [IO.Compression.ZipArchiveMode]::Create)
            foreach($n in $entryNames){
                if($entryData[$n] -eq $null -and $entryData.ContainsKey($n)){ $oZip.CreateEntry($n) | Out-Null; continue }
                $d = $entryData[$n]
                if($d -eq $null){ continue }
                $ne = $oZip.CreateEntry($n, [IO.Compression.CompressionLevel]::Optimal)
                $ns = $ne.Open(); $ns.Write($d, 0, $d.Length); $ns.Close()
            }
            if($padSize -gt 0){
                $pe = $oZip.CreateEntry('zz_padding.bin', [IO.Compression.CompressionLevel]::NoCompression)
                $ps = $pe.Open(); $z = New-Object byte[] $padSize; $ps.Write($z, 0, $padSize); $ps.Close()
            }
            $oZip.Dispose()
            $cand = $oMs.ToArray()
            $oMs.Dispose()
            if($cand.Length -eq $zipLen){ $newZip = $cand; $okBuild = $true; break }
            if($cand.Length -gt $zipLen){
                $over = $cand.Length - $zipLen
                if($padSize - $over -lt 0){
                    if($iter -eq 1){ break }
                    $padSize = [Math]::Max(0, $padSize - $over)
                } else { $padSize = $padSize - $over }
            } else {
                $padSize = $padSize + ($zipLen - $cand.Length)
            }
        }
        if(-not $okBuild){
            Wr ('资源包无法精确重建 (需要 ' + $zipLen + ' 字节), 跳过此包')
            continue
        }
        $fs = [IO.File]::Open($exe, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite)
        $fs.Seek($idx, [IO.SeekOrigin]::Begin) | Out-Null
        $fs.Write($newZip, 0, $newZip.Length)
        $fs.Close()
        $patched++
    }
    if($patched -gt 0){
        # PE 完整性验证
        Add-Type -MemberDefinition '[DllImport("kernel32.dll",SetLastError=true)] public static extern IntPtr LoadLibraryEx(string f, IntPtr h, uint flags);' -Name K -Namespace MallPatch -ErrorAction SilentlyContinue
        $h = [MallPatch.K]::LoadLibraryEx($exe, [IntPtr]::Zero, 0x20)
        if($h -eq [IntPtr]::Zero){
            Copy-Item -LiteralPath $bk -Destination $exe -Force
            Wr '补丁后 PE 验证失败, 已自动回滚!'
        } else {
            Save-Record 'mall' $exe $bk
            Ok ('已隐藏商城/无用入口 (' + $patched + ' 个资源包), PE 验证通过')
        }
    } else {
        Sk '未发现可修补的布局资源包 (版本可能不同, 已跳过)'
    }
}

# ============ 项目调度 ============
$Script:ItemDefs = [ordered]@{
    'ads'        = '广告/推广弹窗进程'
    'update'     = '升级程序+升级服务'
    'crash'      = '崩溃上报程序'
    'ai'         = 'AI助手浏览器(116MB)+渲染器'
    'telemetry'  = '遥测/上报 DLL'
    'components' = '营销组件目录+开关'
    'login'      = '登录/账户痕迹'
    'mall'       = '商城/无用设置页入口(实验性!默认不执行)'
    'hosts'      = '域名拦截(保留词库更新)'
    'track'      = '追踪/状态注册表键'
    'logs'       = '日志/缓存清理'
    'startup'    = '自启动面清理'
}

function Invoke-Item2($key, $R){
    switch($key){
        'ads'        { Do-Ads $R }
        'update'     { Do-Update $R }
        'crash'      { Do-Crash $R }
        'ai'         { Do-AI $R }
        'telemetry'  { Do-Telemetry $R }
        'components' { Do-Components $R }
        'login'      { Do-Login $R }
        'mall'       { Do-Mall $R }
        'hosts'      { Do-Hosts $R }
        'track'      { Do-Track $R }
        'logs'       { Do-Logs $R }
        'startup'    { Do-Startup $R }
        default      { Wr ('未知项目: ' + $key) }
    }
}

# ============ 还原 ============
function Invoke-Restore {
    $root = $BackupRoot
    if(-not $root){ $root = Join-Path $env:SystemDrive 'SogouDebloatBackup' }
    $mf = Join-Path $root 'manifest.jsonl'
    if(-not (Test-Path -LiteralPath $mf)){ Wr ('未找到备份清单: ' + $mf); return }
    Say ('从备份还原: ' + $mf) 'Cyan'
    $lines = Get-Content -LiteralPath $mf | Where-Object { $_.Trim() -ne '' }
    [array]::Reverse($lines)
    foreach($ln in $lines){
        $r = $ln | ConvertFrom-Json
        switch($r.action){
            'stub' {
                if($r.backup -and (Test-Path -LiteralPath $r.backup)){
                    Remove-Deny $r.target
                    if(Test-Path -LiteralPath $r.target){ Remove-Item -LiteralPath $r.target -Recurse -Force -ErrorAction SilentlyContinue }
                    Move-Item -LiteralPath $r.backup -Destination $r.target -Force -ErrorAction SilentlyContinue
                    Ok ('还原文件: ' + (Split-Path -Leaf $r.target))
                }
            }
            'move' {
                if($r.backup -and (Test-Path -LiteralPath $r.backup)){
                    Move-Item -LiteralPath $r.backup -Destination $r.target -Force -ErrorAction SilentlyContinue
                    Ok ('还原文件: ' + (Split-Path -Leaf $r.target))
                }
            }
            'clear' {
                if($r.backup -and (Test-Path -LiteralPath $r.backup)){
                    Remove-Deny $r.target
                    if(Test-Path -LiteralPath $r.target){ Remove-Item -LiteralPath $r.target -Recurse -Force -ErrorAction SilentlyContinue }
                    Move-Item -LiteralPath $r.backup -Destination $r.target -Force -ErrorAction SilentlyContinue
                    Ok ('还原目录: ' + (Split-Path -Leaf $r.target))
                } else {
                    Remove-Deny $r.target
                    Ok ('解除目录锁定: ' + (Split-Path -Leaf $r.target))
                }
            }
            'hosts' {
                $h = Join-Path $env:SystemRoot 'System32\drivers\etc\hosts'
                $c = Get-Content -LiteralPath $h -Raw -ErrorAction SilentlyContinue
                $c = [regex]::Replace($c, '(?ms)\r?\n?# sogou-debloat-start.*?# sogou-debloat-end\r?\n?', "`r`n")
                Set-Content -LiteralPath $h -Value $c -Encoding ASCII
                & ipconfig.exe /flushdns 2>$null | Out-Null
                Ok '已移除 hosts 拦截段'
            }
            'regdel' {
                if($r.backup -and (Test-Path -LiteralPath $r.backup)){
                    & reg.exe import $r.backup 2>$null | Out-Null
                    Ok ('已还原注册表: ' + $r.target)
                }
            }
            'svc' {
                $st = 'auto'
                if($r.backup){ $st = $r.backup.ToLower() }
                & sc.exe config $r.target start= $st 2>$null | Out-Null
                Ok ('已还原服务启动类型: ' + $r.target + ' -> ' + $st)
            }
            'task' { Sk ('计划任务需手动恢复: ' + $r.target) }
        }
    }
    Say '还原完成。建议重启相关应用使改动生效。' 'Green'
}

# ============ 主流程 ============
Say ''
Say '=====================================================' 'Cyan'
Say '  搜狗输入法 去广告/去推广/去遥测 通用脚本 v1.0' 'Cyan'
Say '=====================================================' 'Cyan'

if(-not (Test-Admin)){
    Wr '需要管理员权限! 请右键以管理员身份运行 PowerShell 后重试。'
    exit 1
}

if($Restore){
    Invoke-Restore
    exit 0
}

$R = Find-Sogou
if(-not $R){
    Wr '未找到搜狗输入法安装目录。可用 -InstallDir 手动指定。'
    exit 1
}
Say ('安装目录: ' + $R.Root)
Say ('当前版本: ' + (Split-Path -Leaf $R.Ver))
if($DryRun){ Say '[预演模式] 只报告不修改' 'Yellow' }

# 选择项目
$keys = @($Script:ItemDefs.Keys)
if($All){
    # mall 为实验性项目, -All 默认不含, 需显式 -Remove mall 才执行
    $sel = @($keys | Where-Object { $_ -ne 'mall' })
    Say '注意: -All 不包含实验性项目 mall (需显式指定 -Remove mall)' 'Yellow'
}
elseif($Remove.Count -gt 0){
    $sel = @()
    foreach($r0 in $Remove){
        foreach($piece in ($r0 -split ',')){
            $p = $piece.Trim().ToLower()
            if($keys -contains $p){ $sel += $p }
            elseif($p -match '^\d+$'){ $i=[int]$p; if($i -ge 1 -and $i -le $keys.Count){ $sel += $keys[$i-1] } }
        }
    }
    $sel = @($sel | Select-Object -Unique)
}
else {
    Say ''
    Say '可选项目:'
    for($i=0; $i -lt $keys.Count; $i++){
        Say ('  [' + ($i+1) + '] ' + $keys[$i].PadRight(12) + $Script:ItemDefs[$keys[$i]])
    }
    Say ''
    Say '  all = 全部   none = 取消'
    $ans = Read-Host '请输入要执行的编号(逗号分隔, 如 1,2,5-8 或 all)'
    $ans = $ans.Trim().ToLower()
    if($ans -eq 'none' -or $ans -eq ''){ Say '已取消' 'Yellow'; exit 0 }
    if($ans -eq 'all'){ $sel = $keys }
    else {
        $sel = @()
        foreach($part in ($ans -split ',')){
            $p = $part.Trim()
            if($p -match '^(\d+)\s*-\s*(\d+)$'){
                for($j=[int]$Matches[1]; $j -le [int]$Matches[2]; $j++){
                    if($j -ge 1 -and $j -le $keys.Count){ $sel += $keys[$j-1] }
                }
            } elseif($p -match '^\d+$'){
                $j=[int]$p
                if($j -ge 1 -and $j -le $keys.Count){ $sel += $keys[$j-1] }
            }
        }
        $sel = @($sel | Select-Object -Unique)
    }
    if($sel.Count -eq 0){ Say '未选择任何项目, 退出' 'Yellow'; exit 0 }
    Say ''
    Say ('将执行: ' + ($sel -join ', ')) 'Yellow'
    $go = Read-Host '确认执行? (y/N)'
    if($go.Trim().ToLower() -ne 'y'){ Say '已取消' 'Yellow'; exit 0 }
}

# 初始化备份
if(-not $DryRun){
    $root = $BackupRoot
    if(-not $root){ $root = Join-Path $env:SystemDrive 'SogouDebloatBackup' }
    $Script:BackupDir = Join-Path $root ((Get-Date).ToString('yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Path $Script:BackupDir -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $Script:BackupDir 'files') -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $Script:BackupDir 'dirs') -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $Script:BackupDir 'reg') -Force | Out-Null
    $Script:Manifest = Join-Path $root 'manifest.jsonl'
    Say ('备份目录: ' + $Script:BackupDir) 'Green'
}

foreach($k in $sel){
    Hdr ($k + ' — ' + $Script:ItemDefs[$k])
    Invoke-Item2 $k $R
}

Say ''
Say '=====================================================' 'Cyan'
if($DryRun){ Say '预演完成 (未做任何修改)' 'Yellow' }
else {
    Say '执行完成' 'Green'
    Say ('备份与清单: ' + (Join-Path $Script:BackupDir '..')) 'Green'
    Say '如需还原: 运行本脚本加 -Restore' 'Green'
    Say '建议重启相关应用/输入法使改动生效' 'DarkGray'
}
