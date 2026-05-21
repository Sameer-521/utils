function abort_destructive_commands --on-event fish_preexec
    # Convert the command to lowercase for consistent matching
    set -l cmd (string lower $argv[1])

    # Define dangerous patterns using regular expressions
    # This catches variations like: rm -rf /, sudo rm -fr /*, rm -R /etc, etc.
    if string match -r 'rm\s+-[a-z]*[rfR][a-z]*\s+(/\*|/|/etc|/usr|/var|/home)' "$cmd"
        echo (set_color red --bold)"[BLOCK] Destructive command detected!"(set_color normal)
        echo (set_color yellow)"You attempted to run:" (set_color normal)"$argv[1]"
        echo "If you absolutely must run this, use an explicit absolute path or temporarily disable this function."

        # Emulate a command failure to halt execution
        return 1
    end
end
