# A Dotfile Link Farm Manager

[Example Dotfile Repo](https://github.com/NonLogicalDev/conf.dotfiles)

## Example Usage:

```
git clone https://github.com/NonLogicalDev/conf.dotfiles ~/.config/dotter
python3 -m pip install --user nl-dotter
dotter link
```

## Usage Output:

### Root Command:

```
usage: dotter [-h] {version,link,config} ...

A dotfile linker. This utility creates a link farm from a data root to users home directory.
It's intended use is to keep dotfiles neatly organized and separated by topics.

optional arguments:
  -h, --help            show this help message and exit

command:
  {version,link,config}
    version             print version and exit
    link                link dotfiles from $HOME/.config/dotter
    config              query configuration values
```

### Link Command:
```
usage: dotter link [-h] [--root ROOT_DIR] [--conf-dir CONF_DIR] [-c CATEGORY]
                   [-t TOPIC] [-f] [-d] [-b]

links files into the home directory from the data root.

optional arguments:
  -h, --help           show this help message and exit
  --root ROOT_DIR      Alternative root location (for testing configuration)
  --conf-dir CONF_DIR  Alternative configuration location (for testing configuration)
  -c CATEGORY          Specify a category to sync (defaults to common)
  -t TOPIC             Specify a topic to sync (inside a category)
  -f                   Force execution
  -d                   Dry run current setup
  -b                   Backup files and place new ones in place, appends ".backup"
```
