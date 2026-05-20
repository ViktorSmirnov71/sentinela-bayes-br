# Notebooks

Numbered exploratory notebooks. Convention:

    `NN-author-shortname.ipynb`

where `NN` is a zero-padded sequence and `author` is the GitHub handle of the
person who created it. Notebooks are exploratory by definition — anything that
needs to be reproducible is promoted into `src/` and an `experiments/` config.

Do not commit notebook output cells without reviewing them for embedded data
that should be loaded from `data/raw/` instead.
