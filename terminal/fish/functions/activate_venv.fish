function activate_venv
    set -l dir $PWD
    while test "$dir" != "/"
        for venv_dir in .venv venv
            set -l activate_script "$dir/$venv_dir/bin/activate.fish"
            if test -f "$activate_script"
                source "$activate_script"
                echo "Activated $activate_script"
                return 0
            end
        end
        set dir (dirname "$dir")
    end
    echo "No virtual environment found" >&2
    return 1
end
