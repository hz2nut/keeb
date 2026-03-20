#!/bin/bash     
real=`realpath $0`
path=`dirname $real`

function link_file {
    src=$path/$1
    dest=$2
    ln -s -f $src $dest
}

mkdir -p ~/.local/bin
mkdir -p ~/.vim/plugin

link_file bin/optimize.py ~/.local/bin/keeboptimize
link_file bin/edit.sh ~/.local/bin/keebedit
link_file bin/build.sh ~/.local/bin/keebuild
link_file mappings.vim ~/.vim/plugin/keebmappings.vim
