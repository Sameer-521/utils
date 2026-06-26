set -g fish_greeting
set -gx PATH $PATH /usr/local/go/bin

if status is-interactive
    # Commands to run in interactive sessions can go here
    alias av activate_venv
end

if not contains "$TERM_PROGRAM" zed
    starship init fish | source
end
