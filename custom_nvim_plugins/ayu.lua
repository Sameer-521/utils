return {
  {
    "Shatur/neovim-ayu",
    name = "ayu",
    priority = 1000,
    opts = {
      mirage = false, -- Set to true if you want the lighter 'mirage' variant instead of deep dark
      overrides = {}, -- You can add custom overrides here if needed
    },
    config = function(_, opts)
      -- Ayu requires a specific global variable to set the variant before loading
      -- Options are: 'light', 'mirage', or 'dark'
      vim.g.ayucolor = "dark"
      require("ayu").setup(opts)
    end,
  },

  -- Configure LazyVim to load ayu
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "ayu",
    },
  },
}
