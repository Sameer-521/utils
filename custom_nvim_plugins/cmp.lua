return {
    "hrsh7th/nvim-cmp",
    opts = function(_, opts)
    local cmp = require("cmp")

    opts.mapping = vim.tbl_extend("force", opts.mapping, {
        ["<Down>"] = cmp.mapping.select_next_item({ behavior = cmp.SelectBehavior.Select }),
                                  ["<Up>"] = cmp.mapping.select_prev_item({ behavior = cmp.SelectBehavior.Select }),
    })

    return opts
    end,
}
