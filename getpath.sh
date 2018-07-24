#!/bin/bash
function getpath() {
    # 获取脚本所在目录
    SOURCE=$1
    while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
        DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
        SOURCE="$(readlink "$SOURCE")"
        [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
    done
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    echo $DIR
}

echo $(getpath $1)
