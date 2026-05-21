function pydocs --description "Open local Python 3.14 documentation in the default browser"
    set -l docs_dir "$HOME/.local/share/python-docs"
    if test -f "$docs_dir/index.html"
        xdg-open "$docs_dir/index.html"
    else
        echo "Python docs not found at $docs_dir" >&2
        return 1
    end
end
