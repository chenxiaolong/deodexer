#!/usr/local/bin/tini /bin/bash

set -eu

uid=$(id -u)
gid=$(id -g)

if [[ "${uid}" -eq 0 ]] && [[ "${gid}" -eq 0 ]]; then
    uid=${USER_ID:-$(stat -c '%u' .)}
    gid=${GROUP_ID:-$(stat -c '%g' .)}

    if ! getent group "${gid}" >/dev/null; then
        groupadd -g "${gid}" limiteduser
    else
        echo >&2 "WARNING WARNING WARNING"
        echo >&2 "GID ${gid} already exists"
        echo >&2 "WARNING WARNING WARNING"
    fi

    if ! getent passwd "${uid}" >/dev/null; then
        useradd -s /bin/bash -u "${uid}" -g "${gid}" -M limiteduser
    else
        echo >&2 "WARNING WARNING WARNING"
        echo >&2 "UID ${uid} already exists"
        echo >&2 "WARNING WARNING WARNING"
    fi

    export HOME=$(getent passwd limiteduser | cut -d: -f6)

    exec gosu "${uid}:${gid}" "${@}"
else
    echo >&2 "WARNING WARNING WARNING"
    echo >&2 "Skipping user creation because container is not running as root"
    echo >&2 "Expected (uid=0, gid=0), but have (uid=${uid}, gid=${gid})"
    echo >&2 "WARNING WARNING WARNING"

    exec "${@}"
fi
