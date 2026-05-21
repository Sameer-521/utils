function ds
    set -l proc deepseek-tui

    if pgrep -x $proc > /dev/null
        set -l pid (pgrep -x $proc)
        if command -v wmctrl > /dev/null
            for wid in (wmctrl -lp | awk -v p="$pid" '$3 == p {print $1}')
                wmctrl -i -a "$wid" 2>/dev/null
                break
            end
        end
    else
        ghostty -e $proc &
    end
end
