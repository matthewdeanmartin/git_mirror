# Design goals

Not specifically TODO items, but guidance for making TODO items.

## Differentiating features
- safety (dry run, lots of output, confirmations)
- ease of use (menu, init, q&a config)

## Who to please/Degree of Opinionatedness
- Just two hosts, github, gitlab
- Python concerns (pypi publish and poetry update)
- Support windows, linux, mac

## Out of scope features 
- Try not to overlap with `gh` and `glab`'s feature sets.

## Extension points
- Do support pluggy
- Don't support running arbitrary code (e.g. a yaml file full of bash to be run on each repo)

