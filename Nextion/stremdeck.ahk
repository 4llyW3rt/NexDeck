SetTitleMatchMode, 2

; --- YOUTUBE KONTROLÜ (F21) ---
F21::
if WinExist("YouTube")
{
    WinActivate, YouTube
}
else
{
    Run, https://www.youtube.com
}
return

; --- KICK KONTROLÜ (F22) ---
F22::
if WinExist("Kick")
{
    WinActivate, Kick
}
else
{
    Run, https://kick.com/dashboard/stream
}
return