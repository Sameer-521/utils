return {
    {
        "neovim/nvim-lspconfig",
        opts = {
            servers = {
                basedpyright = {
                    settings = {
                        basedpyright = {
                            analysis = {
                                autoSearchPaths = true,
                                autoImportCompletions = true,
                                diagnosticMode = "openFilesOnly",
                                indexing = false,
                            },
                        },
                    },
                },
            },
        },
    },
}
