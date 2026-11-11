# Import boundary fixtures

These files are parsed as syntax only, never imported or executed. The legal tree admits R16 -> R02 and bootstrap -> R17. The illegal tree intentionally contains R16 -> R17 implementation import. pytest expects checker exit 1 and B01 for the illegal tree; therefore the normal suite passes only when the rejection works. These fixtures are excluded from lint targets because their unresolved/unused names are intentional.
