return {
    "stevearc/conform.nvim",
    opts = {
        formatters_by_ft = {
            -- Ensure conform targets prettier for css files
            css = { "prettier" },
        },
        formatters = {
            prettier = {
                -- This forces prettier to treat any custom extensions mapped to CSS (like .tcss)
                -- as regular css, overriding its internal filename checks.
                prepend_args = { "--parser", "css" },
            },
        },
    },
}
